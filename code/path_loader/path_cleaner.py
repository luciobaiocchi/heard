import xml.etree.ElementTree as ET

# File di input e output
input_file = "activity_19135267297.gpx"
output_file = "output_cleaned.gpx"

# Parsing dell'albero XML
tree = ET.parse(input_file)
root = tree.getroot()

# Namespace da usare per la ricerca dei tag
namespaces = {
    "default": "http://www.topografix.com/GPX/1/1",
    "ns3": "http://www.garmin.com/xmlschemas/TrackPointExtension/v1"
}

# Itera su ogni trkpt
for trkpt in root.findall(".//default:trkpt", namespaces):
    # Rimuove il tag <time> se presente
    time_tag = trkpt.find("default:time", namespaces)
    if time_tag is not None:
        trkpt.remove(time_tag)

    # Rimuove il tag <extensions> se presente
    ext_tag = trkpt.find("default:extensions", namespaces)
    if ext_tag is not None:
        trkpt.remove(ext_tag)

# Scrive il nuovo file XML mantenendo l'intestazione
tree.write(output_file, encoding="UTF-8", xml_declaration=True)
print(f"File salvato come: {output_file}")
