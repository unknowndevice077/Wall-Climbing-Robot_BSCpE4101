# Simulation

Physics sim of the thrust-vectoring climber (design: [docs/BUILD.md](../docs/BUILD.md)) in [MuJoCo](https://mujoco.readthedocs.io).
The wheels roll freely. Two props in tilting hoops press the robot to the wall and push it up.
Meshes and masses come from the CAD (`design/mass_properties.json`), so the sim always weighs what the design weighs.

```bash
pip install mujoco
python sim/climb.py                          # live 3D viewer (drag to orbit)
python sim/climb.py --video                  # ideal run -> sim/climb.mp4 (needs ffmpeg)
python sim/climb.py --video --real           # real-world limits -> sim/climb_real.mp4
python sim/climb.py --check --real           # pass/fail only, no video
python sim/climb.py --real --thrust-gf 780   # use YOUR measured thrust per motor (grams on the scale)
python sim/climb.py --min-thrust             # smallest thrust per motor that still climbs (real-world)
```

| File | What |
|---|---|
| `wall_climber.xml` | Robot + floor + 2.5 m wall: joints, hoop servos, prop thrust |
| `climb.py` | Loads the CAD masses, runs the controller: drive -> tip onto the wall -> climb -> hold at 1.75 m |
| `meshes/*.stl` | Made by `design/blender/build_robot.py` (don't edit by hand) |
| `climb.mp4`, `climb_real.mp4` | Recorded runs |
| `webots/` | Same robot and controller in [Webots](https://cyberbotics.com): open `webots/worlds/wall_climber.wbt` ([README](webots/README.md)) |
| `wokwi/` | ESP32 prototype sketch + [Wokwi](https://wokwi.com) circuit. Reference only, not the team firmware |

## How the controller works

Each prop gets a wanted force in the world frame (X = toward the wall, Z = up). The IMU pitch turns it into a hoop
angle and a thrust: `phi = atan2(Fx*cos p + Fz*sin p, -Fx*sin p + Fz*cos p)`.

| Phase | Front prop | Rear prop |
|---|---|---|
| Drive | forward | forward |
| Transition (front wheels touch the wall) | almost all up (lifts the nose) | forward + a bit up |
| Wall | half the weight up + 4.2 N into the wall | half the weight up + 2.6 N into the wall |

The top prop pushes harder into the wall because gravity tries to peel the top wheels off.

## `--real` mode

The controller doesn't know about any of these:
- 10% heavier than the CAD
- battery sag (-11% thrust)
- μ 0.6 grip
- MG90S speed limit and servo range (front hoop -4...140°, rear -40...140°)
- 80 ms motor lag
- IMU bias and noise
- a 1.5 N pull off the wall at 6 s

With the CAD weight (1,043 g) it climbs and holds. `--min-thrust` gives 721 gf per motor as the minimum,
so the bench thrust test must show >= 750 g per motor.

## Wokwi prototype (`wokwi/`)

A single-file Arduino sketch with the same control logic, serial-controlled for Wokwi:
1. Make a new ESP32 project.
2. Paste in `sketch.ino`, `diagram.json` and `libraries.txt`.
3. Press play and type `h` in the serial monitor.
4. Click the MPU6050 to tilt it.

It compiles for the ESP32 (Arduino core 3.x + ESP32Servo), so it does not follow AGENTS.md (core 2.0.17, `ledcSetup`, no new libraries).
Porting it into `firmware/` needs the lead's decision on the locomotion/adhesion interfaces first (docs/SETUP.md §7).
