// Firmware version. Shown in telemetry and in the web UI.
// The web build reads this line too (web/vite.config.ts), so the UI built from the
// same commit shows the same version. If the UI shows a MISMATCH, you forgot to
// upload either the filesystem image or the firmware.
// Bump it (lead) when merging a release to main.
#pragma once

constexpr const char* FIRMWARE_VERSION = "0.1.0";
