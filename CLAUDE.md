@AGENTS.md

# Robot design notes (read this too)

AGENTS.md covers the firmware/web rules. This part is about the robot itself, the 3D model and the sims.

## What the robot is

A thrust-vectoring wall climber (based on VertiGo). 4 big printed wheels that are NOT driven, just roll.
2 props sit in hoops that a servo tilts. Tilting the hoop changes where the thrust points:
- forward = drive on the floor
- mostly up = lift the nose onto the wall
- into the wall + up = stick and climb

So the props do both jobs (sticking and moving). There are no drive motors.

Main numbers: 1,039 g total, needs >= 721 gf per motor to climb (sim), test pass mark is 750 g per motor,
robot must stay <= 1,050 g. Full specs in docs/SPECIFICATIONS.md.

## Where things are

| Path | What |
|---|---|
| `docs/SPECIFICATIONS.md` | specs, weight of every part, parts list + prices, pins |
| `docs/BUILD.md` | build guide: dimensions, printing, wiring, build order, tests |
| `docs/SETUP.md` | checklist from ordering parts to the first climb |
| `design/blender/build_robot.py` | the 3D model. Everything in `design/` and `sim/meshes/` is generated from it |
| `design/print/*.stl` | printable parts (mm) |
| `design/mass_properties.json`, `design/PARTS_REPORT.md` | generated weights, don't edit by hand |
| `sim/wall_climber.xml`, `sim/climb.py` | MuJoCo sim (main one) |
| `sim/webots/` | same sim in Webots |
| `sim/wokwi/sketch.ino` | ESP32 prototype for Wokwi. Reference only, uses core 3.x + ESP32Servo so it breaks AGENTS.md rules on purpose |

## Commands

```bash
blender -b --factory-startup -P design/blender/build_robot.py   # rebuild model, must print CLEARANCE OK
python sim/climb.py --check --real                              # must print RESULT PASS
python sim/climb.py --min-thrust                                # min thrust per motor
python sim/climb.py --video --real                              # writes sim/climb_real.mp4
```

Webots headless: `CLIMB_CHECK=16 webots --batch --mode=fast --no-rendering --minimize --stdout sim/webots/worlds/wall_climber.wbt`

## Rules for changing the design

- Change dimensions in the KEY DIMENSIONS block of `build_robot.py`, then the same numbers in `sim/wall_climber.xml`
  and `sim/webots/worlds/wall_climber.wbt`. Rebuild, then rerun the sim check and `--min-thrust`.
- Walls/infill per printed part are in `PRINTED` (build_robot.py). Change them there, not just in the slicer,
  so the weight numbers stay right. Current: wheel 2 walls 20%, bracket 3/40%, gear solid, motor mount + clips 3/50%,
  tray 2/15%, bumper 2/20%.
- Bought-part weights are in `HW_CHASSIS` / `HW_HOOP` / `HW_WHEEL`. Use weighed numbers, not guesses.
- If the clearance check fails, fix the geometry. Don't loosen the check.
- Update the numbers in the docs if weight or min thrust changes (SPECIFICATIONS, BUILD, sim/README).

## Things that will bite you

- Front hoop can't go below -4 deg or it hits the battery. Reversing uses the rear hoop only.
- Hoop flat = 40 deg on the servo (servo deg = hoop deg + 40), not 90.
- Cutting thrust on the wall means the robot falls. Link loss should mean "hold position", not "stop props".
- `locomotion.h` (left/right wheel speed) and `adhesion.h` (one power %) don't fit this robot.
  Porting the Wokwi logic into `firmware/` needs the lead to decide new interfaces first (docs/SETUP.md step 7).
  Don't change those headers on your own.
- Webots: the built-in `Propeller` node gave almost no thrust here, so the controller applies the thrust as a force
  on each hoop. Giving the prop solid its own Physics made the hoop servo crawl, so it has none. Contact bounce must be 0.
- MuJoCo: after changing masses in code call `mj_setConst`, or the robot settles wrong.

## Writing style for this repo

Short and plain, like the rest of the docs. Units in names (`pitchDeg`, `thrustGf`). Short comments only where
something is tricky. Commit messages start with the area: `sim: ...`, `design: ...`, `docs: ...`.
