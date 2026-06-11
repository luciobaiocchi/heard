#pragma once
#include "group/ConnectionManager.h"
#include "sim/SimConnection.h"
#include <map>
#include <tuple>
#include <string>
#include <utility>

// Wraps a ConnectionManager + SimConnection into a Python-facing simulation device.
// Python drives the clock (sim_ms), feeds GPS positions, and acts as the radio layer.
class SimDevice {
public:
    explicit SimDevice(int deviceId);

    // Called each simulation tick
    void step(unsigned long sim_ms);

    // GPS update from Python
    void setPosition(float lat, float lon);

    // Position query
    float getLat() const { return _lat; }
    float getLon() const { return _lon; }
    int   getId()  const { return _deviceId; }

    // Radio layer interface (Python drains/injects messages)
    bool hasPendingOut() const;
    std::pair<int, std::string> popPendingOut();
    void injectMessage(const std::string& msg, int senderId);

    // Protocol state
    bool isRequestInProgress() const;
    std::map<int, std::tuple<float, float, unsigned long>> getKnownPositions();

    // Manual trigger (for testing)
    bool startPositionRequest();

private:
    int            _deviceId;
    float          _lat = 0.0f;
    float          _lon = 0.0f;
    SimConnection  _conn;
    ConnectionManager _manager;
};
