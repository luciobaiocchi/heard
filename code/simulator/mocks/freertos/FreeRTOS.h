#pragma once
#include <cstdint>

using BaseType_t  = int;
using UBaseType_t = unsigned int;
using TickType_t  = uint32_t;

constexpr BaseType_t pdTRUE  = 1;
constexpr BaseType_t pdFALSE = 0;
constexpr BaseType_t pdPASS  = 1;
constexpr BaseType_t pdFAIL  = 0;

constexpr uint32_t portTICK_PERIOD_MS = 1;

inline TickType_t pdMS_TO_TICKS(uint32_t ms) { return ms; }
