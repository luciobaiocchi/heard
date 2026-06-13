#include <SPI.h>
#include <LoRa.h>

// Configurazione LoRa
#define LORA_SCK  18
#define LORA_MISO 19
#define LORA_MOSI 23
#define LORA_CS   5

void setup() {
  Serial.begin(115200);

  LoRa.setPins(SS, -1, -1);  // -1 = nessun pin per RESET o DIO0

  while (!LoRa.begin(433E6)) {
    Serial.println("Errore nell'inizializzazione del modulo LoRa");
  }

  Serial.println("Trasmettitore LoRa Avviato");
}

void loop() {
  Serial.println("Invio messaggio...");
  LoRa.beginPacket();
  LoRa.print("Messaggio senza DIO0 e RESET!");
  LoRa.endPacket();
  
  delay(2000);
}
