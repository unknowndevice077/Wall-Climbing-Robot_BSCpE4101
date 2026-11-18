# Simulation

Physics sim of the thrust-vectoring climber (design: [docs/BUILD.md](../docs/BUILD.md)) in [MuJoCo](https://mujoco.readthedocs.io).
The wheels roll freely. Two props in tilting hoops press the robot to the wall and push it up.

```bash
pip install mujoco
python sim/climb.py                  # live 3D viewer (drag to orbit)
python sim/climb.py --video          # ideal run -> sim/climb.mp4 (needs ffmpeg)
python sim/climb.py --video --real   # real-world limits -> sim/climb_real.mp4
```

| File | What |
|---|---|
| `wall_climber.xml` | Robot + floor + 2.5 m wall: masses, wheel joints, hoop servos, prop thrust (max 7.4 N each) |
| `climb.py` | Controller: drive → tip onto the wall → climb → hold at 1.75 m |
| `meshes/*.stl` | Body parts, made by `design/blender/build_robot.py` (don't edit by hand) |
| `climb.mp4`, `climb_real.mp4` | Recorded runs |
| `wokwi/` | ESP32 prototype sketch + [Wokwi](https://wokwi.com) circuit. **Reference only**, not the team firmware (see below) |

## How the controller works

Each prop gets a wanted force in the world frame (X = toward the wall, Z = up). The IMU pitch turns it into a hoop
angle and a thrust: `phi = atan2(Fx·cos p + Fz·sin p, −Fx·sin p + Fz·cos p)`.

| Phase | Front prop | Rear prop |
|---|---|---|
| Drive | forward | forward |
| Transition (front wheels touch the wall) | almost all **up** (lifts the nose) | forward + a bit up |
| Wall | half the weight up + 4.2 N into the wall | half the weight up + 2.6 N into the wall |

The top prop pushes harder into the wall because gravity tries to peel the top wheels off.

## `--real` mode

10% heavier, battery sag (7.4 → 6.6 N), μ 0.6 wheels, MG90S speed limit, servo range −40…140°, 80 ms motor lag,
IMU bias + noise, and a 1.5 N pull off the wall at 6 s. The controller doesn't know about any of it.
Result: it climbs and holds, but the top prop runs at **100 %** of its thrust. See BUILD.md §7.

## Wokwi prototype (`wokwi/`)

A single-file Arduino sketch with the same control logic, serial-controlled for Wokwi: new ESP32 project →
paste `sketch.ino`, `diagram.json`, `libraries.txt` → play → type `h` in the serial monitor. Click the MPU6050 to tilt it.
It uses Arduino core 3.x + ESP32Servo, so it does **not** follow AGENTS.md (core 2.0.17, `ledcSetup`, no new libraries).
Porting it into `firmware/` needs the lead's decision on the locomotion/adhesion interfaces first.
