# Decisions log

Write down every important decision so nobody has to remember why things are the way they are.
Newest at the bottom. Keep each entry short. Hardware decisions come from an approved "Hardware change" issue.

| Date | Decision | Reason | Who |
|---|---|---|---|
| 2026-09-29 | Microcontroller: **ESP32**. Firmware: **PlatformIO**, Arduino framework, C++. | Team choice. | Lead |
| 2026-09-29 | **PlatformIO only; Arduino IDE is not supported.** Firmware lives in `firmware/` (`include/` for interfaces + config, `src/<module>/` for code). | The web UI needs LittleFS uploads, pinned libraries, and CI; Arduino IDE can't do these reliably. One tool = one way to build. | Lead |
| 2026-09-29 | Pin **Arduino-ESP32 core 2.0.17** via the official `espressif32 @ 7.1.3` platform. | Core 3.x changed APIs (e.g. PWM `ledcSetup/ledcAttachPin` → `ledcAttach`). The community pioarduino platform (core 3.x) broke the shared PlatformIO Python environment on Windows during install, too risky for beginners. Revisit if we need a 3.x feature. | Lead |
| 2026-09-29 | All pins, constants and network settings live only in `firmware/include/config.h`. Unknown pins are `PIN_NOT_SET` (-1). WiFi credentials for station mode go in git-ignored `secrets.h`. | One place to check wiring; no conflicting pin numbers; no passwords in git. | Lead |
| 2026-09-29 | **Control = web UI over WiFi.** React + Vite (TS) in `web/`, served gzipped from LittleFS by ESPAsyncWebServer. Control + telemetry over a WebSocket at `/ws` (not HTTP requests). | Works on any phone/laptop, no app install, no internet. WebSocket gives low latency and one connection for both directions. | Lead |
| 2026-09-29 | WiFi **Access Point by default** (`WallBot`, http://192.168.4.1); optional station mode with mDNS (`wallbot.local`) that falls back to AP. | Must work anywhere without internet or school WiFi. | Lead |
| 2026-09-29 | Libraries: `esp32async/ESPAsyncWebServer 3.12.1`, `esp32async/AsyncTCP 3.5.0`, `bblanchon/ArduinoJson 7.2.2` (exact versions). | Maintained forks; support core 2.x. Exact versions so everyone builds the same thing. | Lead |
| 2026-09-29 | **Two FreeRTOS tasks:** control task on core 1 (every 10 ms), comms task + AsyncTCP on core 0. They share data only through `shared_state` (spinlock-protected copies). | Networking can't delay motor control; WebSocket callbacks never touch motors directly. | Lead |
| 2026-09-29 | JSON protocol with `type` field and `PROTOCOL_VERSION` (docs/protocol.md). `build-web.mjs` fails if firmware and web versions differ. Firmware version (`version.h`) shown in telemetry and UI. | Catch firmware/UI mismatches early (e.g. forgot the filesystem upload). | Lead |
| 2026-09-29 | **Link-loss failsafe:** no message for 500 ms → wheels stop, **adhesion keeps running**. Drive commands older than 500 ms are ignored even if heartbeats arrive. Not latched: wheels move again after a new `drive`. | Cutting adhesion on the wall makes the robot fall. Stopping wheels is always safe. | Lead |
| 2026-09-29 | **E-stop latches** until an explicit `reset_estop`. During e-stop, adhesion is **frozen** at its current power (adhesion commands rejected). Robot **boots in e-stop**. Estop and reset both clear the stored drive command. | Nothing should change unexpectedly while stopped; a reconnecting UI can't drive the robot without a deliberate reset. | Lead |
| 2026-09-29 | Operator controls adhesion power directly (slider); the UI confirms before setting it to 0. The firmware does not yet react to `adhesionIsOk()` (only reports it). | Adhesion hardware and how to detect "holding" are unknown; decide the fault behaviour later (see tasks). | Lead |
| 2026-09-29 | Testing drive limit `MAX_MOTOR_POWER_PCT = 30`. | Keep early tests slow. Lead raises it after tests. | Lead |
