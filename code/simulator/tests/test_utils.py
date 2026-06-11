"""Tests for utils.py — haversine and local projection."""
import math
import pytest
from utils import haversine, to_local


class TestHaversine:
    def test_zero_distance(self):
        assert haversine(44.0, 12.0, 44.0, 12.0) == pytest.approx(0.0)

    def test_known_distance(self):
        # Bologna to Milan straight-line ≈ 200 km (rough check ±15 km)
        d = haversine(44.498, 11.343, 45.464, 9.188)
        assert 185_000 < d < 215_000

    def test_symmetry(self):
        d1 = haversine(44.12, 12.24, 44.13, 12.25)
        d2 = haversine(44.13, 12.25, 44.12, 12.24)
        assert d1 == pytest.approx(d2, rel=1e-9)

    def test_small_distance(self):
        # ~100 m north
        d = haversine(44.0, 12.0, 44.0009, 12.0)
        assert 90 < d < 110

    def test_non_negative(self):
        assert haversine(44.0, 12.0, 44.1, 11.9) >= 0.0


class TestToLocal:
    def test_origin_is_zero(self):
        x, y = to_local(44.0, 12.0, 44.0, 12.0)
        assert x == pytest.approx(0.0)
        assert y == pytest.approx(0.0)

    def test_north_positive_y(self):
        _, y = to_local(44.01, 12.0, 44.0, 12.0)
        assert y > 0

    def test_east_positive_x(self):
        x, _ = to_local(44.0, 12.01, 44.0, 12.0)
        assert x > 0

    def test_scale_consistency(self):
        # Moving ~1 km north should give y ≈ 1000 m
        _, y = to_local(44.009, 12.0, 44.0, 12.0)
        assert 950 < y < 1050
