#include <Arduino.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "path/StateManager.h"
#include "SharedData.h"
#include "path/Path.h"
#include "group/Connection.h"
#include "group/ConnectionManager.h" 
#include "DisplayEInk.h"

// Config
#define DEVICE_ID 0  // ID del dispositivo madre
#define DELAY_STATUS_MS 10000  // Status ogni 10 secondi

// Handle dei task
TaskHandle_t TaskGPSHandle = NULL;
TaskHandle_t TaskLoRaHandle = NULL;
TaskHandle_t TaskStatusHandle = NULL;

// Oggetti condivisi
SharedData* const sharedData = new SharedData();
DisplayEInk display;
Connection connection;
ConnectionManager* connectionManager;

// Task GPS - gestisce GPS e stato generale del dispositivo
void TaskGPS(void* pvParameters) {
    Serial.println("TaskGPS: Avvio su core " + String(xPortGetCoreID()));
    StateManager manager(sharedData, display);
    
    while (true) {
        manager.updateState();
        
        // Se abbiamo una nuova posizione GPS, aggiorniamo il ConnectionManager
        if (sharedData->hasValidGPS()) {
            float lat = sharedData->getPos().getX();
            float lng = sharedData->getPos().getY();
            connectionManager->updateDevicePosition(DEVICE_ID, lat, lng);
        }
        
        vTaskDelay(pdMS_TO_TICKS(1000)); // Aggiorna ogni 1s
    }
}

// Task LoRa - ora gestito completamente dal ConnectionManager
void TaskLoRa(void* pvParameters) {
    Serial.println("TaskLoRa: Avvio su core " + String(xPortGetCoreID()));
    Serial.println("TaskLoRa: ConnectionManager gestisce automaticamente LoRa");
    
    // Questo task ora può essere utilizzato per altre funzioni LoRa
    // o per monitorare lo stato del ConnectionManager
    
    while (true) {
        // Esempio: potresti utilizzare questo task per inviare altri tipi di messaggi
        // o per gestire comunicazioni non legate alle richieste di posizione
        
        // Per ora, monitoriamo lo stato
        if (connectionManager->getRequestInProgress()) {
            Serial.println("TaskLoRa: Request pos...");
        }
        
        vTaskDelay(pdMS_TO_TICKS(5000)); // Check ogni 5 secondi
    }
}

// DEBUG
void TaskStatus(void* pvParameters) {
    Serial.println("TaskStatus: loading on core " + String(xPortGetCoreID()));
    
    while (true) {
        Serial.println("\n=== SYSTEM STATUS ===");
        Serial.println("Actual Core: " + String(xPortGetCoreID()));
        Serial.println("Free Heap: " + String(ESP.getFreeHeap()) + " bytes");
        Serial.println("Connected devices: " + String(connectionManager->getConnectedDevicesCount()));
        Serial.println("Active request: " + String(connectionManager->getRequestInProgress() ? "SÌ" : "NO"));
        Serial.println("GPS valid: " + String(sharedData->hasValidGPS() ? "SÌ" : "NO"));
        
        if (sharedData->hasValidGPS()) {
            Serial.println("Pos GPS: (" + String(sharedData->getPos().getX(), 6) + 
                          ", " + String(sharedData->getPos().getY(), 6) + ")");
        }
        
        auto positions = connectionManager->getKnownPositions();
        Serial.println("Known positions: " + String(positions.size()));
        for (const auto& pair : positions) {
            const DevicePosition& pos = pair.second;
            Serial.println("  Dev " + String(pos.deviceId) + 
                          ": (" + String(pos.latitude, 6) + ", " + String(pos.longitude, 6) + ")");
        }
        Serial.println("=====================\n");
        
        vTaskDelay(pdMS_TO_TICKS(DELAY_STATUS_MS));
    }
}

