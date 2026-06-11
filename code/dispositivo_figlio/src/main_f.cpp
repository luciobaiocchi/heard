#include <SPI.h>
#include <LoRa.h>

// Configurazione LoRa
#define LORA_SCK  18
#define LORA_MISO 19
#define LORA_MOSI 23
#define LORA_CS   5


void setup() {
  Serial.begin(115200);

  LoRa.setPins(LORA_CS, -1, -1);  // SENZA DIO0 e RESET
  while (!LoRa.begin(433E6)) {
    Serial.println("Errore nell'inizializzazione del modulo LoRa");
  }
  Serial.println("Ricevitore LoRa Avviato");
}


void loop() {
  // try to parse packet
  int packetSize = LoRa.parsePacket();
  if (packetSize) {
    // received a packet
    Serial.print("Received packet '");

    // read packet
    while (LoRa.available()) {
      Serial.print((char)LoRa.read());
    }

    // print RSSI of packet
    Serial.print("' with RSSI ");
    Serial.println(LoRa.packetRssi());
  }
}
