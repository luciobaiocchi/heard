#pragma once
#include "group/Connection.h"
#include <queue>
#include <string>
#include <utility>

struct RawMessage {
    std::string content;
    int senderId;
};

// Queue-based Connection override for simulation.
// Python radio layer calls injectMessage() to deliver incoming messages
// and drains outgoing messages via hasPendingOut() / popPendingOut().
class SimConnection : public Connection {
public:
    explicit SimConnection(int deviceId);

    // Connection interface
    bool   begin()                                         override;
    bool   sendMessage(int destinationId, const String& message) override;
    bool   broadcastMessage(const String& message)         override;
    bool   hasMessage()                              const override;
    String receiveMessage()                                override;
    int    getLastSenderId()                         const override;

    // Used by Python radio layer
    bool hasPendingOut() const;
    std::pair<int, std::string> popPendingOut();   // dest=-1 means broadcast
    void injectMessage(const std::string& msg, int senderId);

private:
    int _deviceId;
    std::queue<RawMessage>               _inQueue;
    std::queue<std::pair<int,std::string>> _outQueue;
    mutable int _lastSenderId = -1;
};
