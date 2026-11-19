# Wall-Climbing Robot (BSCpE 4101)

A small robot that sticks to a wall and drives up it, controlled from a phone or laptop browser.
Built by a 5-person team.

- **Firmware:** ESP32 + PlatformIO (Arduino framework, C++), in `firmware/`
- **Web UI:** React + Vite (TypeScript), in `web/`. The robot serves it itself; no internet needed.

> **Status:** early development. Hardware modules are empty stubs that compile; the web UI, WebSocket
> link, and safety logic work. Hardware that isn't decided yet is marked `TODO(hardware)`.

**Read before touching the robot:** [SAFETY.md](SAFETY.md)
**Read before your first commit:** [CONTRIBUTING.md](CONTRIBUTING.md)
**Using an AI tool?** It must follow [AGENTS.md](AGENTS.md).

**The robot design** (thrust-vectoring climber, 1,039 g):
[specs, weights and parts](docs/SPECIFICATIONS.md) · [build guide](docs/BUILD.md) · [setup checklist](docs/SETUP.md) ·
[3D model + printable parts](design/README.md) · [simulation (MuJoCo + Webots)](sim/README.md)

---

## Who owns what

| Role | GitHub | Owns |
|---|---|---|
| Lead / integration | `@lead-owner` | `firmware/src/main/`, `config.h`, state machine, protocol, reviews all PRs |
| Locomotion | `@locomotion-owner` | `firmware/src/locomotion/`, `include/locomotion.h` |
| Adhesion | `@adhesion-owner` | `firmware/src/adhesion/`, `include/adhesion.h` |
| Sensors | `@sensors-owner` | `firmware/src/sensors/`, `include/sensors.h` |
| Control / UI | `@control-owner` | `web/`, `firmware/src/comms/` (with lead), `scripts/` |

## Project layout

```
firmware/                 PlatformIO project (open THIS folder in VS Code for firmware work)
  platformio.ini
  include/                interfaces (.h) + config.h (ALL pins/constants) + protocol.h + version.h
  src/
    main/                 startup, control task, state machine, shared state   (lead)
    locomotion/           drive motors                                         (locomotion)
    adhesion/             staying on the wall                                  (adhesion)
    sensors/              IMU, battery, ...                                    (sensors)
    comms/                WiFi, web server, WebSocket, protocol parser         (control/UI + lead)
  test/                   PC unit tests
  data/                   GENERATED web UI files for LittleFS (git-ignored, never edit)
web/                      React + Vite app                                     (control/UI)
  src/protocol.ts         message types, must match docs/protocol.md
scripts/build-web.mjs     builds web/ → gzips → firmware/data
docs/                     protocol, decisions log, task backlog, robot specs/build/setup
design/                   3D model (Blender script), printable STLs, weight report
sim/                      MuJoCo + Webots climb simulations, Wokwi prototype
```

## How it works

```
 phone/laptop browser                         ESP32
 ┌──────────────────┐   WiFi "WallBot"   ┌───────────────────────────────────────┐
 │ React UI         │ ── HTTP (once) ──► │ core 0: comms task                    │
 │  joystick,       │                    │   web server (LittleFS, gzip)         │
 │  adhesion,       │ ◄─ WebSocket /ws ─►│   WebSocket ──► shared state (locked) │
 │  E-STOP,         │    drive/heartbeat │                      │                │
 │  telemetry       │    every 100 ms,   │ core 1: control task ▼  every 10 ms   │
 └──────────────────┘    telemetry 10 Hz │   sensors → state machine → motors,   │
                                         │   adhesion → telemetry                │
                                         └───────────────────────────────────────┘
```

| State | Wheels | Adhesion |
|---|---|---|
| `ESTOP` (boot state, latched) | stopped | frozen at current power |
| `LINK_LOST` (no message for 500 ms) | stopped | **keeps running** |
| `RUNNING` | follow joystick (max `MAX_MOTOR_POWER_PCT`) | follows slider |

Message format: [docs/protocol.md](docs/protocol.md).

---

## Setup (once)

1. Install [git](https://git-scm.com/) (or [GitHub Desktop](https://desktop.github.com/)),
   [VS Code](https://code.visualstudio.com/), and [Node.js 22 LTS](https://nodejs.org/).
2. In VS Code, install the **PlatformIO IDE** extension.
3. Clone the repo (see CONTRIBUTING.md).
4. Install the web dependencies:
   ```bash
   cd web
   npm ci
   ```
5. Open the `firmware/` folder in VS Code (**File → Open Folder → firmware**). PlatformIO downloads the ESP32
   tools and libraries on the first build (takes a few minutes).

> Arduino IDE is **not** supported: the project needs PlatformIO for the libraries, the LittleFS upload, and CI.

## Build and upload to the robot

The robot needs **two** uploads: the **web UI** (filesystem image) and the **firmware**. Do them in this order:

| # | Step | Command (terminal) | PlatformIO sidebar |
|---|---|---|---|
| 1 | Build the web UI into `firmware/data` | `node scripts/build-web.mjs` (from repo root) | – |
| 2 | Upload the web UI | `cd firmware` then `pio run -t uploadfs` | esp32dev → Platform → **Upload Filesystem Image** |
| 3 | Upload the firmware | `pio run -t upload` | esp32dev → General → **Upload** |
| 4 | Watch the logs | `pio device monitor` | **Monitor** |

> ⚠️ **Most common mistake: forgetting step 2.** Then you get "Not found" in the browser, or the old UI.
> The UI shows **"UI x.y.z · Robot x.y.z"** in the top bar. If it says *version mismatch*, you forgot step 2 or 3.
> Close the Serial Monitor before uploading (it blocks the USB port).

Changed only web code → steps 1–2. Changed only firmware → step 3. Not sure → do all.

## Use it

1. Power the robot. On your phone/laptop, join WiFi **WallBot** (password: `WIFI_AP_PASSWORD` in `config.h`).
2. Open **http://192.168.4.1**.
3. The robot starts in **E-STOP**. Press **Reset E-STOP** to arm it. Then drive with the joystick and set adhesion.

Optional station mode (robot joins an existing WiFi, reachable at **http://wallbot.local**): copy
`firmware/include/secrets.example.h` to `secrets.h`, fill it in, and set `WIFI_USE_STATION = true` in `config.h`.
If it can't connect within 10 s, it falls back to the WallBot access point.

## Working on the web UI without re-flashing

1. Connect your laptop to the robot's WiFi (**WallBot**).
2. In `web/`, copy `.env.example` to `.env.local` (it contains `VITE_ROBOT_WS_URL=ws://192.168.4.1/ws`).
3. `npm run dev`, then open the address it prints (e.g. http://localhost:5173). Changes show up instantly and the
   page talks to the real robot. Only upload to the robot (steps 1–2 above) when you're done.

## Tests and CI

- PC unit tests for the state machine and protocol: `cd firmware && pio test -e native` (see [firmware/test/README.md](firmware/test/README.md)).
- Every pull request is checked automatically by GitHub Actions: web build, build-web script, firmware build,
  filesystem image, and PC tests. If the check is red ❌, the PR can't be merged. Click **Details** to see why.
