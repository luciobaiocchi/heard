"""Unicast overhearing: bystanders in range log connectivity events but
never receive the protocol message, and delivery stats are untouched."""
import pytest
from radio import SimRadio


class FakeDevice:
    """Minimal radio participant that records injected messages."""

    def __init__(self, device_id: int, lat: float, lon: float):
        self._id = device_id
        self.lat = lat
        self.lon = lon
        self.inbox = []
        self.outbox = []

    def get_id(self):
        return self._id

    def get_lat(self):
        return self.lat

    def get_lon(self):
        return self.lon

    def has_pending_out(self):
        return bool(self.outbox)

    def pop_pending_out(self):
        return self.outbox.pop(0)

    def inject_message(self, msg, sender_id):
        self.inbox.append((msg, sender_id))


LAT = 44.0
DEG_700M = 700 / 111_000  # ~700 m in latitude degrees


@pytest.fixture
def radio():
    return SimRadio(d_reliable=800.0, d_max=900.0, rng_seed=7)


def test_unicast_overheard_by_bystander_in_range(radio):
    sender = FakeDevice(0, LAT, 12.0)
    target = FakeDevice(1, LAT + DEG_700M, 12.0)
    bystander = FakeDevice(2, LAT - DEG_700M, 12.0)
    devices = [sender, target, bystander]

    sender.outbox.append((1, "POS|0,44.0,12.0"))
    radio.tick(devices, tick_num=0)

    overheard = [ev for ev in radio.events if ev.overheard]
    assert len(overheard) == 1
    assert overheard[0].recipient_id == 2
    assert overheard[0].success is True
    # The protocol message is delivered only to the addressed target
    assert len(target.inbox) == 1
    assert bystander.inbox == []


def test_overhear_does_not_affect_stats(radio):
    sender = FakeDevice(0, LAT, 12.0)
    target = FakeDevice(1, LAT + DEG_700M, 12.0)
    bystander = FakeDevice(2, LAT - DEG_700M, 12.0)

    sender.outbox.append((1, "POS|0,44.0,12.0"))
    radio.tick([sender, target, bystander], tick_num=0)

    # Stats count only the addressed transmission
    assert radio.stats == {"sent": 1, "delivered": 1, "dropped": 0}


def test_no_overhear_out_of_range(radio):
    sender = FakeDevice(0, LAT, 12.0)
    target = FakeDevice(1, LAT + DEG_700M, 12.0)
    far = FakeDevice(2, LAT + 1.0, 12.0)  # ~111 km away

    sender.outbox.append((1, "POS|0,44.0,12.0"))
    radio.tick([sender, target, far], tick_num=0)

    assert not any(ev.overheard for ev in radio.events)


def test_broadcast_events_not_marked_overheard(radio):
    sender = FakeDevice(0, LAT, 12.0)
    n1 = FakeDevice(1, LAT + DEG_700M, 12.0)
    n2 = FakeDevice(2, LAT - DEG_700M, 12.0)

    sender.outbox.append((-1, "REQ|0|"))
    radio.tick([sender, n1, n2], tick_num=0)

    assert len(radio.events) == 2
    assert not any(ev.overheard for ev in radio.events)


def test_link_prob_boundaries(radio):
    assert radio.link_prob(0.0) == 1.0
    assert radio.link_prob(800.0) == 1.0
    assert radio.link_prob(900.0) == 0.0
    assert radio.link_prob(850.0) == pytest.approx(0.25)  # (1 - 0.5)^2
