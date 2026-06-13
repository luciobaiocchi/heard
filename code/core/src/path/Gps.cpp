#include "path/Gps.h"
#include <Arduino.h>

Gps::Gps() : SerialGPS(2), gps() {
    sensorOn = false;
    position = GeoPoint(0, 0, 0);
}

Gps::~Gps() {}

void Gps::begin() {
    SerialGPS.begin(9600, SERIAL_8N1, RXD2, TXD2);  
    Serial.println("GPS avviato...");
}

const GeoPoint Gps::getPos(){
    readSensor();
    return position;
}

void Gps::readSensor() {
    sensorOn = false; // reset a ogni lettura
    Serial.print("Satelliti: ");
    Serial.println(gps.satellites.value());
    while (SerialGPS.available() > 0) {
        sensorOn = true;
        char c = SerialGPS.read();
        gps.encode(c);

        if (gps.location.isUpdated()) {
            position = GeoPoint(
                static_cast<float>(gps.location.lat()),
                static_cast<float>(gps.location.lng()),
                gps.altitude.meters()
            );

            Serial.print("Satelliti: ");
            Serial.println(gps.satellites.value());
        }
    }
    vTaskDelay(pdMS_TO_TICKS(1));  // 500 ms
}


const bool Gps::isOn() {
    // Considera "acceso" solo se ricevi dati e hai una posizione valida
    readSensor();
    return sensorOn;

    //return gps.location.isValid();
    //&& gps.location.age() < 2000;
}
