#include "state_machine.h"

#include "config.h"

static int clampInt(int value, int low, int high) {
  if (value < low) return low;
  if (value > high) return high;
  return value;
}

// How long ago `thenMs` was. Signed, so a timestamp slightly in the future
// (set by the other core a moment ago) counts as "just now", not "long ago".
static int32_t ageMs(uint32_t nowMs, uint32_t thenMs) {
  return static_cast<int32_t>(nowMs - thenMs);
}

const char* applyClientMessage(Commands& c, const ClientMessage& m, uint32_t nowMs) {
  // Every valid message proves the link is alive.
  c.everReceived = true;
  c.lastMessageMs = nowMs;

  switch (m.type) {
    case ClientMessageType::HEARTBEAT:
      return nullptr;

    case ClientMessageType::DRIVE:
      // Ignored while e-stopped. The UI disables driving then, so no error spam.
      if (c.estopLatched) return nullptr;
      c.driveLeftPct = m.leftPct;
      c.driveRightPct = m.rightPct;
      c.lastDriveMs = nowMs;
      return nullptr;

    case ClientMessageType::ADHESION:
      // E-stop freezes adhesion at its current power: no surprises while stopped.
      if (c.estopLatched) return "adhesion is locked while e-stop is active";
      c.adhesionPct = m.adhesionPct;
      return nullptr;

    case ClientMessageType::ESTOP:
      c.estopLatched = true;
      c.driveLeftPct = 0;
      c.driveRightPct = 0;
      return nullptr;

    case ClientMessageType::RESET_ESTOP:
      // Clear the old drive command so the robot doesn't jump when reset.
      c.estopLatched = false;
      c.driveLeftPct = 0;
      c.driveRightPct = 0;
      return nullptr;
  }
  return "unknown message";
}

RobotState robotState(const Commands& c, uint32_t nowMs) {
  if (c.estopLatched) return RobotState::ESTOP;
  if (!c.everReceived || ageMs(nowMs, c.lastMessageMs) > static_cast<int32_t>(LINK_TIMEOUT_MS)) {
    return RobotState::LINK_LOST;
  }
  return RobotState::RUNNING;
}

Outputs computeOutputs(const Commands& c, RobotState state, uint32_t nowMs) {
  Outputs out;

  // Adhesion is never cut by the safety logic (the robot would fall).
  out.adhesionPct = clampInt(c.adhesionPct, 0, MAX_ADHESION_POWER_PCT);

  // Wheels only move while RUNNING and with a fresh drive command.
  const bool driveFresh = ageMs(nowMs, c.lastDriveMs) <= static_cast<int32_t>(LINK_TIMEOUT_MS);
  if (state == RobotState::RUNNING && driveFresh) {
    out.leftPct = clampInt(c.driveLeftPct, -MAX_MOTOR_POWER_PCT, MAX_MOTOR_POWER_PCT);
    out.rightPct = clampInt(c.driveRightPct, -MAX_MOTOR_POWER_PCT, MAX_MOTOR_POWER_PCT);
  }
  return out;
}

const char* stateName(RobotState state) {
  switch (state) {
    case RobotState::ESTOP:     return "ESTOP";
    case RobotState::LINK_LOST: return "LINK_LOST";
    case RobotState::RUNNING:   return "RUNNING";
  }
  return "UNKNOWN";
}
