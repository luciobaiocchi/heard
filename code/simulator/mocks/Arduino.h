#pragma once
#include <string>
#include <sstream>
#include <iomanip>
#include <cstdint>
#include <cstring>
#include <algorithm>
#include <stdexcept>

// In the real ESP32 Arduino core, Arduino.h pulls in FreeRTOS automatically.
// Our mocks replicate that so any file that only includes <Arduino.h> still
// gets vTaskDelay, pdMS_TO_TICKS, xSemaphore*, etc.
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"

// ── Simulation clock ──────────────────────────────────────────────────────
inline unsigned long g_sim_ms = 0;
inline unsigned long millis() { return g_sim_ms; }
inline void delay(unsigned long) {}

// ── Integer types ─────────────────────────────────────────────────────────
using uint8_t  = unsigned char;
using uint16_t = unsigned short;
using uint32_t = unsigned int;
using int32_t  = int;
// TickType_t is defined in freertos/FreeRTOS.h (included above)

// ── String class ──────────────────────────────────────────────────────────
class String {
public:
    String() {}
    String(const char* s) : s_(s ? s : "") {}
    String(const std::string& s) : s_(s) {}
    String(char c) : s_(1, c) {}
    String(int v) : s_(std::to_string(v)) {}
    String(long v) : s_(std::to_string(v)) {}
    String(unsigned int v) : s_(std::to_string(v)) {}
    String(unsigned long v) : s_(std::to_string(v)) {}
    String(float v, int decimals = 2) {
        std::ostringstream ss;
        ss << std::fixed << std::setprecision(decimals) << v;
        s_ = ss.str();
    }
    String(double v, int decimals = 2) {
        std::ostringstream ss;
        ss << std::fixed << std::setprecision(decimals) << v;
        s_ = ss.str();
    }

    String& operator+=(const String& o) { s_ += o.s_; return *this; }
    String& operator+=(char c)          { s_ += c;    return *this; }
    String  operator+(const String& o) const { return String(s_ + o.s_); }
    bool    operator==(const String& o) const { return s_ == o.s_; }
    bool    operator!=(const String& o) const { return s_ != o.s_; }
    bool    operator< (const String& o) const { return s_ <  o.s_; }

    bool isEmpty()  const { return s_.empty(); }
    int  length()   const { return (int)s_.size(); }
    const char* c_str() const { return s_.c_str(); }

    bool startsWith(const String& prefix) const {
        return s_.size() >= prefix.s_.size() &&
               s_.compare(0, prefix.s_.size(), prefix.s_) == 0;
    }

    int indexOf(char c, int from = 0) const {
        if (from < 0) from = 0;
        auto pos = s_.find(c, (size_t)from);
        return pos == std::string::npos ? -1 : (int)pos;
    }
    int indexOf(const String& sub, int from = 0) const {
        if (from < 0) from = 0;
        auto pos = s_.find(sub.s_, (size_t)from);
        return pos == std::string::npos ? -1 : (int)pos;
    }

    String substring(int from, int to = -1) const {
        if (from < 0) from = 0;
        if (from >= (int)s_.size()) return String("");
        int end = (to < 0 || to > (int)s_.size()) ? (int)s_.size() : to;
        if (end <= from) return String("");
        return String(s_.substr((size_t)from, (size_t)(end - from)));
    }

    int   toInt()   const {
        if (s_.empty()) return 0;
        try { return std::stoi(s_); } catch(...) { return 0; }
    }
    float toFloat() const {
        if (s_.empty()) return 0.0f;
        try { return std::stof(s_); } catch(...) { return 0.0f; }
    }

    void trim() {
        size_t a = s_.find_first_not_of(" \t\r\n");
        if (a == std::string::npos) { s_ = ""; return; }
        size_t b = s_.find_last_not_of(" \t\r\n");
        s_ = s_.substr(a, b - a + 1);
    }

    explicit operator std::string() const { return s_; }

private:
    std::string s_;
};

inline String operator+(const char* lhs, const String& rhs) {
    return String(std::string(lhs ? lhs : "") + std::string(rhs.c_str()));
}

// ── Serial stub ───────────────────────────────────────────────────────────
struct SerialClass {
    void begin(long) {}
    template<typename T> void print(const T&) {}
    template<typename T> void println(const T&) {}
    void println() {}
    int available() { return 0; }
    String readStringUntil(char) { return ""; }
};
inline SerialClass Serial;

// ── ESP stub ──────────────────────────────────────────────────────────────
struct EspClass {
    uint32_t getFreeHeap() const { return 100000u; }
};
inline EspClass ESP;

inline int xPortGetCoreID() { return 0; }
