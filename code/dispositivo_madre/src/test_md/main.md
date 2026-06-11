#include <Arduino.h>
#include "Point.h"
#include "Path.h"
#include "LinkedList.h"


void setup() {
  Serial.begin(250000);
  while (!Serial); // per i dispositivi USB

  Serial.println("Attendo punti...");
  LinkedList* points = new LinkedList();
  String line;

  while (true) {
    if (Serial.available()) {
      char c = Serial.read();
      if (c == '\n') {
        line.trim();
        if (line == "END") break;

        int commaIndex = line.indexOf(',');
        if (commaIndex > 0) {
          double lat = line.substring(0, commaIndex).toDouble();
          double lon = line.substring(commaIndex + 1).toDouble();
          points->append(Point(lat,lon));
        }

        line = "";
      } else {
        line += c;
      }
    }
  }

  Serial.println("Tutti i punti ricevuti:");
  points->printPoints();
  Serial.println(points->size());
}

void loop() {
  // Vuoto
}






#include <Arduino.h>
#include "GeoPoint.h"
#include "Gps.h"


Gps gps;



void setup() {
  Serial.begin(115200);
}


void loop() {
  gps.getPos();                    // aggiorna internamente
  GeoPoint pos = gps.getPos();     // ottieni l'oggetto aggiornato
  pos.print();                     // stampa
  delay(1000);                     // per non inondare la seriale
}
























#include <Arduino.h>
#include "path/Point.h"
#include "path/Path.h"
#include "path/LinkedList.h"

float distancePointToSegment(Point a, Point b, Point p);

void setup() {
  Serial.begin(250000);
  while (!Serial); // per i dispositivi USB

  Serial.println("Attendo punti...");
  LinkedList* points = new LinkedList();
  String line;

  while (true) {
    if (Serial.available()) {
      char c = Serial.read();
      if (c == '\n') {
        line.trim();
        if (line == "END") break;

        int commaIndex = line.indexOf(',');
        if (commaIndex > 0) {
          double lat = line.substring(0, commaIndex).toDouble();
          double lon = line.substring(commaIndex + 1).toDouble();
          points->append(Point(lat,lon));
        }

        line = "";
      } else {
        line += c;
      }
    }
  }

  Serial.println("Tutti i punti ricevuti:");
  //points->printPoints();
  Serial.println(points->size());
  Path percorso = Path(points, 10);
  Serial.println(percorso.getPathLeght());
  Serial.println("dentro ");
  Serial.println(percorso.isInsidePath(Point(44.1343530,12.2491696)));
  Serial.println("fuori ");
  Serial.println(Point(44.134350,12.249120).haversineDistanceTo(Point(44.135263,12.249205)));
  Serial.println(percorso.isInsidePath(Point(44.135263,12.249205)));
  Serial.println(percorso.isInsidePath(Point(44.134556,12.248849)));
  Serial.println(percorso.isInsidePath(Point(44.134447,12.249036)));
  Serial.println(percorso.isInsidePath(Point(44.134417,12.249037)));
  Serial.println("dentro ");
  Serial.println(percorso.isInsidePath(Point(44.134378,12.248981)));
  Serial.println("poco prima del limite ");
  Serial.println(percorso.isInsidePath(Point(44.134435,12.249099)));
  


  /*
  Point a = Point(44.116011,12.418999);
  Point b = Point(44.115942,12.420854);
  Point p = Point(44.116329,12.420290);

  Serial.println(p.distanceToLine(a,b));
  Serial.println(a.haversineDistanceTo(b));
  Serial.println(p.haversineDistanceTo(b));
  Serial.println(b.haversineDistanceTo(a));
  Serial.println(p.haversineDistanceTo(a));


  Serial.println(distancePointToSegment(a,b,p));*/

}

void loop() {
  // Vuoto
}

