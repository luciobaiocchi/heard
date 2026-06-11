# HEARD Simulator — Architecture

## Design goals

1. **Use actual firmware C++** — the protocol logic in `ConnectionManager.cpp` runs unmodified inside the simulator.
2. **Python as the "world"** — GPS data, radio propagation, and time are all controlled from Python.
3. **Deterministic and reproducible** — all randomness is seeded; the same seed produces the same run.

## Component responsibilities

### SimDevice (C++)

Wraps a single `ConnectionManager` instance. Exposes a minimal Python-facing API:

| Method | Description |
|--------|-------------|
| `step(sim_ms)` | Advance one tick: sets `g_sim_ms`, calls `ConnectionManager::step()` |
| `set_position(lat, lon)` | Push GPS fix; also calls `updateDevicePosition()` |
| `inject_message(msg, sender_id)` | Deliver a raw protocol string from the radio layer |
| `has_pending_out()` / `pop_pending_out()` | Drain outgoing messages for the radio layer |
| `get_known_positions()` | Read the core's position table |

### SimConnection (C++)

Drop-in replacement for the hardware `Connection` class. Uses two `std::queue`s:

- **inQueue** — messages waiting to be read by `ConnectionManager` (`hasMessage` / `receiveMessage`)
- **outQueue** — messages queued by `ConnectionManager` (`sendMessage` / `broadcastMessage`)

The Python radio layer drains `outQueue` and fills `inQueue` every tick.

### millis() synchronisation

`Arduino.h` exposes `inline unsigned long g_sim_ms = 0`. `SimDevice::step(sim_ms)` sets this before calling `ConnectionManager::step()`, so all timeout comparisons inside the firmware use the simulated clock.

### NodeDevice (Python)

Implements the relay/endpoint behaviour that the actual child firmware (`dispositivo_figlio`) would provide. Each tick it:

1. Receives any incoming messages from `_inbox`.
2. If it sees a `REQ|...|` whose hop list does not include its own ID, it:
   - Broadcasts a forwarded `REQ` with its ID appended.
   - Schedules a `POS` broadcast after `POS_DELAY_TICKS` ticks (to let the core process the forwarded REQ first).

### SimRadio (Python)

Each call to `tick(devices, tick_num)`:

1. Snapshots all pending outgoing messages from every device.
2. For each message, computes delivery probability `p(d)` from Haversine distance, then multiplies by the terrain propagation factor from `Environment.signal_factor()` when `--terrain` is active.
3. Flips a seeded random coin per recipient; delivers or drops accordingly.
4. Logs a `LinkEvent` for the visualiser.

For **unicast** messages, an additional overhearing pass rolls the same probability for every bystander device. Successful overhears are logged as `LinkEvent(overheard=True)`: they feed the connectivity table but are not injected into the protocol and are excluded from the link-arc visualisation.

### Environment / Terrain (Python)

`Environment` is the single entry-point for channel physics. It calls `Terrain.fresnel_factor()`, which computes the ITU-R P.526 single knife-edge diffraction loss for the worst obstacle along the path and returns a linear factor in `[LOS_BLOCK .. 1.0]`. The `Terrain` class fetches AWS terrarium DEM tiles (zoom 12, ~38 m/pixel) on first use and caches them in memory.

### Delivery model

```
p(d) = 1.0                                      d ≤ d_reliable (default 2000 m)
p(d) = (1 - (d - d_r) / (d_max - d_r))²        d_r < d < d_max (default 5000 m)
p(d) = 0.0                                      d ≥ d_max
```

Both thresholds are set by `LORA_RELIABLE_M` / `LORA_MAX_M` in `config.py` and can be overridden per-run with `--reliable` / `--max-range`.

### Protocol flow (one full round)

```
Core (C++ SimDevice)                    Node (Python NodeDevice)
─────────────────────────────────────   ─────────────────────────────────
step(t=0)  → startPositionRequest()
           → broadcasts REQ|0|
                                        ← receives REQ|0|
                                        → broadcasts REQ|0,N|      (forwarded)
                                        [waits POS_DELAY_TICKS]
step(t=?)  ← receives REQ|0,N|
           → adds N to pendingDevices
           → sends WAIT|0 → N
                                        ← receives WAIT|0 (ignored)
                                        → broadcasts POS|N,lat,lon
step(t=?)  ← receives POS|N,lat,lon
           → stores position for N
           → removes N from pendingDevices
           (round complete when pendingDevices empty)
```

## Firmware patches (minimal, non-breaking)

| File | Change |
|------|--------|
| `Connection.h` | Added `virtual` to 6 methods + virtual destructor |
| `ConnectionManager.h` | Added `void step(unsigned long sim_ms)` declaration + `simLastAutoRequestMs` field |
| `ConnectionManager.cpp` | Implemented `step()`: one synchronous iteration of the task loop |

No other firmware files are changed.
