#include "group/Connection.h"
#include "freertos/task.h"

Connection::Connection() : spiLoRa(VSPI){}

bool Connection::begin() {
    //spiLoRa.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_CS);

    // Configura LoRa per usare bus SPI custom
    //LoRa.setSPI(spiLoRa);
    LoRa.setPins(LORA_CS, -1, -1);  // SENZA DIO0 e RESET

    // Puoi impostare i pin se necessario con LoRa.setPins(cs, reset, irq);
    
    if (!LoRa.begin(LORA_FREQ)) {
        debug("LoRa init failed!");
        return false;
    }
    debug("LoRa init successful.");
    return true;
}

bool Connection::sendMessage(int destinationId, const String& message) {
    if (!LoRa.beginPacket()) {
        debug("LoRa beginPacket failed");
        return false;
    }

    // Scrivi nel buffer
    LoRa.print(destinationId);  
    LoRa.print('|');
    LoRa.print(message);

    // Invia in modalità asincrona
    if (LoRa.endPacket(true) == 0) { 
        debug("LoRa endPacket failed");
        return false;
    }

    debug("Trasmissione avviata");

    vTaskDelay(pdMS_TO_TICKS(200)); // attesa indicativa, non blocca CPU
    debug("Trasmissione completata");
    return true;
}


bool Connection::broadcastMessage(const String& message) {
    //debug("BROADCAST MESSAGE");
    return sendMessage(0, message); // 0 come ID broadcast convenzionale
}

bool Connection::hasMessage() const {
    return LoRa.parsePacket() > 0;
}

String Connection::receiveMessage() {
    if (!hasMessage()) return "";

    String received = "";
    while (LoRa.available()) {
        received += (char)LoRa.read();
    }

    // Parsing: formato "id|messaggio"
    int separatorIndex = received.indexOf('|');
    if (separatorIndex == -1) {
        lastSenderId = -1;
        return "";
    }

    String idPart = received.substring(0, separatorIndex);
    String messagePart = received.substring(separatorIndex + 1);

    lastSenderId = idPart.toInt();
    return messagePart;
}

int Connection::getLastSenderId() const {
    return lastSenderId;
}

void Connection::debug(String info) {
    Serial.println("CONNECTION [ " + info + " ]");
}