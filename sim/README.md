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
python sim/climb.py --walls                  # tries ramps, overhangs, slippery walls, bumps (real-world)
python sim/climb.py --video --real --wall-angle 75 --mu 0.3 --bumps 15   # one specific wall
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

Each prop gets a wanted force, the IMU pitch turns it into a hoop angle and a thrust.
On the floor and while tipping up it thinks in world directions (toward the wall, up). Once on the wall it works in
its own frame: push along the face to cancel the weight, plus a light push into the face. It doesn't need to know
the wall angle: the IMU says which way gravity pulls.

| Phase | Front prop | Rear prop |
|---|---|---|
| Drive | forward | forward |
| Transition (front wheels touch the wall) | almost all up (lifts the nose) | forward + a bit up |
| Wall | half the weight along the face + 1.0 N into the wall | half the weight along the face + 2.0 N into the wall |

The props sit 150 mm off the wall and the CG only 109 mm, so the thrust tips the top in and tries to lift the
bottom wheels. That's why the rear pushes harder. A light press also saves thrust and lets the wheels roll over
bumps (4.2 / 2.6 N, the old values, jammed on a 10 mm ridge).

Tip-up is done when the nose is near 90 deg, or when the pitch stops changing for 0.3 s (ramps).

## `--real` mode

The controller doesn't know about any of these:
- 10% heavier than the CAD
- battery sag (-11% thrust)
- μ 0.6 grip on the wall
- MG90S speed limit and servo range (front hoop -4...140°, rear -40...140°)
- 80 ms motor lag
- IMU bias and noise
- a 1.5 N pull off the wall at 6 s

With the CAD weight (1,043 g) it climbs and holds. `--min-thrust` gives 721 gf per motor as the minimum,
so the bench thrust test must show >= 750 g per motor.

## Which walls it climbs (`--walls`, all with `--real`, 755 gf)

| Wall | Result |
|---|---|
| Ramps and walls 30-90 deg | climbs |
| Overhangs (95 deg and up) | fails: the front wheels wedge under the face when tipping up, even with 1,100 gf motors |
| Grip μ 0.1 to 0.9 (glass, dusty paint, plywood, whiteboard) | climbs: the props carry the weight, the wheels just roll |
| Ridges across the wall up to 20 mm (tile edges, trim, cables) | climbs |
| Ridges 25 mm and up | stuck under the ridge |

The wall has to be flat-ish and solid enough not to blow around. Props don't care what it's made of.

## Wokwi prototype (`wokwi/`)

A single-file Arduino sketch with the same control logic, serial-controlled for Wokwi:
1. Make a new ESP32 project.
2. Paste in `sketch.ino`, `diagram.json` and `libraries.txt`.
3. Press play and type `h` in the serial monitor.
4. Click the MPU6050 to tilt it.

It compiles for the ESP32 (Arduino core 3.x + ESP32Servo), so it does not follow AGENTS.md (core 2.0.17, `ledcSetup`, no new libraries).
Porting it into `firmware/` needs the lead's decision on the locomotion/adhesion interfaces first (docs/SETUP.md §7).
