#include <Arduino.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "path/StateManager.h"
#include "SharedData.h"
#include "path/Path.h"
#include "group/ConnectionManager.h" // Assumendo che sia lì la tua classe

// Handle dei task
TaskHandle_t TaskGPSHandle = NULL;
TaskHandle_t TaskLoRaHandle = NULL;

// Oggetti condivisi
SharedData* const sharedData = new SharedData();

ConnectionManager connectionManager = ConnectionManager(); // Istanza globale, opzionale

// Task GPS
void TaskGPS(void* pvParameters) {
    StateManager manager(sharedData);
    while (true) {
        manager.updateState();
        vTaskDelay(pdMS_TO_TICKS(1000)); // Aggiorna ogni 1s
    }
}

void TaskLoRa(void* pvParameters) {
    Serial.println("TaskLoRa: Avvio");

    if (!connectionManager.begin()) {
        Serial.println("Errore inizializzazione LoRa!");
        vTaskDelete(NULL); // Termina il task in caso di errore
    }

    //Serial.println("TaskLoRa: Inizializzazione ok");

    while (true) {
        Serial.println("TaskLoRa: invio richiesta...");
        connectionManager.sendRequest(DEVICE_ID);
        vTaskDelay(pdMS_TO_TICKS(DELAY_LORA_MS));  // es. 2000ms
    }
}


void setup() {
    Serial.begin(115200);
    delay(1000);
    
    // Task GPS su Core 1
    xTaskCreatePinnedToCore(
        TaskGPS,
        "TaskGPS",
        8192,
        NULL,
        1,
        &TaskGPSHandle,
        1
    );

    // Task LoRa su Core 0
    xTaskCreatePinnedToCore(
        TaskLoRa,
        "TaskLoRa",
        8192,
        NULL,
        1,
        &TaskLoRaHandle,
        0
    );
}

void loop() {
    // Vuoto: tutto gestito da FreeRTOS
}
