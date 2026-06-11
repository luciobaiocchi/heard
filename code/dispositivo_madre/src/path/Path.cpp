#include "path/Path.h"
#include <Arduino.h>

Path::Path(LinkedList* points, int maxDistance)
    : points(points), maxDistance(maxDistance) {}

Path::Path(int maxDistance)
    : maxDistance(maxDistance) {}

Path::~Path() {
    // Se la lista è allocata dinamicamente fuori da Path, NON va cancellata qui.
    // Ma se Path è il proprietario, allora:
    if (points) {
        points->clear();
        delete points;
        points = nullptr;
    }
}

void Path::clear() {
    if (points) {
        points->clear();
    }
}

int Path::size() const {
    return points ? points->size() : 0;
}

double Path::getPathLeght() const {
    if (!points || points->size() < 2) return 0;

    double total = 0.0;
    Node* current = points->head;
    while (current && current->next) {
        total += current->point.haversineDistanceTo(current->next->point);
        current = current->next;
    }
    return total;
}

void Path::printPath() {
    if (!points) return;
    points->printPoints();
}

bool Path::isInsidePath(Point p) const {
    if (!points || points->size() == 0) return false;

    Node* nearest = points->findNearestPoint(p);
    /*Serial.print("Point");
    p.print();
    Serial.print("   nearest");
    nearest->point.print();*/

    if (nearest->point.haversineDistanceTo(p) <= maxDistance) {
        /*
        Serial.print("circle");
        Serial.println(nearest->point.haversineDistanceTo(p));
        */
        return true;
    }else if (nearest->prev){
        double distance = distancePointToSegment(nearest->point,nearest->prev->point,p);
        /*
        Serial.print(distance);
        Serial.print(" prev");
        */
        if (distance <= maxDistance){
            return true;
        }
    }else if (nearest->next){
        double distance = distancePointToSegment(nearest->point,nearest->next->point,p);
        /*
        Serial.print(distance);
        Serial.print(" next");
        */
        if (distance <= maxDistance){
            return true;
        }
    };
    return false;
}

void Path::addList(LinkedList* newPoints){
    points = newPoints;
}


// Distanza punto -> segmento (in metri)
double Path::distancePointToSegment(Point a, Point b, Point p) const {
    // 1. Converti i tre punti da coordinate geografiche a coordinate locali in metri
    double latRef = a.getX(); // latitudine di riferimento

    // punto A (origine)
    double ax = 0.0;
    double ay = 0.0;

    // punto B
    double bx = EARTH_RADIUS * toRadians(b.getY() - a.getY()) * cos(toRadians((a.getX() + b.getX()) / 2.0));
    double by = EARTH_RADIUS * toRadians(b.getX() - a.getX());

    // punto P
    double px = EARTH_RADIUS * toRadians(p.getY() - a.getY()) * cos(toRadians((a.getX() + p.getX()) / 2.0));
    double py = EARTH_RADIUS * toRadians(p.getX() - a.getX());

    // 2. Calcola il punto proiettato di P sul segmento AB (geometria piana)
    double dx = bx - ax;
    double dy = by - ay;

    double lengthSquared = dx * dx + dy * dy;
    if (lengthSquared == 0.0) {
        // A e B sono lo stesso punto
        return sqrt((px - ax) * (px - ax) + (py - ay) * (py - ay));
    }

    // Proiezione scalare normalizzata
    double t = ((px - ax) * dx + (py - ay) * dy) / lengthSquared;
    t = fmax(0.0, fmin(1.0, t));  // clamp tra 0 e 1

    // Punto proiettato sulla retta AB
    double projX = ax + t * dx;
    double projY = ay + t * dy;

    // Distanza euclidea tra P e la proiezione su AB
    double dist = sqrt((px - projX) * (px - projX) + (py - projY) * (py - projY));
    return dist;
}