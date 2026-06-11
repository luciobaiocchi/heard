#ifndef __LINKEDLIST__
#define __LINKEDLIST__

#include "path/Point.h"

struct Node {
    Point point;
    Node* next = nullptr;
    Node* prev = nullptr;
    Node(Point p) : point(p), next(nullptr), prev(nullptr) {}
};

class LinkedList {
public:
Node* head;
    LinkedList();
    ~LinkedList();

    void append(Point p);
    Node* findNearestPoint(Point reference);
    void clear();
    int size() const;
    void printPoints();
private:
    Node* tail;
    int count;
};

#endif
