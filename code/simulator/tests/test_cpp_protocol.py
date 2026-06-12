"""Protocol regression tests against the real C++ ConnectionManager
(compiled into heard_sim via pybind11). Skipped when the module is absent."""
import pytest

heard_sim = pytest.importorskip(
    "heard_sim", reason="heard_sim not built — run cmake first (see README)"
)

from node_device import NodeDevice
from radio import SimRadio
from config import TICK_S

# Must mirror dispositivo_madre/include/config.h
CM_REQUEST_INTERVAL_MS = 10_000
CM_GLOBAL_TIMEOUT_MS = 30_000

INTERVAL_TICKS = int(CM_REQUEST_INTERVAL_MS / (TICK_S * 1000))
TIMEOUT_TICKS = int(CM_GLOBAL_TIMEOUT_MS / (TICK_S * 1000))

LAT = 44.0
LON = 12.0
DEG_PER_700M = 700 / 111_000


def make_group(node_offsets_m, d_reliable=800.0, d_max=900.0, seed=42):
    """Core at origin plus one NodeDevice per northward offset (metres)."""
    core = heard_sim.SimDevice(0)
    core.set_position(LAT, LON)
    devices = [core]
    for i, off in enumerate(node_offsets_m, start=1):
        devices.append(NodeDevice(i, LAT + off / 111_000, LON))
    radio = SimRadio(d_reliable=d_reliable, d_max=d_max, rng_seed=seed)
    return devices, radio


def run(devices, radio, n_ticks):
    for tick in range(n_ticks):
        for dev in devices:
            dev.step(int(tick * TICK_S * 1000))
        radio.tick(devices, tick)


def core_req_ticks(radio):
    return sorted({ev.tick for ev in radio.events
                   if ev.sender_id == 0 and ev.msg_kind == "REQ"})


class TestRequestInterval:
    def test_first_request_fires_immediately(self):
        devices, radio = make_group([300])
        run(devices, radio, 10)
        assert core_req_ticks(radio)[0] <= 2

    def test_requests_repeat_at_configured_interval(self):
        """Pins CM_REQUEST_INTERVAL_MS: REQ rounds every ~INTERVAL_TICKS."""
        devices, radio = make_group([300, 500])
        run(devices, radio, int(INTERVAL_TICKS * 2.5))

        reqs = core_req_ticks(radio)
        assert len(reqs) >= 3
        gaps = [b - a for a, b in zip(reqs, reqs[1:])]
        for gap in gaps:
            # Rounds complete quickly with nearby nodes, so the next REQ
            # fires one interval after the previous one (small jitter ok).
            assert INTERVAL_TICKS - 2 <= gap <= INTERVAL_TICKS + 10


class TestRoundCompletion:
    def test_core_learns_all_node_positions(self):
        devices, radio = make_group([300, 500, 700])
        run(devices, radio, INTERVAL_TICKS)

        known = devices[0].get_known_positions()
        assert set(known.keys()) >= {1, 2, 3}

    def test_request_not_stuck_in_progress(self):
        devices, radio = make_group([300])
        run(devices, radio, INTERVAL_TICKS)
        assert devices[0].is_request_in_progress() is False


class TestUnreachableGroup:
    def test_core_keeps_retrying_and_learns_nothing(self):
        """With nobody in range the round ends cleanly (no WAIT/POS ever
        arrives, so nothing is pending) and the core re-polls every interval
        instead of wedging in a timed-out round."""
        devices, radio = make_group([50_000])  # node 50 km away: unreachable
        run(devices, radio, INTERVAL_TICKS * 4 + 10)

        reqs = core_req_ticks(radio)
        assert len(reqs) >= 4
        gaps = [b - a for a, b in zip(reqs, reqs[1:])]
        assert all(INTERVAL_TICKS - 2 <= g <= INTERVAL_TICKS + 10 for g in gaps)
        assert set(devices[0].get_known_positions().keys()) <= {0}
        assert not devices[0].is_request_in_progress()


class TestMultiHopRelay:
    def test_out_of_range_node_reached_via_relay(self):
        """Core ↔ far node impossible directly (1400 m > d_max 900 m);
        the middle node relays the REQ out, announces the far node via
        WAIT, and forwards its POS back (fixed in issue #2)."""
        devices, radio = make_group([700, 1400])
        run(devices, radio, INTERVAL_TICKS * 3)

        known = devices[0].get_known_positions()
        assert 2 in known, (
            f"far node never reached the core; known={sorted(known.keys())}"
        )

    def test_relay_round_completes_without_global_timeout(self):
        """After the far node's POS arrives via relay, the round must close
        cleanly (the core erases relayed entries from its accounting)."""
        devices, radio = make_group([700, 1400])
        run(devices, radio, INTERVAL_TICKS)
        assert not devices[0].is_request_in_progress()

    def test_three_hop_chain(self):
        """0 — 700 — 1400 — 2100 m: two relays deep."""
        devices, radio = make_group([700, 1400, 2100])
        run(devices, radio, INTERVAL_TICKS * 3)

        known = devices[0].get_known_positions()
        assert {1, 2, 3} <= set(known.keys()), (
            f"chain incomplete; known={sorted(known.keys())}"
        )
