#include "group/ConnectionManager.h"

ConnectionManager::ConnectionManager(Connection* conn, int motherId) 
    : connection(conn), motherDeviceId(motherId), requestInProgress(false),
      requestStartTime(0), globalTimeout(30000), taskHandle(NULL), taskRunning(false)
{
    if (connection == nullptr) {
        debug("ERRORE: Connection è nullptr!");
    }
    
    // Crea mutex per thread safety
    positionMutex = xSemaphoreCreateMutex();
    stateMutex = xSemaphoreCreateMutex();
    
    if (positionMutex == NULL || stateMutex == NULL) {
        debug("ERRORE: Creazione mutex fallita!");
    }
}

ConnectionManager::~ConnectionManager() {
    stopTask();
    
    if (positionMutex != NULL) {
        vSemaphoreDelete(positionMutex);
    }
    if (stateMutex != NULL) {
        vSemaphoreDelete(stateMutex);
    }
}

bool ConnectionManager::startTask(int coreId, UBaseType_t priority, uint32_t stackSize) {
    if (taskRunning) {
        debug("Task già in esecuzione");
        return false;
    }
    
    BaseType_t result = xTaskCreatePinnedToCore(
        taskFunction,
        "ConnectionManager",
        stackSize,
        this,
        priority,
        &taskHandle,
        coreId
    );
    
    if (result == pdPASS) {
        taskRunning = true;
        debug("Task avviato su core " + String(coreId));
        return true;
    } else {
        debug("ERRORE: Creazione task fallita");
        return false;
    }
}

void ConnectionManager::stopTask() {
    if (taskHandle != NULL && taskRunning) {
        taskRunning = false;
        vTaskDelete(taskHandle);
        taskHandle = NULL;
        debug("Task fermato");
    }
}

void ConnectionManager::taskFunction(void* pvParameters) {
    ConnectionManager* cm = static_cast<ConnectionManager*>(pvParameters);
    cm->taskLoop();
}

void ConnectionManager::taskLoop() {
    debug("Task loop avviato");
    
    unsigned long lastPositionRequest = 0;
    const unsigned long REQUEST_INTERVAL = CM_REQUEST_INTERVAL_MS; // intervallo tra richieste (config.h)
    
    while (taskRunning) {
        // Gestisci messaggi in arrivo
        handleIncomingMessage();
        
        // Controlla timeout
        checkTimeouts();
        
        // Cleanup dispositivi scaduti
        cleanupExpiredPending();
        
        // Avvia nuove richieste se necessario (solo il core avvia i round)
        if (isCoreRole() && !getRequestInProgress()) {
            if (millis() - lastPositionRequest > REQUEST_INTERVAL) {
                debug("Avvio richiesta automatica");
                if (startPositionRequest()) {
                    lastPositionRequest = millis();
                }
            }
        }
        
        // Pausa per non sovraccaricare il sistema
        vTaskDelay(pdMS_TO_TICKS(100));
    }
    
    debug("Task loop terminato");
    vTaskDelete(NULL);
}

void ConnectionManager::update() {
    // Mantenuto per compatibilità, ma ora gestito dal task
    debug("ATTENZIONE: update() chiamato ma il ConnectionManager usa un task");
}

bool ConnectionManager::startPositionRequest() {
    // Thread safety
    if (xSemaphoreTake(stateMutex, pdMS_TO_TICKS(100)) != pdTRUE) {
        debug("ERRORE: Timeout acquisizione mutex state");
        return false;
    }
    
    bool result = false;
    
    if (requestInProgress) {
        debug("Richiesta già in corso");
    } else {
        // Reset stato
        resetRequestState();
        
        // Crea messaggio di richiesta iniziale
        String hopList = String(motherDeviceId);
        String knownPositions = createKnownPositionsString();
        String requestMessage = "REQ|" + hopList + "|" + knownPositions;
        
        debug("Avvio richiesta posizioni: " + requestMessage);
        
        if (connection->broadcastMessage(requestMessage)) {
            requestInProgress = true;
            requestStartTime = millis();
            debug("Richiesta inviata con successo");
            result = true;
        } else {
            debug("ERRORE nell'invio della richiesta");
        }
    }
    
    xSemaphoreGive(stateMutex);
    return result;
}

