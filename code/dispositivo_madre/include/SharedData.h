#ifndef __SHAREDDATA__
#define __SHAREDDATA__

#include "path/GeoPoint.h"
#include "path/State.h"
#include <mutex>

class SharedData {
public:
    SharedData();

    GeoPoint getPos();
    void setPos(const GeoPoint& pos);
    bool hasValidGPS();

    State getState();
    void setState(State state);

private:
    GeoPoint position;
    State state;
    std::mutex mtx;
};

#endif
