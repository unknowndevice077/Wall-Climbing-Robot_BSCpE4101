# Plan and checklist

The whole project from deciding the design to the first climb, in order.
Tick the boxes as you go. Other docs:
- [SPECIFICATIONS.md](SPECIFICATIONS.md): specs, weights, parts list
- [PRINTING.md](PRINTING.md): 3D printing
- [WIRING.md](WIRING.md): wiring and placement
- [CODE.md](CODE.md): code and control
- [SAFETY.md](../SAFETY.md): rules for wall tests

## Goal

A robot that drives up to a wall, tips itself onto it and climbs to 1.75 m, then holds there.
Two props in servo-tilted hoops push it into the wall and up. The 4 wheels just roll.
In the sim it climbs any material and any grip, ramps from 30° to vertical, and ridges up to 20 mm. No overhangs.

## Team

| Role | Owns | Main jobs |
|---|---|---|
| Lead | `firmware/src/main/`, `config.h`, decisions | approve the design and pins, port the control logic, run wall tests |
| Hoops (locomotion) | `firmware/src/locomotion/` | hoop pitch + roll servos, trims, limits, building the hoops |
| Thrust (adhesion) | `firmware/src/adhesion/` | ESCs, motors, props, thrust test |
| Sensors | `firmware/src/sensors/` | MPU6050, battery voltage, bumper, wiring |
| Control/UI | `firmware/src/comms/`, `web/` | phone controller, Climb mode, telemetry |

Printing and the frame build are shared: whoever has a printer prints.

## Budget

