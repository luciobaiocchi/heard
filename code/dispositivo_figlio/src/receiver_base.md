#include <SPI.h>
#include <LoRa.h>

#define SS 5

void setup() {
  Serial.begin(115200);

  LoRa.setPins(SS, -1, -1);  // -1 = nessun pin per RESET o DIO0

  if (!LoRa.begin(433E6)) {
    Serial.println("Errore nell'inizializzazione del modulo LoRa");
    while (1);
  }

  Serial.println("Ricevitore LoRa Avviato");
}

void loop() {
  int packetSize = LoRa.parsePacket();  // polling continuo
  
  if (packetSize) {
    Serial.print("Messaggio ricevuto: ");
    while (LoRa.available()) {
      Serial.print((char)LoRa.read());
    }
    Serial.println();
  }
}
