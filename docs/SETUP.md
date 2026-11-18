# Setup checklist: from zero to the first wall climb

Work top to bottom. Each step says what "done" looks like. Details live in [BUILD.md](BUILD.md),
the code setup in the root [README.md](../README.md), and the rules in [SAFETY.md](../SAFETY.md).

## 0. Decide first (lead)

- [ ] Approve the design: open a *Hardware change* issue with BUILD.md §2 (parts) and §7 (pins), and log it in `docs/decisions.md`.
- [ ] Decide the firmware interfaces. This robot has **no driven wheels**: the props both hold it and move it.
      `locomotion.h` (left/right wheel motors) and `adhesion.h` (one power output) don't fit as they are. See "Firmware" below.
- [ ] Decide who pays and orders. ₱5,000 covers one robot (BUILD.md §2).

## 1. Order (week 1)

- [ ] Order everything in BUILD.md §2. Electronics from one seller if possible (fewer shipping fees).
- [ ] Buy 1–2 spare props and 1 spare MG90S if the budget allows: those break first.
- [ ] When parts arrive: **weigh each one** and write the grams in `HW_*` in `design/blender/build_robot.py`.

## 2. Software on the laptops

| Who | Install | Check |
|---|---|---|
| Everyone | git or GitHub Desktop, VS Code | `git clone` works |
| Firmware people | VS Code **PlatformIO** extension, Node.js 22 (root README) | `cd firmware && pio run` builds |
| Sim people | Python 3.10+, `pip install mujoco`, ffmpeg (for videos) | `python sim/climb.py --check` prints `RESULT PASS` |
| CAD people (optional) | Blender 4.2+ | `blender -b --factory-startup -P design/blender/build_robot.py` prints `CLEARANCE OK` |
| Printing | Cura, PrusaSlicer or OrcaSlicer, set up for your printer | test cube prints at the right size |

## 3. Print (week 1–2, ~19 h of printer time)

- [ ] Print **one bracket + one gear** and check the fit (BUILD.md §4). Adjust and reprint if needed.
- [ ] Print the rest: 4 wheels (brim!), 3 more brackets (2 mirrored), 3 gears, 2 motor mounts, 4 hoop clips, tray, bumper arm.
- [ ] Weigh the printed parts. The total should be ~330 g. More than 380 g means the slicer used more walls/infill than BUILD.md says.

## 4. Build (week 2)

Follow BUILD.md §8 in order. Done when:
- [ ] All 4 wheels spin freely, with no wobble
- [ ] Both hoops swing all the way through their range by hand without touching anything
- [ ] Buck output reads 5.0 V **before** anything is connected to it
- [ ] Multimeter: no short between battery + and −

## 5. Bench calibration (props OFF)

| Step | How | Done when |
|---|---|---|
| ESC calibration | Throttle signal at max → power on → beeps → throttle at min → beeps | Both motors start at the same throttle |
| Motor direction | Spin each motor briefly | Front and rear spin opposite ways, matching CW/CCW props |
| Servo zero + trim | Command hoop angle 0° (= servo 40°), set `trimF`/`trimR` until both hoops are flat | Hoops flat |
| Servo direction | Command hoop angle +10° | Both hoops tip their prop **forward** (change `flip` if not; the gears reverse it) |
| Front hoop limit | Command the front hoop to −4° | It clears the battery by a few mm. Never lower |
| IMU | Robot flat, then nose-up against a box | Pitch reads 0 ±2 and 90 ±2 |
| Battery reading | Compare with a multimeter | Within 0.1 V |

## 6. Thrust test (the go / no-go)

1. Clamp a motor + prop to a stick so the prop pushes **down** onto a kitchen scale, at least 15 cm above the scale.
2. Fully charged battery. Eye protection. Nobody in line with the prop.
3. Full throttle for 3 seconds. Read the scale.

| Result per motor | Meaning |
|---|---|
| ≥ 800 g | Good margin |
| 750–800 g | OK, but keep the robot ≤ 1,050 g |
| 721–750 g | Climbs only in perfect conditions. Cut weight |
| < 721 g | **Will not climb.** Check the battery and prop direction, or get stronger motors |

Then run the sim with your number: `python sim/climb.py --video --real --thrust-gf <your grams>`.

## 7. Firmware

The prototype logic (`sim/wokwi/sketch.ino`, tested in [Wokwi](https://wokwi.com)) has to be ported into `firmware/`
(PlatformIO, core 2.0.17, `ledcSetup`, no ESP32Servo). It needs the interface decision from step 0. A suggestion:

| Module | Does | Replaces |
|---|---|---|
| `adhesion` | Both ESCs: thrust per prop (N) | `adhesionSetPower(pct)` |
| `locomotion` | Both hoop pitch servos + roll servos | `setMotorSpeed(left, right)` |
| `main` control task | The force → hoop angle maths (sim/README.md) | — |
| `sensors` | MPU6050 pitch + battery voltage + bumper | already planned |

**Safety change to discuss:** on this robot, cutting thrust on the wall = it falls. The link-loss rule
"wheels stop, adhesion keeps running" maps to "keep holding, no climbing". The physical kill switch cuts everything,
so the mat under the wall is mandatory.

## 8. First runs

- [ ] Floor only, low throttle: drive forward and back, check the link-loss stop.
- [ ] Hold the robot against the wall by hand at 30 cm, Climb mode: it should press itself on and hold.
- [ ] Full climb: mat under the wall, one person on the kill switch, the SAFETY.md checklist done.
