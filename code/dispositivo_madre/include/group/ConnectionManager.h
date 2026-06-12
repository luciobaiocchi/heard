#ifndef CONNECTION_MANAGER_H
#define CONNECTION_MANAGER_H

#include <Arduino.h>
#include <map>
#include <vector>
#include <set>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "group/Connection.h"
#include "config.h"

struct DevicePosition {
    int deviceId;
    float latitude;
    float longitude;
    unsigned long timestamp;
    
    DevicePosition(int id = 0, float lat = 0.0, float lng = 0.0) 
        : deviceId(id), latitude(lat), longitude(lng), timestamp(millis()) {}
};

struct PendingDevice {
    int deviceId;
    unsigned long waitStartTime;
    unsigned long timeout;
    
    PendingDevice(int id, unsigned long timeout_ms = 10000) 
        : deviceId(id), waitStartTime(millis()), timeout(timeout_ms) {}
    
    bool isExpired() const {
        return (millis() - waitStartTime) > timeout;
    }
};

class ConnectionManager {
private:
    Connection* connection;
    int motherDeviceId;
    
    // Mutex per thread safety
    SemaphoreHandle_t positionMutex;
    SemaphoreHandle_t stateMutex;
    
    // Task handle
    TaskHandle_t taskHandle;
    bool taskRunning;
    
    // Stato del round di richieste
    bool requestInProgress;
    unsigned long requestStartTime;
    unsigned long globalTimeout;
    
    // Dispositivi e posizioni
    std::map<int, DevicePosition> knownPositions;
    std::vector<PendingDevice> pendingDevices;
    std::set<int> waitingDevices;
    
    // Parsing dei messaggi
    bool parsePositionMessage(const String& message, DevicePosition& position);
    bool parseWaitMessage(const String& message, int& deviceId);
    std::vector<int> parseHopList(const String& hopListStr);
    String createHopListString(const std::vector<int>& hops);
    String createKnownPositionsString();
    
    // Gestione timeout e cleanup
    void checkTimeouts();
    void cleanupExpiredPending();
    void resetRequestState();

    void update();


    // Debug
    void debug(const String& message);

public:
    ConnectionManager(Connection* conn, int motherId = 999);
    ~ConnectionManager();
    
    // Gestione task
    bool startTask(int coreId = 0, UBaseType_t priority = 1, uint32_t stackSize = 8192);
    void stopTask();
    static void taskFunction(void* pvParameters);
    
    // Controllo principale (chiamato dal task)
    void taskLoop();
    
    // Gestione richieste di posizione
    bool startPositionRequest();
    bool isRequestInProgress() const { return requestInProgress; }
    
    // Gestione messaggi ricevuti
    void handleIncomingMessage();
    void handlePositionRequest(const String& message, int senderId);
    void handleWaitMessage(const String& message, int senderId);
    void handlePositionData(const String& message, int senderId);
    
    // Gestione posizioni (thread-safe)
    void updateDevicePosition(int deviceId, float lat, float lng);
    std::map<int, DevicePosition> getKnownPositions(); // Rimuove const per thread safety
    bool hasPositionFor(int deviceId);
    DevicePosition getPositionFor(int deviceId);
    
    // Configurazione timeout
    void setGlobalTimeout(unsigned long timeout_ms) { globalTimeout = timeout_ms; }
    void setDefaultDeviceTimeout(unsigned long timeout_ms) { defaultDeviceTimeout = timeout_ms; }
    
    // Stato del sistema (thread-safe)
    int getConnectedDevicesCount();
    bool areAllDevicesResponded();
    bool getRequestInProgress();

    // Simulation: single-threaded tick (replaces task loop)
    void step(unsigned long sim_ms);

private:
    unsigned long defaultDeviceTimeout = 10000; // 10 secondi default
    // Initialized one interval in the past so the first REQ fires immediately.
    unsigned long simLastAutoRequestMs = 0UL - (unsigned long)CM_REQUEST_INTERVAL_MS;

    // ── Node role (multi-hop relay) ──────────────────────────────────
    // The same ConnectionManager implements both roles: device id 0 is
    // the core (initiates polling rounds), every other id acts as a node
    // (relays REQs, announces downstream devices via WAIT, forwards POS
    // reports toward the core).
    bool isCoreRole() const { return motherDeviceId == 0; }
    void handleRequestAsNode(const String& hopListStr, const String& posData, int senderId);

    int upstreamId = -1;                    // device we relay toward this round
    unsigned long lastReqHeardMs = 0;       // round detection by time gap
    bool postedOwnPosThisRound = false;
    std::set<String> respondedHops;         // hop-list fingerprints relayed this round
    std::set<int> announcedDownstream;      // ids already announced upstream via WAIT
    std::set<String> forwardedPosPayloads;  // POS payloads already relayed upstream
};

#endif // CONNECTION_MANAGER_H