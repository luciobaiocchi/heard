


#include <SPI.h>
#include <LoRa.h>
#include <TinyGPS++.h>
#include <HardwareSerial.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// Configurazione OLED Display
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET    -1
#define SCREEN_ADDRESS 0x3C  // indirizzo I2C display

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// Configurazione LoRa
#define LORA_SCK  18
#define LORA_MISO 19
#define LORA_MOSI 23
#define LORA_CS   5
#define LORA_FREQ 433E6

// Configurazione GPS
#define GPS_RX_PIN 16  // ESP32 RX ← GPS TX
#define GPS_TX_PIN 17  // ESP32 TX → GPS RX (opzionale)

TinyGPSPlus gps;
HardwareSerial SerialGPS(1);  // UART1 (Serial1 su ESP32)

bool lora_status = false;
bool gps_status = false;

String getStatusString(bool state);

void setup() {
  Serial.begin(115200);
  Serial.println("Avvio dispositivo GPS + LoRa + Display...");

  // Inizializza Display OLED
  if (!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS)) {
    Serial.println(F("Errore Display SSD1306"));
    while (true);
  }
  display.clearDisplay();
  display.setTextSize(3);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(15, 18);
  display.println("HEARD");
  display.display();

  // Inizializza GPS
  SerialGPS.begin(9600, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);
  Serial.println("GPS inizializzato.");
  gps_status = true;

  // Inizializza LoRa
  delay(500);
  LoRa.setPins(LORA_CS, -1, -1);  // SENZA DIO0 e RESET
  if (!LoRa.begin(LORA_FREQ)) {
    Serial.println("Errore inizializzazione LoRa");
    while (true);
  }
  Serial.println("LoRa inizializzato correttamente.");
  lora_status = true;
  delay(2000);
}

void loop() {
  // Lettura GPS
  while (SerialGPS.available()) {
    char c = SerialGPS.read();
    gps.encode(c);
  }

  if (gps.location.isUpdated()) {
    // Costruisci stringa solo con Latitudine e Longitudine
    String gpsData = "LA:" + String(gps.location.lat(), 6) + ";LO:" + String(gps.location.lng(), 6);
    
    Serial.print("Invio dati GPS: ");
    Serial.println(gpsData);

    // Invio dati via LoRa
    LoRa.beginPacket();
    LoRa.print(gpsData);
    LoRa.endPacket();

    Serial.println("Dati GPS inviati via LoRa.");

    // Visualizza sul Display OLED (PARTE AZZURRA DEL TUO PROGETTO)
    display.clearDisplay();
    display.setTextSize(2);
    display.setCursor(0, 0);
    display.print("G " + getStatusString(gps_status));
    display.println(" L " + getStatusString(lora_status));
    display.setTextSize(2);
    display.println(gps.location.lat(), 6);
    display.println(gps.location.lng(), 6);
    display.print("N Sat " + String(gps.satellites.value()));
    display.display();
  }

  delay(2000);  // Aspetta 2 secondi prima di leggere di nuovo
}

String getStatusString(bool state) {
  if (state){
    return "ON";
  }
  return "OFF";
}









#include <SPI.h>
#include <LoRa.h>

// crea bus SPI custom su HSPI
SPIClass spiLoRa(HSPI);

void setup() {
  Serial.begin(115200);

  // inizializza bus HSPI con pin custom
  spiLoRa.begin(14 /*SCK*/, 12 /*MISO*/, 13 /*MOSI*/, 5 /*NSS*/);

  // configura LoRa per usare il bus custom spiLoRa
  LoRa.setSPI(spiLoRa);
  LoRa.setPins(5 /*NSS*/, 14 /*reset pin LoRa*/, 26 /*dio0*/);

  if (!LoRa.begin(433E6)) {
    Serial.println("LoRa init failed");
    while (1);
  }
  Serial.println("LoRa init OK");

  // qui codice display con libreria originale su VSPI (non modificato)
}

void loop() {
  // loop codice LoRa + display separati
}
