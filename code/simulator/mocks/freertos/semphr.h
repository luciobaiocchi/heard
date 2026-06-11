#pragma once
#include "FreeRTOS.h"

using SemaphoreHandle_t = void*;

// Single-threaded simulation: all mutex ops are no-ops that always succeed.
inline SemaphoreHandle_t xSemaphoreCreateMutex() { return (void*)1; }
inline BaseType_t xSemaphoreTake(SemaphoreHandle_t, TickType_t) { return pdTRUE; }
inline void xSemaphoreGive(SemaphoreHandle_t) {}
inline void vSemaphoreDelete(SemaphoreHandle_t) {}
