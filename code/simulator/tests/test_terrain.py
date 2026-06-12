"""Terrain model tests — no network: tiles are injected or elevation stubbed."""
import math

import numpy as np
import pytest

from terrain import Terrain, _knife_edge_db, _tile_xy, _pixel_in_tile, LOS_BLOCK


class FlatTerrain(Terrain):
    """Terrain stub with a constant ground elevation (no tile downloads)."""

    def __init__(self, ground: float = 1000.0):
        super().__init__()
        self.ground = ground

    def elevation(self, lat, lon):
        return self.ground


class RidgeTerrain(Terrain):
    """Flat terrain with a tall ridge in a latitude band (no tile downloads)."""

    def __init__(self, ground=1000.0, ridge=1500.0, band=(44.004, 44.008)):
        super().__init__()
        self.ground, self.ridge, self.band = ground, ridge, band

    def elevation(self, lat, lon):
        lo, hi = self.band
        return self.ridge if lo <= lat <= hi else self.ground


class TestKnifeEdge:
    def test_full_clearance_no_loss(self):
        assert _knife_edge_db(-1.5) == 0.0

    def test_grazing_is_minus_6db(self):
        assert _knife_edge_db(0.0) == pytest.approx(20 * math.log10(0.5))

    def test_monotonically_decreasing(self):
        vs = [-1.0, -0.5, 0.0, 0.5, 1.0, 2.0, 3.0, 5.0]
        gains = [_knife_edge_db(v) for v in vs]
        assert all(a >= b for a, b in zip(gains, gains[1:]))


class TestTileMath:
    def test_tile_indices_in_bounds(self):
        tx, ty = _tile_xy(45.85, 6.93, 12)
        assert 0 <= tx < 2**12 and 0 <= ty < 2**12

    def test_pixel_within_tile(self):
        tx, ty = _tile_xy(45.85, 6.93, 12)
        px, py = _pixel_in_tile(45.85, 6.93, tx, ty, 12)
        assert 0 <= px <= 255 and 0 <= py <= 255

    def test_northern_latitude_has_smaller_tile_y(self):
        _, ty_north = _tile_xy(60.0, 6.93, 12)
        _, ty_south = _tile_xy(40.0, 6.93, 12)
        assert ty_north < ty_south


class TestElevation:
    def test_elevation_from_injected_tile(self):
        t = Terrain()
        tx, ty = _tile_xy(45.85, 6.93, t.zoom)
        t._cache[(t.zoom, tx, ty)] = np.full((256, 256), 1234.5, dtype=np.float32)
        assert t.elevation(45.85, 6.93) == pytest.approx(1234.5)

    def test_missing_tile_returns_zero(self):
        t = Terrain()
        tx, ty = _tile_xy(45.85, 6.93, t.zoom)
        t._cache[(t.zoom, tx, ty)] = None  # simulate failed download
        assert t.elevation(45.85, 6.93) == 0.0


class ValleyTerrain(Terrain):
    """Endpoints on flat ground with a dip between them (no tile downloads)."""

    def __init__(self, ground=1000.0, valley=900.0, band=(44.0001, 44.0119)):
        super().__init__()
        self.ground, self.valley, self.band = ground, valley, band

    def elevation(self, lat, lon):
        lo, hi = self.band
        return self.valley if lo <= lat <= hi else self.ground


class TestFresnel:
    A = (44.00, 12.00)
    B = (44.012, 12.00)  # ~1.3 km north

    def test_flat_terrain_is_grazing(self):
        # On perfectly flat ground both antennas and every obstacle sit at the
        # same height: the LOS ray grazes the terrain (v=0 → −6 dB → 0.5).
        t = FlatTerrain()
        assert t.fresnel_factor(*self.A, *self.B) == pytest.approx(0.5)

    def test_valley_between_endpoints_is_clear(self):
        t = ValleyTerrain()
        assert t.fresnel_factor(*self.A, *self.B) == pytest.approx(1.0)

    def test_ridge_blocks_link(self):
        t = RidgeTerrain()
        factor = t.fresnel_factor(*self.A, *self.B)
        assert factor < 0.2
        assert factor >= LOS_BLOCK

    def test_factor_bounded(self):
        t = RidgeTerrain(ridge=5000.0)
        assert t.fresnel_factor(*self.A, *self.B) == pytest.approx(LOS_BLOCK)
