"""Animated 2-panel matplotlib visualizer for the HEARD simulator."""
from __future__ import annotations
import math
from typing import List, Tuple, Dict

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Circle
from matplotlib.lines import Line2D
import numpy as np

from utils import to_local
from config import (
    LORA_RELIABLE_M, LORA_MAX_M, LINK_FADE_TICKS,
    ANIM_INTERVAL_MS, SHOW_RANGE_CIRCLES, TICKS_PER_FRAME,
)

# ── Colour palette ────────────────────────────────────────────────────────
BG         = "#1a1a2e"
PANEL_BG   = "#16213e"
CORE_CLR   = "#e94560"
NODE_CLR   = "#0f3460"
NODE_EDGE  = "#53d8fb"
PATH_CLR   = "#53d8fb"
REQ_CLR    = "#f5a623"
WAIT_CLR   = "#7ed321"
POS_CLR    = "#bd10e0"
LINK_ALPHA_MAX = 0.85


def _kind_color(kind: str) -> str:
    return {"REQ": REQ_CLR, "WAIT": WAIT_CLR, "POS": POS_CLR}.get(kind, "#ffffff")


class Visualizer:
    def __init__(self, path_points, devices, radio, config_ref):
        self._path  = path_points
        self._devs  = devices
        self._radio = radio
        self._cfg   = config_ref

        # Compute origin as path midpoint
        mid = path_points[len(path_points) // 2]
        self._lat0 = mid.lat
        self._lon0 = mid.lon

        self._fig, (self._ax_map, self._ax_stats) = plt.subplots(
            1, 2, figsize=(14, 7),
            gridspec_kw={"width_ratios": [2, 1]},
        )
        self._fig.patch.set_facecolor(BG)
        for ax in (self._ax_map, self._ax_stats):
            ax.set_facecolor(PANEL_BG)
            for spine in ax.spines.values():
                spine.set_color("#334")

        self._setup_map()
        self._setup_stats()

        self._link_artists: List = []
        self._node_artists: Dict[int, plt.Artist] = {}
        self._tick_counter = [0]
        self._stats_history: Dict[str, List] = {"ticks": [], "delivered": [], "dropped": []}

    # ── Map panel setup ───────────────────────────────────────────────────

    def _setup_map(self):
        ax = self._ax_map
        ax.set_title("HEARD — Live Map", color="white", pad=8)
        ax.tick_params(colors="#aaa")
        ax.set_xlabel("East (m)", color="#aaa")
        ax.set_ylabel("North (m)", color="#aaa")

        # Draw path
        xs = [to_local(p.lat, p.lon, self._lat0, self._lon0)[0] for p in self._path]
        ys = [to_local(p.lat, p.lon, self._lat0, self._lon0)[1] for p in self._path]
        ax.plot(xs, ys, color=PATH_CLR, linewidth=1.2, alpha=0.4, zorder=1)

        if SHOW_RANGE_CIRCLES:
            for r, ls in [(LORA_RELIABLE_M, "--"), (LORA_MAX_M, ":")]:
                c = Circle((0, 0), r, fill=False, linestyle=ls,
                            edgecolor="#aaaaaa", linewidth=0.6, alpha=0.3, zorder=0)
                ax.add_patch(c)
                self._range_circles = getattr(self, "_range_circles", [])
                self._range_circles.append(c)

        ax.set_aspect("equal")

    # ── Stats panel setup ─────────────────────────────────────────────────

    def _setup_stats(self):
        ax = self._ax_stats
        ax.set_title("Protocol Metrics", color="white", pad=8)
        ax.tick_params(colors="#aaa")
        ax.set_xlabel("Tick", color="#aaa")
        ax.set_ylabel("Cumulative messages", color="#aaa")
        self._line_del, = ax.plot([], [], color=WAIT_CLR, label="delivered", linewidth=1.5)
        self._line_drp, = ax.plot([], [], color=CORE_CLR, label="dropped",   linewidth=1.5)
        ax.legend(facecolor=PANEL_BG, labelcolor="white", edgecolor="#334")

    # ── Animation ─────────────────────────────────────────────────────────

    def start(self, sim_step_fn, total_frames: int):
        """
        sim_step_fn: callable() that advances TICKS_PER_FRAME ticks.
        total_frames: number of animation frames (None = loop forever).
        """
        self._sim_step = sim_step_fn
        self._anim = animation.FuncAnimation(
            self._fig,
            self._frame,
            frames=total_frames,
            interval=ANIM_INTERVAL_MS,
            blit=False,
            repeat=False,
        )
        plt.tight_layout(pad=1.5)
        plt.show()

    def _frame(self, _frame_idx):
        self._sim_step()
        self._tick_counter[0] += TICKS_PER_FRAME
        tick = self._tick_counter[0]

        self._draw_links(tick)
        self._draw_devices()
        self._update_stats(tick)

    # ── Draw helpers ──────────────────────────────────────────────────────

    def _local(self, lat, lon):
        return to_local(lat, lon, self._lat0, self._lon0)

    def _draw_links(self, tick):
        ax = self._ax_map
        for art in self._link_artists:
            art.remove()
        self._link_artists.clear()

        for ev in self._radio.events:
            age = tick - ev.tick
            if age > LINK_FADE_TICKS:
                continue
            alpha = LINK_ALPHA_MAX * (1.0 - age / LINK_FADE_TICKS)
            color = _kind_color(ev.msg_kind) if ev.success else "#555"

            try:
                s = next(d for d in self._devs if d.get_id() == ev.sender_id)
                r = next(d for d in self._devs if d.get_id() == ev.recipient_id)
            except StopIteration:
                continue

            sx, sy = self._local(s.get_lat(), s.get_lon())
            rx, ry = self._local(r.get_lat(), r.get_lon())
            line, = ax.plot([sx, rx], [sy, ry],
                            color=color, alpha=alpha, linewidth=1.0, zorder=2)
            self._link_artists.append(line)

    def _draw_devices(self):
        ax = self._ax_map
        for art in self._node_artists.values():
            art.remove()
        self._node_artists.clear()

        for i, dev in enumerate(self._devs):
            x, y = self._local(dev.get_lat(), dev.get_lon())
            is_core = (i == 0)
            color    = CORE_CLR if is_core else NODE_CLR
            ec       = CORE_CLR if is_core else NODE_EDGE
            marker   = "*" if is_core else "o"
            size     = 180 if is_core else 80
            sc = ax.scatter([x], [y], s=size, c=color, marker=marker,
                            edgecolors=ec, linewidths=1.2, zorder=5)
            txt = ax.text(x + 15, y + 15, str(dev.get_id()),
                          color="white", fontsize=7, zorder=6)
            self._node_artists[dev.get_id()] = sc
            self._node_artists[str(dev.get_id()) + "_lbl"] = txt

    def _update_stats(self, tick):
        self._stats_history["ticks"].append(tick)
        self._stats_history["delivered"].append(self._radio.stats["delivered"])
        self._stats_history["dropped"].append(self._radio.stats["dropped"])

        t = self._stats_history["ticks"]
        self._line_del.set_data(t, self._stats_history["delivered"])
        self._line_drp.set_data(t, self._stats_history["dropped"])
        self._ax_stats.relim()
        self._ax_stats.autoscale_view()
