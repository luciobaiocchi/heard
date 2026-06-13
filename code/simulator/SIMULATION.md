# How the simulation works

A deep dive into the HEARD digital twin: the architecture, the physics models,
and the reasoning behind every parameter. For build/run instructions see
[README.md](README.md); for the build internals see [ARCHITECTURE.md](ARCHITECTURE.md).

## Architecture: three layers, one clock

```
┌────────────────────────────────────────────────────────────┐
│ C++ firmware (ConnectionManager) ── compiled via pybind11  │  protocol truth
├────────────────────────────────────────────────────────────┤
│ Python: world physics ── GPX movement, radio, terrain      │  environment
├────────────────────────────────────────────────────────────┤
│ Browser: MapLibre 3D replay of the recorded trace          │  observation
└────────────────────────────────────────────────────────────┘
```

The defining design decision: **the protocol is never reimplemented for
simulation**. `ConnectionManager.cpp` — the exact file flashed to the ESP32 —
is compiled on the host against small Arduino/FreeRTOS mocks (`mocks/`), where
`millis()` returns simulated time instead of wall-clock. When a test passes, it
is a statement about the shipping firmware, not about a model of it. Python's
job is only to play "the world": GPS positions, the radio channel, the terrain.
The parity suite (`tests/test_cpp_node_parity.py`) runs groups where *every*
device is the real C++ code, up to 3 relay hops deep.

## The clock

| Parameter | Value | Rationale |
|---|---|---|
| `TICK_S` | 0.1 s | Fine enough that protocol timing (2 s windows, 10 s timeouts) resolves to 20–100 ticks; coarse enough that a 2-hour hike simulates in seconds. Roughly one LoRa packet airtime, so "one message per device per tick" is a sane serialization. |

Per tick: (1) every device gets its new GPS position, (2) every device's
`step(sim_ms)` runs the protocol state machine, (3) the radio drains all
outgoing messages and delivers them probabilistically. A consequence worth
knowing: **each radio hop costs exactly one tick of latency** — relayed REQs
appear at `t+1` in traces.

## Movement: kinematics on a real GPX track

Devices move *along the recorded trail*, parameterized by cumulative distance
(`device_dist` in `sim_setup.py`), with positions linearly interpolated
between GPX points (`pos3d_at_dist`) so motion is continuous even where track
points are sparse.

| Parameter | Value | Rationale |
|---|---|---|
| `WALKING_SPEED` | 1.2 m/s | ≈ 4.3 km/h, relaxed hiking pace. |
| `MAX_SPREAD_M` | 1000 m | The group is strung out over up to 1 km of trail (`reverse=True` puts the core in front, like a guide). 1 km deliberately straddles the radio's reliable range when the trail switchbacks — it generates the interesting "edge of contact" cases. |

**Off-path excursions** (`ExcursionScheduler`) follow a trapezoid: ramp out
over `EXCURSION_RAMP_S = 1.5 s`, hold at peak, ramp back.

| Mode | Peak | Hold | Start prob/tick | Meaning |
|---|---|---|---|---|
| `uniform` | — | — | — | nobody leaves the path (baseline) |
| `normal` | 120 m | 5 s | 0.0015 | just past the 100 m corridor — tests detection at the boundary |
| `hard` | 250 m | 14 s | 0.005 | unambiguous emergencies |

`scripted` entries (e.g. node 1 at tick 30) guarantee a demo-visible event
early, regardless of dice.

## The radio channel

Delivery probability per recipient: `p = link_prob(d) × channel_factor`.

```
link_prob(d) = 1.0                          d ≤ LORA_RELIABLE_M
             = (1 − t)²                     between, t = (d−d_r)/(d_max−d_r)
             = 0.0                          d ≥ LORA_MAX_M
```

