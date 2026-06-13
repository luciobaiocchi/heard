#include "group/Person.h"

Person::Person(String nome, GeoPoint pos) : nome(nome), pos(pos) {}

void Person::print() const {
    Serial.print("Nome: ");
    Serial.print(nome);
    Serial.print(", Posizione: ");
    pos.print();
}

GeoPoint Person::getPos() const {
    return pos;
}

String Person::getPosAsString(){
    return "(" + String(pos.getX()) + ", " + String(pos.getY()) + ", " + String(pos.getAlt()) + ")";
}

String Person::getName() const{
    return nome;
}


void Person::updatePos(GeoPoint newPos) {
    pos = newPos;
}
