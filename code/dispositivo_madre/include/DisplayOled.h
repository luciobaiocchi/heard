#ifndef __OLED_DISPLAY__
#define __OLED_DISPLAY__
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Wire.h>


// Configurazione OLED Display
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET    -1
#define SCREEN_ADDRESS 0x3C  // indirizzo I2C display



class DisplayOled: {
    Adafruit_SSD1306 display(int screenWidth, int screenHeigth, Wire& wire, int oledReset);
    public:
    GeoPoint(double x, double y, int alt);  
    double startScreen();
    void clearScreen();
    void navigateTo(double x, double y);
    int getAlt();
private:
    double x;
    double y;
    int alt;
};

#endif
