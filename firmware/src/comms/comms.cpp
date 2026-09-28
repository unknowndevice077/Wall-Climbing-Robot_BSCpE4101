// =============================================================================
// comms.cpp — WiFi, web server (LittleFS) and WebSocket. Owner: control/UI + lead.
//
// Runs on core 0. Never calls motor/adhesion/sensor code: incoming messages go
// into shared state, and the control task (core 1) acts on them.
// =============================================================================
#include "comms.h"

#include <Arduino.h>
#include <AsyncTCP.h>
#include <ESPAsyncWebServer.h>
#include <ESPmDNS.h>
#include <LittleFS.h>
#include <WiFi.h>

#include "config.h"
#include "protocol.h"
#include "shared_state.h"

static AsyncWebServer server(80);
static AsyncWebSocket ws("/ws");

static void sendError(AsyncWebSocketClient* client, const char* message) {
  char buffer[160];
  if (protocolWriteError(message, buffer, sizeof(buffer)) > 0) client->text(buffer);
}

static void onWebSocketEvent(AsyncWebSocket*, AsyncWebSocketClient* client, AwsEventType type,
                             void* arg, uint8_t* data, size_t length) {
  switch (type) {
    case WS_EVT_CONNECT: {
      Serial.printf("ws: client %u connected\n", client->id());
      char buffer[128];
      if (protocolWriteHello(buffer, sizeof(buffer)) > 0) client->text(buffer);
      break;
    }
    case WS_EVT_DISCONNECT:
      Serial.printf("ws: client %u disconnected\n", client->id());
      break;
    case WS_EVT_DATA: {
      // Only accept complete, single-frame text messages (all our messages are small).
      const AwsFrameInfo* info = static_cast<AwsFrameInfo*>(arg);
      if (!info->final || info->index != 0 || info->len != length || info->opcode != WS_TEXT) {
        sendError(client, "send one small text message per frame");
        break;
      }
      ClientMessage message;
      const char* error = protocolParseClientMessage(reinterpret_cast<const char*>(data), length, message);
      if (error == nullptr) error = sharedApplyClientMessage(message);
      if (error != nullptr) sendError(client, error);
      break;
    }
    default:
      break;
  }
}

static bool startStation() {
  if (!WIFI_USE_STATION || strlen(WIFI_STA_SSID) == 0) return false;

  Serial.printf("wifi: connecting to \"%s\"...\n", WIFI_STA_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.setHostname(MDNS_HOSTNAME);
  WiFi.begin(WIFI_STA_SSID, WIFI_STA_PASSWORD);
  const uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < WIFI_STA_CONNECT_TIMEOUT_MS) {
    vTaskDelay(pdMS_TO_TICKS(100));  // fine here: this is the comms task, not the control task
  }
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("wifi: station failed, falling back to Access Point");
    WiFi.disconnect(true);
    return false;
  }
  Serial.printf("wifi: connected, open http://%s.local or http://%s\n", MDNS_HOSTNAME,
                WiFi.localIP().toString().c_str());
  return true;
}

static void startAccessPoint() {
  WiFi.mode(WIFI_AP);
  WiFi.softAP(WIFI_AP_SSID, WIFI_AP_PASSWORD);
  Serial.printf("wifi: access point \"%s\", open http://%s\n", WIFI_AP_SSID,
                WiFi.softAPIP().toString().c_str());
}

static void startWebServer() {
  if (!LittleFS.begin(false)) {
    Serial.println("LittleFS mount failed: did you run 'Upload Filesystem Image'? (see README)");
  }

  ws.onEvent(onWebSocketEvent);
  server.addHandler(&ws);

  // Serves the gzipped web UI (index.html.gz, ...) with Content-Encoding: gzip.
  server.serveStatic("/", LittleFS, "/").setDefaultFile("index.html").setCacheControl("no-cache");
  server.onNotFound([](AsyncWebServerRequest* request) {
    request->send(404, "text/plain",
                  "Not found. If this is the home page, upload the filesystem image (see README).");
  });
  server.begin();
}

static void commsTask(void*) {
  if (!startStation()) startAccessPoint();
  if (MDNS.begin(MDNS_HOSTNAME)) MDNS.addService("http", "tcp", 80);
  startWebServer();

  char buffer[384];
  TickType_t lastWake = xTaskGetTickCount();
  for (;;) {
    ws.cleanupClients();
    if (ws.count() > 0) {
      const TelemetryData t = sharedGetTelemetry();
      const size_t length = protocolWriteTelemetry(t, buffer, sizeof(buffer));
      if (length > 0) ws.textAll(buffer, length);
    }
    vTaskDelayUntil(&lastWake, pdMS_TO_TICKS(TELEMETRY_PERIOD_MS));
  }
}

void commsStart() {
  xTaskCreatePinnedToCore(commsTask, "comms", COMMS_TASK_STACK, nullptr, COMMS_TASK_PRIORITY,
                          nullptr, COMMS_TASK_CORE);
}
