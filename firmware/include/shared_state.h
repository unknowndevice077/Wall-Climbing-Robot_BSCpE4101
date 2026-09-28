// =============================================================================
// shared_state.h — the ONLY way the networking side (core 0) and the control
// task (core 1) talk to each other. Owner: lead.
//
// Every function copies data in or out under a lock, so it is thread-safe.
// WebSocket callbacks must NEVER call motor/adhesion functions directly;
// they call sharedApplyClientMessage() and the control task picks it up.
// =============================================================================
#pragma once

#include "protocol.h"
#include "state_machine.h"

// Called once from setup() before any task starts.
void sharedStateInit();

// ----- networking side (comms, core 0) ---------------------------------------
// Apply a parsed message. Returns nullptr or an error text to send back to the client.
const char* sharedApplyClientMessage(const ClientMessage& message);
// Latest telemetry published by the control task.
TelemetryData sharedGetTelemetry();

// ----- control side (main.cpp control task, core 1) --------------------------
Commands sharedGetCommands();
void sharedPublishTelemetry(const TelemetryData& telemetry);
