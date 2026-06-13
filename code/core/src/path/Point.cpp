#include "path/Point.h"

const float R = 6371000; // Raggio medio della Terra in metri


Point::Point(float x, float y) : x(x), y(y) {}

float Point::getX() const {
    return x;
}

float Point::getY() const {
    return y;
}

float Point::distanceTo(const Point& other) const {
    float dx = x - other.x;
    float dy = y - other.y;
    return sqrt(dx * dx + dy * dy);
}

void Point::print() const {
    Serial.printf("Point(x=%.6f, y=%.6f)\n", x, y);
}


double Point::haversineDistanceTo(const Point& other) const {
    double lat1 = this->getX();  
    double lon1 = this->getY();

    double lat2 = other.getX();
    double lon2 = other.getY();

    double dLat = toRadians(lat2 - lat1);
    double dLon = toRadians(lon2 - lon1);

    double a = sin(dLat / 2) * sin(dLat / 2) +
               cos(toRadians(lat1)) * cos(toRadians(lat2)) *
               sin(dLon / 2) * sin(dLon / 2);
    double c = 2 * atan2(sqrt(a), sqrt(1 - a));

    return EARTH_RADIUS * c; // distanza in metri
}


double Point::distanceToLine(const Point& A, const Point& B) const {
    // Centro latitudine per la proiezione
    double lat0 = toRadians((A.getX() + B.getX()) / 2.0);

    // Convertiamo lat/lon in coordinate cartesiane locali
    double x0 = EARTH_RADIUS * toRadians(x - A.getX()) * cos(lat0);
    double y0 = EARTH_RADIUS * toRadians(y - A.getY());

    double x1 = 0;
    double y1 = 0;

    double x2 = EARTH_RADIUS * toRadians(B.getX() - A.getX()) * cos(lat0);
    double y2 = EARTH_RADIUS * toRadians(B.getY() - A.getY());

    // Formula della distanza punto-retta in 2D
    double num = fabs((y2 - y1) * x0 - (x2 - x1) * y0 + x2 * y1 - y2 * x1);
    double den = sqrt((y2 - y1) * (y2 - y1) + (x2 - x1) * (x2 - x1));
    return num / den;
}


