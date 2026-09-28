// Parser/writer for the WebSocket protocol. Owner: lead. Spec: docs/protocol.md
// Plain C++ + ArduinoJson (no Arduino.h) so the PC unit tests can use it.
#include "protocol.h"

#include <ArduinoJson.h>
#include <math.h>
#include <string.h>

#include "version.h"

constexpr size_t MAX_MESSAGE_LENGTH = 256;

// Round and clamp a JSON number into an int range. NaN becomes 0.
static int toClampedInt(float value, int low, int high) {
  if (isnan(value)) return 0;
  if (value < low) return low;
  if (value > high) return high;
  return static_cast<int>(lroundf(value));
}

// One decimal place is plenty for the UI and keeps messages short.
static float round1(float value) {
  return roundf(value * 10.0f) / 10.0f;
}

const char* protocolParseClientMessage(const char* json, size_t length, ClientMessage& out) {
  if (length > MAX_MESSAGE_LENGTH) return "message too long";

  JsonDocument doc;
  if (deserializeJson(doc, json, length)) return "invalid JSON";

  const char* type = doc["type"];
  if (type == nullptr) return "missing type";

  out = ClientMessage();
  if (strcmp(type, "drive") == 0) {
    if (!doc["left"].is<float>() || !doc["right"].is<float>()) return "drive needs numbers left and right";
    out.type = ClientMessageType::DRIVE;
    out.leftPct = toClampedInt(doc["left"].as<float>(), -100, 100);
    out.rightPct = toClampedInt(doc["right"].as<float>(), -100, 100);
    return nullptr;
  }
  if (strcmp(type, "adhesion") == 0) {
    if (!doc["power"].is<float>()) return "adhesion needs a number power";
    out.type = ClientMessageType::ADHESION;
    out.adhesionPct = toClampedInt(doc["power"].as<float>(), 0, 100);
    return nullptr;
  }
  if (strcmp(type, "heartbeat") == 0) {
    out.type = ClientMessageType::HEARTBEAT;
    return nullptr;
  }
  if (strcmp(type, "estop") == 0) {
    out.type = ClientMessageType::ESTOP;
    return nullptr;
  }
  if (strcmp(type, "reset_estop") == 0) {
    out.type = ClientMessageType::RESET_ESTOP;
    return nullptr;
  }
  return "unknown type";
}

// Serialize `doc` into buffer. Returns 0 if it doesn't fit.
static size_t writeDoc(const JsonDocument& doc, char* buffer, size_t capacity) {
  if (measureJson(doc) >= capacity) return 0;
  return serializeJson(doc, buffer, capacity);
}

size_t protocolWriteHello(char* buffer, size_t capacity) {
  JsonDocument doc;
  doc["type"] = "hello";
  doc["protocol"] = PROTOCOL_VERSION;
  doc["firmware"] = FIRMWARE_VERSION;
  return writeDoc(doc, buffer, capacity);
}

size_t protocolWriteTelemetry(const TelemetryData& t, char* buffer, size_t capacity) {
  JsonDocument doc;
  doc["type"] = "telemetry";
  doc["protocol"] = PROTOCOL_VERSION;
  doc["firmware"] = FIRMWARE_VERSION;
  doc["state"] = t.state;
  doc["estop"] = t.estop;
  doc["linkOk"] = t.linkOk;
  if (t.batteryValid) {
    doc["batteryV"] = round1(t.batteryV);
  } else {
    doc["batteryV"] = nullptr;
  }
  doc["adhesionPct"] = t.adhesionPct;
  doc["adhesionOk"] = t.adhesionOk;
  doc["motorLeftPct"] = t.motorLeftPct;
  doc["motorRightPct"] = t.motorRightPct;
  if (t.tiltValid) {
    doc["pitchDeg"] = round1(t.pitchDeg);
    doc["rollDeg"] = round1(t.rollDeg);
  } else {
    doc["pitchDeg"] = nullptr;
    doc["rollDeg"] = nullptr;
  }
  doc["uptimeMs"] = t.uptimeMs;
  return writeDoc(doc, buffer, capacity);
}

size_t protocolWriteError(const char* message, char* buffer, size_t capacity) {
  JsonDocument doc;
  doc["type"] = "error";
  doc["message"] = message;
  return writeDoc(doc, buffer, capacity);
}