void ConnectionManager::handleIncomingMessage() {
    if (!connection->hasMessage()) {
        return;
    }
    
    String message = connection->receiveMessage();
    int senderId = connection->getLastSenderId();
    
    if (message.isEmpty() || senderId == -1) {
        debug("Messaggio vuoto o ID sender non valido");
        return;
    }
    
    debug("Ricevuto da " + String(senderId) + ": " + message);
    
    // Determina tipo di messaggio
    if (message.startsWith("REQ|")) {
        handlePositionRequest(message, senderId);
    } else if (message.startsWith("WAIT|")) {
        handleWaitMessage(message, senderId);
    } else if (message.startsWith("POS|")) {
        handlePositionData(message, senderId);
    } else {
        debug("Tipo messaggio non riconosciuto: " + message);
    }
}

void ConnectionManager::handlePositionRequest(const String& message, int senderId) {
    // Formato: "REQ|hop1,hop2,hop3|pos_data"
    int firstSep = message.indexOf('|', 4);
    if (firstSep == -1) return;

    String hopListStr = message.substring(4, firstSep);
    String posData = message.substring(firstSep + 1);
    std::vector<int> hops = parseHopList(hopListStr);

    // Verifica se siamo nella catena di hop
    bool foundMother = false;
    for (int hop : hops) {
        if (hop == motherDeviceId) {
            foundMother = true;
            break;
        }
    }

    if (!foundMother) {
        // REQ di una catena che non ci contiene: il core la ignora
        // (rete a core singolo), un nodo la inoltra e risponde.
        if (!isCoreRole()) {
            handleRequestAsNode(hopListStr, posData, senderId);
        }
        return;
    }

    if (hops.size() > 1) {
        if (isCoreRole()) {
            // Richiesta ricorsiva da un dispositivo nella catena
            int requesterDevice = hops.back();

            debug("Richiesta ricorsiva da dispositivo " + String(requesterDevice));

            // Aggiungi il dispositivo ai pending se non già presente
            bool alreadyPending = false;
            for (const auto& pending : pendingDevices) {
                if (pending.deviceId == requesterDevice) {
                    alreadyPending = true;
                    break;
                }
            }

            if (!alreadyPending) {
                pendingDevices.push_back(PendingDevice(requesterDevice, defaultDeviceTimeout));
                waitingDevices.insert(requesterDevice);
            }

            // Invia messaggio di attesa
            String waitMessage = "WAIT|" + String(motherDeviceId);
            connection->sendMessage(senderId, waitMessage);

            debug("Inviato WAIT a dispositivo " + String(requesterDevice));
        } else {
            // Nodo: un dispositivo a valle ha esteso la nostra catena.
            // Lo annunciamo a monte (WAIT) così il core tiene aperto il
            // round per un dispositivo che non può sentire direttamente.
            int downstream = hops.back();
            if (downstream != motherDeviceId && upstreamId >= 0 &&
                announcedDownstream.find(downstream) == announcedDownstream.end()) {
                announcedDownstream.insert(downstream);
                connection->sendMessage(upstreamId, "WAIT|" + String(downstream));
                debug("Annunciato dispositivo a valle " + String(downstream));
            }
        }
    }
}

