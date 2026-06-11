#ifndef __EINK_DISPLAY__
#define __EINK_DISPLAY__

#include <Arduino.h>
#include <GxEPD2_BW.h>
#include <Adafruit_GFX.h>
#include "Constants.h"

class DisplayEInk {
public:
    DisplayEInk(); // costruttore
    
    void begin();

    void drawMainScreen();
    void drawLoadingScreen();
    void drawReceivedPOints(int points, double distanceMeters);

    void loadActivityScreen();
    void updateUserData(const char* posizione, const char* stato);
    void updateTableRow(int rowIndex, const char* nome, const char* stato);


    void clearScreen();
    void navigateTo(double x, double y);
    int getAlt();
    void updateHeader(bool loraState, bool gpsState);

private:
    void updateFooter(const char* text);
    void updateBody(const char* text, int textSize = 2);
    void drawCenteredText(const char* text, int y, int textSize);

    void drawUserData(const char* posizione, const char* stato);
    void drawTableRow(int rowIndex, const char* nome, const char* stato, bool isHeader);

    double x;
    double y;
    int alt;

    // Solo epd2, nessun altro wrapper
    GxEPD2_290_T94_V2 epd2;
    GxEPD2_BW<GxEPD2_290_T94_V2, GxEPD2_290_T94_V2::HEIGHT> display;

    static const int headerH = 30;
    static const int userH = 80;
    static const int rowH = 20;
    static const int tableRows = 7;

};

#endif
