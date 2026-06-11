"""Protocol-level integration tests (no C++ required — uses NodeDevice only)."""
import pytest
from node_device import NodeDevice
from radio import SimRadio


def run_ticks(devices, radio, n_ticks: int) -> None:
    for tick in range(n_ticks):
        for dev in devices:
            dev.step(tick)
        radio.tick(devices, tick)


class TestProtocolFlowPythonOnly:
    """Full REQ→WAIT→POS cycle simulated in pure Python."""

    def _make_group(self, n_nodes: int = 3, seed: int = 1):
        radio = SimRadio(d_reliable=800.0, d_max=3000.0, rng_seed=seed)
        # Core is node 0; others are nodes 1..n
        devices = [NodeDevice(i, 44.12 + i * 0.001, 12.24) for i in range(n_nodes + 1)]
        return devices, radio

    def test_req_propagates_to_all_nodes(self):
        devices, radio = self._make_group(3)
        # Manually inject REQ from "core" device 0
        for dev in devices[1:]:
            dev.inject_message("REQ|0|", sender_id=0)

        run_ticks(devices, radio, NodeDevice.POS_DELAY_TICKS + 5)

        # Check that each node broadcast a forwarded REQ
        forwarded = [ev for ev in radio.events if ev.msg_kind == "REQ"]
        assert len(forwarded) >= 3   # one per node (3 nodes)

    def test_pos_messages_sent_after_delay(self):
        devices, radio = self._make_group(2)
        for dev in devices[1:]:
            dev.inject_message("REQ|0|", sender_id=0)

        run_ticks(devices, radio, NodeDevice.POS_DELAY_TICKS + 5)

        pos_events = [ev for ev in radio.events if ev.msg_kind == "POS"]
        assert len(pos_events) >= 2   # at least one per node (may be more due to delivery)

    def test_stats_accumulate(self):
        devices, radio = self._make_group(4)
        for dev in devices[1:]:
            dev.inject_message("REQ|0|", sender_id=0)

        run_ticks(devices, radio, 20)

        assert radio.stats["sent"] > 0
        assert radio.stats["delivered"] + radio.stats["dropped"] == radio.stats["sent"]

    def test_delivery_rate_close_devices(self):
        radio = SimRadio(d_reliable=800.0, d_max=3000.0, rng_seed=7)
        # All devices within 50 m of each other — delivery rate should be high
        devices = [NodeDevice(i, 44.12, 12.24) for i in range(5)]
        for dev in devices[1:]:
            dev.inject_message("REQ|0|", sender_id=0)
        run_ticks(devices, radio, 20)
        total = radio.stats["sent"]
        if total > 0:
            rate = radio.stats["delivered"] / total
            assert rate > 0.8

    def test_delivery_rate_far_devices(self):
        radio = SimRadio(d_reliable=800.0, d_max=3000.0, rng_seed=7)
        # Devices 2 km apart — delivery rate should decrease
        devices = [NodeDevice(i, 44.12 + i * 0.018, 12.24) for i in range(3)]
        for dev in devices[1:]:
            dev.inject_message("REQ|0|", sender_id=0)
        run_ticks(devices, radio, 20)
        total = radio.stats["sent"]
        if total > 0:
            rate = radio.stats["delivered"] / total
            assert rate < 1.0   # not all messages get through
