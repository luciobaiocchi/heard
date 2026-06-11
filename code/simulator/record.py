"""
Headless HEARD simulation recorder.

Runs the simulation and writes a CesiumJS-compatible trace to web/trace.json.

Usage:
    python3 record.py                              # 120 s, uniform, 100 m margin
    python3 record.py --mode hard                  # off-path excursions
    python3 record.py --loops 1                    # full path traversal, 1 loop
    python3 record.py --loops 2 --mode normal      # 2 loops with brief excursions
    python3 record.py --margin 150                 # wider safe zone
    python3 record.py --ticks 3600                 # explicit tick count
    python3 record.py --reliable 1000 --max-range 2500   # custom LoRa radii
"""
from __future__ import annotations
import argparse
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))

from config import (
    GPX_FILE, RANDOM_SEED, TICK_S, LORA_RELIABLE_M, LORA_MAX_M,
    MARGIN_M, WALKING_SPEED, REACH_WINDOW_TICKS,
)
from gpx_loader import load_gpx, pos3d_at_dist, lateral_pos
from path_state import is_inside_path
from sim_setup import build_devices, advance_one_tick, build_radio, device_dist, ExcursionScheduler

DEFAULT_TICKS = 1200   # 120 s of sim time at TICK_S=0.1
DEFAULT_OUT   = os.path.join(os.path.dirname(__file__), "web", "trace.json")
MAX_FRAMES    = 5000   # cap on recorded frames; excess ticks are subsampled

try:
    from heard_sim import SimDevice as _SimDevice
    _CPP_AVAILABLE = True
except ImportError:
    _CPP_AVAILABLE = False


def _device_snapshot(dev, path_points, idx, n, tick, margin_m, reach, loop, reverse, terrain=None):
    lat = dev.get_lat()
    lon = dev.get_lon()
    d   = device_dist(idx, n, tick, path_points[-1].cum_dist, loop=loop, reverse=reverse)
    _, _, ele = pos3d_at_dist(path_points, d)
    out = not is_inside_path(lat, lon, path_points, margin_m)
    snap = {"id": dev.get_id(), "lat": lat, "lon": lon, "ele": ele, "out": out, "reach": reach}
    if terrain is not None:
        snap["dem_ele"] = terrain.elevation(lat, lon)
    return snap


def _state_snapshot(devices):
    core = devices[0]
    if not _CPP_AVAILABLE:
        return {"req_active": False, "known": []}
    req_active = core.is_request_in_progress()
    known_raw  = core.get_known_positions()
    known = [
        {"id": did, "lat": float(lat), "lon": float(lon)}
        for did, (lat, lon, _ts) in known_raw.items()
    ]
    return {"req_active": req_active, "known": known}


