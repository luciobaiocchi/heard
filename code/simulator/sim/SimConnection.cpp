#include "sim/SimConnection.h"

SimConnection::SimConnection(int deviceId) : _deviceId(deviceId) {}

bool SimConnection::begin() { return true; }

bool SimConnection::sendMessage(int destinationId, const String& message) {
    _outQueue.push({destinationId, std::string(message.c_str())});
    return true;
}

bool SimConnection::broadcastMessage(const String& message) {
    _outQueue.push({-1, std::string(message.c_str())});
    return true;
}

bool SimConnection::hasMessage() const {
    return !_inQueue.empty();
}

String SimConnection::receiveMessage() {
    if (_inQueue.empty()) return String("");
    auto msg = _inQueue.front();
    _inQueue.pop();
    _lastSenderId = msg.senderId;
    return String(msg.content.c_str());
}

int SimConnection::getLastSenderId() const {
    return _lastSenderId;
}

bool SimConnection::hasPendingOut() const {
    return !_outQueue.empty();
}

std::pair<int, std::string> SimConnection::popPendingOut() {
    auto msg = _outQueue.front();
    _outQueue.pop();
    return msg;
}

void SimConnection::injectMessage(const std::string& msg, int senderId) {
    _inQueue.push({msg, senderId});
}
