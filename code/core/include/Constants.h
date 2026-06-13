#ifndef __CONSTANTS_H__
#define __CONSTANTS_H__

#include <Arduino.h>

// === LoRa ===
constexpr long LORA_FREQ  = 433E6;
// === Pin SPI LoRa (HSPI) ===
constexpr uint8_t LORA_SCK  = 18;  // BLU
constexpr uint8_t LORA_MISO = 19;  // Grigio
constexpr uint8_t LORA_MOSI = 23;  // Viola
constexpr uint8_t LORA_CS   = 5;   // Verde

// === Pin SPI Display e-Ink (VSPI) ===
constexpr uint8_t EINK_MOSI = 23;  // Blu (VSPI MOSI)
//constexpr uint8_t EINK_MISO = 19;  (VSPI MISO, non sempre usato)
constexpr uint8_t EINK_SCK  = 18;  // Giallo (VSPI SCK)
constexpr uint8_t EINK_CS   = 21;  // Arancione

constexpr uint8_t EINK_DC   = 2;  // Verde
constexpr uint8_t EINK_RST  = 22;  // Bianco
constexpr uint8_t EINK_BUSY = 4;   // Viola

//constexpr uint8_t EINK_DC   = 27;  // Verde
//constexpr uint8_t EINK_RST  = 33;  // Bianco

// === Identificativo dispositivo ===
constexpr int DEVICE_ID = 1;

// === FreeRTOS ===
constexpr TickType_t DELAY_GPS_MS = 1000;
constexpr TickType_t DELAY_LORA_MS = 2000;

// === Limiti ===
constexpr size_t MAX_PEOPLE = 10;

// === Protocollo LoRa ===
const String PROTO_REQUEST = "REQ";
const String PROTO_WAIT    = "WAIT";

// === Debug ===
constexpr long SERIAL_BAUD = 115200;

#endif // __CONSTANTS_H__
