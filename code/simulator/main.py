"""HEARD protocol simulator entry point (matplotlib live view)."""
from __future__ import annotations
import sys
import os
import random

sys.path.insert(0, os.path.dirname(__file__))

from config import GPX_FILE, RANDOM_SEED, TICKS_PER_FRAME
from gpx_loader import load_gpx
from sim_setup import build_devices, advance_one_tick, build_radio
from visualizer import Visualizer


def make_sim_step(devices, radio, path_points, tick_holder: list):
    def step():
        for _ in range(TICKS_PER_FRAME):
            advance_one_tick(devices, radio, path_points, tick_holder[0])
            tick_holder[0] += 1
    return step


def main():
    rng = random.Random(RANDOM_SEED)
    path_points = load_gpx(GPX_FILE)
    print(f"Loaded GPX: {len(path_points)} points, "
          f"{path_points[-1].cum_dist:.0f} m total")

    devices = build_devices(path_points, rng)
    radio   = build_radio()
    tick_holder = [0]

    print(f"Devices: {[d.get_id() for d in devices]}")
    print("Starting simulation…  (close the window to exit)")

    vis = Visualizer(path_points, devices, radio, None)
    sim_step = make_sim_step(devices, radio, path_points, tick_holder)
    vis.start(sim_step, total_frames=None)


if __name__ == "__main__":
    main()
