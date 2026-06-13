#ifndef __CONNECTION__
#define __CONNECTION__

#include <Arduino.h>
#include <SPI.h>
#include <LoRa.h>

#include "Constants.h"


class Connection {
public:
    Connection();
    virtual ~Connection() = default;

    // Inizializza il modulo LoRa (frequenza, pin, ecc.)
    virtual bool begin();

    // Invia un messaggio a un ID specifico
    virtual bool sendMessage(int destinationId, const String& message);

    // Invia un messaggio broadcast
    virtual bool broadcastMessage(const String& message);

    // Controlla se è disponibile un messaggio ricevuto
    virtual bool hasMessage() const;

    // Ottiene l'ultimo messaggio ricevuto
    virtual String receiveMessage();

    // Ottiene l'ID del mittente dell'ultimo messaggio ricevuto
    virtual int getLastSenderId() const;

private:
    int lastSenderId = -1;
    void debug(String info);
    SPIClass spiLoRa = SPIClass(HSPI);

    // Eventuali pin di configurazione o metodi privati
    // int csPin, resetPin, irqPin;
};

#endif // __CONNECTION__
