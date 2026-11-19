# Code

What code is in this repo, how the robot's control works, and what's left to write.
The rules every coder (and every AI tool) follows are in [AGENTS.md](../AGENTS.md). This page explains; AGENTS.md sets the rules.

## What's where

| Path | What | Status |
|---|---|---|
| `firmware/` | the real robot firmware: ESP32, PlatformIO, Arduino core 2.0.17 | team template. Builds and runs, but its motor/adhesion modules were written for a different robot (see below) |
| `web/` | phone/laptop controller: React + Vite + TypeScript, talks to the robot over a WebSocket at `/ws` | works with the template firmware |
| `scripts/build-web.mjs` | builds `web/` and gzips it into `firmware/data` for the ESP32 | works |
| `sim/climb.py` | MuJoCo physics sim with the climbing controller | works, the reference for the control logic |
| `sim/webots/` | same robot and controller in Webots | works, vertical wall only |
| `sim/wokwi/sketch.ino` | one-file ESP32 prototype of the controller, runs in [Wokwi](https://wokwi.com) | works, reference only (uses core 3.x + ESP32Servo, which the firmware rules don't allow) |
| `design/blender/build_robot.py` | the 3D model. Makes the STLs, sim meshes and weights | works |

## Firmware layout

```
firmware/
  include/          the shared .h files = the contract between team members
    config.h          every pin and tuning constant (pins still TODO(hardware))
    state_machine.h   ESTOP / LINK_LOST / RUNNING, pure C++, unit-tested on the PC
    shared_state.h    the only way the two tasks talk
    protocol.h        WebSocket message format
    locomotion.h, adhesion.h, sensors.h, comms.h
  src/
    main/           setup(), control task, state machine
    comms/          Wi-Fi AP, web server, WebSocket
    locomotion/ adhesion/ sensors/   one module per owner
  test/             PC tests: pio test -e native
```

Two tasks run at the same time:
- **Control task**, core 1, every 10 ms: read sensors -> state machine -> set outputs -> telemetry.
- **Comms task**, core 0: Wi-Fi, web server, WebSocket. Only this task touches networking.

They only share data through `shared_state.h`. No `delay()` anywhere in the control path.

The robot boots in `ESTOP` (latched). The operator presses Reset in the UI to go to `RUNNING`.
No message for 500 ms -> `LINK_LOST`.

## How the robot is controlled

There are no drive motors. Each prop sits in a hoop that a servo tilts, so the controller picks a force for each prop
and the hoop angle points the thrust that way.

### Phases

| Phase | When | Front prop | Rear prop |
|---|---|---|---|
| Drive | Drive mode, on the floor | forward (1.6 N x stick) | same |
| Approach | Climb mode, pitch < 15° and bumper not pressed | forward 1.6 N | forward 1.6 N |
| Transition | pitch 15-80°, nose lifting onto the wall | mostly up (7 N), blending into the wall forces as pitch rises | forward + a bit up |
| Wall: hold / climb / descend | pitch >= 80° | half the weight up + 1.0 N into the wall | half the weight up + 2.0 N into the wall |

On the wall the stick changes the up force by ±12%: push up to climb, centre to hold, pull down to come down.
Steering tilts the two motor arms (roll servos) opposite ways, which yaws the robot.

Why the rear presses harder: the props sit 150 mm off the wall but the centre of mass only 109 mm, so thrust tries to lift
the bottom wheels. A light press (1.0 / 2.0 N) also saves thrust and lets the wheels roll over bumps up to 20 mm.

### From force to servo and ESC

This is `setProp()` in `sketch.ino`. `fx` = toward the wall, `fz` = up, both in N, `p` = IMU pitch.

```
bx  = fx*cos(p) + fz*sin(p)      // turn the world force into the robot's own frame
bz  = -fx*sin(p) + fz*cos(p)
hoop angle = atan2(bx, bz)       // 0 = prop pushes straight up off the chassis, 90 = forward
thrust     = sqrt(bx² + bz²), capped at TMAX
throttle   = sqrt(thrust / TMAX) // thrust goes with rpm², roughly throttle²
ESC pulse  = 1050 + 900 * throttle µs
servo deg  = hoop angle + 40 (+ trim, mirrored if flip)
```

Hoop limits: front -4° to 140° (below -4° it hits the battery), rear -40° to 140°.

### Pitch from the IMU

Complementary filter on the raw MPU6050 (no library):
`pitch = 0.98 * (pitch - gyroY * dt) + 0.02 * atan2(ax, az)`. 0 = flat on the floor, 90 = on a vertical wall.

## Numbers to set from the real robot

| Constant | In the sketch now | Set it to |
|---|---|---|
| `MASS` | 0.95 kg | the weighed robot (design is 1.04 kg) |
| `TMAX` | 6.6 N | thrust test result in N per motor (grams / 102) |
| `trimF`, `trimR` | 0 | servo degrees that make each hoop sit flat |
| `flipF`, `flipR` | false, true | whatever makes +10° tip the prop forward on both hoops |
| pins | see [WIRING.md](WIRING.md) | after the lead approves them, into `config.h` |

Then put the real numbers into the sim too: `python sim/climb.py --check --real --thrust-gf <grams>`.

## Porting the controller into firmware/

The Wokwi sketch works, but the firmware's `locomotion.h` (left/right wheel speed) and `adhesion.h` (one power %)
were made for a robot with drive wheels and suction. They don't fit this one.
Changing them is a shared-interface change, so the lead decides first. A suggestion to start from:

| Module | Owner | Does | Replaces |
|---|---|---|---|
| `adhesion` -> thrust | Adhesion | both ESCs: arm, set thrust per prop in N, report it | `adhesionSetPower(pct)` |
| `locomotion` -> hoops | Locomotion | both pitch servos + both roll servos, with limits, trims and flip | `setMotorSpeed(left, right)` |
| `sensors` | Sensors | MPU6050 pitch, battery voltage, bumper | already planned |
| `main` | Lead | the phase logic and the force -> angle maths above | - |
| `protocol` + `web/` | Control/UI | add Climb mode + the stick meaning climb/hold/descend | needs a protocol version bump |

Rules while porting:
- Use `ledcSetup()` + `ledcAttachPin()` for the ESCs and servos (core 2.0.17). No ESP32Servo.
- Every pin and constant goes in `config.h`. No numbers in the modules.
- Keep `state_machine` free of Arduino code so the PC tests still run.

## Safety in code

- On the wall, cutting thrust = the robot falls. Link lost on the wall means **hold**, not stop.
- On the floor, link lost means thrust off.
- E-STOP stays latched until Reset. The physical power switch is the real kill switch.
- Clamp everything that comes from the UI. Never let a hoop past its limit, even for one loop.

Read [SAFETY.md](../SAFETY.md) before the first wall test.

## Testing

| What | Command | Pass |
|---|---|---|
| Firmware builds | `cd firmware && pio run` | no errors |
| PC unit tests | `cd firmware && pio test -e native` | all pass |
| Web builds | `cd web && npm ci && npm run build` | no errors |
| Control logic in physics | `python sim/climb.py --check --real` | `RESULT PASS` |
| Every wall type | `python sim/climb.py --walls` | ramps 30-90°, μ 0.1-0.9, ridges to 20 mm pass |
| ESP32 logic without hardware | Wokwi: paste the 3 files from `sim/wokwi/`, play, type `h` | phases change as you tilt the MPU6050 |

CI runs the first three on every pull request.