void setup() {
    Serial.begin(115200);
    delay(2000);
    
    Serial.println("Setup: init components...");
    Serial.println("Mother dev ID: " + String(DEVICE_ID));

    // Inizializzazione Display
    Serial.println("init display...");
    display.begin();
    display.drawLoadingScreen();
    delay(1000);


    // Inizializzazione LoRa
    Serial.println("init LoRa...");
    if (!connection.begin()) {
        Serial.println("ERROR: LoRa init failed!");
        //display.displayError("LoRa Init Failed");
        while(1) {
            vTaskDelay(pdMS_TO_TICKS(1000));
        }
    }
    
    // Inizializzazione ConnectionManager
    Serial.println("ConnectionManager init...");
    connectionManager = new ConnectionManager(&connection, DEVICE_ID);
    connectionManager->setGlobalTimeout(30000);        // 30 secondi timeout globale
    connectionManager->setDefaultDeviceTimeout(10000); // 10 secondi timeout singoli dispositivi
    
    // Avvio del task ConnectionManager su Core 0
    if (!connectionManager->startTask(0, 2, 8192)) { // Core 0, priorità 2, stack 8KB
        Serial.println("ERROR: ConnectionManager's task init failed!");
        //display.displayError("CM Task Failed");
        while(1) {
            vTaskDelay(pdMS_TO_TICKS(1000));
        }
    }

    vTaskDelay(pdMS_TO_TICKS(500));

    xTaskCreatePinnedToCore(
        TaskGPS,
        "TaskGPS",
        8192,
        NULL,
        3,
        &TaskGPSHandle,
        1
    );

    xTaskCreatePinnedToCore(
        TaskLoRa,
        "TaskLoRa", 
        4096,
        NULL,
        1,
        &TaskLoRaHandle,
        0
    );

    xTaskCreatePinnedToCore(
        TaskStatus,
        "TaskStatus",
        4096,
        NULL,
        0,
        &TaskStatusHandle,
        1
    );

    Serial.println("Setup completed - all tasks started");
    Serial.println("ConnectionManager automatically handles LoRa requests");

    // Serial command for debug
    Serial.println("\nAvailable commands:");
    Serial.println("  'request' - Force position request");
    Serial.println("  'status'  - Show system status");
    Serial.println("  'positions' - Show known positions");
    Serial.println("  'add ID lat lng' - Manually add a position");
}

void loop() {
    // Handle commands from serial input
    if (Serial.available()) {
        String command = Serial.readStringUntil('\n');
        command.trim();
        
        if (command == "request") {
            Serial.println("Command: Starting manual request...");
            if (connectionManager->startPositionRequest()) {
                Serial.println("Request started successfully");
            } else {
                Serial.println("Error starting request");
            }
        } 
        else if (command == "status") {
            Serial.println("Command: System status");
            Serial.println("Devices: " + String(connectionManager->getConnectedDevicesCount()));
            Serial.println("Request in progress: " + String(connectionManager->getRequestInProgress()));
            Serial.println("Free heap: " + String(ESP.getFreeHeap()));
        }
        else if (command == "positions") {
            Serial.println("Command: Known positions");
            auto positions = connectionManager->getKnownPositions();
            for (const auto& pair : positions) {
                const DevicePosition& pos = pair.second;
                Serial.println("Device " + String(pos.deviceId) + 
                              ": (" + String(pos.latitude, 6) + ", " + String(pos.longitude, 6) + 
                              ") - " + String((millis() - pos.timestamp) / 1000) + " seconds ago");
            }
        }
        else if (command.startsWith("add ")) {
            // Format: "add deviceId lat lng"
            int firstSpace = command.indexOf(' ', 4);
            int secondSpace = command.indexOf(' ', firstSpace + 1);
            
            if (firstSpace != -1 && secondSpace != -1) {
                int deviceId = command.substring(4, firstSpace).toInt();
                float lat = command.substring(firstSpace + 1, secondSpace).toFloat();
                float lng = command.substring(secondSpace + 1).toFloat();
                
                connectionManager->updateDevicePosition(deviceId, lat, lng);
                Serial.println("Position added for device " + String(deviceId));
            } else {
                Serial.println("Incorrect format. Use: add deviceId lat lng");
            }
        }
        else if (command == "help") {
            Serial.println("Available commands:");
            Serial.println("  request - Force position request");
            Serial.println("  status - Show system status");
            Serial.println("  positions - Show known positions");
            Serial.println("  add ID lat lng - Add a position");
            Serial.println("  help - Show this message");
        }
        else {
            Serial.println("Unknown command: '" + command + "' (use 'help')");
        }
    }
    
    // Main loop is now very lightweight
    // All heavy work is handled by tasks
    vTaskDelay(pdMS_TO_TICKS(100));
}
