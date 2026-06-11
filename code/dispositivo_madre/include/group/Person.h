#ifndef __PERSON__
#define __PERSON__

#include <Arduino.h> 
#include "path/GeoPoint.h"

class Person {
public:
    Person(String nome = "", GeoPoint pos = GeoPoint(0,0,0));

    void print() const;
    GeoPoint getPos() const;
    String getName() const;
    String getPosAsString();
    void updatePos(GeoPoint newPos);

private:
    String nome;
    GeoPoint pos;
};

#endif
