#ifndef CONFIG_H
#define CONFIG_H

// =========================
// CONFIGURAZIONE DISPOSITIVO
// =========================
#define DEVICE_ID 999  // ID del dispositivo madre
#define IS_MOTHER_DEVICE true

// =========================
// CONFIGURAZIONE CONNECTIONMANAGER
// =========================
#define CM_GLOBAL_TIMEOUT_MS 30000      // Timeout globale per round completo
#define CM_DEVICE_TIMEOUT_MS 10000      // Timeout per singolo dispositivo
#define CM_REQUEST_INTERVAL_MS 10000    // Intervallo tra richieste automatiche
#define CM_TASK_STACK_SIZE 8192         // Stack size per task ConnectionManager
#define CM_TASK_PRIORITY 2              // Priorità task ConnectionManager
#define CM_TASK_CORE 0                  // Core per task ConnectionManager

// =========================
// CONFIGURAZIONE TASK
// =========================
#define GPS_TASK_STACK_SIZE 8192
#define GPS_TASK_PRIORITY 3
#define GPS_TASK_CORE 1
#define GPS_UPDATE_INTERVAL_MS 1000

#define LORA_TASK_STACK_SIZE 4096
#define LORA_TASK_PRIORITY 1
#define LORA_TASK_CORE 0

#define STATUS_TASK_STACK_SIZE 4096
#define STATUS_TASK_PRIORITY 0
#define STATUS_TASK_CORE 1
#define STATUS_PRINT_INTERVAL_MS 10000

// =========================
// CONFIGURAZIONE LORA
// =========================
#define LORA_FREQ 868E6    // Frequenza LoRa (Europa)
#define LORA_CS 5          // Pin CS
#define LORA_SCK 18        // Pin SCK
#define LORA_MISO 19       // Pin MISO  
#define LORA_MOSI 27       // Pin MOSI

// =========================
// CONFIGURAZIONE DEBUG
// =========================
#define SERIAL_BAUD_RATE 115200
#define DEBUG_ENABLED true

// Macro per debug condizionale
#if DEBUG_ENABLED
    #define DEBUG_PRINT(x) Serial.print(x)
    #define DEBUG_PRINTLN(x) Serial.println(x)
#else
    #define DEBUG_PRINT(x)
    #define DEBUG_PRINTLN(x)
#endif

// =========================
// CONFIGURAZIONE DISPLAY
// =========================
#define DISPLAY_UPDATE_INTERVAL_MS 5000

// =========================
// CONFIGURAZIONE MEMORIA
// =========================
#define MIN_FREE_HEAP 10000  // Heap minimo prima di warning

#endif // CONFIG_H