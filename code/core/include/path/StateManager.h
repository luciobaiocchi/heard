#ifndef __STATEMANAGER__
#define __STATEMANAGER__


#include "path/GeoPoint.h"
#include "path/Path.h"
#include "path/LinkedList.h"
#include "path/State.h"
#include "path/Gps.h"
#include "SharedData.h"
#include "DisplayEInk.h"


class StateManager {
public:
    StateManager(SharedData* sharedData, DisplayEInk& disp);
    ~StateManager();

    void updateState();
    void loadPath();
    
private:
    SharedData* sharedData;
    Path path;
    Gps sensor;
    DisplayEInk& display;
    bool pathLoaded = false;
};

#endif
