#include "path/GeoPoint.h"
#include <Arduino.h>

GeoPoint::GeoPoint(float x, float y, int alt)
    : Point(x, y), alt(alt) {}

GeoPoint::GeoPoint() : Point(0, 0), alt(0) {}

void GeoPoint::print() const {
    Serial.printf("GeoPoint(x=%.6f, y=%.6f, alt=%d)\n", getX(), getY(), alt);
}

int GeoPoint::getAlt() const {
    return alt;
}
