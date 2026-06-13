"""All-real-firmware groups: every device (core AND nodes) runs the C++
ConnectionManager. Mirrors the scenarios of test_cpp_protocol.py, proving
the node role implemented in firmware matches the Python NodeDevice spec."""
import pytest

heard_sim = pytest.importorskip(
    "heard_sim", reason="heard_sim not built — run cmake first (see README)"
)

from radio import SimRadio
from config import TICK_S

CM_REQUEST_INTERVAL_MS = 10_000  # mirrors core/include/config.h
INTERVAL_TICKS = int(CM_REQUEST_INTERVAL_MS / (TICK_S * 1000))

LAT = 44.0
LON = 12.0


def make_cpp_group(node_offsets_m, d_reliable=800.0, d_max=900.0, seed=42):
    """Core (id 0) plus C++ nodes, offset northward in metres."""
    devices = []
    for i, off in enumerate([0.0] + list(node_offsets_m)):
        dev = heard_sim.SimDevice(i)
        dev.set_position(LAT + off / 111_000, LON)
        devices.append(dev)
    radio = SimRadio(d_reliable=d_reliable, d_max=d_max, rng_seed=seed)
    return devices, radio


def run(devices, radio, n_ticks):
    for tick in range(n_ticks):
        for dev in devices:
            dev.step(int(tick * TICK_S * 1000))
        radio.tick(devices, tick)


class TestNodeRole:
    def test_nodes_do_not_start_rounds(self):
        """Without a core present, C++ nodes must stay silent: only the
        core role (device id 0) initiates polling rounds."""
        devices = []
        for i in (1, 2):
            dev = heard_sim.SimDevice(i)
            dev.set_position(LAT + i * 0.001, LON)
            devices.append(dev)
        radio = SimRadio(d_reliable=800.0, d_max=900.0, rng_seed=42)
        run(devices, radio, INTERVAL_TICKS * 3)
        assert len(radio.events) == 0

    def test_node_answers_a_round(self):
        devices, radio = make_cpp_group([300])
        run(devices, radio, INTERVAL_TICKS)
        known = devices[0].get_known_positions()
        assert 1 in known
        assert not devices[0].is_request_in_progress()

    def test_known_position_matches_gps(self):
        devices, radio = make_cpp_group([300])
        run(devices, radio, INTERVAL_TICKS)
        lat, lon, _ = devices[0].get_known_positions()[1]
        assert lat == pytest.approx(LAT + 300 / 111_000, abs=1e-4)
        assert lon == pytest.approx(LON, abs=1e-4)


class TestAllCppMultiHop:
    def test_two_hop_relay(self):
        """Core ↔ far node impossible directly (1400 m > d_max 900 m):
        the middle C++ node must relay REQ out, WAIT-announce, POS back."""
        devices, radio = make_cpp_group([700, 1400])
        run(devices, radio, INTERVAL_TICKS * 3)

        known = devices[0].get_known_positions()
        assert 2 in known, (
            f"far node never reached the core; known={sorted(known.keys())}"
        )

    def test_two_hop_round_completes(self):
        devices, radio = make_cpp_group([700, 1400])
        run(devices, radio, INTERVAL_TICKS)
        assert not devices[0].is_request_in_progress()

    def test_three_hop_chain(self):
        devices, radio = make_cpp_group([700, 1400, 2100])
        run(devices, radio, INTERVAL_TICKS * 3)

        known = devices[0].get_known_positions()
        assert {1, 2, 3} <= set(known.keys()), (
            f"chain incomplete; known={sorted(known.keys())}"
        )

    def test_rounds_repeat_with_relays(self):
        """Relay-only nodes must keep answering in later rounds (round
        detection by time gap, not by hearing the core directly)."""
        devices, radio = make_cpp_group([700, 1400])
        run(devices, radio, INTERVAL_TICKS * 3)

        pos_from_far = sorted({ev.tick for ev in radio.events
                               if ev.msg_kind == "POS" and ev.sender_id == 2
                               and not ev.overheard})
        rounds_with_far_pos = {t // INTERVAL_TICKS for t in pos_from_far}
        assert len(rounds_with_far_pos) >= 2, (
            f"far node responded only in rounds {rounds_with_far_pos}"
        )
