# Roadmap

Where HEARD goes from here. The thesis delivered the architecture and a working
demo; this is the path from prototype to something people can actually carry.
Items link to issues where one exists — contributions welcome on any of them.

## 1. Firmware

- **Standalone Node build** ([#1](https://github.com/luciobaiocchi/heard/issues/1)) —
  the protocol now implements both roles (PR #3); what's left is packaging:
  extract `ConnectionManager`/`Connection` into a shared library used by both
  PlatformIO projects, give `node` a real `main` (protocol + GPS
  + path check, no display), and select the role/device id via build flag or
  NVS instead of a hardcoded constant.
- **Field test the multi-hop chain** — the 2-hop and 3-hop relay rounds are
  proven in simulation only; they need a real-world walk with 3+ devices.
- **Battery + power budget** — the prototypes run without a battery. Pick a
  cell, measure real consumption per role (a node that polls every 10 s has a
  very different budget than one polling every 60 s), add deep-sleep between
  protocol rounds.
- **Duty-cycle compliance** — at 868 MHz (EU) the legal limit is 1 % airtime
  per channel. Model it, then enforce it in firmware (adaptive polling
  interval based on group size and hop depth).

## 2. Better simulator

- **All-C++ groups in the recorder** — the parity tests already run
  all-real-firmware groups; add `record.py --cpp-nodes` so recorded traces
  (and the 3D replay) exercise the firmware on every device instead of the
  Python stand-in.
- **Fit the radio model to field data** — the `(1−t)²` falloff is a sensible
  shape but not fitted; collect packet-loss-vs-distance measurements with the
  real prototypes and calibrate `link_prob` against them.
- **Airtime and collisions** — today the medium delivers any number of
  messages per tick with no interference. Model packet airtime (SF, bandwidth,
  payload length) and collisions when two devices transmit simultaneously —
  this is what limits real flooding protocols, and the simulator currently
  can't see it.
- **Battery model** — charge consumed per TX/RX/sleep tick, so protocol
  changes can be evaluated in days-of-battery, not just delivery %.
- **Monte Carlo batch runs** — sweep seeds/parameters headlessly and output
  aggregate statistics (delivery %, detection latency, worst-case
  out-of-contact time) instead of inspecting single runs by eye.
- **Scenario library** — more GPX tracks (forest switchbacks, canyon, glacier
  traverse) with terrain, as named regression scenarios.

## 3. Communication layer: MeshCore / Meshtastic

The custom REQ/WAIT/POS flooding was the right thesis exercise, but mature
open-source LoRa mesh stacks now exist. HEARD's real value is the **safety
application layer** (route corridor, group accounting, leader UX) — the
transport could be delegated:

- **[Meshtastic](https://meshtastic.org)** — the largest ecosystem: managed
  flood routing, AES-encrypted channels, region-correct radio presets with
  duty-cycle handling, phone apps, and broad tested hardware (T-Beam, T-Echo
  with GPS/e-ink). Integration path: a custom firmware **module**
  (`MeshModule` subclass + custom portnum) that broadcasts compact
  IN_PATH/OUT_PATH state changes and, on the leader's device, aggregates the
  node DB into the "all accounted for" view. Design inversion to accept:
  Meshtastic is push-based (periodic position broadcasts), HEARD is
  poll-based — on a mesh, push is simpler and cheaper, so the leader module
  watches who is silent/off-path rather than polling. License: GPL-3.0
  (compatible: our Apache-2.0 code can be contributed into a GPL module).
- **[MeshCore](https://github.com/ripplebiz/MeshCore)** — a lighter
  alternative: a C++ mesh routing library designed to be embedded into custom
  firmware rather than replacing it. Better fit if HEARD keeps its own
  firmware identity (display, buttons, path engine) and swaps only the
  transport underneath `Connection`. Smaller community than Meshtastic, but
  much closer to HEARD's "library, not platform" needs.
- **Decision experiment**: port `Connection` to each stack behind the existing
  interface, run the same simulated scenarios (the simulator's application
  logic is transport-agnostic), and compare delivery %, latency, airtime and
  battery. The simulator is the differentiator here — nobody else in either
  ecosystem has a firmware-in-the-loop 3D testbed for this comparison.

## 4. Safety detection criteria

Today the device classifies each hiker with a single test: lateral distance to
the planned route (the IN_PATH / OUT_PATH corridor, default ±100 m). That catches
someone who wandered sideways off the trail, but not someone who is *on* the
trail yet falling dangerously behind, or who has drifted away from the rest of
the group. The following thresholds turn off-route detection into a richer,
multi-criteria safety model. These three were proposed by
[aemfbm](https://www.reddit.com/user/aemfbm/).

- **Off-path distance** — the allowable lateral distance from the leader's path.
  This generalises today's static-GPX corridor: once devices can record their
  own track (see [§6](#6-on-device-path-recording)), waypoints can be laid down
  automatically from the leader's actual route and each member checked against
  *those* — letting a group follow the leader even with no pre-loaded GPX. The lateral test already exists in
  `StateManager`; what's new is sourcing the reference line from the leader's
  recorded breadcrumbs, not only a loaded file. Per-member threshold (a child's
  corridor can be tighter than an adult's).
- **Fall-behind distance** — the allowable *along-track* distance a member may
  trail the leader. A new dimension, orthogonal to off-path: a hiker can be
  perfectly on the trail and still be the straggler the leader needs to know
  about. Implementation: project each position onto the route, compare its
  cumulative arc-length to the leader's, and alert when the gap exceeds the
  threshold. The simulator already projects positions onto the path and tracks
  the leader, so this is a natural regression scenario.
- **Isolation distance** *(optional)* — the allowable distance between one member
  and the rest of the group, independent of the route. Catches someone who has
  separated from everyone even while on-path and keeping pace. The Core already
  aggregates the whole group's positions each polling round, so this is a cheap
  nearest-neighbour check over the position table: flag a member whose nearest
  neighbour is farther than the threshold. Lower priority than the first two.

All three are per-member (or per-role) configurable thresholds, and are exactly
the kind of behaviour the simulator should regression-test before any field walk
— they belong in the [scenario library](#2-better-simulator).

## 5. Product / community

- Publish the 3D-printable enclosures (cleaned STL names) as a GitHub Release.
- `v0.1.0` release once #1 lands (both firmwares build, multi-hop proven in sim).
- CONTRIBUTING.md + good-first-issue labels (radio-model fitting and scenario
  library are ideal entry points).
- Hardware revision: integrated GPS+LoRa boards (T-Beam class) to drop the
  hand-wiring, with HEARD as firmware — overlaps with the Meshtastic decision
  above.

## 6. On-device path recording

A device can *load* a planned route but cannot yet *capture* one. Today the route
is streamed in as `lat,lon` points over serial — `StateManager::loadPath()` reads
them and the desktop `path_loader/` tool sends them from a GPX — and there is no
firmware code that records the device's own GPS into a path, nor any flash
storage (SPIFFS/NVS) to keep one. The goal is to let any device with a GPS record
a new path as it walks, and save it on-device as a reusable planned route.

- Sample GPS into a track while walking, with distance/time thinning so the
  stored path stays small; start and stop from the e-ink UI or a button.
- Persist recordings to flash and let one be re-selected as the active route for
  a later hike — walk a trail once, follow it the next time.
- This is the capability the leader-breadcrumb variant of
  [off-path distance](#4-safety-detection-criteria) builds on, and a natural GPX
  source for the phone path loader (BLE / Wi-Fi) under discussion: record on the
  device, pull it to the phone, or push a phone-recorded track back.

## 7. Hardware and enclosure

Turning the hand-wired prototype into something you can actually carry up a
mountain and trust in bad weather.

- **PCB design** — replace the hand-wired ESP32 + u-blox GPS + LoRa + e-ink with
  a single custom board: fewer connections to shake loose on the trail, a smaller
  footprint, and repeatable builds. This is the in-house alternative to adopting
  an off-the-shelf integrated board (the T-Beam-class option in
  [§5](#5-product--community)) — pick between them once the form factor and
  antenna placement (LoRa + GPS) are settled.
  - **Help wanted:** we're looking for someone to turn the existing breadboard
    schematic ([Wokwi project](https://wokwi.com/projects/436295484715573249))
    into a manufacturable PCB layout — **[PCBWay](https://www.pcbway.com/) is
    open to sponsoring the prototype prints**, so this can move from design to
    real boards quickly. Reach out via an issue if you can help with the layout.
- **Battery integration** — the hardware side of [§1](#1-firmware)'s power
  budget: a LiPo cell sized to the measured per-role consumption, USB-C charging
  with a charge IC and protection (BMS), and a fuel gauge so the leader can see
  the group's remaining battery alongside their positions.
- **Haptic feedback** — a vibration motor so the wearer is alerted silently when
  they go OUT_PATH, fall behind, or receive an SOS — no need to be staring at the
  e-ink or to hear a buzzer over wind. This is the delivery channel for the
  [§4 detection criteria](#4-safety-detection-criteria); distinct buzz patterns
  per alert type, driven at low power.
- **Waterproof case** — take the 3D-printed enclosures
  ([§5](#5-product--community)) to a sealed, IP-rated case for rain, snow and
  dust: gasketed seams, sealed or portless charging (pads/wireless to avoid a USB
  opening), waterproof buttons, and an RF-transparent window for the antennas.
