"""Terrain elevation from AWS terrarium DEM tiles, used for LoRa propagation."""
from __future__ import annotations
import io
import math
import urllib.request
from typing import List, Optional

import numpy as np

from gpx_loader import PathPoint
from utils import haversine

ZOOM        = 12      # ~38 m/pixel at mid-latitudes — good balance of detail vs tile count
ANTENNA_H   = 2.0     # metres above ground level for device antenna
LOS_SAMPLES = 30      # interior points sampled along each link
LOS_BLOCK   = 0.05    # minimum probability multiplier (deep obstruction floor)

# LoRa 868 MHz propagation constants
_FREQ_HZ    = 868e6
_C_LIGHT    = 3e8
_WAVELENGTH = _C_LIGHT / _FREQ_HZ   # ≈ 0.345 m


def _knife_edge_db(v: float) -> float:
    """ITU-R P.526 single knife-edge diffraction loss in dB for parameter v.

    v > 0: obstacle above line-of-sight (blocked); v < 0: obstacle below (clear).
    """
    if v <= -1.0:
        return 0.0
    if v <= 0.0:
        return 20.0 * math.log10(0.5 - 0.62 * v)
    if v <= 1.0:
        return 20.0 * math.log10(0.5 * math.exp(-0.95 * v))
    if v <= 2.4:
        inner = max(0.0, 0.1184 - (0.38 - 0.1 * v) ** 2)
        return 20.0 * math.log10(0.4 - math.sqrt(inner))
    return 20.0 * math.log10(0.225 / v)


# ── Tile math ─────────────────────────────────────────────────────────────────

def _tile_xy(lat: float, lon: float, z: int = ZOOM):
    """Web-Mercator tile indices (x, y) for a given lat/lon."""
    n = 1 << z
    x = int((lon + 180.0) / 360.0 * n)
    lat_r = math.radians(lat)
    y = int((1.0 - math.log(math.tan(lat_r) + 1.0 / math.cos(lat_r)) / math.pi) / 2.0 * n)
    return max(0, min(n - 1, x)), max(0, min(n - 1, y))


def _pixel_in_tile(lat: float, lon: float, tx: int, ty: int, z: int = ZOOM):
    """Pixel (px, py) within the 256×256 tile at (tx, ty)."""
    n = 1 << z
    lat_r = math.radians(lat)
    fx = (lon + 180.0) / 360.0 * n - tx
    fy = (1.0 - math.log(math.tan(lat_r) + 1.0 / math.cos(lat_r)) / math.pi) / 2.0 * n - ty
    return max(0, min(255, int(fx * 256))), max(0, min(255, int(fy * 256)))


# ── Main class ────────────────────────────────────────────────────────────────

