import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Tuple
from utils import haversine, EARTH_R

NS = {"g": "http://www.topografix.com/GPX/1/1"}


@dataclass
class PathPoint:
    lat: float
    lon: float
    cum_dist: float  # cumulative distance from path start, in metres
    ele: float = 0.0  # elevation in metres (from <ele> tag)


def load_gpx(filepath: str) -> List[PathPoint]:
    tree = ET.parse(filepath)
    root = tree.getroot()
    trkpts = root.findall(".//g:trkpt", NS)

    points: List[PathPoint] = []
    dist = 0.0
    prev_ele = 0.0
    for i, pt in enumerate(trkpts):
        lat = float(pt.attrib["lat"])
        lon = float(pt.attrib["lon"])
        ele_tag = pt.find("g:ele", NS)
        ele = float(ele_tag.text) if ele_tag is not None else prev_ele
        prev_ele = ele
        if i > 0:
            dist += haversine(points[-1].lat, points[-1].lon, lat, lon)
        points.append(PathPoint(lat, lon, dist, ele))
    return points


def _interp(points: List[PathPoint], d: float) -> Tuple[int, int, float]:
    """Return (lo_idx, hi_idx, t) for interpolation at distance d."""
    if d <= 0:
        return 0, 0, 0.0
    if d >= points[-1].cum_dist:
        n = len(points) - 1
        return n, n, 0.0
    lo, hi = 0, len(points) - 1
    while lo < hi - 1:
        mid = (lo + hi) // 2
        if points[mid].cum_dist <= d:
            lo = mid
        else:
            hi = mid
    t = (d - points[lo].cum_dist) / (points[hi].cum_dist - points[lo].cum_dist)
    return lo, hi, t


def pos_at_dist(points: List[PathPoint], d: float) -> Tuple[float, float]:
    """Return (lat, lon) at cumulative distance d along the path."""
    lo, hi, t = _interp(points, d)
    a, b = points[lo], points[hi]
    return a.lat + t * (b.lat - a.lat), a.lon + t * (b.lon - a.lon)


def pos3d_at_dist(points: List[PathPoint], d: float) -> Tuple[float, float, float]:
    """Return (lat, lon, ele_m) at cumulative distance d along the path."""
    lo, hi, t = _interp(points, d)
    a, b = points[lo], points[hi]
    return (
        a.lat + t * (b.lat - a.lat),
        a.lon + t * (b.lon - a.lon),
        a.ele + t * (b.ele - a.ele),
    )


def lateral_pos(points: List[PathPoint], d: float, offset_m: float) -> Tuple[float, float]:
    """Return (lat, lon) displaced offset_m perpendicular to the path at distance d.

    Positive offset = left of the direction of travel.
    Uses the path heading at d (computed from neighbouring samples ±1 m) and
    applies an equirectangular perpendicular displacement.
    """
    lat, lon = pos_at_dist(points, d)
    if offset_m == 0.0:
        return lat, lon

    total = points[-1].cum_dist
    d_lo = max(0.0, d - 1.0)
    d_hi = min(total, d + 1.0)
    if d_lo >= d_hi:
        return lat, lon

    lat_lo, lon_lo = pos_at_dist(points, d_lo)
    lat_hi, lon_hi = pos_at_dist(points, d_hi)

    lat_mid_r = math.radians((lat_lo + lat_hi) / 2.0)
    east_fwd  = math.radians(lon_hi - lon_lo) * math.cos(lat_mid_r) * EARTH_R
    north_fwd = math.radians(lat_hi - lat_lo) * EARTH_R
    length = math.sqrt(east_fwd ** 2 + north_fwd ** 2)
    if length < 1e-9:
        return lat, lon

    # Rotate 90° CCW → perpendicular pointing left of travel
    east_perp  = -north_fwd / length
    north_perp =  east_fwd  / length

    m_per_deg = EARTH_R * math.pi / 180.0
    dlat = offset_m * north_perp / m_per_deg
    dlon = offset_m * east_perp  / (m_per_deg * math.cos(math.radians(lat)))
    return lat + dlat, lon + dlon
