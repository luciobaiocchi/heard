#pragma once

class SPIClass {
public:
    explicit SPIClass(int) {}
    void begin(int, int, int, int) {}
};

constexpr int HSPI = 0;
constexpr int VSPI = 1;
