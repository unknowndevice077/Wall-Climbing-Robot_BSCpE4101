// =============================================================================
// comms.h — WiFi, web server and WebSocket. Owner: control/UI + lead. Implementation: src/comms/
//
// comms is the ONLY module that touches networking. It runs in its own task on
// core 0 and talks to the control task only through shared_state.h.
// Message format: docs/protocol.md.
// =============================================================================
#pragma once

// Start the comms task: WiFi (Access Point or station), serving the web UI from
// LittleFS, the WebSocket at /ws, and telemetry at TELEMETRY_PERIOD_MS.
// Returns immediately; the work happens in the background task.
void commsStart();
