"""Python NodeDevice: simulates a relay/endpoint node without C++ firmware."""
from __future__ import annotations
from typing import List, Tuple


class NodeDevice:
    """
    Simulates a HEARD Node (relay/endpoint) device in pure Python.

    Protocol behaviour
    ------------------
    * Receives REQ  → appends own ID to hop list, re-broadcasts the REQ,
                      then broadcasts own POS after POS_DELAY_TICKS ticks.
    * Receives WAIT → no action (just an ACK from the core).
    * Receives POS  → no action.

    The core (C++ SimDevice) receives the forwarded REQ, adds this node to
    its pendingDevices, sends a WAIT back, then expects a POS reply.
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
        self._last_core_req_ms: int = -(self.ROUND_GAP_MS + 1)  # forces clear on first REQ

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
        # WAIT and POS messages require no action from a simple node

    def _handle_req(self, msg: str, sender_id: int) -> None:
        parts = msg.split("|")
        hop_str = parts[1] if len(parts) > 1 else ""
        known_pos = parts[2] if len(parts) > 2 else ""
        hop_list = [int(x) for x in hop_str.split(",") if x.strip()]

        # A direct REQ from the core (sender_id=0) may signal a new polling round.
        # Clear stale fingerprints only if enough time has elapsed since the last
        # core REQ (> ROUND_GAP_MS), so within-round duplicates are still suppressed.
        if sender_id == 0:
            if self._sim_ms - self._last_core_req_ms > self.ROUND_GAP_MS:
                self._responded_hops.clear()
            self._last_core_req_ms = self._sim_ms

        # Avoid re-relaying a chain we've already forwarded within this round
        fingerprint = tuple(hop_list)
        if fingerprint in self._responded_hops:
            return
        if self.device_id in hop_list:
            return  # already in chain

        self._responded_hops.add(fingerprint)

        # Forward REQ with our ID appended to the hop list
        new_hop_str = (hop_str + "," if hop_str else "") + str(self.device_id)
        forwarded = f"REQ|{new_hop_str}|{known_pos}"
        self._outbox.append((-1, forwarded))

        # Buffer our POS — send after a short delay so the core processes
        # the forwarded REQ (and adds us to pendingDevices) first
        pos_msg = f"POS|{self.device_id},{self.lat:.6f},{self.lon:.6f}"
        self._pending_pos.append((-1, pos_msg))
        self._pos_ticks_left = self.POS_DELAY_TICKS
