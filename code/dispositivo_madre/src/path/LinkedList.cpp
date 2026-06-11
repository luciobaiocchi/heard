#include "path/LinkedList.h"
#include <Arduino.h>

LinkedList::LinkedList() : head(nullptr), count(0) {}

LinkedList::~LinkedList() {
    clear();
}

void LinkedList::append(Point p) {
    Node* newNode = new Node(p);
    if (!head) {
        head = newNode;
        tail = newNode;
    } else {
        tail->next = newNode;
        newNode->prev = tail;
        tail = newNode;
    }
    count++;
}

Node* LinkedList::findNearestPoint(Point reference) {
    if (!head) return new Node(Point()); // Return a default node if the list is empty

    Node* current = head;
    Node* closest = current;
    double minDist = reference.distanceTo(closest->point);

    while (current) {
        double dist = reference.distanceTo(current->point);
        if (dist < minDist) {
            minDist = dist;
            closest = current;
        }
        current = current->next;
    }
    return closest;
}


void LinkedList::clear() {
    Node* current = head;
    while (current) {
        Node* temp = current;
        current = current->next;
        delete temp;
    }
    head = nullptr;
    tail = nullptr;
    count = 0;
}

void LinkedList::printPoints() {
  Node* current = head;
  while (current) {
    Serial.printf("x=%.6f, y=%.6f\n",
                  current->point.getX(), current->point.getY());
    current = current->next;
  }
}


int LinkedList::size() const {
    return count;
}

