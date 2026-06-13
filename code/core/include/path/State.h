#ifndef __STATE__
#define __STATE__

#include <Arduino.h> // Necessario per usare String

enum class State {
    IN_PATH,
    OUT_PATH,
    NO_DATA
};


inline String toString(State state) {
    switch (state) {
        case State::IN_PATH:
            return "IN PATH";
        case State::OUT_PATH:
            return "OUT PATH";
        case State::NO_DATA:
            return "NO DATA";
        default:
            return "UNKNOWN";
    }
}

#endif
