#include "group/Group.h"

void Group::addPerson(const Person& person) {
    if (people.full()) {
        Serial.println("Gruppo pieno, impossibile aggiungere nuova persona.");
        return;
    }
    people.push_back(person);
}

int Group::findPersonIndexByName(const String& name) const {
    for (size_t i = 0; i < people.size(); ++i) {
        //people[i].print();
        if (people[i].getName() == name) {
            return i;
        }
    }
    return -1; // non trovato
}

void Group::printGroup() const {
    for (const auto& p : people) {
        p.print();
    }
}
