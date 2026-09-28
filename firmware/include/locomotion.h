// =============================================================================
// locomotion.h — drive motors. Owner: locomotion. Implementation: src/locomotion/
//
// SHARED INTERFACE: the control task calls these. Do not rename them or change
// their parameters without the lead's OK (see AGENTS.md).
// Called only from the control task (core 1). Never call from networking code.
// =============================================================================
#pragma once

// Set up motor driver pins and PWM. Called once from setup().
// Must leave both motors stopped.
void locomotionInit();

// Set drive speed for each side.
//   leftPct, rightPct: -100 .. 100 percent of full power.
//     positive = forward (up the wall), negative = backward, 0 = stop.
//   Values are clamped to -MAX_MOTOR_POWER_PCT .. +MAX_MOTOR_POWER_PCT (config.h).
// Called every control loop (100x/s) while RUNNING: must be fast, must not block.
void setMotorSpeed(int leftPct, int rightPct);

// Stop both motors immediately. Called every control loop when not RUNNING,
// so repeat calls must be harmless.
void stopMotors();
