// =============================================================================
// sensors.h — reads and filters sensor data. Owner: sensors. Implementation: src/sensors/
//
// SHARED INTERFACE: the control task calls these. Do not rename them or change
// existing fields without the lead's OK (see AGENTS.md).
// Adding a NEW field to SensorData is fine; mention it in your PR.
// Called only from the control task (core 1).
// =============================================================================
#pragma once

// Latest filtered sensor readings.
// Every reading has a *Valid flag. If Valid is false, do not trust the value
// (sensor missing, not initialised yet, or read error). Telemetry sends null.
//
// TODO(hardware): which sensors the robot has is not decided yet.
struct SensorData {
  float pitchDeg = 0.0f;   // degrees, nose up = positive
  float rollDeg = 0.0f;    // degrees, right side down = positive
  bool tiltValid = false;

  float batteryV = 0.0f;   // volts
  bool batteryValid = false;
};

// Set up sensors (bus, calibration). Called once from setup().
// If a sensor is missing, keep going and leave its Valid flag false. Never block forever.
void sensorsInit();

// Read sensors and update filters. Called every control loop (100x/s).
// Must be fast and must not block.
void sensorsUpdate();

// Returns a copy of the latest readings.
SensorData sensorsGet();
