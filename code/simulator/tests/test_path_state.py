"""Tests for path_state.py — Python port of firmware Path::isInsidePath."""
import math
import random
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gpx_loader import PathPoint
from path_state import is_inside_path, dist_point_to_segment
from sim_setup import ExcursionScheduler
from config import EXCURSION_RAMP_S, TICK_S, MODE_PARAMS


# ── Synthetic straight N-S path for geometry tests ───────────────────────
# Path runs due north from (44.0, 12.0) with points every 50 m.
# 1 degree latitude ≈ 111_195 m  →  50 m ≈ 0.0004497°
_DEG_PER_M = 1.0 / 111_195.0

def _make_path(n_points: int = 20):
    pts = []
    for i in range(n_points):
        lat = 44.0 + i * 50 * _DEG_PER_M
        lon = 12.0
        dist = i * 50.0
        pts.append(PathPoint(lat=lat, lon=lon, cum_dist=dist, ele=100.0))
    return pts


PATH = _make_path()


class TestIsInsidePath:
    def test_on_path_point(self):
        p = PATH[5]
        assert is_inside_path(p.lat, p.lon, PATH)

    def test_close_to_path_within_threshold(self):
        # 50 m east of the midpoint — should be inside (50 ≤ 100)
        p = PATH[10]
        offset_lat = 0.0
        offset_lon = 50 * _DEG_PER_M / math.cos(math.radians(p.lat))
        assert is_inside_path(p.lat + offset_lat, p.lon + offset_lon, PATH)

    def test_exactly_at_threshold_is_inside(self):
        # 100 m east — should be inside (distance == threshold)
        p = PATH[10]
        offset_lon = 100 * _DEG_PER_M / math.cos(math.radians(p.lat))
        # is_inside uses ≤, so exactly at 100 m should pass
        assert is_inside_path(p.lat, p.lon + offset_lon, PATH)

    def test_outside_threshold(self):
        # 150 m east — should be outside
        p = PATH[10]
        offset_lon = 150 * _DEG_PER_M / math.cos(math.radians(p.lat))
        assert not is_inside_path(p.lat, p.lon + offset_lon, PATH)

    def test_segment_midpoint_perpendicular(self):
        # Point perpendicular to the midpoint of a segment, 80 m away
        # Nearest point is a segment end but the segment distance is 80 m < 100 m
        p_mid_lat = (PATH[7].lat + PATH[8].lat) / 2
        p_mid_lon = PATH[7].lon
        offset_lon = 80 * _DEG_PER_M / math.cos(math.radians(p_mid_lat))
        assert is_inside_path(p_mid_lat, p_mid_lon + offset_lon, PATH)

    def test_far_from_path(self):
        # 500 m away laterally
        p = PATH[5]
        offset_lon = 500 * _DEG_PER_M / math.cos(math.radians(p.lat))
        assert not is_inside_path(p.lat, p.lon + offset_lon, PATH)

    def test_custom_threshold(self):
        # With max_distance=50, the same 80 m lateral point should be outside
        p = PATH[5]
        offset_lon = 80 * _DEG_PER_M / math.cos(math.radians(p.lat))
        assert not is_inside_path(p.lat, p.lon + offset_lon, PATH, max_distance=50.0)


class TestDistPointToSegment:
    def test_perpendicular_midpoint(self):
        # Horizontal segment from (0,0) to (0, 0.001 deg lon)
        # Point 100 m north of the midpoint
        a_lat, a_lon = 44.0, 12.0
        b_lat, b_lon = 44.0, 12.001
        # North of midpoint by ~100 m
        p_lat = a_lat + 100 * _DEG_PER_M
        p_lon = (a_lon + b_lon) / 2
        d = dist_point_to_segment(a_lat, a_lon, b_lat, b_lon, p_lat, p_lon)
        assert 90 < d < 115  # roughly 100 m

    def test_beyond_endpoint_clamps_to_endpoint(self):
        # Point is far past the b endpoint — should clamp to b
        a_lat, a_lon = 44.0, 12.0
        b_lat, b_lon = 44.0, 12.001
        p_lat, p_lon = 44.0, 12.005  # well past b
        d = dist_point_to_segment(a_lat, a_lon, b_lat, b_lon, p_lat, p_lon)
        d_to_b = math.sqrt(
            (dist_point_to_segment(b_lat, b_lon, b_lat, b_lon, p_lat, p_lon)) ** 2
        )
        # d should match haversine from b to p (≈ distance at clamped end)
        from utils import haversine
        assert abs(d - haversine(b_lat, b_lon, p_lat, p_lon)) < 10  # within 10 m


class TestExcursionScheduler:
    def test_uniform_always_zero(self):
        rng = random.Random(0)
        sched = ExcursionScheduler(5, "uniform", rng)
        for tick in range(200):
            for idx in range(5):
                assert sched.offset(idx, tick) == 0.0

    def test_core_always_zero(self):
        rng = random.Random(0)
        sched = ExcursionScheduler(5, "hard", rng)
        for tick in range(500):
            assert sched.offset(0, tick) == 0.0

    def test_normal_scripted_kick_fires(self):
        rng = random.Random(42)
        sched = ExcursionScheduler(5, "normal", rng)
        # Scripted kick for node 1 at tick 30 — offset should be 0 before, >0 at tick 31
        assert sched.offset(1, 29) == 0.0
        assert sched.offset(1, 30) == 0.0  # ramp just starts; t=0 → off=0
        assert sched.offset(1, 31) > 0.0   # t=0.1 s → just starting to ramp

    def test_trapezoid_shape(self):
        """Offset should ramp up, hold at peak, then ramp down."""
        rng = random.Random(0)
        sched = ExcursionScheduler(5, "normal", rng)
        params = MODE_PARAMS["normal"]
        peak_m = params["peak_m"]
        hold_s = params["hold_s"]
        ramp_s = EXCURSION_RAMP_S
        start  = 30  # scripted kick for node 1

        # Collect offsets across the full excursion
        ticks = list(range(start, start + int((2 * ramp_s + hold_s) / TICK_S) + 5))
        offsets = [abs(sched.offset(1, t)) for t in ticks]

        # Must reach peak
        assert max(offsets) >= peak_m * 0.98

        # Must be zero after excursion ends
        end_tick = start + int((2 * ramp_s + hold_s) / TICK_S) + 2
        assert sched.offset(1, end_tick) == 0.0

    def test_peak_exceeds_100m_threshold_in_normal(self):
        params = MODE_PARAMS["normal"]
        assert params["peak_m"] > 100.0

    def test_peak_exceeds_100m_threshold_in_hard(self):
        params = MODE_PARAMS["hard"]
        assert params["peak_m"] > 100.0
