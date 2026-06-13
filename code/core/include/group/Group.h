#ifndef __GROUP__
#define __GROUP__

#include <Arduino.h>
#include <etl/vector.h>
#include "group/Person.h"

class Group {
public:
    static constexpr size_t MAX_PEOPLE = 10;

    Group() = default;

    void addPerson(const Person& person);
    int findPersonIndexByName(const String& name) const;
    void printGroup() const;

private:
    etl::vector<Person, MAX_PEOPLE> people;
};

#endif
