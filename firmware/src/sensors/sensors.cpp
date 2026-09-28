#include "sensors.h"

#include <Arduino.h>

#include "config.h"

static SensorData latest;

void sensorsInit() {
  // TODO(sensors): start the sensor bus and each sensor. Leave Valid = false for any that fail.
  // TODO(hardware): sensor models and pins unknown, see config.h.
}

void sensorsUpdate() {
  // TODO(sensors): read sensors, filter, and store results in `latest`.
}

SensorData sensorsGet() {
  return latest;
}