void ConnectionManager::handleRequestAsNode(const String& hopListStr, const String& posData, int senderId) {
    // Rilevamento nuovo round: un nodo raggiungibile solo via relay non
    // sente mai il core direttamente, quindi l'unico confine affidabile
    // tra round è il tempo trascorso dall'ultima REQ udita.
    unsigned long now = millis();
    if (now - lastReqHeardMs > (unsigned long)CM_ROUND_GAP_MS) {
        respondedHops.clear();
        announcedDownstream.clear();
        forwardedPosPayloads.clear();
        upstreamId = -1;
        postedOwnPosThisRound = false;
    }
    lastReqHeardMs = now;

    // Evita di re-inoltrare una catena già gestita in questo round
    if (respondedHops.find(hopListStr) != respondedHops.end()) return;
    respondedHops.insert(hopListStr);

    if (upstreamId < 0) upstreamId = senderId;  // la prima REQ definisce il monte

    // Inoltra la REQ con il nostro ID accodato alla hop list
    String newHops = hopListStr.isEmpty()
        ? String(motherDeviceId)
        : hopListStr + "," + String(motherDeviceId);
    connection->broadcastMessage("REQ|" + newHops + "|" + posData);

    // Risponde con la propria posizione (una sola volta per round)
    if (!postedOwnPosThisRound && hasPositionFor(motherDeviceId)) {
        postedOwnPosThisRound = true;
        DevicePosition own = getPositionFor(motherDeviceId);
        String pos = "POS|" + String(motherDeviceId) + "," +
                     String(own.latitude, 6) + "," + String(own.longitude, 6);
        connection->broadcastMessage(pos);
    }
}

void ConnectionManager::handleWaitMessage(const String& message, int senderId) {
    // Formato: "WAIT|waiting_device_id"
    int deviceId;
    if (!parseWaitMessage(message, deviceId)) {
        debug("ERRORE: parsing messaggio WAIT fallito");
        return;
    }
    
    debug("Ricevuto WAIT per dispositivo " + String(deviceId) + " da " + String(senderId));
    
    // Reset timeout per il dispositivo che sta aspettando
    for (auto& pending : pendingDevices) {
        if (pending.deviceId == senderId) {
            pending.waitStartTime = millis(); // Reset timeout
            debug("Timeout resettato per dispositivo " + String(senderId));
            break;
        }
    }
    
    // Aggiungi il dispositivo ai waiting
    waitingDevices.insert(deviceId);

    // Nodo: inoltra a monte i WAIT provenienti da valle, così le catene
    // profonde restano contabilizzate dal core.
    if (!isCoreRole() && upstreamId >= 0 && senderId != upstreamId &&
        deviceId != motherDeviceId &&
        announcedDownstream.find(deviceId) == announcedDownstream.end()) {
        announcedDownstream.insert(deviceId);
        connection->sendMessage(upstreamId, message);
    }
}

void ConnectionManager::handlePositionData(const String& message, int senderId) {
    // Formato: "POS|device_id,lat,lng|device_id,lat,lng|..."
    String posData = message.substring(4); // Rimuove "POS|"
    
    debug("Ricevuti dati posizione da " + String(senderId) + ": " + posData);
    
    // Parse delle posizioni multiple
    int start = 0;
    int pos = 0;
    bool containsOwnPosition = false;

    while (pos != -1) {
        pos = posData.indexOf('|', start);
        String singlePos = (pos == -1) ? posData.substring(start) : posData.substring(start, pos);

        if (!singlePos.isEmpty()) {
            DevicePosition position;
            if (parsePositionMessage(singlePos, position)) {
                if (position.deviceId == motherDeviceId) containsOwnPosition = true;
                updateDevicePosition(position.deviceId, position.latitude, position.longitude);
                debug("Aggiornata posizione dispositivo " + String(position.deviceId));

                // L'entry può essere stata inoltrata per conto di un dispositivo
                // fuori portata diretta: va rimossa dalla contabilità del round
                // (non solo il sender), altrimenti il round termina solo per
                // timeout globale anche quando tutte le posizioni sono arrivate.
                waitingDevices.erase(position.deviceId);
                int entryId = position.deviceId;
                auto pit = std::find_if(pendingDevices.begin(), pendingDevices.end(),
                                        [entryId](const PendingDevice& p) { return p.deviceId == entryId; });
                if (pit != pendingDevices.end()) {
                    pendingDevices.erase(pit);
                }
            }
        }
        
        start = pos + 1;
    }
    
    // Rimuovi il sender dai dispositivi in attesa
    auto it = std::find_if(pendingDevices.begin(), pendingDevices.end(),
                          [senderId](const PendingDevice& p) { return p.deviceId == senderId; });
    
    if (it != pendingDevices.end()) {
        pendingDevices.erase(it);
        debug("Dispositivo " + String(senderId) + " rimosso dai pending");
    }
    
    waitingDevices.erase(senderId);

    // Nodo: inoltra a monte i report di posizione provenienti da valle
    // (gamba di ritorno della catena multi-hop). Le proprie posizioni e i
    // payload già inoltrati vengono scartati per evitare loop.
    if (!isCoreRole() && upstreamId >= 0 && senderId != upstreamId &&
        !containsOwnPosition &&
        forwardedPosPayloads.find(posData) == forwardedPosPayloads.end()) {
        forwardedPosPayloads.insert(posData);
        connection->sendMessage(upstreamId, message);
        debug("Inoltrato POS a monte verso " + String(upstreamId));
    }

    // Controlla se abbiamo finito
    if (areAllDevicesResponded()) {
        debug("Round di richieste completato con successo!");
        requestInProgress = false;
    }
}

