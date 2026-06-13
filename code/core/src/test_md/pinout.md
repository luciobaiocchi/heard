
GPS                             (UART)
ESP_TX  17 -> RX    VERDE
ESP_RX  16 -> TX    BLU


                                (SPI)
LORA_SCK  18    BLU (adesso giallo)
LORA_MISO 19    GRIGIO
LORA_MOSI 23    VIOLA
LORA_NSS   5    VERDE

Display E-INK	(2.9)           (SPI)
e-Paper Pin     ESP32 Pin (esempio)
VCC	            3.3V            GRIGIO
GND	            GND             MARRONE
DIN (MOSI)      GPIO23 (MOSI)   BLU
CLK (SCK)       GPIO18 (SCK)    GIALLO
CS	            GPI21           ARANCIONE
DC	            GPIO27          VERDE
RST	            GPIO33          BIANCO
BUSY	        GPIO4           VIOLA


SHARED lora-gps
18 giallo/arancio
23 blu 


MOSI = 13  (nuovo)             BLU
MISO = 12  (nuovo)                           - anche se l'e-Ink in molti modelli non usa MISO
SCK  = 14  (nuovo)             GIALLO
CS   = 15  (nuovo)             ARANCIONE      → invece del 21 di prima
DC   = 27  (VERDE)                          [come prima]
RST  = 33  (BIANCO)                         [come prima]
BUSY = 4   (VIOLA)                          [come prima]
VCC  = 3.3V                    GRIGIO
GND  = GND                     MARRONE











// Pin ePaper VECCHI
static const uint8_t EPD_CS   = 5;
static const uint8_t EPD_DC   = 17;
static const uint8_t EPD_RST  = 16;
static const uint8_t EPD_BUSY = 4;


Display OLED	ESP32 Pin

VCC	    3.3V o 5V
GND	    GND
SCL	    GPIO 22   VERDE
SDA	    GPIO 21   GIALLO
