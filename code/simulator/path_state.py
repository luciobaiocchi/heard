"""
Python port of the firmware Path::isInsidePath / distancePointToSegment.

Replicates the exact algorithm in:
  core/src/path/Path.cpp

Used by record.py to compute per-device OUT_PATH state for visualization.
The C++ sim module has no path subsystem, so this runs entirely in Python.
"""
from __future__ import annotations
import math
from typing import List

import numpy as np

from utils import EARTH_R, haversine
from gpx_loader import PathPoint

# Per-path numpy array cache (keyed by id; path_points list lives for the
# whole simulation run so the id is stable).
_np_cache: dict = {}

def _path_arrays(path_points: List[PathPoint]):
    key = id(path_points)
    if key not in _np_cache:
        _np_cache[key] = (
            np.array([p.lat for p in path_points], dtype=np.float64),
            np.array([p.lon for p in path_points], dtype=np.float64),
        )
    return _np_cache[key]


def dist_point_to_segment(
    a_lat: float, a_lon: float,
    b_lat: float, b_lon: float,
    p_lat: float, p_lon: float,
) -> float:
    """Equirectangular point-to-segment distance in metres.

    Direct port of Path::distancePointToSegment(a, b, p) in Path.cpp.
    'a' is the origin (nearest path point); 'b' is the prev/next neighbour.
    Uses mean-latitude cosine scaling (matching the firmware's exact formula).
    """
    # Project b relative to a (firmware: getX()=lat, getY()=lon)
    bx = EARTH_R * math.radians(b_lon - a_lon) * math.cos(math.radians((a_lat + b_lat) / 2.0))
    by = EARTH_R * math.radians(b_lat - a_lat)
    # Project p relative to a
    px = EARTH_R * math.radians(p_lon - a_lon) * math.cos(math.radians((a_lat + p_lat) / 2.0))
    py = EARTH_R * math.radians(p_lat - a_lat)
    # a is origin (0, 0)
    dx, dy = bx, by
    len_sq = dx * dx + dy * dy
    if len_sq == 0.0:
        return math.sqrt(px * px + py * py)
    t = (px * dx + py * dy) / len_sq
    t = max(0.0, min(1.0, t))
    proj_x = t * dx
    proj_y = t * dy
    return math.sqrt((px - proj_x) ** 2 + (py - proj_y) ** 2)


def is_inside_path(
    lat: float, lon: float,
    path_points: List[PathPoint],
    max_distance: float = 100.0,
) -> bool:
    """Return True if (lat, lon) is within max_distance metres of the path.

    Mirrors StateManager::updateState() + Path::isInsidePath() exactly:
    1. Find the nearest path point by haversine distance.
    2. If that distance ≤ max_distance → inside.
    3. Else if the nearest point has a predecessor (firmware: nearest->prev),
       check the segment [nearest, prev]; if ≤ max_distance → inside.
    4. Else if the nearest is the first point (no prev), check [nearest, next].
    5. Otherwise → outside.
    """
    if not path_points:
        return False

    # Step 1: find nearest path point.
    # Squared equirectangular distance (no trig per point) is sufficient for
    # argmin — only one real haversine is needed afterwards for the threshold check.
    np_lats, np_lons = _path_arrays(path_points)
    cos_lat = math.cos(math.radians(lat))
    dlat = np_lats - lat
    dlon = (np_lons - lon) * cos_lat
    nearest_idx = int(np.argmin(dlat * dlat + dlon * dlon))
    nearest = path_points[nearest_idx]

    # Step 2: direct point distance
    if haversine(lat, lon, nearest.lat, nearest.lon) <= max_distance:
        return True

    # Step 3/4: segment check (firmware's else-if chain)
    if nearest_idx > 0:
        prev = path_points[nearest_idx - 1]
        if dist_point_to_segment(
            nearest.lat, nearest.lon,
            prev.lat, prev.lon,
            lat, lon,
        ) <= max_distance:
            return True
    elif nearest_idx < len(path_points) - 1:
        nxt = path_points[nearest_idx + 1]
        if dist_point_to_segment(
            nearest.lat, nearest.lon,
            nxt.lat, nxt.lon,
            lat, lon,
        ) <= max_distance:
            return True

    return False
