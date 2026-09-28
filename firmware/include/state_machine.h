// =============================================================================
// state_machine.h — the robot's safety logic. Owner: lead.
// Plain C++ (no Arduino.h, no FreeRTOS) so it can be unit-tested on a PC.
//
//   state      wheels                  adhesion
//   ---------  ----------------------  -----------------------------------------
//   ESTOP      stopped                 FROZEN at its current power (commands rejected)
//   LINK_LOST  stopped                 keeps running at the last commanded power
//   RUNNING    follow `drive` (clamped) follows `adhesion` commands (clamped)
//
// ESTOP is latched: only an explicit `reset_estop` message clears it.
// The robot boots in ESTOP. Adhesion is never cut by the firmware's safety
// logic, because cutting adhesion on the wall makes the robot fall (docs/decisions.md).
// =============================================================================
#pragma once

#include <stdint.h>

#include "protocol.h"

enum class RobotState : uint8_t {
  ESTOP,
  LINK_LOST,
  RUNNING,
};

// Everything the operator has asked for so far.
struct Commands {
  bool estopLatched = true;   // boot e-stopped: operator must press Reset first
  bool everReceived = false;  // any valid message received since boot
  uint32_t lastMessageMs = 0; // time of the last valid message of any type
  uint32_t lastDriveMs = 0;   // time of the last `drive` message
  int driveLeftPct = 0;
  int driveRightPct = 0;
  int adhesionPct = 0;
};

// Apply one parsed message from the web UI.
// Returns nullptr if accepted, or an error text (static string) to send back.
const char* applyClientMessage(Commands& commands, const ClientMessage& message, uint32_t nowMs);

// Which state are we in right now?
RobotState robotState(const Commands& commands, uint32_t nowMs);

// What the motors and adhesion should do. All values are clamped to config.h limits.
struct Outputs {
  int leftPct = 0;
  int rightPct = 0;
  int adhesionPct = 0;
};
Outputs computeOutputs(const Commands& commands, RobotState state, uint32_t nowMs);

// Human-readable name, e.g. "RUNNING". Returns a static string.
const char* stateName(RobotState state);
