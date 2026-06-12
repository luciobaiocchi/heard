"""Python NodeDevice: simulates a relay/endpoint node without C++ firmware."""
from __future__ import annotations
from typing import List, Tuple


class NodeDevice:
    """
    Simulates a HEARD Node (relay/endpoint) device in pure Python.

    Protocol behaviour (all three legs of the multi-hop chain)
    ----------------------------------------------------------
    * Receives REQ (not in hop list) → appends own ID, re-broadcasts the
      REQ, remembers the sender as its *upstream*, then broadcasts own POS
      after POS_DELAY_TICKS ticks.
    * Hears a REQ that contains its own ID (a downstream device relayed
      our chain) → sends WAIT|<downstream_id> upstream, so the core keeps
      the round open for a device it cannot hear directly.
    * Receives WAIT from downstream → forwards it upstream (deep chains).
    * Receives POS from downstream → forwards it upstream (return leg);
      the core parses the entries and clears them from its accounting.
    """

    POS_DELAY_TICKS = 3   # ticks between forwarding REQ and sending POS
    # Gap (ms) separating two protocol rounds. Must stay > BROADCAST_WINDOW (2 s)
    # and strictly < the core's CM_REQUEST_INTERVAL_MS (10 s, config.h), or round
    # detection never fires and nodes stop relaying new rounds.
    ROUND_GAP_MS = 5_000

    def __init__(self, device_id: int, lat: float, lon: float):
        self.device_id = device_id
        self.lat = lat
        self.lon = lon

        self._inbox: List[Tuple[str, int]] = []          # (msg, sender_id)
        self._outbox: List[Tuple[int, str]] = []         # (dest_id, msg); -1 = broadcast
        self._pending_pos: List[Tuple[int, str]] = []    # buffered POSes to send later
        self._pos_ticks_left: int = 0
        self._responded_hops: set = set()                # hop-list fingerprints already relayed this round
        self._sim_ms: int = 0                            # updated each step(); used for round detection
        self._last_req_ms: int = -(self.ROUND_GAP_MS + 1)  # forces clear on first REQ
        self._upstream: int | None = None                # who we relay toward this round
        self._waited_ids: set = set()                    # downstream ids already announced via WAIT
        self._forwarded_pos: set = set()                 # POS payloads already relayed this round

    # ── Python radio layer interface ──────────────────────────────────────

    def get_id(self) -> int:    return self.device_id
    def get_lat(self) -> float: return self.lat
    def get_lon(self) -> float: return self.lon

    def set_position(self, lat: float, lon: float) -> None:
        self.lat = lat
        self.lon = lon

    def inject_message(self, msg: str, sender_id: int) -> None:
        self._inbox.append((msg, sender_id))

    def has_pending_out(self) -> bool:
        return bool(self._outbox)

    def pop_pending_out(self) -> Tuple[int, str]:
        return self._outbox.pop(0)

    # ── Simulation tick ───────────────────────────────────────────────────

    def step(self, sim_ms: int) -> None:
        self._sim_ms = sim_ms

        # Release buffered POS after delay (checked before inbox so the counter
        # starts counting on the tick AFTER it was set, not the same tick)
        if self._pos_ticks_left > 0:
            self._pos_ticks_left -= 1
            if self._pos_ticks_left == 0:
                self._outbox.extend(self._pending_pos)
                self._pending_pos.clear()

        # Process incoming messages
        for msg, sender_id in self._inbox:
            self._handle(msg, sender_id)
        self._inbox.clear()

    # ── Internal ──────────────────────────────────────────────────────────

    def _handle(self, msg: str, sender_id: int) -> None:
        if msg.startswith("REQ|"):
            self._handle_req(msg, sender_id)
        elif msg.startswith("WAIT|"):
            self._handle_wait(msg, sender_id)
        elif msg.startswith("POS|"):
            self._handle_pos(msg, sender_id)

    def _new_round(self) -> None:
        self._responded_hops.clear()
        self._waited_ids.clear()
        self._forwarded_pos.clear()
        self._upstream = None

    def _handle_req(self, msg: str, sender_id: int) -> None:
        parts = msg.split("|")
        hop_str = parts[1] if len(parts) > 1 else ""
        known_pos = parts[2] if len(parts) > 2 else ""
        hop_list = [int(x) for x in hop_str.split(",") if x.strip()]

        # New-round detection by time gap from the last REQ heard from ANY
        # sender — a relay-only node never hears the core directly, so the
        # gap (> ROUND_GAP_MS) is the only reliable round boundary.
        if self._sim_ms - self._last_req_ms > self.ROUND_GAP_MS:
            self._new_round()
        self._last_req_ms = self._sim_ms

        if self.device_id in hop_list:
            # A downstream device relayed our chain: announce it upstream
            # (WAIT leg) so the core keeps the round open for a device it
            # cannot hear. The core inserts it into waitingDevices and
            # resets our timeout.
            downstream = hop_list[-1]
            if (downstream != self.device_id and self._upstream is not None
                    and downstream not in self._waited_ids):
                self._waited_ids.add(downstream)
                self._outbox.append((self._upstream, f"WAIT|{downstream}"))
            return

        # Avoid re-relaying a chain we've already forwarded within this round
        fingerprint = tuple(hop_list)
        if fingerprint in self._responded_hops:
            return

        self._responded_hops.add(fingerprint)
        if self._upstream is None:
            self._upstream = sender_id  # first REQ of the round defines upstream

        # Forward REQ with our ID appended to the hop list
        new_hop_str = (hop_str + "," if hop_str else "") + str(self.device_id)
        forwarded = f"REQ|{new_hop_str}|{known_pos}"
        self._outbox.append((-1, forwarded))

        # Buffer our POS — send after a short delay so the core processes
        # the forwarded REQ (and adds us to pendingDevices) first
        pos_msg = f"POS|{self.device_id},{self.lat:.6f},{self.lon:.6f}"
        self._pending_pos.append((-1, pos_msg))
        self._pos_ticks_left = self.POS_DELAY_TICKS

    def _handle_wait(self, msg: str, sender_id: int) -> None:
        """Relay downstream WAITs upstream so deep chains stay accounted for."""
        if self._upstream is None or sender_id == self._upstream:
            return
        try:
            waiting_id = int(msg.split("|")[1])
        except (IndexError, ValueError):
            return
        if waiting_id == self.device_id or waiting_id in self._waited_ids:
            return
        self._waited_ids.add(waiting_id)
        self._outbox.append((self._upstream, msg))

    def _handle_pos(self, msg: str, sender_id: int) -> None:
        """Forward downstream position reports toward the core (return leg)."""
        if self._upstream is None or sender_id == self._upstream:
            return
        payload = msg[4:]
        try:
            entry_ids = {int(e.split(",")[0]) for e in payload.split("|") if e}
        except ValueError:
            return
        if self.device_id in entry_ids:
            return  # echo of our own (or already-merged) report
        if payload in self._forwarded_pos:
            return
        self._forwarded_pos.add(payload)
        self._outbox.append((self._upstream, msg))
