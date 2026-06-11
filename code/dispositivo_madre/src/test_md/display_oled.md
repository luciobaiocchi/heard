#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// Impostazioni display
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET    -1  // Reset pin (non collegato)
#define SCREEN_ADDRESS 0x3C  // Indirizzo I²C standard

// Crea oggetto display
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

void setup() {
  Serial.begin(115200);

  // Inizializza il display
  if (!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS)) {
    Serial.println(F("SSD1306 non trovato!"));
    while (true); // Stop
  }

  display.clearDisplay();

  // Test: scritta "Ciao ESP32"
  display.setTextSize(2);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 10);
  display.println(F("Ciao ESP32!"));
  display.display(); // Mostra sullo schermo

  delay(2000);
}

void loop() {
  // Test animazione: inverti display ogni secondo
  display.invertDisplay(true);
  delay(1000);
  display.invertDisplay(false);
  delay(1000);
}
