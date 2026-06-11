#include "SharedData.h"

SharedData::SharedData() : position(0, 0, 0), state(State::IN_PATH) {}

GeoPoint SharedData::getPos() {
    std::lock_guard<std::mutex> lock(mtx);
    return position;
}

void SharedData::setPos(const GeoPoint& pos) {
    std::lock_guard<std::mutex> lock(mtx);
    position = pos;
}

State SharedData::getState() {
    std::lock_guard<std::mutex> lock(mtx);
    return state;
}

void SharedData::setState(State s) {
    std::lock_guard<std::mutex> lock(mtx);
    state = s;
}

bool SharedData::hasValidGPS() {
    std::lock_guard<std::mutex> lock(mtx);
    return true;
}

