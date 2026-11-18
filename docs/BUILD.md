# Build guide: thrust-vectoring wall climber

Design from *Wall Climbing Design.docx*: 4 big star-spoke wheels, 2 propellers in tilting hoops, a light frame.
The wheels roll freely. The props do all the work: they push the robot into the wall and hold it up.
Everything here was checked in the MuJoCo sim ([sim/](../sim/README.md)), including a run with real-world limits (see the end).

> Pins, parts and frame changes below are a **proposal**. In the team repo they go through a
> *Hardware change* issue and `docs/decisions.md` before anyone edits `config.h`.

---

## 1. Parts (one robot, ₱5,000 = ₱200 × 25)

Typical Shopee/Lazada prices. Check them before ordering. Soldering iron, multimeter, drill and hot glue come from the lab.

| # | Part | Pick this | Qty | ₱ |
|---|---|---|---|---|
| 1 | Microcontroller | ESP32 DevKit V1 (30-pin, CP2102 or CH340) | 1 | 250 |
| 2 | IMU | MPU6050 (GY-521) | 1 | 120 |
| 3 | Front bumper | Micro limit switch with lever | 1 | 25 |
| 4 | Buck converter | XL4015 5 A step-down (servos + ESP32) | 1 | 120 |
| 5 | Battery | 3S 11.1 V 1500 mAh 25C LiPo, XT60 | 1 | 750 |
| 6 | Charger | B3 2S/3S balance charger | 1 | 220 |
| 7 | LiPo alarm | 1–8S voltage checker / buzzer | 1 | 60 |
| 8 | Power wiring | XT60 pairs ×3, 14 AWG silicone wire 1 m, toggle switch | 1 | 180 |
| 9 | Small parts | Dupont wires, perfboard, 100k + 27k resistors | 1 | 80 |
| 10 | Brushless motor | A2212 1400KV (2212 size) with prop adapter | 2 | 500 |
| 11 | ESC | 30 A SimonK / BLHeli | 2 | 520 |
| 12 | Propellers | **9045** CW + CCW pair (fits the 10" hoop, more thrust than 8045) | 2 | 140 |
| 13 | Servos | MG90S metal gear (2 hoop pitch + 2 arm roll) | 4 | 440 |
| 14 | Prop hoops | 10" wooden embroidery hoop (inner ring), or carbon/PVC ring | 2 | 160 |
| 15 | Wheels | 3D-printed PLA from `sim/meshes/wheel.stl` (~250 g filament) or 5 mm PVC foam board | 4 | 250 |
| 16 | Tires | Bicycle inner tube cut into 15 mm strips | 1 | 50 |
| 17 | Frame | Aluminium flat bar 1" × 1/8" (1 m) + 3 mm plywood | 1 | 250 |
| 18 | Bearings + axles | 608ZZ ×8, M8 bolts ×4 with lock nuts, M3 bolts for hoop pivots | 1 | 200 |
| 19 | Fasteners | M3 screw / nut / standoff kit | 1 | 150 |
| 20 | Consumables | Zip ties, foam tape, velcro strap, glue sticks | 1 | 150 |
| | **Subtotal** | | | **4,615** |
| | Buffer | spare props, 1 spare servo, shipping | | 385 |
| | **Total** | | | **5,000** |

No RC radio: the ESP32 makes its own Wi-Fi and the phone is the controller (the team repo's web UI).

**Weight target: ≤ 950 g.** Weigh every part as it arrives and keep a running total.

| Group | Grams |
|---|---|
| 2 motors + props | 130 |
| 2 ESCs | 50 |
| 4 servos | 55 |
| Battery | 130 |
| ESP32 + IMU + buck + switch | 35 |
| 2 hoops + inner struts | 120 |
| 4 wheels + tires | 200 |
| Frame (rails, beam, towers, tray) | 150 |
| Wires, screws, ties | 80 |
| **Total** | **≈ 950** |

## 2. Frame and dimensions

Units: mm. X forward, Y left, Z up. Origin = centre of the frame at axle height.

| Item | Size / position |
|---|---|
| Wheelbase × track | 320 × 350 (wheel centres at X ±160, Y ±175) |
| Wheels | Ø220, 14 thick, 608 bearing pressed in the hub, M8 axle |
| Side rails (carbon or alu flat bar) | 360 long, at Y ±155, Z −12 |
| Hoop towers (plywood) | 30 × 70, at X ±135, Y ±155, carry the hoop pivots and the pitch servos |
| Hoop pivot | X ±135, Z +30, axis along Y |
| Hoops | 10" (Ø254 outer), prop hub in the centre on two inner struts |
| Cross beam | X 0, Z −45, full width between the rails |
| Battery / electronics tray | 40 × 90, hangs under the cross beam, floor at Z −88 (20 mm ground clearance) |

**Keep-out rule (most important):** each hoop sweeps a ball of radius 130 mm around its pivot when it tilts.
Nothing may be mounted inside that ball. That's why there is **no centre spine** and nothing under the hoops.
`design/blender/build_robot.py` checks this every time you rebuild (it prints `CLEARANCE OK`).
If you change the frame, run it again.

## 3. Where the electronics go

| Part | Place | Why |
|---|---|---|
| Battery | In the tray under the cross beam, lying sideways, velcro strap | Lowest and closest to the wall when climbing: less thrust needed to hold on |
| ESP32 + MPU6050 | On a small plywood plate on the tray side walls, IMU flat with X pointing forward | Centre of the robot = cleanest pitch reading. USB port facing sideways for reprogramming |
| Buck converter | On the left rail, between the towers | Outside both hoop balls, short wire to the servos |
| ESCs | On the right rail, one near each hoop | Short motor wires; the hoop pivot passes the 3 motor wires (leave a loop for ±90° of tilt) |
| Pitch servos | On the left towers, horn locked to the hoop pivot | Turns the hoop |
| Roll servos | On the hoop, driving the motor arm | Steering |
| Front bumper switch | Under the front of the left rail, lever sticking 5 mm past the wheel line | Tells the firmware "front wheels hit the wall" |
| Power switch | On the right rail at the back | Easy to reach while the robot is on the wall |

## 4. Wiring (pin proposal)

```
 3S LiPo ──XT60── switch ──┬── ESC front ── motor front
                           ├── ESC rear  ── motor rear
                           └── XL4015 IN ── OUT 5.0 V ──┬── 4 servos (+)
                                                        └── ESP32 VIN
 ALL GROUNDS TOGETHER. Cut or tape back the red wire of both ESC signal plugs.
```

| Signal | ESP32 GPIO | Note |
|---|---|---|
| ESC front | 25 | 50 Hz, 1000–2000 µs |
| ESC rear | 26 | |
| Pitch servo front / rear | 18 / 32 | 50 Hz, 500–2500 µs, `ledcSetup` (core 2.0.17) |
| Roll servo front / rear | 19 / 33 | |
| MPU6050 SDA / SCL | 21 / 22 | address 0x68 |
| Front bumper | 27 | to GND, `INPUT_PULLUP` |
| Battery voltage | 34 | 100k top / 27k bottom → 12.6 V reads as 2.68 V |
| Status LED | 2 | on-board LED |

## 5. Build order

1. Print or cut the 4 wheels. Press in the bearings, stretch on the inner-tube tires.
2. Cut the rails, towers, cross beam and tray. Bolt the H-frame together, then fit the wheels.
3. Fit the hoop pivots (M3 bolt through a 608 or brass tube in the tower). The hoop must swing freely all the way around.
4. Mount the motors on the hoop hubs. **No props yet.**
5. Set the buck to **5.0 V with a multimeter before connecting anything.**
6. Wire everything (section 4). Check for shorts with the multimeter before the first power-up.
7. Centre the servos (90°) before fixing the horns. Hoop flat = 90° on the servo.
8. Calibrate both ESCs (full throttle signal at power-up, then zero) with **props off**.

## 6. Tests before the wall

| Test | How | Pass |
|---|---|---|
| Thrust test | Motor + prop on a stick, pushing down on a kitchen scale. Full throttle on a charged battery | **≥ 700 g per motor**. If less, the robot won't climb |
| Weight | Kitchen scale, everything on | ≤ 950 g |
| Hoop sweep | Command −40° → 140° slowly | Hoop and prop touch nothing |
| IMU | Tilt the robot by hand | Pitch reads 0 flat, 90 nose-up |
| Floor drive | Props on, low throttle, on a floor | Drives straight, stops when the link drops |
| Wall test | Follow [SAFETY.md](../SAFETY.md): mat under the wall, one person on the power switch | Climbs and holds |

**Rule of thumb:** thrust needed to hang on the wall ≈ weight × √(1 + (2h/L)²).
h = distance from the wall to the centre of mass (~0.10 m), L = wheelbase (0.32 m). That's about 1.2 × the weight.

## 7. Simulation results

`python sim/climb.py --video` (ideal) and `python sim/climb.py --video --real`. The real run has a 10% heavier robot,
battery sag (7.4 → 6.6 N per prop), worse grip (μ 0.6), servo speed and angle limits, IMU noise and bias, motor spin-up lag,
and someone pulling it off the wall at 6 s.

| | Ideal | Real-world |
|---|---|---|
| On the wall after | 1.7 s | 2.5 s |
| Reaches 1.75 m | yes | yes, survives the pull |
| Top prop while holding | 6.3 N of 7.4 (85 %) | 6.6 N of 6.6 (**100 %**) |
| Hoop angles used | 0 … 135° | 0 … 132° (servo range −40 … 140°) |

The real-world run passes with **zero thrust margin**. That's why the list uses 9045 props instead of 8045, and why the 950 g limit matters.
If the thrust test gives under 700 g per motor, either cut weight or switch to 2216-size motors (≈ ₱400 more each, over budget).

Found and fixed in the sim: (1) the nose-up transition must put almost all front thrust **upward**; pushing hard into the wall pitches the nose back down;
(2) a centre spine sits inside the hoop sweep, so the frame became an H-frame.
