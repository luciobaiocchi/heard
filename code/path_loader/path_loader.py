import xml.etree.ElementTree as ET
import serial
import time

# === CONFIGURAZIONE ===
BYTES_PER_POINT = 8 
DECIMAL_NUM = 6 # Numero di cifre dopo virgola, 6 è ideale perchè precisione di 1 metro e non occcupa troppo spazio
SERIAL_PORT = '/dev/tty.usbserial-110'

# Serial setup
ser = serial.Serial(SERIAL_PORT, 115200, timeout=1)
time.sleep(2)

# Parse GPX
tree = ET.parse('activity_19135281495.gpx')
root = tree.getroot()
ns = {'default': 'http://www.topografix.com/GPX/1/1'}
trkpts = root.findall('.//default:trkpt', ns)

print(f"\nInvio di {len(trkpts)} punti...")

# Invio punti
for pt in trkpts:
    lat = round(float(pt.attrib['lat']), DECIMAL_NUM)
    lon = round(float(pt.attrib['lon']), DECIMAL_NUM)
    msg = f"{lat},{lon}\n"
    ser.write(msg.encode('utf-8'))
    print("Inviato:", msg.strip())
    time.sleep(0.001)

# Fine
ser.write(b"END\n")
print("Fine inviato.")

# === STIMA MEMORIA ===
used_bytes = len(trkpts) * BYTES_PER_POINT
total_heap = 350656  # esempio: heap disponibile all'avvio
used_percent = (used_bytes / total_heap) * 100

print(f"\n--- Stima memoria ESP32 ---")
print(f"Tipo punto (byte): {BYTES_PER_POINT}")
print(f"Memoria stimata usata: {used_bytes} byte")
print(f"Percentuale heap usato: {used_percent:.2f}%\n")

ser.close()