| Parameter | Value | Rationale |
|---|---|---|
| `LORA_RELIABLE_M` | 2000 m | Within solid link budget, LoRa in open mountain terrain is essentially lossless. |
| `LORA_MAX_M` | 5000 m | Beyond the noise floor. Field tests measured ~3 km usable in the open — deliberately placed between "reliable" and "max". |
| falloff `(1−t)²` | — | Packet success vs distance is not linear: SNR degrades with log-distance and a packet either decodes or doesn't — a knee, then a long soft tail. The exponent is a sensible shape but not yet fitted to field data (see ROADMAP). |

Both radii are per-run overridable (`record.py --reliable M --max-range M`) and
written into the trace meta, so the viewer's range circles always match the
physics that generated the data.

**Unicast overhearing**: LoRa is a broadcast medium, so every device in range
rolls the same dice on every transmission. Only the addressed recipient gets
the message injected into its protocol; overhears are logged
(`LinkEvent(overheard=True)`) and feed the connectivity table only — stats and
the link-arc visualization show protocol traffic exclusively.

## Terrain: real elevation, real diffraction

With `--terrain`, the channel factor comes from physics over real DEM data
(AWS Terrarium tiles, prefetched once for the track's bounding box).

| Parameter | Value | Rationale |
|---|---|---|
| `ZOOM` | 12 (~38 m/px) | Fine enough to capture a ridge between two hikers; coarse enough that a whole valley is ~10 tiles. |
| `ANTENNA_H` | 2 m | Chest/backpack height above ground. |
| `LOS_SAMPLES` | 30 | Samples every ~50–100 m on typical links — well below ridge width. |
| `LOS_BLOCK` | 0.05 | Floor: even a deep shadow leaks ~5 % of packets (diffraction, reflections); keeps rare lucky deliveries possible. |

For each link, the worst obstacle's **Fresnel–Kirchhoff parameter** is computed
— `v = h·√(2(d₁+d₂)/(λ·d₁·d₂))`, λ ≈ 0.345 m at 868 MHz — and converted to a
loss via the **ITU-R P.526 single knife-edge** approximation: 0 dB with full
Fresnel-zone clearance (v ≤ −1), −6 dB exactly grazing (v = 0), rapid decay
above. Note one model property the tests pin: on perfectly flat terrain the
ray *grazes* everywhere (v = 0 → factor 0.5) — flat ground at equal antenna
height is the half-obstructed worst case of the model, not full clearance.

## Protocol timing: one chain of inequalities

The timing constants (in `core/include/config.h` and `config.py`)
only work because they are ordered:

```
BROADCAST_WINDOW (2 s) < CM_ROUND_GAP_MS (5 s) < CM_REQUEST_INTERVAL_MS (10 s)
    ≤ CM_DEVICE_TIMEOUT_MS (10 s) < CM_GLOBAL_TIMEOUT_MS (30 s) < REACH_WINDOW (70 s)
```

- a round's internal relaying must finish (2 s) well before a node may treat
  the next REQ as a *new round* (5 s);
- the round-gap detector must be strictly shorter than the polling period, or
  relay-only nodes never reset their duplicate-suppression fingerprints (a
  real bug found by the test suite — see issue #2);
- a single device gets 10 s before the core drops it; the whole round caps at
  30 s, before the next poll would queue behind it;
- the connectivity table remembers for 70 s (`REACH_WINDOW_TICKS = 700`) —
  longer than one polling period, so a single dropped round doesn't flicker
  the table empty.

## Recording and replay

`record.py` snapshots every tick — or every `frame_stride` ticks once a run
exceeds `MAX_FRAMES = 5000`, capping trace size regardless of duration. Each
frame holds: device positions with GPS and DEM elevation, in/out-of-corridor
state, the stride window's radio events (overhears excluded), cumulative
delivery stats, and the rolling per-device "heard recently" sets.

Everything is **deterministic**: one seed (`RANDOM_SEED = 42`) drives device
placement, excursion dice, and every delivery roll — the same command produces
a byte-identical trace (enforced by `tests/test_record.py`).

The browser replays frames with position interpolation between strided frames
and radio-wave rings whose duration scales with playback speed. It is pure
visualization — no simulation happens client-side.
