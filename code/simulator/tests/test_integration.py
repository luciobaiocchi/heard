"""
Integration tests that exercise the full simulation stack.
If heard_sim.so is not built the C++-dependent tests are skipped automatically.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from heard_sim import SimDevice
    CPP_AVAILABLE = True
except (ImportError, OSError) as _e:
    CPP_AVAILABLE = False
    _CPP_SKIP_REASON = f"heard_sim not loadable: {_e}"
else:
    _CPP_SKIP_REASON = "heard_sim.so not built — run cmake+make first"

skip_no_cpp = pytest.mark.skipif(not CPP_AVAILABLE, reason=_CPP_SKIP_REASON)

from node_device import NodeDevice
from radio import SimRadio
from gpx_loader import load_gpx, pos_at_dist
from config import GPX_FILE, LORA_RELIABLE_M, LORA_MAX_M


# ── Pure Python integration ────────────────────────────────────────────────

class TestSimulationWithGPX:
    def test_devices_move_along_path(self, path_points):
        from config import WALKING_SPEED, TICK_S, MAX_SPREAD_M
        total = path_points[-1].cum_dist
        devices = [NodeDevice(i, *pos_at_dist(path_points, 0)) for i in range(4)]

        for tick in range(100):
            for idx, dev in enumerate(devices):
                dist_walked = idx * MAX_SPREAD_M / 3 + tick * TICK_S * WALKING_SPEED
                lat, lon = pos_at_dist(path_points, min(dist_walked, total))
                dev.set_position(lat, lon)

        # After 100 ticks devices should have moved
        for dev in devices:
            assert 44.0 < dev.get_lat() < 44.2

    def test_full_round_python_only(self, path_points):
        radio = SimRadio(LORA_RELIABLE_M, LORA_MAX_M, rng_seed=0)
        devices = [NodeDevice(i, *pos_at_dist(path_points, i * 200)) for i in range(5)]

        # Simulate one full round: core broadcasts REQ, nodes respond
        for node in devices[1:]:
            node.inject_message("REQ|0|", sender_id=0)

        for tick in range(NodeDevice.POS_DELAY_TICKS + 10):
            for dev in devices:
                dev.step(tick)
            radio.tick(devices, tick)

        assert radio.stats["sent"] > 0
        pos_evs = [e for e in radio.events if e.msg_kind == "POS"]
        assert len(pos_evs) >= 4   # 4 nodes should have sent positions


# ── C++ integration (skipped without heard_sim.so) ────────────────────────

@skip_no_cpp
class TestCppSimDevice:
    def test_create_device(self):
        dev = SimDevice(0)
        assert dev.get_id() == 0

    def test_set_and_get_position(self):
        dev = SimDevice(5)
        dev.set_position(44.12, 12.24)
        assert dev.get_lat() == pytest.approx(44.12)
        assert dev.get_lon() == pytest.approx(12.24)

    def test_step_does_not_crash(self):
        dev = SimDevice(0)
        dev.set_position(44.12, 12.24)
        for ms in range(0, 1000, 100):
            dev.step(ms)

    def test_auto_request_after_60s(self):
        dev = SimDevice(0)
        dev.set_position(44.12, 12.24)
        # Advance past 60 000 ms — auto-request should fire
        dev.step(0)
        dev.step(60_001)
        assert dev.is_request_in_progress() or dev.has_pending_out()

    def test_inject_and_process_req(self):
        core = SimDevice(0)
        core.set_position(44.120, 12.240)

        # Simulate a node forwarding a REQ with core's ID in hop list
        forwarded_req = "REQ|0,1|"
        core.inject_message(forwarded_req, sender_id=1)
        core.step(0)

        # Core should have sent a WAIT back to node 1
        found_wait = False
        while core.has_pending_out():
            dest, msg = core.pop_pending_out()
            if msg.startswith("WAIT") and dest == 1:
                found_wait = True
        assert found_wait

    def test_pos_updates_known_positions(self):
        core = SimDevice(0)
        core.set_position(44.120, 12.240)

        # First, let the core issue a request so node 1 is in pendingDevices
        core.inject_message("REQ|0,1|", sender_id=1)
        core.step(0)
        while core.has_pending_out():
            core.pop_pending_out()

        # Now inject the POS reply from node 1
        core.inject_message("POS|1,44.121,12.241", sender_id=1)
        core.step(100)

        pos = core.get_known_positions()
        assert 1 in pos
        lat, lon, _ = pos[1]
        assert lat == pytest.approx(44.121, abs=1e-4)
        assert lon == pytest.approx(12.241, abs=1e-4)

    def test_cpp_and_python_nodes_together(self, path_points):
        radio = SimRadio(LORA_RELIABLE_M, LORA_MAX_M, rng_seed=42)
        core  = SimDevice(0)
        core.set_position(*pos_at_dist(path_points, 0))

        nodes = [NodeDevice(i, *pos_at_dist(path_points, i * 300)) for i in range(1, 4)]
        devices = [core] + nodes

        # Manually start a round
        core.step(0)
        assert core.has_pending_out()   # should have broadcast REQ

        for tick in range(1, NodeDevice.POS_DELAY_TICKS + 15):
            for dev in devices:
                dev.step(tick * 100)
            radio.tick(devices, tick)

        # Core should have collected at least one position
        pos = core.get_known_positions()
        assert len(pos) >= 1
