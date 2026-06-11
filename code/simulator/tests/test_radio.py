"""Tests for SimRadio and NodeDevice message routing."""
import pytest
from radio import SimRadio, LinkEvent
from node_device import NodeDevice


class TestSimRadioLinkProb:
    def test_within_reliable(self, radio):
        assert radio.link_prob(0.0)   == pytest.approx(1.0)
        assert radio.link_prob(800.0) == pytest.approx(1.0)

    def test_beyond_max(self, radio):
        assert radio.link_prob(3000.0) == pytest.approx(0.0)
        assert radio.link_prob(5000.0) == pytest.approx(0.0)

    def test_midpoint(self, radio):
        mid = (800.0 + 3000.0) / 2
        p = radio.link_prob(mid)
        assert 0.0 < p < 1.0

    def test_monotone_decreasing(self, radio):
        probs = [radio.link_prob(d) for d in range(0, 3200, 100)]
        assert all(b <= a for a, b in zip(probs, probs[1:]))


class TestSimRadioTick:
    def _make_nodes(self, n: int, lat_offset: float = 0.0):
        return [NodeDevice(i, 44.12 + i * lat_offset, 12.24) for i in range(n)]

    def test_broadcast_delivered_when_close(self):
        radio = SimRadio(d_reliable=800.0, d_max=3000.0, rng_seed=0)
        # Two nodes 100 m apart — all messages should deliver
        a = NodeDevice(0, 44.120, 12.240)
        b = NodeDevice(1, 44.121, 12.240)  # ~111 m north
        a.inject_message("", -1)  # ensure inbox is empty
        a._outbox.append((-1, "REQ|0|"))   # manual outbox
        radio.tick([a, b], tick_num=0)
        assert radio.stats["delivered"] >= 1

    def test_broadcast_dropped_when_far(self):
        radio = SimRadio(d_reliable=800.0, d_max=3000.0, rng_seed=0)
        a = NodeDevice(0, 44.120, 12.240)
        b = NodeDevice(1, 44.120, 12.600)  # >30 km away
        a._outbox.append((-1, "REQ|0|"))
        radio.tick([a, b], tick_num=0)
        assert radio.stats["dropped"] >= 1

    def test_events_logged(self):
        radio = SimRadio(d_reliable=800.0, d_max=3000.0, rng_seed=42)
        a = NodeDevice(0, 44.120, 12.240)
        b = NodeDevice(1, 44.121, 12.240)
        a._outbox.append((-1, "POS|0,44.120,12.240"))
        radio.tick([a, b], tick_num=5)
        assert len(radio.events) >= 1
        ev = radio.events[-1]
        assert ev.sender_id == 0
        assert ev.tick == 5

    def test_unicast_reaches_target(self):
        radio = SimRadio(d_reliable=800.0, d_max=3000.0, rng_seed=1)
        a = NodeDevice(0, 44.120, 12.240)
        b = NodeDevice(1, 44.121, 12.240)
        # Force delivery by overriding link_prob temporarily
        original = radio.link_prob
        radio.link_prob = lambda _d: 1.0
        a._outbox.append((1, "WAIT|0"))
        radio.tick([a, b], tick_num=0)
        radio.link_prob = original
        assert len(b._inbox) == 1
        assert b._inbox[0] == ("WAIT|0", 0)


class TestNodeDevice:
    def test_relays_req(self):
        node = NodeDevice(1, 44.12, 12.24)
        node.inject_message("REQ|0|", sender_id=0)
        node.step(0)
        assert node.has_pending_out()
        dest, msg = node.pop_pending_out()
        assert msg.startswith("REQ|0,1|")

    def test_pos_delayed(self):
        node = NodeDevice(2, 44.12, 12.24)
        node.inject_message("REQ|0|", sender_id=0)
        node.step(0)

        # Drain the forwarded REQ
        while node.has_pending_out():
            node.pop_pending_out()

        # POS should not arrive for POS_DELAY_TICKS steps
        for _ in range(NodeDevice.POS_DELAY_TICKS - 1):
            node.step(0)
            assert not node.has_pending_out()

        node.step(0)
        assert node.has_pending_out()
        _, msg = node.pop_pending_out()
        assert msg.startswith("POS|2,")

    def test_no_duplicate_relay(self):
        node = NodeDevice(3, 44.12, 12.24)
        node.inject_message("REQ|0|", sender_id=0)
        node.inject_message("REQ|0|", sender_id=0)  # duplicate
        node.step(0)
        msgs = []
        while node.has_pending_out():
            msgs.append(node.pop_pending_out())
        # Only one forwarded REQ (duplicate suppressed)
        req_msgs = [m for _, m in msgs if m.startswith("REQ|0,3|")]
        assert len(req_msgs) == 1

    def test_ignores_own_hop(self):
        node = NodeDevice(4, 44.12, 12.24)
        node.inject_message("REQ|0,4|", sender_id=0)  # already has node 4
        node.step(0)
        assert not node.has_pending_out()
