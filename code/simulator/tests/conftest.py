"""Shared pytest fixtures for the HEARD simulator test suite."""
import os
import sys
import pytest

# Make simulator package importable (use abspath so .. is resolved)
_SIM_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _SIM_DIR not in sys.path:
    sys.path.insert(0, _SIM_DIR)
# Also add cwd so heard_sim.so is found when running pytest from simulator/
_CWD = os.path.abspath(os.getcwd())
if _CWD not in sys.path:
    sys.path.insert(0, _CWD)


GPX_PATH = os.path.join(
    os.path.dirname(__file__), "../../path_loader/activity_19135281495.gpx"
)


@pytest.fixture
def gpx_path():
    return GPX_PATH


@pytest.fixture
def path_points(gpx_path):
    from gpx_loader import load_gpx
    return load_gpx(gpx_path)


@pytest.fixture
def radio():
    from radio import SimRadio
    return SimRadio(d_reliable=800.0, d_max=3000.0, rng_seed=42)


@pytest.fixture
def node_factory():
    from node_device import NodeDevice
    def _make(device_id: int, lat: float = 44.12, lon: float = 12.24):
        return NodeDevice(device_id, lat, lon)
    return _make
