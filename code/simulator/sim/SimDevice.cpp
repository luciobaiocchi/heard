#include "sim/SimDevice.h"

extern unsigned long g_sim_ms;

SimDevice::SimDevice(int deviceId)
    : _deviceId(deviceId), _conn(deviceId), _manager(&_conn, deviceId) {}

void SimDevice::step(unsigned long sim_ms) {
    g_sim_ms = sim_ms;
    _manager.step(sim_ms);
}

void SimDevice::setPosition(float lat, float lon) {
    _lat = lat;
    _lon = lon;
    _manager.updateDevicePosition(_deviceId, lat, lon);
}

bool SimDevice::hasPendingOut() const {
    return _conn.hasPendingOut();
}

std::pair<int, std::string> SimDevice::popPendingOut() {
    return _conn.popPendingOut();
}

void SimDevice::injectMessage(const std::string& msg, int senderId) {
    _conn.injectMessage(msg, senderId);
}

bool SimDevice::isRequestInProgress() const {
    return _manager.isRequestInProgress();
}

std::map<int, std::tuple<float, float, unsigned long>> SimDevice::getKnownPositions() {
    auto raw = _manager.getKnownPositions();
    std::map<int, std::tuple<float, float, unsigned long>> result;
    for (auto& [id, pos] : raw) {
        result[id] = {pos.latitude, pos.longitude, pos.timestamp};
    }
    return result;
}

bool SimDevice::startPositionRequest() {
    return _manager.startPositionRequest();
}
