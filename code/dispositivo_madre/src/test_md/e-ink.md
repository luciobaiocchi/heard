#include <Arduino.h>
#include "DisplayEInk.h"

DisplayEInk display;

void setup() {
    Serial.begin(115200);
    display.begin();
    display.drawLoadingScreen();
    delay(3000);
    display.drawMainScreen();
}

void loop() {
    delay(60000); // Non serve aggiornare continuamente
}