bool ConnectionManager::parsePositionMessage(const String& message, DevicePosition& position) {
    // Formato: "device_id,lat,lng"
    int firstComma = message.indexOf(',');
    int secondComma = message.indexOf(',', firstComma + 1);
    
    if (firstComma == -1 || secondComma == -1) return false;
    
    position.deviceId = message.substring(0, firstComma).toInt();
    position.latitude = message.substring(firstComma + 1, secondComma).toFloat();
    position.longitude = message.substring(secondComma + 1).toFloat();
    position.timestamp = millis();
    
    return true;
}

bool ConnectionManager::parseWaitMessage(const String& message, int& deviceId) {
    // Formato: "WAIT|device_id"
    int sepIndex = message.indexOf('|');
    if (sepIndex == -1) return false;
    
    deviceId = message.substring(sepIndex + 1).toInt();
    return deviceId > 0;
}

std::vector<int> ConnectionManager::parseHopList(const String& hopListStr) {
    std::vector<int> hops;
    int start = 0;
    int pos = 0;
    
    while (pos != -1) {
        pos = hopListStr.indexOf(',', start);
        String hopStr = (pos == -1) ? hopListStr.substring(start) : hopListStr.substring(start, pos);
        
        if (!hopStr.isEmpty()) {
            hops.push_back(hopStr.toInt());
        }
        
        start = pos + 1;
    }
    
    return hops;
}

String ConnectionManager::createHopListString(const std::vector<int>& hops) {
    String result = "";
    for (size_t i = 0; i < hops.size(); i++) {
        if (i > 0) result += ",";
        result += String(hops[i]);
    }
    return result;
}

String ConnectionManager::createKnownPositionsString() {
    String result = "";
    bool first = true;
    
    for (const auto& pair : knownPositions) {
        if (!first) result += "|";
        result += String(pair.second.deviceId) + "," + 
                 String(pair.second.latitude, 6) + "," + 
                 String(pair.second.longitude, 6);
        first = false;
    }
    
    return result;
}

void ConnectionManager::updateDevicePosition(int deviceId, float lat, float lng) {
    if (xSemaphoreTake(positionMutex, pdMS_TO_TICKS(100)) == pdTRUE) {
        knownPositions[deviceId] = DevicePosition(deviceId, lat, lng);
        debug("Posizione aggiornata per dispositivo " + String(deviceId) + 
              ": (" + String(lat, 6) + ", " + String(lng, 6) + ")");
        xSemaphoreGive(positionMutex);
    } else {
        debug("ERRORE: Timeout acquisizione mutex posizioni");
    }
}

std::map<int, DevicePosition> ConnectionManager::getKnownPositions() {
    std::map<int, DevicePosition> result;
    
    if (xSemaphoreTake(positionMutex, pdMS_TO_TICKS(100)) == pdTRUE) {
        result = knownPositions;
        xSemaphoreGive(positionMutex);
    } else {
        debug("ERRORE: Timeout acquisizione mutex posizioni");
    }
    
    return result;
}