def record(
    num_ticks: int,
    out_path: str,
    mode: str = "uniform",
    margin_m: float = MARGIN_M,
    loops: int = 0,
    gpx_file: str = GPX_FILE,
    use_terrain: bool = False,
    reliable_m: float = LORA_RELIABLE_M,
    max_range_m: float = LORA_MAX_M,
) -> None:
    rng         = random.Random(RANDOM_SEED)
    path_points = load_gpx(gpx_file)
    total_dist  = path_points[-1].cum_dist
    devices     = build_devices(path_points, rng)

    environment = None
    _terrain_ref = None
    if use_terrain:
        from terrain import Terrain
        from environment import Environment
        _terrain_ref = Terrain()
        _terrain_ref.prefetch(path_points)
        environment = Environment(_terrain_ref)

    radio = build_radio(environment=environment,
                        d_reliable=reliable_m, d_max=max_range_m)
    n           = len(devices)
    scheduler   = ExcursionScheduler(n, mode, rng)

    # --loops overrides --ticks: compute ticks to complete N full traversals
    use_loop = loops > 0
    if use_loop:
        ticks_per_loop = int(total_dist / (WALKING_SPEED * TICK_S)) + 1
        num_ticks = ticks_per_loop * loops

    # Subsample large runs to keep trace file manageable (≤ MAX_FRAMES frames)
    frame_stride = max(1, num_ticks // MAX_FRAMES)

    print(f"Recording {num_ticks} ticks ({num_ticks * TICK_S:.0f} s sim time), "
          f"mode={mode}, margin={margin_m} m, "
          f"{'loop' if use_loop else 'no-loop'}, stride={frame_stride}")

    # Static trail (thin to ≤ 2000 pts for payload size)
    trail_stride = max(1, len(path_points) // 2000)
    thinned = path_points[::trail_stride]
    trail  = [[p.lat, p.lon, p.ele] for p in thinned]

    # Safe-zone corridor at ±margin_m
    margin_left  = [list(lateral_pos(path_points, p.cum_dist,  margin_m)) for p in thinned]
    margin_right = [list(lateral_pos(path_points, p.cum_dist, -margin_m)) for p in thinned]

    meta = {
        "tick_s":          TICK_S,
        "num_ticks":       num_ticks,
        "frame_stride":    frame_stride,
        "lora_reliable_m": reliable_m,
        "lora_max_m":      max_range_m,
        "mode":            mode,
        "margin_m":        margin_m,
        "devices": [
            {"id": dev.get_id(), "role": "core" if i == 0 else "node"}
            for i, dev in enumerate(devices)
        ],
    }

    # Per-device "heard from" rolling window: heard_recent[dev_id][sender_id] = last_tick
    heard_recent: dict = {dev.get_id(): {} for dev in devices}
    all_dev_ids = [dev.get_id() for dev in devices]

    frames = []
    for tick in range(num_ticks):
        advance_one_tick(devices, radio, path_points, tick, scheduler,
                         loop=use_loop, reverse=True)

        # Update connectivity from this tick's radio events
        for ev in radio.events:
            if ev.tick != tick or not ev.success:
                continue
            sid, rid = ev.sender_id, ev.recipient_id
            if rid == -1:   # broadcast → all devices except sender hear it
                for did in all_dev_ids:
                    if did != sid:
                        heard_recent[did][sid] = tick
            else:
                if rid in heard_recent:
                    heard_recent[rid][sid] = tick

        # Only write a frame every frame_stride ticks
        if tick % frame_stride != 0:
            continue

        # Compute per-device reach (who each device has heard in the rolling window)
        window_start = tick - REACH_WINDOW_TICKS
        reach_map = {
            did: [sid for sid, lt in hr.items() if lt >= window_start]
            for did, hr in heard_recent.items()
        }

        # Capture the full stride window so relay events (1 tick after broadcast)
        # are never silently dropped when frame_stride > 1.
        # Overheard events feed connectivity above but are excluded from the
        # link-arc visualization to keep it showing protocol traffic only.
        links = [
            {"src": ev.sender_id, "dst": ev.recipient_id, "kind": ev.msg_kind, "ok": ev.success, "tick": ev.tick}
            for ev in radio.events
            if tick - frame_stride < ev.tick <= tick and not ev.overheard
        ]

        frame = {
            "tick":    tick,
            "sim_ms":  int(tick * TICK_S * 1000),
            "devices": [
                _device_snapshot(
                    dev, path_points, idx, n, tick,
                    margin_m, reach_map.get(dev.get_id(), []),
                    loop=use_loop, reverse=True, terrain=_terrain_ref,
                )
                for idx, dev in enumerate(devices)
            ],
            "links":   links,
            "metrics": dict(radio.stats),
            "state":   _state_snapshot(devices),
        }
        frames.append(frame)

        if (tick // frame_stride) % max(1, (num_ticks // frame_stride) // 12) == 0:
            pct = 100 * tick // num_ticks
            print(f"  {pct:3d}%  tick {tick}/{num_ticks}  "
                  f"delivered={radio.stats['delivered']}  "
                  f"dropped={radio.stats['dropped']}")

    trace = {
        "meta":         meta,
        "path":         trail,
        "margin_left":  margin_left,
        "margin_right": margin_right,
        "frames":       frames,
    }

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(trace, f, separators=(",", ":"))

    size_kb = os.path.getsize(out_path) // 1024
    print(f"\nWrote {out_path}  ({size_kb} KB, {len(frames)} frames)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Record a HEARD simulation trace.")
    ap.add_argument("--ticks",  type=int,   default=DEFAULT_TICKS, metavar="N",
                    help=f"simulation ticks (default {DEFAULT_TICKS}; overridden by --loops)")
    ap.add_argument("--out",    type=str,   default=DEFAULT_OUT,   metavar="PATH",
                    help=f"output JSON (default {DEFAULT_OUT})")
    ap.add_argument("--mode",   type=str,   default="uniform",
                    choices=["uniform", "normal", "hard"],
                    help="uniform = on-path; normal = brief OUT_PATH; hard = deep OUT_PATH")
    ap.add_argument("--margin", type=float, default=MARGIN_M, metavar="M",
                    help=f"safe-zone radius in metres (default {MARGIN_M})")
    ap.add_argument("--loops",  type=int,   default=0, metavar="N",
                    help="auto-compute ticks for N full path traversals (0 = use --ticks)")
    ap.add_argument("--gpx",     type=str,   default=GPX_FILE, metavar="FILE",
                    help="GPX file to simulate (default: activity_19135281495.gpx)")
    ap.add_argument("--terrain", action="store_true",
                    help="Enable terrain LOS obstruction (downloads DEM tiles from AWS)")
    ap.add_argument("--reliable", type=float, default=LORA_RELIABLE_M, metavar="M",
                    help=f"distance with guaranteed delivery (default {LORA_RELIABLE_M:.0f} m)")
    ap.add_argument("--max-range", type=float, default=LORA_MAX_M, metavar="M",
                    help=f"distance beyond which delivery is impossible (default {LORA_MAX_M:.0f} m)")
    args = ap.parse_args()
    record(args.ticks, args.out, args.mode, args.margin, args.loops, args.gpx, args.terrain,
           reliable_m=args.reliable, max_range_m=args.max_range)
