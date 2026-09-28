// =============================================================================
// protocol.h — WebSocket message format. Owner: lead. Spec: docs/protocol.md
//
// Must match web/src/protocol.ts. Changing anything here needs the lead's OK
// and a PROTOCOL_VERSION bump in BOTH files (scripts/build-web.mjs checks this).
// Plain C++ (no Arduino.h) so the PC unit tests can use it.
// =============================================================================
#pragma once

#include <stddef.h>
#include <stdint.h>

constexpr int PROTOCOL_VERSION = 1;

// ----- client -> robot -------------------------------------------------------
enum class ClientMessageType : uint8_t {
  DRIVE,        // {"type":"drive","left":-100..100,"right":-100..100}
  ADHESION,     // {"type":"adhesion","power":0..100}
  HEARTBEAT,    // {"type":"heartbeat"}
  ESTOP,        // {"type":"estop"}
  RESET_ESTOP,  // {"type":"reset_estop"}
};

struct ClientMessage {
  ClientMessageType type = ClientMessageType::HEARTBEAT;
  int leftPct = 0;      // DRIVE only, already clamped to -100..100
  int rightPct = 0;     // DRIVE only, already clamped to -100..100
  int adhesionPct = 0;  // ADHESION only, already clamped to 0..100
};

// Parse one JSON text message. Out-of-range numbers are clamped.
// Returns nullptr on success, or a short error text (static string) on failure.
const char* protocolParseClientMessage(const char* json, size_t length, ClientMessage& out);

// ----- robot -> client -------------------------------------------------------
struct TelemetryData {
  const char* state = "";   // state name, e.g. "RUNNING" (must point to a static string)
  bool estop = true;        // e-stop latched
  bool linkOk = false;      // robot is receiving messages in time
  float batteryV = 0.0f;
  bool batteryValid = false;
  int adhesionPct = 0;      // adhesion power actually applied
  bool adhesionOk = false;
  int motorLeftPct = 0;     // motor output actually applied
  int motorRightPct = 0;
  float pitchDeg = 0.0f;
  float rollDeg = 0.0f;
  bool tiltValid = false;
  uint32_t uptimeMs = 0;
};

// Each writer fills `buffer` with a JSON message and returns its length (0 if it didn't fit).
size_t protocolWriteHello(char* buffer, size_t capacity);
size_t protocolWriteTelemetry(const TelemetryData& t, char* buffer, size_t capacity);
size_t protocolWriteError(const char* message, char* buffer, size_t capacity);