bool ConnectionManager::hasPositionFor(int deviceId) {
    bool result = false;
    
    if (xSemaphoreTake(positionMutex, pdMS_TO_TICKS(100)) == pdTRUE) {
        result = knownPositions.find(deviceId) != knownPositions.end();
        xSemaphoreGive(positionMutex);
    } else {
        debug("ERRORE: Timeout acquisizione mutex posizioni");
    }
    
    return result;
}

DevicePosition ConnectionManager::getPositionFor(int deviceId) {
    DevicePosition result;
    
    if (xSemaphoreTake(positionMutex, pdMS_TO_TICKS(100)) == pdTRUE) {
        auto it = knownPositions.find(deviceId);
        if (it != knownPositions.end()) {
            result = it->second;
        }
        xSemaphoreGive(positionMutex);
    } else {
        debug("ERRORE: Timeout acquisizione mutex posizioni");
    }
    
    return result;
}

int ConnectionManager::getConnectedDevicesCount() {
    int result = 0;
    
    if (xSemaphoreTake(positionMutex, pdMS_TO_TICKS(100)) == pdTRUE) {
        result = knownPositions.size();
        xSemaphoreGive(positionMutex);
    } else {
        debug("ERRORE: Timeout acquisizione mutex posizioni");
    }
    
    return result;
}

bool ConnectionManager::areAllDevicesResponded() {
    bool result = false;
    
    if (xSemaphoreTake(stateMutex, pdMS_TO_TICKS(100)) == pdTRUE) {
        result = pendingDevices.empty() && waitingDevices.empty();
        xSemaphoreGive(stateMutex);
    } else {
        debug("ERRORE: Timeout acquisizione mutex state");
    }
    
    return result;
}

bool ConnectionManager::getRequestInProgress() {
    bool result = false;
    
    if (xSemaphoreTake(stateMutex, pdMS_TO_TICKS(100)) == pdTRUE) {
        result = requestInProgress;
        xSemaphoreGive(stateMutex);
    } else {
        debug("ERRORE: Timeout acquisizione mutex state");
    }
    
    return result;
}

void ConnectionManager::checkTimeouts() {
    if (!requestInProgress) return;
    
    // Timeout globale per l'intero round
    if ((millis() - requestStartTime) > globalTimeout) {
        debug("TIMEOUT GLOBALE raggiunto - termino richiesta");
        resetRequestState();
        return;
    }
    
    // Controlla timeout individuali dei dispositivi
    cleanupExpiredPending();
    
    // Se non ci sono più dispositivi in attesa, termina
    if (areAllDevicesResponded()) {
        debug("Tutti i dispositivi hanno risposto - round completato");
        requestInProgress = false;
    }
}

void ConnectionManager::cleanupExpiredPending() {
    auto it = pendingDevices.begin();
    while (it != pendingDevices.end()) {
        if (it->isExpired()) {
            debug("TIMEOUT dispositivo " + String(it->deviceId));
            waitingDevices.erase(it->deviceId);
            it = pendingDevices.erase(it);
        } else {
            ++it;
        }
    }
}

void ConnectionManager::resetRequestState() {
    requestInProgress = false;
    requestStartTime = 0;
    pendingDevices.clear();
    waitingDevices.clear();
    debug("Stato richiesta resettato");
}

void ConnectionManager::debug(const String& message) {
    Serial.println("CM[M" + String(motherDeviceId) + "] " + message);
}

void ConnectionManager::step(unsigned long sim_ms) {
    handleIncomingMessage();
    checkTimeouts();
    cleanupExpiredPending();
    if (isCoreRole() && !requestInProgress) {
        if (sim_ms - simLastAutoRequestMs >= (unsigned long)CM_REQUEST_INTERVAL_MS) {
            startPositionRequest();
            simLastAutoRequestMs = sim_ms;
        }
    }
}