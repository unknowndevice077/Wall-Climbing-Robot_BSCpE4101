# Wiring and placement

Where every part sits on the robot and how it's all wired.
The pins and the layout are a proposal: the lead still has to approve them (Hardware change issue + `docs/decisions.md`)
before anything goes into `firmware/include/config.h`.

## Axes and frame

Units are mm. X points forward (toward the wall), Y left, Z up.
The origin is the centre between the 4 axles, at axle height (108 mm above the floor).

| Item | Size / position |
|---|---|
| Wheelbase x track | 330 x 350 (wheel centres at X ±165, Y ±175) |
| Wheels | Ø212 printed + inner-tube tire = Ø216. 10 wide, hub 14 wide. 2 x 624ZZ each, M4 axle |
| Rails | 8x8 alu tube, 380 long, at Y ±146, Z -12 |
| Cross beam | 8x8 alu tube, 284 long, at X 0, Z -12 |
| Corner brackets | bolted to the outside of the rails (2 x M3 each). Each holds a wheel axle, a hoop pivot and (left side) a pitch servo |
| Hoop pivots | X ±140, Z +32, axis along Y, M3 pin in a 693ZZ |
| Pitch drive | MG90S on the inner face of each left bracket, 24T gear on its horn -> 24T gear on the hoop pin (1:1) |
| Hoops | 10" embroidery hoop inner ring (Ø254, 8 x 10 section). Hoop clips at both ends of a Ø6 carbon roll axle, 30 mm below the hoop centre |
| Motor | on the motor mount riding the roll axle, prop plane 10 mm above the hoop centre |
| Tray | hangs under the cross beam, floor at Z -48. With the ESP32 under it you get 50 mm ground clearance |

Keep-out: each hoop with its clips, motor and prop sweeps a ball of about 130 mm around its pivot.
Nothing may go inside that ball. `design/blender/build_robot.py` checks it and prints `CLEARANCE OK`.
The front hoop must never tilt back past -4° or it hits the battery.

## Where the electronics go

```
            FRONT (wall side)  ->  +X
   [bumper]
   FL bracket ── front hoop pivot (X +140) ── FR bracket
      |  pitch servo F                             |
      |                                [ESC F]  X +30
   left rail   [buck]   ===== cross beam =====   right rail
      |                                [ESC R]  X -30
      |  pitch servo R                             |
   RL bracket ── rear hoop pivot (X -140) ─── RR bracket
                                      [power switch]
   tray under the beam: battery on top, ESP32 + MPU6050 under it
```

| Part | Where | How it's held |
|---|---|---|
| Battery | on the tray floor, long side along Y | velcro strap through the tray's side slots |
| ESP32 + MPU6050 | under the tray floor. MPU6050 flat, its X arrow pointing forward. USB port faces sideways | foam tape |
| ESC front / rear | on top of the right rail at X +30 / -30 | zip ties |
| Buck converter | on top of the left rail, centred | zip ties or foam tape |
| Pitch servos | inner face of the left front and left rear brackets | 2 x M2 screws each |
| Roll servos | on the outer hoop clip of each hoop, short M2 pushrod to the motor mount | M2 screws |
| Bumper switch | end of the bumper arm on the front-left bracket, lever 3 mm past the front tires | M2 screws |
| Power switch | rear end of the right rail | zip ties |

Keep the heavy stuff (battery, ESCs) low and centred: the climb maths assumes the centre of mass is 109 mm off the surface.

## Power

```
 3S LiPo ──XT60── switch ──┬── ESC front ── motor front
  11.1 V                   ├── ESC rear  ── motor rear
                           └── XL4015 IN ── OUT 5.0 V ──┬── 4 servos (+)
                                                        └── ESP32 VIN
 All grounds together.
 Cut (or tape back) the red wire on both ESC signal plugs.
```

- Battery to switch to ESCs: 14 AWG silicone wire, XT60 plugs. This side carries up to ~20 A.
- Buck output to servos and ESP32: 20-22 AWG is plenty.
- The red wire on an ESC signal plug is its own 5 V output. With two ESCs plus the buck all on one 5 V line they fight, so cut both.
- Servos pull big spikes when they move. If the ESP32 resets when a hoop swings, put a 470-1000 µF capacitor across the buck output.

## Pins

| Signal | ESP32 GPIO | Notes |
|---|---|---|
| ESC front / rear | 25 / 26 | 50 Hz, 1000-2000 µs |
| Pitch servo front / rear | 18 / 32 | 50 Hz, 500-2500 µs. Front hoop limit -4° |
| Roll servo front / rear | 19 / 33 | 50 Hz, 500-2500 µs |
| MPU6050 SDA / SCL | 21 / 22 | address 0x68 |
| Front bumper | 27 | switch to GND, `INPUT_PULLUP` |
| Battery voltage | 34 | 100k top / 27k bottom: 12.6 V reads 2.68 V. GPIO34 is input-only, which is fine |
| Status LED | 2 | the on-board LED |

## Every connection

| From | To | Wire |
|---|---|---|
| Battery + / - | power switch -> XT60 splitter | 14 AWG |
| Splitter | ESC front + / -, ESC rear + / - | 14 AWG |
| Splitter | XL4015 IN + / - | 20 AWG |
| XL4015 OUT + (5.0 V) | ESP32 VIN, red of all 4 servos | 20-22 AWG |
| XL4015 OUT - | ESP32 GND, brown/black of all 4 servos, ESC signal grounds | 20-22 AWG |
| ESC front signal (white/yellow) | GPIO 25 | Dupont |
| ESC rear signal | GPIO 26 | Dupont |
| ESC front 3 motor wires | front motor | 16-18 AWG, see extensions below |
| ESC rear 3 motor wires | rear motor | same |
| Pitch servo front / rear signal (orange) | GPIO 18 / 32 | servo lead |
| Roll servo front / rear signal | GPIO 19 / 33 | servo lead + extension |
| MPU6050 VCC / GND | ESP32 3V3 / GND | Dupont |
| MPU6050 SDA / SCL | GPIO 21 / 22 | Dupont |
| Bumper switch COM / NO | GND / GPIO 27 | Dupont |
| Battery + (after the switch) | 100k -> GPIO 34 -> 27k -> GND | on the perfboard |

## Wires across the hoop pivots

The ESCs sit on the rail but the motors ride on the hoops, and each hoop turns up to 180°.
So the 3 motor wires and the roll servo lead have to cross the pivot.

- Motor wires: the A2212 and ESC leads are short, so each motor needs 3 extension wires of about 25 cm
  (16-18 AWG silicone, soldered + heat shrink, or 3.5 mm bullet connectors).
- Roll servo: a 30 cm servo extension each.
- Leave a slack loop at each pivot. Swing the hoop through its full range by hand and make sure nothing pulls tight
  or gets near the prop.
- Measure first, then cut. These extensions aren't in the parts list yet: add about 2 m of 18 AWG and 2 servo extensions (~₱100).

Order of the motor wires doesn't matter at first. If a motor spins the wrong way, swap any two of its 3 wires.

## Before the first power-up

1. Props OFF.
2. Set the buck output to 5.0 V with a multimeter before anything is connected to it.
3. Multimeter on continuity: no short between battery + and -, and none between 5 V and GND.
4. Check the ESC signal red wires are cut.
5. Plug in the battery with the switch off, then switch on. Watch for smoke or heat for 10 s.
6. The ESP32 LED comes on and the ESCs beep their arming tones.

Then go on to bench calibration in [PLAN.md](PLAN.md).
