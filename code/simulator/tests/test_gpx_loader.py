"""Tests for gpx_loader.py."""
import pytest
from gpx_loader import load_gpx, pos_at_dist, PathPoint


class TestLoadGpx:
    def test_loads_points(self, path_points):
        assert len(path_points) > 100

    def test_monotone_cumulative_dist(self, path_points):
        dists = [p.cum_dist for p in path_points]
        assert all(b >= a for a, b in zip(dists, dists[1:]))

    def test_first_point_zero_dist(self, path_points):
        assert path_points[0].cum_dist == pytest.approx(0.0)

    def test_total_length_reasonable(self, path_points):
        # GPX file is ~4.87 km
        assert 4000 < path_points[-1].cum_dist < 6000

    def test_coordinates_in_range(self, path_points):
        for p in path_points:
            assert 44.0 < p.lat < 44.2
            assert 12.0 < p.lon < 12.4


class TestPosAtDist:
    def test_zero_returns_start(self, path_points):
        lat, lon = pos_at_dist(path_points, 0.0)
        assert lat == pytest.approx(path_points[0].lat)
        assert lon == pytest.approx(path_points[0].lon)

    def test_beyond_end_returns_end(self, path_points):
        lat, lon = pos_at_dist(path_points, 1e9)
        assert lat == pytest.approx(path_points[-1].lat)
        assert lon == pytest.approx(path_points[-1].lon)

    def test_midpoint_in_range(self, path_points):
        mid = path_points[-1].cum_dist / 2
        lat, lon = pos_at_dist(path_points, mid)
        assert 44.0 < lat < 44.2
        assert 12.0 < lon < 12.4

    def test_interpolation_smooth(self, path_points):
        # Two close distances should give close coordinates
        d = path_points[-1].cum_dist / 3
        lat1, lon1 = pos_at_dist(path_points, d)
        lat2, lon2 = pos_at_dist(path_points, d + 1.0)
        assert abs(lat2 - lat1) < 0.01
        assert abs(lon2 - lon1) < 0.01
