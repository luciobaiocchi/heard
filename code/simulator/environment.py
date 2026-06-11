"""
Environment: unified propagation model for the HEARD simulator.

Architecture
------------
Device → SimRadio._broadcast/_unicast
           → Environment.signal_factor(lat1,lon1, lat2,lon2)  → float [0..1]
               ├── Terrain.fresnel_factor   (ITU-R P.526 knife-edge, always)
               └── VegetationLayer.factor   (optional, requires OSM/Copernicus data)

The Environment class is the single entry-point for all channel physics.
Radio.py only calls signal_factor(); adding a new physical effect (e.g. rain
attenuation, urban clutter) means adding a method here, not touching radio.py.

Usage
-----
    from terrain import Terrain
    from environment import Environment

    terrain = Terrain()
    terrain.prefetch(path_points)
    env = Environment(terrain)

    factor = env.signal_factor(lat1, lon1, lat2, lon2)  # → [0.05 .. 1.0]
"""
from __future__ import annotations
import math
from typing import List, Tuple, Optional

from terrain import Terrain


class Environment:
    """Combines terrain propagation effects into a single signal_factor() call.

    Currently implemented layers:
    - Fresnel / knife-edge diffraction  (terrain.fresnel_factor)

    Planned / stub layers:
    - Vegetation attenuation            (not yet implemented)
    """

    def __init__(self, terrain: Terrain) -> None:
        self._terrain = terrain

    # ── Public API ────────────────────────────────────────────────────────────

    def signal_factor(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float,
    ) -> float:
        """Combined [0..1] propagation factor for a point-to-point link.

        Multiplied into the distance-based probability inside SimRadio:
            p_final = link_prob(distance) × signal_factor(src, dst)

        Returns 1.0 when there is no terrain obstruction and no attenuation.
        Returns terrain.LOS_BLOCK (~0.05) for a deeply blocked path.
        """
        factor = self._terrain.fresnel_factor(lat1, lon1, lat2, lon2)
        # Future: factor *= self._vegetation_factor(lat1, lon1, lat2, lon2)
        return factor

    # ── Debug helpers ─────────────────────────────────────────────────────────

    def describe_link(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float,
    ) -> str:
        """Human-readable one-line description of a link's propagation conditions."""
        from utils import haversine
        dist = haversine(lat1, lon1, lat2, lon2)
        ele1 = self._terrain.elevation(lat1, lon1)
        ele2 = self._terrain.elevation(lat2, lon2)
        factor = self.signal_factor(lat1, lon1, lat2, lon2)
        return (
            f"dist={dist:.0f} m  ele {ele1:.0f}→{ele2:.0f} m  "
            f"factor={factor:.3f} ({20*math.log10(max(factor,1e-9)):.1f} dB)"
        )
