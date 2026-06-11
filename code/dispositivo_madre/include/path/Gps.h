#ifndef __GPS__
#define __GPS__


#include "path/Gps.h"
#include "path/GeoPoint.h"
#include <TinyGPS++.h>
#include <HardwareSerial.h>

class Gps {
public:
    Gps();
    ~Gps();

    const GeoPoint getPos();
    void begin();
    const bool isOn();
private:
    GeoPoint position;
    TinyGPSPlus gps;
    HardwareSerial SerialGPS;
    bool sensorOn;
    static const int RXD2 = 16;
    static const int TXD2 = 17;
    void readSensor();
};

#endif
