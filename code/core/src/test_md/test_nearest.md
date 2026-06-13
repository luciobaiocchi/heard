#include <Arduino.h>
#include <math.h>

// Classe Point
class Point {
public:
    Point(double x = 0.0, double y = 0.0) : x(x), y(y) {}
    double getX() const { return x; }
    double getY() const { return y; }

    double distanceTo(const Point &other) const {
        double dx = x - other.x;
        double dy = y - other.y;
        return sqrt(dx * dx + dy * dy);
    }

private:
    double x, y;
};

// Nodo della lista
struct PointNode {
    Point point;
    PointNode *next;
};

// Head della lista
PointNode *head = nullptr;

// Funzione per aggiungere un punto in testa alla lista
void addPoint(double x, double y) {
    PointNode *newNode = new PointNode{{x, y}, head};
    head = newNode;
}

// Trova il punto più vicino a un dato punto
Point *findClosestPoint(const Point &target) {
    if (!head) return nullptr;

    PointNode *current = head;
    Point *closest = &head->point;
    double minDist = closest->distanceTo(target);

    while (current) {
        double dist = current->point.distanceTo(target);
        if (dist < minDist) {
            closest = &current->point;
            minDist = dist;
        }
        current = current->next;
    }

    return closest;
}

// Popolamento iniziale del percorso con punti casuali
void populatePath() {
    for (int i = 0; i < 5000; ++i) {
        double x = random(0, 1000) / 10.0;
        double y = random(0, 1000) / 10.0;
        addPoint(x, y);
    }
}

void setup() {
    Serial.begin(115200);
    delay(1000);
    randomSeed(analogRead(0));

    populatePath();
    Serial.println("Percorso inizializzato.");
    Serial.printf("Heap libero dopo popolamento: %u byte\n", ESP.getFreeHeap());

}

void loop() {
    Serial.println("Ricerca del punto più vicino...");
    double x = random(0, 1000) / 10.0;
    double y = random(0, 1000) / 10.0;
    Point currentPos(x, y); // esempio posizione "utente"
    Point *closest = findClosestPoint(currentPos);

    if (closest) {
        Serial.printf("Closest point to (%.2f, %.2f): (%.2f, %.2f)\n",
                      currentPos.getX(), currentPos.getY(),
                      closest->getX(), closest->getY());
    } else {
        Serial.println("No points in the path.");
    }
    
    Serial.printf("Heap libero dopo ricerca: %u byte\n\n", ESP.getFreeHeap());

    delay(2000); // ogni 2 secondi
}

```
plantuml @startuml Alice -> Bob : Ciao! @enduml
```

```
mermaid sequenceDiagram 
Alice->>Bob: Ciao! 
```