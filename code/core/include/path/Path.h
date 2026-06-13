#ifndef __PATH__
#define __PATH__

#include "path/Point.h"
#include "path/LinkedList.h"
#include "MathUtils.h"

class Path {
public:
    Path(LinkedList* points, int maxDistance = 100);
    Path(int maxDistance = 100);
    ~Path();

    void addList(LinkedList* points);
    void clear();
    int size() const;
    double getPathLeght() const;
    void printPath();
    bool isInsidePath(Point p) const;
    double distancePointToSegment(Point a, Point b, Point p) const;
private:
    int maxDistance;
    LinkedList* points; 
};

#endif
