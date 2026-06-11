#ifndef __GEO_POINT__
#define __GEO_POINT__

#include "path/Point.h"

class GeoPoint: public Point {
public:
    GeoPoint(); 
    GeoPoint(float x, float y, int alt);  
    int getAlt() const;
    void print() const override;
private:
    int alt;
};

#endif
