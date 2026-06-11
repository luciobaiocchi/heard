# This file is superseded by the C++ ConnectionManager (sim/SimDevice.cpp).
# It is kept only as a tombstone — do not import from it.
raise ImportError(
    "protocol.py is deprecated. Protocol logic lives in the C++ ConnectionManager. "
    "Use heard_sim.SimDevice (built from CMakeLists.txt) instead."
)
