#include "locomotion.h"

#include <Arduino.h>

#include "config.h"

// Keep speed within the safety limit from config.h (the state machine clamps too;
// clamping here again means a bug elsewhere can't exceed the limit).
static int clampSpeed(int pct) {
  return constrain(pct, -MAX_MOTOR_POWER_PCT, MAX_MOTOR_POWER_PCT);
}

void locomotionInit() {
  // TODO(locomotion): set up motor driver pins and PWM (skip any pin that is PIN_NOT_SET).
  // TODO(hardware): motor driver model unknown, see config.h.
  stopMotors();
}

void setMotorSpeed(int leftPct, int rightPct) {
  const int left = clampSpeed(leftPct);
  const int right = clampSpeed(rightPct);
  // TODO(locomotion): write `left` and `right` to the motor driver.
  (void)left;
  (void)right;
}

void stopMotors() {
  // TODO(locomotion): set both motor outputs to 0.
}
