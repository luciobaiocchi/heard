#include <TinyGPS++.h>
#include <HardwareSerial.h>

// Istanza del GPS parser
TinyGPSPlus gps;

// Serial2 per comunicare con il GPS
HardwareSerial SerialGPS(2);

// Configura i pin usati
#define RXD2 16  // Collegato a TX del GPS
#define TXD2 17  // Non serve, ma va inizializzato

void setup() {
  Serial.begin(115200);        // Monitor seriale
  SerialGPS.begin(9600, SERIAL_8N1, RXD2, TXD2);  // GPS in UART2
  Serial.println("Test GPS avviato...");
}

void loop() {
  while (SerialGPS.available() > 0) {
    char c = SerialGPS.read();
    gps.encode(c);

    if (gps.location.isUpdated()) {
      Serial.print("Latitudine: ");
      Serial.println(gps.location.lat(), 6);
      Serial.print("Longitudine: ");
      Serial.println(gps.location.lng(), 6);
      Serial.print("Altitudine: ");
      Serial.print(gps.altitude.meters());
      Serial.println(" m");
      Serial.print("Satelliti: ");
      Serial.println(gps.satellites.value());
      Serial.print("HDOP: ");
      Serial.println(gps.hdop.hdop());
      Serial.println("--------------------------");
    }
  }
}
