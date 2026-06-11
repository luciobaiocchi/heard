"""SimRadio: probabilistic LoRa radio medium connecting C++ and Python devices."""
from __future__ import annotations
import random
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, List, Tuple, Union, TYPE_CHECKING

from utils import haversine

if TYPE_CHECKING:
    from node_device import NodeDevice
    try:
        from heard_sim import SimDevice
        AnyDevice = Union[SimDevice, NodeDevice]
    except ImportError:
        AnyDevice = object


@dataclass
class LinkEvent:
    sender_id:    int
    recipient_id: int     # -1 stored as a per-recipient broadcast event
    success:      bool
    tick:         int
    msg_kind:     str     # 'REQ' | 'WAIT' | 'POS' | '?'
    overheard:    bool = False  # passive overhear of a unicast; counts for
                                # connectivity but carries no protocol message


class SimRadio:
    """
    Probabilistic LoRa radio medium.

    Delivery model
    --------------
    p(d) = 1.0                              for d ≤ d_reliable
    p(d) = (1 - (d - d_r)/(d_max - d_r))²  for d_r < d < d_max
    p(d) = 0.0                              for d ≥ d_max
    """

    def __init__(
        self,
        d_reliable: float = 800.0,
        d_max: float = 3000.0,
        max_events: int = 300,
        rng_seed: int | None = None,
        terrain=None,        # legacy: Terrain instance (uses binary los_factor)
        environment=None,    # preferred: Environment instance (uses fresnel_factor)
    ):
        self.d_reliable  = d_reliable
        self.d_max       = d_max
        self.events:     Deque[LinkEvent] = deque(maxlen=max_events)
        self._rng      = random.Random(rng_seed)
        self._env      = environment  # takes priority over terrain
        self._terrain  = terrain      # legacy fallback
        self.stats = {"sent": 0, "delivered": 0, "dropped": 0}

    # ── Link quality ──────────────────────────────────────────────────────

    def link_prob(self, dist: float) -> float:
        if dist <= self.d_reliable:
            return 1.0
        if dist >= self.d_max:
            return 0.0
        t = (dist - self.d_reliable) / (self.d_max - self.d_reliable)
        return (1.0 - t) ** 2

    # ── Main tick ─────────────────────────────────────────────────────────

    def tick(self, devices: list, tick_num: int) -> None:
        """Drain all devices' outgoing queues and deliver messages probabilistically."""
        # Collect all pending outgoing messages first (snapshot)
        outgoing: List[Tuple[object, int, str]] = []  # (sender_dev, dest_id, msg)
        for dev in devices:
            while dev.has_pending_out():
                dest_id, msg = dev.pop_pending_out()
                outgoing.append((dev, dest_id, msg))

        # Deliver each message
        for sender, dest_id, msg in outgoing:
            kind = _msg_kind(msg)
            if dest_id == -1:
                self._broadcast(sender, msg, kind, devices, tick_num)
            else:
                self._unicast(sender, dest_id, msg, kind, devices, tick_num)

    # ── Delivery helpers ──────────────────────────────────────────────────

    def _channel_factor(self, slat: float, slon: float, dlat: float, dlon: float) -> float:
        """Combined propagation factor from environment or legacy terrain."""
        if self._env is not None:
            return self._env.signal_factor(slat, slon, dlat, dlon)
        if self._terrain is not None:
            return self._terrain.los_factor(slat, slon, dlat, dlon)
        return 1.0

    def _broadcast(self, sender, msg: str, kind: str, devices: list, tick: int) -> None:
        sid = sender.get_id()
        slat, slon = sender.get_lat(), sender.get_lon()
        for dev in devices:
            if dev.get_id() == sid:
                continue
            dlat, dlon = dev.get_lat(), dev.get_lon()
            d = haversine(slat, slon, dlat, dlon)
            p = self.link_prob(d) * self._channel_factor(slat, slon, dlat, dlon)
            ok = self._rng.random() < p
            if ok:
                dev.inject_message(msg, sid)
                self.stats["delivered"] += 1
            else:
                self.stats["dropped"] += 1
            self.stats["sent"] += 1
            self._log(LinkEvent(sid, dev.get_id(), ok, tick, kind))

    def _unicast(
        self, sender, dest_id: int, msg: str, kind: str, devices: list, tick: int
    ) -> None:
        sid = sender.get_id()
        target = next((d for d in devices if d.get_id() == dest_id), None)
        if target is None:
            return
        slat, slon = sender.get_lat(), sender.get_lon()
        dlat, dlon = target.get_lat(), target.get_lon()
        d = haversine(slat, slon, dlat, dlon)
        p = self.link_prob(d) * self._channel_factor(slat, slon, dlat, dlon)
        ok = self._rng.random() < p
        if ok:
            target.inject_message(msg, sid)
            self.stats["delivered"] += 1
        else:
            self.stats["dropped"] += 1
        self.stats["sent"] += 1
        self._log(LinkEvent(sid, dest_id, ok, tick, kind))

        # LoRa is a broadcast medium: every other device in range overhears the
        # unicast even though the protocol addresses one recipient. The message
        # is not injected (protocol behaviour unchanged) and stats are not
        # touched; the event only feeds the connectivity bookkeeping.
        for dev in devices:
            did = dev.get_id()
            if did == sid or did == dest_id:
                continue
            od = haversine(slat, slon, dev.get_lat(), dev.get_lon())
            op = self.link_prob(od) * self._channel_factor(slat, slon, dev.get_lat(), dev.get_lon())
            if self._rng.random() < op:
                self._log(LinkEvent(sid, did, True, tick, kind, overheard=True))

    # ── Utilities ─────────────────────────────────────────────────────────

    def reachable_from(self, device, devices: list) -> List[Tuple[int, float, float]]:
        """Return [(other_id, probability, distance_m)] for all other devices."""
        out = []
        for other in devices:
            if other.get_id() == device.get_id():
                continue
            dist = haversine(device.get_lat(), device.get_lon(), other.get_lat(), other.get_lon())
            out.append((other.get_id(), self.link_prob(dist), dist))
        return out

    def _log(self, ev: LinkEvent) -> None:
        self.events.append(ev)   # deque(maxlen) auto-drops oldest


def _msg_kind(msg: str) -> str:
    if msg.startswith("REQ"):  return "REQ"
    if msg.startswith("WAIT"): return "WAIT"
    if msg.startswith("POS"):  return "POS"
    return "?"
