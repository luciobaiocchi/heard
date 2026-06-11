#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "sim/SimDevice.h"

namespace py = pybind11;

PYBIND11_MODULE(heard_sim, m) {
    m.doc() = "HEARD protocol simulator — C++ core exposed to Python";

    py::class_<SimDevice>(m, "SimDevice")
        .def(py::init<int>(), py::arg("device_id"),
             "Create a simulated HEARD device with the given integer ID.")

        // Clock + GPS
        .def("step", &SimDevice::step, py::arg("sim_ms"),
             "Advance one simulation tick. sim_ms is the current wall-clock in milliseconds.")
        .def("set_position", &SimDevice::setPosition, py::arg("lat"), py::arg("lon"),
             "Push a new GPS fix into the device.")

        // Position accessors
        .def("get_lat",  &SimDevice::getLat)
        .def("get_lon",  &SimDevice::getLon)
        .def("get_id",   &SimDevice::getId)

        // Radio layer
        .def("has_pending_out", &SimDevice::hasPendingOut,
             "True if the device has outgoing messages waiting to be delivered.")
        .def("pop_pending_out", &SimDevice::popPendingOut,
             "Pop one outgoing message. Returns (dest_id, msg_str); dest_id=-1 means broadcast.")
        .def("inject_message",  &SimDevice::injectMessage,
             py::arg("msg"), py::arg("sender_id"),
             "Inject an incoming message from sender_id into this device's receive queue.")

        // Protocol state
        .def("is_request_in_progress", &SimDevice::isRequestInProgress)
        .def("get_known_positions",    &SimDevice::getKnownPositions,
             "Return {device_id: (lat, lon, timestamp_ms)} for all known devices.")
        .def("start_position_request", &SimDevice::startPositionRequest,
             "Manually trigger a REQ round (normally triggered automatically every 60s).");
}
