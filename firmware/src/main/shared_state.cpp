#include "shared_state.h"

#include <Arduino.h>

// A spinlock shared by both cores. Keep the code between ENTER and EXIT tiny:
// only copy data, never call Serial, WiFi, delay, or hardware functions.
static portMUX_TYPE lock = portMUX_INITIALIZER_UNLOCKED;

static Commands commands;
static TelemetryData telemetry;

void sharedStateInit() {
  portENTER_CRITICAL(&lock);
  commands = Commands();
  telemetry = TelemetryData();
  portEXIT_CRITICAL(&lock);
}

const char* sharedApplyClientMessage(const ClientMessage& message) {
  const uint32_t now = millis();
  portENTER_CRITICAL(&lock);
  const char* error = applyClientMessage(commands, message, now);
  portEXIT_CRITICAL(&lock);
  return error;
}

TelemetryData sharedGetTelemetry() {
  portENTER_CRITICAL(&lock);
  const TelemetryData copy = telemetry;
  portEXIT_CRITICAL(&lock);
  return copy;
}

Commands sharedGetCommands() {
  portENTER_CRITICAL(&lock);
  const Commands copy = commands;
  portEXIT_CRITICAL(&lock);
  return copy;
}

void sharedPublishTelemetry(const TelemetryData& t) {
  portENTER_CRITICAL(&lock);
  telemetry = t;
  portEXIT_CRITICAL(&lock);
}
