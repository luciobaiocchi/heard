#ifndef __POINT__
#define __POINT__

#include "path/Point.h"
#include "MathUtils.h"
#include <cmath>
#include <math.h>
#include <Arduino.h>


constexpr float EARTH_RADIUS = 6371000.0; // in metri

class Point{
    public:
    Point(float x = 500.0, float y = 500.0);
    float getX() const;
    float getY() const;
    float distanceTo(const Point& other) const;
    double haversineDistanceTo(const Point& other) const;
    double distanceToLine(const Point& a, const Point& b) const;

    virtual void print() const;
private:
    float x;
    float y;
};

#endif
