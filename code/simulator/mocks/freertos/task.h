#pragma once
#include "FreeRTOS.h"

using TaskHandle_t   = void*;
using TaskFunction_t = void(*)(void*);

inline BaseType_t xTaskCreatePinnedToCore(
    TaskFunction_t, const char*, uint32_t, void*, UBaseType_t, TaskHandle_t*, int) {
    return pdPASS;
}

inline void vTaskDelay(TickType_t) {}
inline void vTaskDelete(TaskHandle_t) {}
