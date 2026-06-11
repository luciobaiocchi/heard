#pragma once

class String;
class SPIClass;

class LoRaClass {
public:
    void setPins(int, int, int) {}
    bool begin(long) { return true; }
    bool beginPacket() { return true; }
    int  endPacket(bool = false) { return 1; }
    int  parsePacket() { return 0; }
    bool available() { return false; }
    int  read() { return -1; }
    int  packetRssi() { return -100; }
    void print(int) {}
    void print(char) {}
    void print(const String&) {}
    void setSPI(SPIClass&) {}
};

inline LoRaClass LoRa;
