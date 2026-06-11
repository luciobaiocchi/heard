"""Shared simulation setup helpers used by both main.py and record.py."""
from __future__ import annotations
import random
from typing import List, Optional

from config import (
    NUM_NODES, MAX_SPREAD_M, WALKING_SPEED, TICK_S,
    LORA_RELIABLE_M, LORA_MAX_M, RANDOM_SEED,
    EXCURSION_RAMP_S, MODE_PARAMS,
)
from gpx_loader import PathPoint, pos3d_at_dist, lateral_pos
from node_device import NodeDevice
from radio import SimRadio

try:
    from heard_sim import SimDevice
    _CPP_AVAILABLE = True
except ImportError:
    _CPP_AVAILABLE = False


def device_dist(
    idx: int,
    n_devices: int,
    tick: int,
    total_dist: float,
    loop: bool = False,
    reverse: bool = False,
) -> float:
    """Cumulative distance along the path for device idx at simulation tick.

    reverse=True  → core (idx 0) leads the group; higher-index devices trail.
    loop=True     → wrap around the path end instead of clamping at total_dist.
    """
    if reverse:
        spread = (n_devices - 1 - idx) * MAX_SPREAD_M / max(n_devices - 1, 1)
    else:
        spread = idx * MAX_SPREAD_M / max(n_devices - 1, 1)
    walked = tick * TICK_S * WALKING_SPEED
    d = spread + walked
    return d % total_dist if loop else min(d, total_dist)


def build_devices(path_points: List[PathPoint], rng: random.Random) -> list:
    total_dist = path_points[-1].cum_dist
    devices = []

    start_lat, start_lon, _ = pos3d_at_dist(path_points, 0.0)
    if _CPP_AVAILABLE:
        core = SimDevice(0)
        core.set_position(start_lat, start_lon)
    else:
        core = NodeDevice(0, start_lat, start_lon)
    devices.append(core)

    for i in range(1, NUM_NODES + 1):
        offset = rng.uniform(0, min(MAX_SPREAD_M, total_dist))
        lat, lon, _ = pos3d_at_dist(path_points, offset)
        devices.append(NodeDevice(i, lat, lon))

    return devices


def advance_one_tick(
    devices: list,
    radio: SimRadio,
    path_points: List[PathPoint],
    tick: int,
    scheduler: Optional[ExcursionScheduler] = None,
    loop: bool = False,
    reverse: bool = False,
) -> None:
    """Advance the simulation by one tick: update GPS, step devices, radio.

    loop/reverse are forwarded to device_dist (see its docstring).
    Default values keep existing behaviour (backward-compatible with main.py).
    """
    total_dist = path_points[-1].cum_dist
    n = len(devices)
    sim_ms = int(tick * TICK_S * 1000)

    for idx, dev in enumerate(devices):
        d = device_dist(idx, n, tick, total_dist, loop=loop, reverse=reverse)
        off = scheduler.offset(idx, tick) if scheduler is not None else 0.0
        if off != 0.0:
            lat, lon = lateral_pos(path_points, d, off)
        else:
            lat, lon, _ = pos3d_at_dist(path_points, d)
        dev.set_position(lat, lon)

    for dev in devices:
        dev.step(sim_ms)

    radio.tick(devices, tick)


def build_radio(rng_seed: int = RANDOM_SEED, terrain=None, environment=None,
                d_reliable: float = LORA_RELIABLE_M, d_max: float = LORA_MAX_M) -> SimRadio:
    return SimRadio(d_reliable, d_max, max_events=10_000, rng_seed=rng_seed,
                    terrain=terrain, environment=environment)


class ExcursionScheduler:
    """Drives lateral off-path excursions for the 'normal' and 'hard' modes.

    Core device (idx 0) and 'uniform' mode always return offset 0.
    Each non-core device independently follows a trapezoidal offset profile:
      ramp-out (EXCURSION_RAMP_S) → hold at peak → ramp-back-in.

    Deterministic: scripted kicks are seeded; random starts consume from the
    shared rng in device-index order, same as device placement in build_devices.
    """

    def __init__(self, n_devices: int, mode: str, rng: random.Random) -> None:
        self._params = MODE_PARAMS.get(mode)   # None → uniform
        self._rng    = rng
        # device_idx → (start_tick, peak_m, hold_s, side)
        self._active: dict = {}
        # Scripted kicks: device_idx → start_tick (one-shot, consumed on fire)
        self._scripted: dict = {}
        if self._params:
            for dev_idx, start_tick in self._params.get("scripted", []):
                if 0 < dev_idx < n_devices:
                    self._scripted[dev_idx] = start_tick

    def offset(self, idx: int, tick: int) -> float:
        """Perpendicular lateral offset in metres for device idx at this tick."""
        if idx == 0 or self._params is None:
            return 0.0

        params  = self._params
        peak_m  = params["peak_m"]
        hold_s  = params["hold_s"]
        ramp_s  = EXCURSION_RAMP_S
        total_s = 2.0 * ramp_s + hold_s

        # Fire scripted kick (replaces any ongoing excursion)
        if idx in self._scripted and tick == self._scripted[idx]:
            self._active[idx] = (tick, peak_m, hold_s, 1.0)
            del self._scripted[idx]
        elif idx not in self._active:
            # Draw from rng (always consume to keep stream deterministic)
            r = self._rng.random()
            if r < params["prob_per_tick"]:
                side = 1.0 if self._rng.random() < 0.5 else -1.0
                self._active[idx] = (tick, peak_m, hold_s, side)

        if idx not in self._active:
            return 0.0

        start_tick_act, p_m, h_s, side = self._active[idx]
        t = (tick - start_tick_act) * TICK_S

        if t >= total_s:
            del self._active[idx]
            return 0.0

        if t < ramp_s:
            off = p_m * t / ramp_s
        elif t < ramp_s + h_s:
            off = p_m
        else:
            off = p_m * (1.0 - (t - ramp_s - h_s) / ramp_s)

        return side * off
