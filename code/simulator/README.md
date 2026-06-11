# HEARD Simulator

Discrete-event simulator for the **HEARD** (Hiking Emergency Assistance and Rescue Device) LoRa group-positioning protocol. The simulator runs the real firmware C++ (`ConnectionManager`) alongside a Python-controlled world (GPS, radio, terrain) to validate protocol behaviour under realistic hiking scenarios.

---

## Table of Contents

1. [What HEARD does](#1-what-heard-does)
2. [System architecture](#2-system-architecture)
3. [Protocol explained](#3-protocol-explained)
4. [Radio model](#4-radio-model)
5. [Terrain and LOS model](#5-terrain-and-los-model)
6. [Safe-zone detection](#6-safe-zone-detection)
7. [Prerequisites and installation](#7-prerequisites-and-installation)
8. [Quick start](#8-quick-start)
9. [Recording a simulation trace](#9-recording-a-simulation-trace)
10. [Web viewer](#10-web-viewer)
11. [Map styles](#11-map-styles)
12. [Live matplotlib view](#12-live-matplotlib-view)
13. [Configuration reference](#13-configuration-reference)
14. [Project structure](#14-project-structure)
15. [Running the tests](#15-running-the-tests)
16. [Extending the simulator](#16-extending-the-simulator)

---

## 1. What HEARD does

HEARD is a hiking group-safety system built on ESP32 + LoRa radio. A designated **core** device (worn by the group leader) periodically polls the rest of the group for GPS positions. Each **node** device (worn by other hikers) receives the poll, relays it further into the group via multi-hop mesh, and replies with its own position. The core accumulates all responses and can detect if any hiker has left the safe zone around the trail (OUT_PATH state).

The key challenge the simulator tests: **can every node reach the core in mountainous terrain**, given LoRa's range limits and possible terrain obstruction?

---

## 2. System architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Python "world"                                                 │
│                                                                 │
│  record.py / main.py                                            │
│    │                                                            │
│    ├── gpx_loader.py    — reads real GPS trail, interpolates    │
│    ├── sim_setup.py     — builds devices, advances ticks        │
│    ├── path_state.py    — firmware-faithful OUT_PATH detection  │
│    ├── terrain.py       — DEM tiles, LOS obstruction check      │
│    └── radio.py         — probabilistic LoRa delivery           │
│         │                                                       │
│         ├── SimDevice (C++)  — real firmware, pybind11 wrapper  │
│         └── NodeDevice (Py) — relay node, pure Python           │
└─────────────────────────────────────────────────────────────────┘

          ↓  writes trace.json

┌──────────────────────────────────────────────┐
│  Web viewer  (web/index.html + app.js)        │
│  MapLibre GL JS — 3D terrain, replay playback │
└──────────────────────────────────────────────┘
```

### Core components

| Component | Language | Responsibility |
|---|---|---|
| `SimDevice` | C++ (pybind11) | Runs the real `ConnectionManager` firmware, manages the REQ/WAIT/POS protocol |
| `NodeDevice` | Python | Simulates a relay/endpoint node: receives REQ, re-broadcasts with hop-list appended, replies with POS |
| `SimRadio` | Python | Probabilistic LoRa medium: delivers or drops messages based on distance and optional terrain LOS |
| `record.py` | Python | Headless simulation runner; records frames to `web/trace.json` for web replay |
| `main.py` | Python | Live animated matplotlib window for quick debugging |
| Web viewer | JavaScript | MapLibre GL JS 3D map with timeline scrubbing, protocol panels, radio wave animation |

### C++ integration detail

The firmware's `ConnectionManager` runs unmodified. Three minimal changes were made to the firmware headers to enable simulation (all non-breaking):

- `Connection.h` — six methods marked `virtual` + virtual destructor
- `ConnectionManager.h` — `step(unsigned long sim_ms)` declaration added
- `ConnectionManager.cpp` — `step()` implemented as one synchronous task-loop iteration

`SimConnection` replaces the hardware `Connection` with two in-memory queues (`inQueue` / `outQueue`). Python drains `outQueue` and fills `inQueue` every tick via `SimRadio`. The `millis()` Arduino function returns `g_sim_ms`, which `SimDevice::step()` sets before calling `ConnectionManager::step()`, so all firmware timeouts use the simulated clock.

---

## 3. Protocol explained

The protocol has one type of polling round, initiated every 60 seconds by the core:

### Round flow

```
Core (C++ firmware)                     Node (Python)
────────────────────────────────────    ─────────────────────────────────────
broadcasts  REQ|0|<knownPos>
                                        ← receives REQ|0|
                                        → broadcasts REQ|0,N|     (hop-list extended)
                                        schedules POS in 3 ticks

receives    REQ|0,N|                    (core's own ID found in hop-list → this is
→ adds N to pendingDevices               a registration from node N)
→ sends WAIT|0  to sender
                                        ← receives WAIT (acknowledged, no action)
                                        → broadcasts POS|N,lat,lon

receives    POS|N,lat,lon
→ stores position for N
→ removes N from pendingDevices
→ (round ends when pendingDevices empty, or global timeout 30 s)
```

### Multi-hop mesh

This is **not** a naive star topology. The core broadcasts REQ once; each receiving node re-broadcasts it with its own ID appended to the hop list. Nodes out of direct range of the core can still register if another node relays the REQ to them.

Example with 3 nodes where Node 3 is out of core range:

```
Core → broadcasts REQ|0|
  Node 1 hears it → broadcasts REQ|0,1|
    Node 3 hears REQ|0,1| → broadcasts REQ|0,1,3|
      Core hears REQ|0,1,3| → registers Node 3
```

### Deduplication

Each node tracks a set of hop-list **fingerprints** it has already relayed this round (`_responded_hops`). If the same chain arrives again (e.g., via two different paths), the second copy is silently dropped. The set is cleared at the start of each new round (detected by a time gap > 10 s from the last core REQ).

### Message types

| Type | Format | Sender | Meaning |
|---|---|---|---|
| `REQ` | `REQ\|<hopList>\|<knownPos>` | Core, then relayed by nodes | Poll the group; hop list grows at each relay |
| `WAIT` | `WAIT\|<coreId>` | Core → node | Acknowledgement: "I know you exist, send your position" |
| `POS` | `POS\|<id>,<lat>,<lon>` | Node (broadcast) | GPS position reply |

---

## 4. Radio model

`SimRadio` implements a **quadratic falloff** delivery probability:

```
p(d) = 1.0                                          d ≤ d_reliable
p(d) = ( 1 − (d − d_r) / (d_max − d_r) )²          d_r < d < d_max
p(d) = 0.0                                          d ≥ d_max
```

Default values are `d_reliable = 2000 m` and `d_max = 5000 m` (tuned for 868 MHz LoRa in open mountain terrain). Both can be overridden per-run with `--reliable` and `--max-range`; the chosen values are written into `trace.json` so the viewer's range circles and wave radii adapt automatically.

Every tick, `SimRadio.tick()`:
1. Snapshots all devices' outgoing queues (snapshot prevents the order of delivery from mattering).
2. For each message and each potential recipient, rolls a seeded random number against `p(d)`.
3. If delivered, calls `recipient.inject_message()`; logs a `LinkEvent` either way.
4. Optionally multiplies `p(d)` by the terrain propagation factor from `Environment` (see §5).

All randomness uses `random.Random(RANDOM_SEED)`, so every run with the same seed is bit-for-bit identical.

### Unicast overhearing

LoRa is a broadcast medium: when device A sends a unicast to device B, every other device in range can also hear it. `SimRadio` models this by rolling a delivery check (same `link_prob × channel_factor`) for each bystander after the addressed unicast is resolved. Overheard receptions are logged as `LinkEvent(overheard=True)`: they count toward the connectivity table but are **not** injected into the protocol, do **not** affect sent/delivered/dropped statistics, and are **excluded** from the link-arc visualisation so it shows protocol traffic only.

---

## 5. Terrain and LOS model

Enabled with `--terrain` flag. Disabled by default.

### How it works

When `--terrain` is active, `record.py` creates a `Terrain` instance and wraps it in an `Environment`. Before rolling the delivery die for each link, `Environment.signal_factor()` calls `Terrain.fresnel_factor()`, which samples 30 equally-spaced interior points along the path between the two devices and computes the worst-case **ITU-R P.526 single knife-edge diffraction** parameter *v* across all obstacles. The result is converted to a linear amplitude factor in the range `[LOS_BLOCK .. 1.0]`:

- *v < −1*: full Fresnel-zone clearance → factor **1.0** (no change)
- *v = 0*: obstacle just touching line-of-sight → factor **~0.5** (−6 dB)
- *v > 0*: obstacle above line-of-sight → rapid decay toward **LOS_BLOCK (0.05)**

This replaces the old binary obstruction model; the `Environment` class is the single entry-point for all channel physics so adding further effects (vegetation, rain attenuation) does not require touching `radio.py`.

### Elevation data

Elevation tiles are fetched from **AWS terrain tiles** (`elevation-tiles-prod`) at zoom level 12 (~38 m/pixel resolution), the same source used by the 3D web viewer. The tiles use the **terrarium encoding**: `elevation_m = R × 256 + G + B/256 − 32768`.

On first run with `--terrain`, all tiles covering the GPX bounding box are downloaded and cached in memory (typically 4–10 tiles, ~1 MB, ~2 s download). Subsequent simulation ticks do in-memory lookups only (O(1)).

### Limitations

- 38 m/pixel resolution: ridges narrower than ~40 m are invisible to the model.
- Single knife-edge model: multiple sequential ridges are not summed — only the worst obstacle contributes.
- DEM source differs slightly from GPX elevation (GPS noise vs. SRTM raster).

---

## 6. Safe-zone detection

Each device is classified as **IN_PATH** or **OUT_PATH** every tick. This replicates the firmware's `StateManager::updateState()` / `Path::isInsidePath()` exactly:

1. Find the nearest trail point (vectorised numpy squared-distance, then one haversine).
2. If that distance ≤ 100 m → **IN_PATH**.
3. Else check perpendicular distance to the segment between the nearest point and its predecessor (or successor if it is the first point). If ≤ 100 m → **IN_PATH**.
4. Otherwise → **OUT_PATH**.

The 100 m threshold is `MARGIN_M` in `config.py`, matching `Path(maxDistance=100)` in the firmware.

### Excursion modes

`record.py --mode` controls how devices wander off the trail:

| Mode | Behaviour | OUT_PATH duration |
|---|---|---|
| `uniform` | All devices stay on the path (default) | Never |
| `normal` | ~1 node briefly crosses 100 m boundary | ~5–6 s per excursion |
| `hard` | Multiple nodes go deep (up to 250 m off) | ~15 s per excursion |

Off-path movement uses a **trapezoid lateral profile**: `ramp-out (1.5 s) → hold at peak → ramp-back-in`. Excursions are partly scripted (deterministic demo events at known ticks) and partly random (seeded, so reproducible).

---

## 7. Prerequisites and installation

### Python dependencies

```bash
pip install -r requirements.txt
# matplotlib>=3.7  numpy>=1.24  pybind11>=2.11  pytest>=7.4
```

### C++ module (optional but recommended)

Without the C++ module the simulator still runs — the core device falls back to a Python `NodeDevice`, so the real firmware protocol is not tested.

Requirements: **cmake ≥ 3.14**, a C++17 compiler (clang or gcc).

```bash
cd code/simulator
mkdir build && cd build
cmake ..
make -j$(nproc)        # Linux / macOS
# or: cmake --build . --parallel
cp heard_sim*.so ..    # copy the shared library next to the Python files
```

On macOS with Apple Silicon you may need:
```bash
cmake .. -DCMAKE_OSX_ARCHITECTURES=arm64
```

Verify the build:
```bash
python3 -c "from heard_sim import SimDevice; print('C++ module OK')"
```

---

## 8. Quick start

```bash
cd code/simulator

# 1. Record a 2-minute simulation (default trail, uniform mode)
python3 record.py

# 2. Serve the web viewer
cd web && python3 -m http.server 8000

# 3. Open http://localhost:8000 in a browser
```

The viewer loads `trace.json` automatically. Press **Play** to watch the simulation.

---

## 9. Recording a simulation trace

`record.py` runs the simulation headlessly and writes `web/trace.json`.

### Basic usage

```bash
python3 record.py                          # 120 s, default trail, uniform mode
python3 record.py --ticks 3600             # 360 s simulation
python3 record.py --loops 1               # one full traversal of the trail
python3 record.py --loops 2 --mode normal # two traversals, brief excursions
python3 record.py --mode hard             # deep off-path excursions
python3 record.py --margin 150            # 150 m safe-zone instead of 100 m
python3 record.py --gpx /path/to/my.gpx  # use a different GPX file
python3 record.py --terrain               # enable terrain LOS obstruction
```

### All options

| Flag | Default | Description |
|---|---|---|
| `--ticks N` | 1200 | Number of simulation ticks (1 tick = 0.1 s). Overridden by `--loops`. |
| `--loops N` | 0 | Auto-compute ticks for N complete trail traversals. |
| `--mode` | `uniform` | Excursion mode: `uniform`, `normal`, or `hard`. |
| `--margin M` | 100.0 | Safe-zone radius in metres (mirrors firmware threshold). |
| `--gpx FILE` | built-in trail | Path to a GPX file. Any GPS-recorded track works. |
| `--terrain` | off | Enable DEM tile download + Fresnel knife-edge terrain check. |
| `--reliable M` | 2000.0 | Distance (m) below which delivery probability = 100%. Written into trace meta. |
| `--max-range M` | 5000.0 | Distance (m) above which delivery probability = 0%. Written into trace meta. |
| `--out PATH` | `web/trace.json` | Output file path. |

### Output file

`trace.json` contains:

```jsonc
{
  "meta": {
    "tick_s": 0.1,
    "num_ticks": 1200,
    "frame_stride": 1,        // 1 = every tick recorded; >1 = subsampled
    "lora_reliable_m": 2000.0,
    "lora_max_m": 5000.0,
    "mode": "normal",
    "margin_m": 100.0,
    "devices": [{"id": 0, "role": "core"}, {"id": 1, "role": "node"}, ...]
  },
  "path": [[lat, lon, ele], ...],        // thinned trail polyline (≤2000 pts)
  "margin_left":  [[lat, lon], ...],     // safe-zone corridor, left side
  "margin_right": [[lat, lon], ...],     // safe-zone corridor, right side
  "frames": [
    {
      "tick": 0,
      "sim_ms": 0,
      "devices": [
        {"id": 0, "lat": ..., "lon": ..., "ele": ..., "out": false, "reach": [1, 2]}
      ],
      "links": [
        {"src": 0, "dst": 1, "kind": "REQ", "ok": true, "tick": 0}
      ],
      "metrics": {"sent": 4, "delivered": 3, "dropped": 1},
      "state": {"req_active": true, "known": [{"id": 1, "lat": ..., "lon": ...}]}
    }
  ]
}
```

For long runs, frames are **subsampled** to at most 5000 entries (`MAX_FRAMES`) to keep the file manageable. The `frame_stride` field records the subsampling factor; the viewer accounts for it automatically.

---

## 10. Web viewer

### Starting the viewer

```bash
cd code/simulator/web
python3 -m http.server 8000
# open http://localhost:8000
```

> The viewer must be served over HTTP, not opened as a local file, because it fetches `trace.json` via `fetch()`.

### Interface

```
┌──────────────────────────────────┬─────────────────────┐
│                                  │  Protocol State      │
│                                  │  Radio Metrics       │
│         3D Map                   │  Message Log         │
│                                  │  Connectivity        │
│                                  │                      │
├──────────────────────────────────┴─────────────────────┤
│  ▶  t 120 (12 s)    [━━━━━━━━━━━━━━━━━━━━]   1× ▾     │
└─────────────────────────────────────────────────────────┘
```

### Map elements

| Element | Description |
|---|---|
| Blue polyline | GPX trail draped on 3D terrain |
| Green ribbon | Safe-zone corridor (±`margin_m` perpendicular to trail) |
| ★ Core dot | Core device; red when request is active |
| N1–N4 dots | Node devices; turns red + ⚠ when OUT_PATH |
| Coloured arcs | LoRa links: orange = REQ, blue = WAIT, green = POS; dashed = dropped. Overheard unicasts are not shown. |
| Expanding rings | Radio wave propagation animation (one ring per broadcast event); ring duration scales with playback speed so they remain visible at 50–100× |
| White circles | Core's LoRa range: inner = reliable radius, outer = max radius (values from trace meta) |
| Coloured trails | Recent path of each device (last 60 s of sim time) |

Device dots and labels are rendered as **native MapLibre GL layers** (GeoJSON source "devices" → circle layer + symbol layer), not DOM elements. The GPU positions them using the same DEM as the terrain, so they cannot float off the surface. Positions are linearly interpolated between recorded frames for smooth motion at any playback speed.

### Playback controls

| Control | Action |
|---|---|
| **▶ / ⏸** | Play / pause |
| Timeline slider | Scrub to any tick |
| Speed selector | 1× / 5× / 10× / 20× / 50× / 100× real-time |

### Sidebar panels

**Protocol State** — shows whether a REQ round is active and the core's current known-position table.

**Radio Metrics** — cumulative sent / delivered / dropped counts and delivery rate sparkline.

**Message Log** — scrolling list of every link event at the current tick (`t12 REQ 0→all ✓`). Color-coded by message type.

**Connectivity** — per-device "heard from" table: which devices each device has successfully received a message from within the last ~70 simulation seconds (REACH_WINDOW_TICKS = 700). The table is directional: each row is the listener, each column a potential sender. Unicast overhears count toward connectivity even though they carry no protocol message.

**Debug overlay** — press **`d`** to toggle. Shows per-device GPS altitude (from the trace) alongside the DEM elevation looked up from the terrain tiles, useful for diagnosing floating markers or elevation mismatches.

---

## 11. Map styles

Edit `web/config.js` (copy from `config.js.example`) to choose the basemap:

```js
window.MAP_STYLE_KEY = 'outdoor';    // default — topo + contour lines
window.MAP_STYLE_KEY = 'satellite';  // aerial photography
window.MAP_STYLE_KEY = 'hybrid';     // satellite + road/place labels
window.MAP_STYLE_KEY = 'topo';       // clean topographic map
```

| Style key | Without API key | With MapTiler key |
|---|---|---|
| `outdoor` | OpenFreeMap liberty | MapTiler outdoor-v2 (contours, hillshade) |
| `satellite` | ESRI World Imagery (free) | MapTiler satellite |
| `hybrid` | ESRI satellite + labels | MapTiler hybrid |
| `topo` | OpenFreeMap positron | MapTiler topo-v2 |

3D terrain and hillshading are loaded from **AWS terrarium tiles** (`elevation-tiles-prod`) regardless of the chosen basemap style.

### Getting a free MapTiler key

1. Sign up at [maptiler.com](https://maptiler.com)
2. Go to **API Keys → Create a key**
3. Add to `web/config.js`:
   ```js
   window.MAPTILER_KEY = 'your_key_here';
   ```

The free tier allows 100 000 tile requests/month, which is more than enough for local development.

---

## 12. Live matplotlib view

`main.py` shows a real-time animated window for quick inspection without generating a trace file.

```bash
python3 main.py
```

Two panels update live at ~20 fps (10× real-time):

- **Left panel** — 2D trail map with device positions, LoRa link arcs, and range circles.
- **Right panel** — cumulative delivered / dropped message count over time.

Close the window to exit. This view does not support terrain or excursion modes; use `record.py` for those.

---

## 13. Configuration reference

All parameters live in `config.py`. Changes take effect on the next `python3 record.py` or `python3 main.py` run.

### Devices and movement

| Parameter | Default | Description |
|---|---|---|
| `NUM_NODES` | 4 | Number of relay nodes. Total devices = NUM_NODES + 1 core. |
| `MAX_SPREAD_M` | 1000 m | Nodes start spread over this distance along the trail. |
| `WALKING_SPEED` | 1.2 m/s | Hiking pace (~4.3 km/h). All devices walk at this speed. |
| `RANDOM_SEED` | 42 | Seed for all randomness. Change for a different but reproducible run. |

### Simulation clock

| Parameter | Default | Description |
|---|---|---|
| `TICK_S` | 0.1 s | Real time per simulation tick. 10 ticks = 1 simulated second. |
| `TICKS_PER_FRAME` | 10 | Ticks per matplotlib animation frame (live view only). |

### LoRa radio model

| Parameter | Default | Description |
|---|---|---|
| `LORA_RELIABLE_M` | 2000 m | Distance below which delivery probability = 100%. |
| `LORA_MAX_M` | 5000 m | Distance above which delivery probability = 0%. Between these, quadratic falloff. |

Both values can be overridden per-run with `--reliable` and `--max-range` without editing `config.py`.

### Protocol timeouts

These mirror the firmware constants in `ConnectionManager.cpp`:

| Parameter | Default | Description |
|---|---|---|
| `REQUEST_INTERVAL` | 600 ticks (60 s) | How often the core starts a new polling round. |
| `GLOBAL_TIMEOUT` | 300 ticks (30 s) | Core abandons the round if not all nodes responded. |
| `DEVICE_TIMEOUT` | 100 ticks (10 s) | Core drops a single non-responding node. |
| `BROADCAST_WINDOW` | 20 ticks (2 s) | Node waits this long for downstream WAITs before assuming it is the last hop. |

### Safe-zone

| Parameter | Default | Description |
|---|---|---|
| `MARGIN_M` | 100 m | Off-path distance threshold. Mirrors firmware `Path(maxDistance=100)`. |
| `REACH_WINDOW_TICKS` | 700 | Rolling window size for connectivity table (~70 s, > one full protocol round). |

### Excursion model

| Parameter | Default | Description |
|---|---|---|
| `EXCURSION_RAMP_S` | 1.5 s | Time to ramp from 0 to peak offset (and back). |
| `MODE_PARAMS["normal"].peak_m` | 120 m | Peak lateral offset for `--mode normal`. |
| `MODE_PARAMS["normal"].hold_s` | 5 s | Time spent at peak before returning. |
| `MODE_PARAMS["hard"].peak_m` | 250 m | Peak lateral offset for `--mode hard`. |
| `MODE_PARAMS["hard"].hold_s` | 14 s | Time spent at peak for hard mode. |

### Terrain

| Parameter | In `terrain.py` | Description |
|---|---|---|
| `ZOOM` | 12 | DEM tile zoom level (~38 m/pixel at mid-latitudes). |
| `ANTENNA_H` | 2.0 m | Antenna height above ground added to both link endpoints. |
| `LOS_SAMPLES` | 30 | Number of interior points sampled along each link for the knife-edge check. |
| `LOS_BLOCK` | 0.05 | Minimum propagation factor floor for a deeply obstructed path (5% of normal). |

---

## 14. Project structure

```
code/simulator/
│
├── config.py           — all tunable parameters
├── gpx_loader.py       — GPX parser, path interpolation, lateral offset
├── path_state.py       — firmware-faithful isInsidePath / dist_to_segment
├── radio.py            — SimRadio: probabilistic LoRa delivery, unicast overhearing
├── terrain.py          — AWS DEM tile fetcher, elevation lookup, Fresnel knife-edge LOS
├── environment.py      — unified propagation entry-point (wraps terrain + future layers)
├── node_device.py      — Python relay node (REQ relay, POS reply)
├── sim_setup.py        — build_devices, advance_one_tick, ExcursionScheduler
├── utils.py            — haversine, equirectangular projection
│
├── record.py           — headless runner → web/trace.json
├── main.py             — live matplotlib animated view
├── visualizer.py       — matplotlib rendering helpers (used by main.py)
│
├── bindings.cpp        — pybind11 module exposing SimDevice to Python
├── CMakeLists.txt      — build config for heard_sim.so
├── heard_sim.so        — compiled C++ module (generated by cmake)
│
├── sim/
│   ├── SimDevice.h/cpp     — wraps ConnectionManager for Python
│   └── SimConnection.h/cpp — queue-based LoRa Connection stub
│
├── mocks/              — Arduino.h, FreeRTOS, SPI, LoRa stubs for compilation
│
├── tests/
│   ├── conftest.py         — shared pytest fixtures
│   ├── test_gpx_loader.py  — GPX parsing and interpolation
│   ├── test_path_state.py  — isInsidePath geometry + excursion profiles
│   ├── test_radio.py       — delivery model, broadcast/unicast mechanics
│   ├── test_protocol.py    — REQ/WAIT/POS flow, relay deduplication
│   ├── test_utils.py       — haversine, local projection
│   └── test_integration.py — full stack (C++ + Python) integration
│
├── web/
│   ├── index.html          — viewer page structure (MapLibre GL JS v4)
│   ├── app.js              — thin orchestrator: imports from web/js/
│   ├── style.css           — dark sidebar and panel styles
│   ├── config.js.example   — copy to config.js, set MAP_STYLE_KEY / MAPTILER_KEY
│   ├── config.js           — your local key config (git-ignored)
│   ├── trace.json          — generated by record.py (git-ignored)
│   └── js/
│       ├── constants.js    — TERRAIN_EXAG, colour palette, unit circle
│       ├── style.js        — MAP_STYLE / MAPTILER_KEY resolution
│       ├── geo.js          — circleFeature, buildWaveEvents
│       ├── trace.js        — loadTrace() — fetch + parse trace.json
│       ├── map-setup.js    — createMap() — MapLibre map + terrain + sky
│       ├── layers.js       — addStaticLayers, addDynamicLayers
│       ├── markers.js      — addDeviceLayers, updateDevices (native GL layers)
│       ├── render.js       — createRenderer — range circles, trails, waves, links
│       ├── sidebar.js      — createSidebar — panel updates + sparkline
│       ├── playback.js     — createPlayback — rAF loop + controls
│       └── debug.js        — createDebugOverlay — press 'd' to toggle
│
└── requirements.txt    — Python dependencies
```

### Related firmware (read-only)

```
code/dispositivo_madre/
├── src/group/ConnectionManager.cpp   — core protocol logic (runs inside SimDevice)
├── src/group/Connection.cpp          — hardware LoRa driver (replaced by SimConnection)
├── include/group/ConnectionManager.h
└── include/group/Connection.h
```

---

## 15. Running the tests

```bash
cd code/simulator
pytest tests/ -v
```

59 tests, organised by module. Tests that exercise `SimDevice` are automatically skipped if `heard_sim.so` is not built.

```
tests/test_utils.py          — 5  tests   haversine, projection
tests/test_gpx_loader.py     — 8  tests   GPX parsing, interpolation
tests/test_radio.py          — 12 tests   link model, broadcast, stats
tests/test_protocol.py       — 14 tests   REQ→WAIT→POS, deduplication
tests/test_path_state.py     — 12 tests   isInsidePath, excursion profiles
tests/test_integration.py    — 8  tests   full stack (requires heard_sim.so)
```

To run only tests that do not need the C++ module:

```bash
pytest tests/ -v -k "not integration"
```

---

## 16. Extending the simulator

### Add a new GPX trail

```bash
python3 record.py --gpx /path/to/your/trail.gpx --loops 1
```

Any GPX file exported from a GPS watch, Strava, Komoot, etc. works. The file needs `<trkpt lat="..." lon="...">` elements; `<ele>` is optional (defaults to 0 if absent).

### Change the number of nodes

Edit `config.py`:
```python
NUM_NODES = 6   # core + 6 nodes = 7 total devices
```

### Adjust the radio model

The delivery probability curve is in `radio.py:SimRadio.link_prob()`. The current model is quadratic falloff. You can swap in a log-distance path loss model, add shadowing variance, or change the default thresholds in `config.py` (`LORA_RELIABLE_M` / `LORA_MAX_M`). For a one-off run without editing config, use `--reliable` and `--max-range`.

### Add a new excursion pattern

Add an entry to `MODE_PARAMS` in `config.py`:
```python
"extreme": {
    "peak_m":        400.0,
    "hold_s":         30.0,
    "prob_per_tick":  0.01,
    "scripted":       [(1, 10), (2, 50)],
},
```
Then use `--mode extreme` with `record.py`.

### Add a new sidebar panel to the web viewer

The sidebar is plain HTML in `web/index.html`. Add a `<div class="panel">` block, then update `web/js/sidebar.js` (the `update(frame)` function) to populate it from the current `frame` object on each tick.
