#include "path/StateManager.h"
#include <Arduino.h>

StateManager::StateManager(SharedData* sd, DisplayEInk& display) 
    : sharedData(sd), path(100), sensor(), display(display) {
    
    //display.begin();
    display.drawMainScreen();

    if (!sharedData) {
        Serial.println("Errore: sharedData null nel costruttore!");
        return;
    }
    sensor = Gps();
    sensor.begin();
    loadPath();
}

StateManager::~StateManager() {
    path.clear();
}

void StateManager::updateState(){
    if (!sharedData) {
        Serial.println("Errore: sharedData è nullptr!");
        return;
    }
    if (sensor.isOn()){
        display.updateHeader(true, true);
        GeoPoint pos = sensor.getPos();
        pos.print();
        if (pathLoaded){
            char posizione[32];
            snprintf(posizione, sizeof(posizione), "%.6f %.6f", pos.getX(), pos.getY());
            display.updateUserData(posizione, toString(State::IN_PATH).c_str());
        }
        if (path.isInsidePath(pos)) {
            sharedData->setState(State::IN_PATH);
        } else {
            sharedData->setState(State::OUT_PATH);
        }
    }else
    {
        Serial.println("waiting gps");
    }
    
}

void StateManager::loadPath(){
    Serial.println("Attendo punti...");
    display.drawMainScreen();
    LinkedList* points = new LinkedList();
    String line;
    
    while (true) {
        if (Serial.available()) {
            char c = Serial.read();
            if (c == '\n') {
                line.trim();
                if (line == "END") break;

                int commaIndex = line.indexOf(',');
                if (commaIndex > 0) {
                double lat = line.substring(0, commaIndex).toDouble();
                double lon = line.substring(commaIndex + 1).toDouble();
                points->append(Point(lat,lon));
                }

                line = "";
            } else {
                line += c;
            }
        }else {
            vTaskDelay(pdMS_TO_TICKS(10));  // aspetta 10 ms, non bloccare
        }
    }

    path.addList(points);

    Serial.println("Tutti i punti ricevuti:");
    display.drawReceivedPOints(points->size(), path.getPathLeght());
    //points->printPoints();
    pathLoaded = true;
    Serial.println(points->size());
    vTaskDelay(1000);
    display.loadActivityScreen();
}