₱5,155 for one robot, or ₱4,505 if the school gives the filament. Full list in [SPECIFICATIONS.md](SPECIFICATIONS.md#parts-list-one-robot).
If it's over: buy one prop pair (-₱70) and borrow a charger (-₱220).
Add ~₱100 for motor-lead and servo extensions ([WIRING.md](WIRING.md#wires-across-the-hoop-pivots)).

## Timeline

| Week | What |
|---|---|
| 1 | decide, order parts, set up laptops, print the test pair |
| 2 | print everything, build the frame and wheels |
| 3 | wire it, bench calibration, thrust test, start porting the code |
| 4 | finish the firmware, floor tests |
| 5 | wall tests, tuning, demo |

## Risks

| Risk | What to do |
|---|---|
| Motors give less than 750 g thrust each | test one motor the day it arrives. Under 721 g it won't climb: get stronger motors early |
| Robot comes out heavier than 1,050 g | weigh parts as they arrive, cut wire length, lighter infill on the tray |
| Prop or servo breaks in a fall | buy spares, mat under the wall, kill switch person every test |
| Firmware interfaces not decided | lead decides in week 1, or nobody can start porting |
| Battery runs flat mid-climb | about 3-4 min per charge. Charge between every few runs |

## Checklist

### 0. Decide (lead, week 1)

- [ ] Approve the design: open a Hardware change issue with the parts list and the pins ([WIRING.md](WIRING.md#pins)), log it in `docs/decisions.md`
- [ ] Decide the new firmware interfaces for thrust and hoops ([CODE.md](CODE.md#porting-the-controller-into-firmware))
- [ ] Decide who pays and who orders

### 1. Order (week 1)

- [ ] Order everything in the parts list. Electronics from one seller if you can
- [ ] Add 1-2 spare props, 1 spare MG90S, 2 m of 18 AWG wire, 2 servo extensions
- [ ] When parts arrive, weigh each one and write the grams in `HW_*` in `design/blender/build_robot.py`

### 2. Laptops (week 1)

| Who | Install | Check |
|---|---|---|
| Everyone | git or GitHub Desktop, VS Code | `git clone` works |
| Firmware | PlatformIO extension, Node.js 22 | `cd firmware && pio run` builds |
| Sim | Python 3.10+, `pip install mujoco`, ffmpeg | `python sim/climb.py --check` prints `RESULT PASS` |
| CAD (optional) | Blender 4.2+ | `blender -b --factory-startup -P design/blender/build_robot.py` prints `CLEARANCE OK` |
| Printing | Cura, PrusaSlicer or OrcaSlicer | a test cube comes out the right size |

- [ ] Everyone's checks pass

### 3. Print (weeks 1-2, ~19 h)

- [ ] Print the test bracket + gear and check the fit ([PRINTING.md](PRINTING.md#test-fit-plate-0))
- [ ] Print the rest: 4 wheels (with brim), 3 brackets (2 mirrored), 3 gears, 2 motor mounts, 4 hoop clips, tray, bumper arm
- [ ] Drill the holes to size, press the wheel bearings in
- [ ] Printed parts weigh about 330 g (over 380 g = wrong slicer settings)

### 4. Build the frame (week 2)

- [ ] Cut the tube: 2 x 380 mm rails, 1 x 284 mm beam. Join the beam to the rails (M3 through both, or an L-bracket)
- [ ] Stretch the tire strips into the wheel rims, a drop of CA at the joint
- [ ] Bolt the brackets to the rails: plain ones on the right, mirrored on the left. Fit the wheels on M4 bolts with a washer
- [ ] Drill each hoop: 2 x Ø3 holes opposite each other for the pivot pins. Slide on the 2 hoop clips 90° from them
- [ ] Push the carbon roll axle through both clips with the motor mount in the middle
- [ ] Mount the motors on the mounts. No props yet
- [ ] Fit the 693ZZ in the brackets, pivot pins through, 24T gears on the left pins and on the pitch-servo horns
- [ ] Set both pitch servos to 40° before tightening the gears (servo 40° = hoop flat)
- [ ] Tray: battery on top, ESP32 + MPU6050 under it. Zip-tie the tray to the beam
- [ ] All 4 wheels spin freely with no wobble
- [ ] Both hoops swing through their whole range by hand without touching anything

### 5. Wire it (week 3)

- [ ] Follow [WIRING.md](WIRING.md), connection by connection
- [ ] Buck output set to 5.0 V before anything is connected to it
- [ ] ESC signal red wires cut
- [ ] Multimeter: no short between battery + and -, or between 5 V and GND
- [ ] Slack loops at both hoop pivots, hoops still swing freely

### 6. Bench calibration (props OFF)

| Step | How | Done when |
|---|---|---|
| ESC calibration | throttle at max -> power on -> beeps -> throttle at min -> beeps | both motors start at the same throttle |
| Motor direction | spin each motor briefly | front and rear spin opposite ways, matching the CW/CCW props |
| Servo zero | command hoop 0° (servo 40°), adjust `trimF`/`trimR` | both hoops flat |
| Servo direction | command hoop +10° | both hoops tip their prop forward (change `flip` if not) |
| Front hoop limit | command the front hoop to -4° | clears the battery by a few mm |
| IMU | robot flat, then nose-up against a box | pitch reads 0 ±2 and 90 ±2 |
| Battery reading | compare with a multimeter | within 0.1 V |

- [ ] All 7 done

### 7. Thrust test

1. Clamp a motor + prop to a stick so the prop pushes down on a kitchen scale, at least 15 cm above it.
2. Fully charged battery, eye protection, nobody in line with the prop.
3. Full throttle for 3 seconds, read the scale. Do both motors.

| Per motor | Meaning |
|---|---|
| 800 g or more | good margin |
| 750-800 g | OK, keep the robot at 1,050 g or less |
| 721-750 g | climbs only in perfect conditions. Cut weight |
| under 721 g | won't climb. Check the battery and prop direction, or get stronger motors |

- [ ] Both motors >= 750 g
- [ ] Sim rerun with your number: `python sim/climb.py --video --real --thrust-gf <grams>` passes
- [ ] Whole robot weighs <= 1,050 g

### 8. Firmware (weeks 3-4)

- [ ] Pins and constants in `config.h` (after step 0)
- [ ] Thrust module: ESCs arm and set thrust ([CODE.md](CODE.md))
- [ ] Hoop module: pitch + roll servos with limits, trims, flip
- [ ] Sensors: pitch, battery, bumper
- [ ] Control phases + force -> angle maths in `main`
- [ ] Climb mode in the protocol and the web UI
- [ ] Link lost on the wall = hold. On the floor = thrust off
- [ ] `pio run`, `pio test -e native`, `npm run build` all pass and CI is green
- [ ] `MASS` and `TMAX` set from the weighed robot and the thrust test

### 9. Tests before the wall

| Test | How | Pass |
|---|---|---|
| Hoop sweep | command each hoop slowly through its range | touches nothing |
| IMU | tilt the robot by hand | pitch 0 flat, 90 nose-up |
| Floor drive | props on, low throttle | drives straight, stops when the link drops |
| Hand-held hold | hold it against the wall at 30 cm, Climb mode | presses itself on and holds |

- [ ] All 4 pass

### 10. Wall (week 5)

- [ ] SAFETY.md checklist done: mat under the wall, one person on the power switch, nobody under the robot
- [ ] Full climb to 1.75 m and hold
- [ ] Climb, hold 10 s, come back down
- [ ] Try another wall (tile, painted, wood) and a ridge if you have one
- [ ] Record a video for the demo