class Terrain:
    """
    Ground elevation lookup and LoRa line-of-sight check.

    Tiles are fetched from AWS terrarium on first access and kept in memory.
    Call prefetch(path_points) before the simulation loop to download all
    tiles covering the trail bounding box up front (avoids mid-run latency).

    LOS check (los_factor):
      - Samples LOS_SAMPLES points along the straight line between two devices.
      - Linearly interpolates the "radio altitude" (ground elevation + ANTENNA_H)
        between the two endpoints.
      - If terrain at any sample point rises above that altitude → blocked.
      - Returns 1.0 (clear) or LOS_BLOCK (obstructed).
    """

    def __init__(self, zoom: int = ZOOM) -> None:
        self.zoom = zoom
        self._cache: dict[tuple, Optional[np.ndarray]] = {}

    # ── Tile fetching ─────────────────────────────────────────────────────

    def _fetch(self, tx: int, ty: int) -> Optional[np.ndarray]:
        key = (self.zoom, tx, ty)
        if key in self._cache:
            return self._cache[key]

        url = (f"https://s3.amazonaws.com/elevation-tiles-prod/"
               f"terrarium/{self.zoom}/{tx}/{ty}.png")
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                data = resp.read()

            # Decode PNG via matplotlib (always available); imread returns float32 in [0,1]
            import matplotlib.image as mpimg
            arr = mpimg.imread(io.BytesIO(data))        # (256, 256, 3 or 4), float32 [0,1]
            arr = (arr[:, :, :3] * 255.0).astype(np.float32)

            # Terrarium encoding: elevation = R*256 + G + B/256 - 32768  (metres)
            elev = arr[:, :, 0] * 256.0 + arr[:, :, 1] + arr[:, :, 2] / 256.0 - 32768.0
            self._cache[key] = elev
            return elev

        except Exception as exc:
            print(f"  [terrain] tile {self.zoom}/{tx}/{ty} failed: {exc}")
            self._cache[key] = None
            return None

    def prefetch(self, path_points: List[PathPoint], margin_deg: float = 0.05) -> None:
        """Download all tiles for the GPX bounding box + margin_deg padding."""
        lats = [p.lat for p in path_points]
        lons = [p.lon for p in path_points]
        lat_min = min(lats) - margin_deg
        lat_max = max(lats) + margin_deg
        lon_min = min(lons) - margin_deg
        lon_max = max(lons) + margin_deg

        # Note: higher lat → smaller tile y in Web Mercator
        x0, y0 = _tile_xy(lat_max, lon_min, self.zoom)
        x1, y1 = _tile_xy(lat_min, lon_max, self.zoom)

        tiles = [(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]
        print(f"  [terrain] fetching {len(tiles)} tile(s) at zoom {self.zoom} "
              f"(~{111_000 * 360 / (1 << self.zoom) / 256:.0f} m/px)…", flush=True)
        for tx, ty in tiles:
            self._fetch(tx, ty)
        ok = sum(1 for v in self._cache.values() if v is not None)
        print(f"  [terrain] {ok}/{len(tiles)} tiles ready", flush=True)

    # ── Elevation ─────────────────────────────────────────────────────────

    def elevation(self, lat: float, lon: float) -> float:
        """Ground elevation in metres at (lat, lon). Returns 0.0 if tile unavailable."""
        tx, ty = _tile_xy(lat, lon, self.zoom)
        tile = self._fetch(tx, ty)
        if tile is None:
            return 0.0
        px, py = _pixel_in_tile(lat, lon, tx, ty, self.zoom)
        return float(tile[py, px])

    # ── LOS check ─────────────────────────────────────────────────────────

    def los_factor(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Binary LOS check: 1.0 (clear) or LOS_BLOCK (obstructed).
        Kept for reference; prefer fresnel_factor for realistic propagation.
        """
        ele1 = self.elevation(lat1, lon1) + ANTENNA_H
        ele2 = self.elevation(lat2, lon2) + ANTENNA_H
        for i in range(1, LOS_SAMPLES):
            t = i / LOS_SAMPLES
            lat_s = lat1 + t * (lat2 - lat1)
            lon_s = lon1 + t * (lon2 - lon1)
            ele_line = ele1 + t * (ele2 - ele1)
            if self.elevation(lat_s, lon_s) > ele_line:
                return LOS_BLOCK
        return 1.0

    def fresnel_factor(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Continuous [LOS_BLOCK..1.0] propagation factor using ITU-R P.526 knife-edge.

        Finds the worst single obstacle along the path (maximum Fresnel-Kirchhoff
        parameter v) and converts it to a linear amplitude factor.

        v < -1 → full Fresnel-zone clearance → 1.0
        v =  0 → obstacle just touching LOS  → ~0.5  (-6 dB)
        v > 0  → obstacle above LOS          → rapid decay toward LOS_BLOCK
        """
        total_dist = haversine(lat1, lon1, lat2, lon2)
        if total_dist < 1.0:
            return 1.0

        ele1 = self.elevation(lat1, lon1) + ANTENNA_H
        ele2 = self.elevation(lat2, lon2) + ANTENNA_H

        worst_v = -math.inf
        for i in range(1, LOS_SAMPLES):
            t = i / LOS_SAMPLES
            d1 = t * total_dist
            d2 = (1.0 - t) * total_dist

            lat_s = lat1 + t * (lat2 - lat1)
            lon_s = lon1 + t * (lon2 - lon1)

            los_ele   = ele1 + t * (ele2 - ele1)
            obs_ele   = self.elevation(lat_s, lon_s) + ANTENNA_H
            h         = obs_ele - los_ele          # positive = obstacle above LOS

            denom = _WAVELENGTH * d1 * d2
            if denom > 0.0:
                v = h * math.sqrt(2.0 * (d1 + d2) / denom)
                if v > worst_v:
                    worst_v = v

        if worst_v == -math.inf:
            return 1.0

        # _knife_edge_db returns amplitude gain in dB (negative = loss).
        # 10^(gain_db/20) converts to linear amplitude factor [0..1].
        gain_db = _knife_edge_db(worst_v)
        return max(LOS_BLOCK, 10.0 ** (gain_db / 20.0))
