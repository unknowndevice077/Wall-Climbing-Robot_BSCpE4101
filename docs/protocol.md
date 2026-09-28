# WebSocket protocol

**Protocol version: 1**

The web UI and the robot talk over one WebSocket at `ws://<robot>/ws`
(`ws://192.168.4.1/ws` in Access Point mode). Every message is one JSON text frame with a `type` field.

This document, [firmware/include/protocol.h](../firmware/include/protocol.h) and
[web/src/protocol.ts](../web/src/protocol.ts) must always agree.
**Changes need the lead's approval** (CODEOWNERS). If a change is not backwards-compatible,
bump `PROTOCOL_VERSION` in both files; `scripts/build-web.mjs` fails the build if they differ.

## Client → robot

| type | fields | meaning |
|---|---|---|
| `drive` | `left`, `right`: number, -100..100 (%) | Wheel power. Positive = forward (up the wall). |
| `adhesion` | `power`: number, 0..100 (%) | Adhesion power. |
| `heartbeat` | – | "I'm still here." |
| `estop` | – | Emergency stop. Latches. |
| `reset_estop` | – | Clear the e-stop latch. |

```json
{"type":"drive","left":25,"right":25}
{"type":"adhesion","power":60}
{"type":"heartbeat"}
{"type":"estop"}
{"type":"reset_estop"}
```

Rules:
- The client **must send a message at least every 100 ms**: `drive` while the operator is driving,
  otherwise `heartbeat`.
- Numbers outside the range are **clamped** by the robot (and rounded to integers). Wheel power is then
  limited again to `MAX_MOTOR_POWER_PCT` from `config.h`.
- When the joystick is released, send `drive` with `0, 0` once, then heartbeats.
- Invalid messages get an `error` reply and are otherwise ignored.

## Robot → client

| type | when | fields |
|---|---|---|
| `hello` | once, on connect | `protocol`, `firmware` |
| `telemetry` | ~10 Hz (every `TELEMETRY_PERIOD_MS`) | see below |
| `error` | when a message is rejected | `message`: string |

`telemetry` fields:

| field | type | meaning |
|---|---|---|
| `protocol` | int | protocol version |
| `firmware` | string | firmware version, e.g. `"0.1.0"` |
| `state` | `"ESTOP"` \| `"LINK_LOST"` \| `"RUNNING"` | robot state |
| `estop` | bool | e-stop latched |
| `linkOk` | bool | robot is receiving messages in time |
| `batteryV` | number \| null | battery voltage (V); null if not measured |
| `adhesionPct` | int 0..100 | adhesion power actually applied |
| `adhesionOk` | bool | adhesion module reports it is holding |
| `motorLeftPct`, `motorRightPct` | int -100..100 | wheel power actually applied |
| `pitchDeg`, `rollDeg` | number \| null | tilt in degrees; null if no valid IMU reading |
| `uptimeMs` | int | ms since the robot booted |

```json
{"type":"hello","protocol":1,"firmware":"0.1.0"}
{"type":"telemetry","protocol":1,"firmware":"0.1.0","state":"RUNNING","estop":false,"linkOk":true,
 "batteryV":null,"adhesionPct":60,"adhesionOk":false,"motorLeftPct":25,"motorRightPct":25,
 "pitchDeg":null,"rollDeg":null,"uptimeMs":123456}
{"type":"error","message":"adhesion is locked while e-stop is active"}
```

## Safety behaviour (implemented in firmware/src/main/state_machine.cpp)

| state | wheels | adhesion |
|---|---|---|
| `ESTOP` | stopped | frozen at current power; `adhesion` messages rejected |
| `LINK_LOST` | stopped | keeps running at the last commanded power |
| `RUNNING` | follow `drive` | follow `adhesion` |

- The robot **boots in `ESTOP`**. Send `reset_estop` to arm it.
- `estop` latches until `reset_estop`. Both clear the stored drive command, so the robot never
  jumps back to an old command.
- **Link loss:** no message of any type for `LINK_TIMEOUT_MS` (500 ms) → `LINK_LOST`: wheels stop,
  **adhesion keeps running**. The robot returns to `RUNNING` when messages arrive again, but the wheels only move
  after a new `drive` message.
- A `drive` command older than 500 ms is ignored, even if heartbeats keep arriving.
- `drive` messages during `ESTOP` are ignored silently. The UI disables the joystick then.
