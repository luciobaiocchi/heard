import os

# ── Paths ──────────────────────────────────────────────────────────────────
GPX_FILE = os.path.join(os.path.dirname(__file__), "../path_loader/activity_19135281495.gpx")

# ── Devices ────────────────────────────────────────────────────────────────
NUM_NODES       = 4        # number of Node devices (plus 1 Core = total 5)
MAX_SPREAD_M    = 1000.0   # nodes start within this many meters along the path
WALKING_SPEED   = 1.2      # m/s  (~4.3 km/h, relaxed hiking pace)
RANDOM_SEED     = 42

# ── Simulation clock ───────────────────────────────────────────────────────
TICK_S          = 0.1      # seconds per simulation tick
TICKS_PER_FRAME = 10       # simulation ticks advanced per animation frame (10× real-time)

# ── Radio (LoRa probabilistic model) ──────────────────────────────────────
LORA_RELIABLE_M = 2000.0   # distance below which p(delivery) = 1.0
LORA_MAX_M      = 5000.0   # distance above which p(delivery) = 0.0
                            # Between: quadratic falloff  p = (1 - t)²  where t ∈ [0,1]
                            # Values tuned for 868 MHz LoRa in open mountain terrain (1800–3400 m)

# ── Protocol timeouts (in ticks) ──────────────────────────────────────────
REQUEST_INTERVAL  = 100    # 10 s  — how often Core polls the group
                            #         (informational: the real value is
                            #         CM_REQUEST_INTERVAL_MS in core/include/config.h;
                            #         keep the two in sync)
GLOBAL_TIMEOUT    = 300    # 30 s  — Core gives up on the entire round
DEVICE_TIMEOUT    = 100    # 10 s  — Core drops one non-responding relay
BROADCAST_WINDOW  = 20     #  2 s  — Node waits this long for downstream WAITs
                            #         before assuming it is the end of the chain

# ── Visualizer ─────────────────────────────────────────────────────────────
LINK_FADE_TICKS = 40       # how many ticks a drawn LoRa link fades over
ANIM_INTERVAL_MS = 50      # ms between animation frames  (~20 fps)
SHOW_RANGE_CIRCLES = True  # draw reliable/max range circles around Core

# ── Path / safe-zone ───────────────────────────────────────────────────────
MARGIN_M = 100.0           # off-path detection threshold (mirrors firmware Path(maxDistance=100))
REACH_WINDOW_TICKS = 700   # rolling window for per-device "heard from" connectivity
                            # kept > REQUEST_INTERVAL (100) so reach persists between rounds

# ── Off-path excursion model ───────────────────────────────────────────────
EXCURSION_RAMP_S = 1.5     # seconds to ramp out (and back in) to the peak offset

# Params per mode. "scripted" = [(node_idx, start_tick)] forced early excursions for demo.
MODE_PARAMS = {
    "uniform": None,        # no excursions; all devices stay on path
    "normal": {
        "peak_m":        120.0,   # peak lateral offset (crosses 100 m threshold)
        "hold_s":          5.0,   # seconds at peak; total out ≈ hold_s + small ramp slices
        "prob_per_tick": 0.0015,  # random start probability per node per tick
        "scripted":      [(1, 30)],
    },
    "hard": {
        "peak_m":        250.0,
        "hold_s":         14.0,   # total out ≈ 15 s
        "prob_per_tick": 0.005,
        "scripted":      [(1, 30), (2, 120), (3, 240)],
    },
}
