// =============================================================================
// config.h — THE ONLY PLACE for pin numbers, tunable constants and network settings.
//
// Rules (see AGENTS.md):
//   * Never hard-code a pin number or tuning value anywhere else.
//   * Changing a PIN here = hardware change. Open a "Hardware change" issue and
//     get the lead's OK first.
//   * A pin value of PIN_NOT_SET (-1) means "not decided yet". Code must check for
//     it and skip that hardware instead of crashing.
//
// This file must stay plain C++ (no Arduino.h) so the PC unit tests can use it.
// =============================================================================
#pragma once

#include <stdint.h>

// Optional, git-ignored file for private settings (home/school WiFi password).
// Copy include/secrets.example.h to include/secrets.h and edit it.
#if __has_include("secrets.h")
#include "secrets.h"
#endif

// -----------------------------------------------------------------------------
// Board
// -----------------------------------------------------------------------------
// TODO(hardware): confirm the exact ESP32 board model (we build for "esp32dev").

constexpr int PIN_NOT_SET = -1;

// -----------------------------------------------------------------------------
// Pins — locomotion (owner: locomotion)
// TODO(hardware): drive motor type, motor driver model and wiring are unknown.
// The A/B pairs are placeholders; rename them once the driver is chosen
// (e.g. PWM + DIR, or IN1 + IN2).
// -----------------------------------------------------------------------------
constexpr int PIN_MOTOR_LEFT_A  = PIN_NOT_SET;  // TODO(hardware)
constexpr int PIN_MOTOR_LEFT_B  = PIN_NOT_SET;  // TODO(hardware)
constexpr int PIN_MOTOR_RIGHT_A = PIN_NOT_SET;  // TODO(hardware)
constexpr int PIN_MOTOR_RIGHT_B = PIN_NOT_SET;  // TODO(hardware)

// -----------------------------------------------------------------------------
// Pins — adhesion (owner: adhesion)
// TODO(hardware): adhesion method (fan / vacuum pump / magnets) and its driver are unknown.
// -----------------------------------------------------------------------------
constexpr int PIN_ADHESION_OUTPUT = PIN_NOT_SET;  // TODO(hardware)

// -----------------------------------------------------------------------------
// Pins — sensors (owner: sensors)
// TODO(hardware): sensor models and bus (I2C / analog / other) are unknown.
// -----------------------------------------------------------------------------
constexpr int PIN_I2C_SDA     = PIN_NOT_SET;  // TODO(hardware)
constexpr int PIN_I2C_SCL     = PIN_NOT_SET;  // TODO(hardware)
constexpr int PIN_BATTERY_ADC = PIN_NOT_SET;  // TODO(hardware): battery type + voltage divider unknown

// -----------------------------------------------------------------------------
// Pins — misc (owner: lead)
// -----------------------------------------------------------------------------
constexpr int PIN_STATUS_LED = PIN_NOT_SET;  // TODO(hardware)

// -----------------------------------------------------------------------------
// Safety limits (see SAFETY.md). Only the lead changes these.
// -----------------------------------------------------------------------------
// Max drive power in percent. Kept LOW while testing. Raise only with lead approval.
constexpr int MAX_MOTOR_POWER_PCT = 30;

// Max adhesion power in percent.
constexpr int MAX_ADHESION_POWER_PCT = 100;  // TODO(hardware): lower it if the adhesion hardware needs a limit

// Link-loss failsafe: if NO message (heartbeat, drive, ...) arrives for this long,
// the wheels stop. Adhesion keeps running. The web UI sends a message every ~100 ms.
constexpr uint32_t LINK_TIMEOUT_MS = 500;

// -----------------------------------------------------------------------------
// Timing
// -----------------------------------------------------------------------------
constexpr uint32_t CONTROL_LOOP_PERIOD_MS = 10;   // control task runs 100 times per second
constexpr uint32_t TELEMETRY_PERIOD_MS    = 100;  // telemetry to the web UI, 10 times per second
constexpr uint32_t SERIAL_BAUD            = 115200;

// -----------------------------------------------------------------------------
// FreeRTOS tasks. Control on core 1, networking on core 0. Don't change without the lead.
// -----------------------------------------------------------------------------
constexpr int      CONTROL_TASK_CORE     = 1;
constexpr int      CONTROL_TASK_PRIORITY = 3;
constexpr uint32_t CONTROL_TASK_STACK    = 4096;
constexpr int      COMMS_TASK_CORE       = 0;
constexpr int      COMMS_TASK_PRIORITY   = 1;
constexpr uint32_t COMMS_TASK_STACK      = 6144;

// -----------------------------------------------------------------------------
// Network (owner: control/UI + lead)
// Default: the robot makes its own WiFi network (Access Point). No internet needed.
//   Join WiFi "WallBot", open http://192.168.4.1
// -----------------------------------------------------------------------------
constexpr const char* WIFI_AP_SSID = "WallBot";
// TODO(team): choose your own AP password before the demo (at least 8 characters).
constexpr const char* WIFI_AP_PASSWORD = "wallbot-change-me";

// Optional station mode: the robot joins an existing WiFi and is reachable at
// http://wallbot.local (mDNS). Falls back to Access Point mode if it can't connect.
// Put WIFI_STA_SSID / WIFI_STA_PASSWORD in include/secrets.h, never here.
constexpr bool WIFI_USE_STATION = false;
#ifndef WIFI_STA_SSID
#define WIFI_STA_SSID ""
#endif
#ifndef WIFI_STA_PASSWORD
#define WIFI_STA_PASSWORD ""
#endif
constexpr uint32_t WIFI_STA_CONNECT_TIMEOUT_MS = 10000;
constexpr const char* MDNS_HOSTNAME = "wallbot";  // -> http://wallbot.local
