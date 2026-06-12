"""End-to-end recorder tests: trace schema, determinism, radio-radius flags."""
import json

import pytest

from tests.conftest import GPX_PATH
from record import record


@pytest.fixture(scope="module")
def trace(tmp_path_factory):
    out = tmp_path_factory.mktemp("trace") / "trace.json"
    record(num_ticks=300, out_path=str(out), mode="uniform", gpx_file=GPX_PATH)
    with open(out) as f:
        return json.load(f)


class TestTraceSchema:
    def test_meta_keys(self, trace):
        meta = trace["meta"]
        for key in ("tick_s", "num_ticks", "frame_stride", "lora_reliable_m",
                    "lora_max_m", "mode", "margin_m", "devices"):
            assert key in meta
        assert meta["num_ticks"] == 300

    def test_top_level_sections(self, trace):
        for key in ("path", "margin_left", "margin_right", "frames"):
            assert key in trace
        assert len(trace["frames"]) == 300  # stride 1 below MAX_FRAMES

    def test_frame_devices(self, trace):
        n_devices = len(trace["meta"]["devices"])
        for frame in (trace["frames"][0], trace["frames"][-1]):
            assert len(frame["devices"]) == n_devices
            for d in frame["devices"]:
                for key in ("id", "lat", "lon", "ele", "out", "reach"):
                    assert key in d

    def test_links_contain_protocol_traffic_only(self, trace):
        kinds = {lk["kind"] for f in trace["frames"] for lk in f["links"]}
        assert kinds <= {"REQ", "WAIT", "POS", "?"}
        assert "REQ" in kinds  # at least one round happened in 30 s

    def test_connectivity_populated(self, trace):
        last = trace["frames"][-1]
        assert any(d["reach"] for d in last["devices"])


class TestDeterminism:
    def test_same_seed_same_trace(self, tmp_path):
        a, b = tmp_path / "a.json", tmp_path / "b.json"
        record(num_ticks=120, out_path=str(a), mode="normal", gpx_file=GPX_PATH)
        record(num_ticks=120, out_path=str(b), mode="normal", gpx_file=GPX_PATH)
        assert a.read_bytes() == b.read_bytes()


class TestRadioRadiusFlags:
    def test_custom_radii_reach_meta(self, tmp_path):
        out = tmp_path / "t.json"
        record(num_ticks=50, out_path=str(out), gpx_file=GPX_PATH,
               reliable_m=1000.0, max_range_m=2500.0)
        meta = json.loads(out.read_text())["meta"]
        assert meta["lora_reliable_m"] == 1000.0
        assert meta["lora_max_m"] == 2500.0
