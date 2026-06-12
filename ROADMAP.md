# Roadmap

Where HEARD goes from here. The thesis delivered the architecture and a working
demo; this is the path from prototype to something people can actually carry.
Items link to issues where one exists — contributions welcome on any of them.

## 1. Firmware

- **Standalone Node build** ([#1](https://github.com/luciobaiocchi/heard/issues/1)) —
  the protocol now implements both roles (PR #3); what's left is packaging:
  extract `ConnectionManager`/`Connection` into a shared library used by both
  PlatformIO projects, give `dispositivo_figlio` a real `main` (protocol + GPS
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

## 4. Product / community

- Publish the 3D-printable enclosures (cleaned STL names) as a GitHub Release.
- `v0.1.0` release once #1 lands (both firmwares build, multi-hop proven in sim).
- CONTRIBUTING.md + good-first-issue labels (radio-model fitting and scenario
  library are ideal entry points).
- Hardware revision: integrated GPS+LoRa boards (T-Beam class) to drop the
  hand-wiring, with HEARD as firmware — overlaps with the Meshtastic decision
  above.
