// =============================================================================
// adhesion.h — keeps the robot stuck to the wall. Owner: adhesion. Implementation: src/adhesion/
//
// SHARED INTERFACE: the control task calls these. Do not rename them or change
// their parameters without the lead's OK (see AGENTS.md).
// Called only from the control task (core 1). Never call from networking code.
//
// SAFETY: if adhesion fails on the wall, the robot falls. Read SAFETY.md.
// =============================================================================
#pragma once

// Set up adhesion hardware. Called once from setup(). Must leave adhesion at 0 %.
void adhesionInit();

// Called every control loop. Use it for regular work (ramping power, reading
// feedback). Must be fast and must not block.
void adhesionUpdate();

// Set adhesion power, 0 .. 100 percent (clamped to MAX_ADHESION_POWER_PCT).
// Called EVERY control loop with the wanted power, usually the same value as last
// time: a repeat call must not restart or glitch the output.
void adhesionSetPower(int pct);

// Power currently applied, 0 .. 100 percent. Reported in telemetry.
int adhesionGetPower();

// True when adhesion is on AND working well enough to hold the robot.
// Return false if you are not sure.
bool adhesionIsOk();
