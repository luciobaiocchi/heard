#include <SPI.h>
#include <LoRa.h>

// Configurazione pin LoRa
#define LORA_SCK  18
#define LORA_MISO 19
#define LORA_MOSI 23
#define LORA_CS   5

// Frequenza LoRa (433 MHz, modifica se necessario)
#define LORA_FREQ 433E6

void setup() {
  Serial.begin(115200);
  Serial.println("Ricevitore GPS + LoRa avviato...");

  // Inizializzazione LoRa
  LoRa.setPins(LORA_CS, -1, -1);  // Senza DIO0 e RESET
  if (!LoRa.begin(LORA_FREQ)) {
    Serial.println("Errore inizializzazione LoRa!");
    while (true);
  }
  Serial.println("LoRa inizializzato correttamente.");
}

void loop() {
  int packetSize = LoRa.parsePacket();
  if (packetSize) {
    Serial.println("Pacchetto ricevuto!");

    String receivedData = "";
    while (LoRa.available()) {
      char c = (char)LoRa.read();
      receivedData += c;
    }

    Serial.println("Dato grezzo ricevuto via LoRa:");
    Serial.println(receivedData);
    Serial.println("--------------------------");
  }
}




```kotlin
val bluetoothAdapter = BluetoothAdapter.getDefaultAdapter()
val device = bluetoothAdapter.getRemoteDevice(deviceAddress)
val gatt = device.connectGatt(context, false, gattCallback)

val gattCallback = object : BluetoothGattCallback() {
    override fun onConnectionStateChange(gatt: BluetoothGatt, status: Int, newState: Int) { ... }
    override fun onServicesDiscovered(gatt: BluetoothGatt, status: Int) { ... }
    override fun onCharacteristicChanged(gatt: BluetoothGatt, characteristic: BluetoothGattCharacteristic) {
        val data = characteristic.getStringValue(0)
        println("Ricevuto: $data")
    }
}
```


```c++
BLEDevice::init("ESP32_Sensor");
BLEServer *pServer = BLEDevice::createServer();
BLEService *pService = pServer->createService(SERVICE_UUID);
BLECharacteristic *pCharacteristic = pService->createCharacteristic(
  CHARACTERISTIC_UUID,
  BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY
);
pCharacteristic->setValue("25°C");
pService->start();
```