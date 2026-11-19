# 3D printing

Everything you need to print the robot's parts, start to finish.
The STL files are in [design/print/](../design/print/). They're in mm and already lying flat the right way up.
Don't rotate or scale them.

Grams and times come from [design/PARTS_REPORT.md](../design/PARTS_REPORT.md), which the CAD script regenerates.

## Printer and filament

| | Use |
|---|---|
| Printer | Any printer with a 220 x 220 mm bed or bigger (Ender-3 class). The wheel is 212 mm wide, so it just fits |
| Filament | PLA+, about 350 g of a 1 kg spool. PETG is better for the wheels if you have it: it bends where PLA cracks on a fall |
| Nozzle | 0.4 mm |
| Slicer | Cura, PrusaSlicer or OrcaSlicer, all fine |

## Slicer settings (all parts)

| Setting | Value |
|---|---|
| Layer height | 0.2 mm |
| Top / bottom layers | 4 / 4 |
| Nozzle / bed temp | what your spool says. PLA+ is usually 210-220 °C / 60 °C |
| Speed | 50 mm/s walls, 25 mm/s first layer |
| Cooling fan | 100% from layer 3 |
| Supports | off, none of the parts need them |
| Infill pattern | gyroid |
| Walls and infill | per part, see below |

## The parts

| File | Qty | Walls | Infill | Brim | g each | Time each |
|---|---|---|---|---|---|---|
| `wheel.stl` | 4 | 2 | 20% | 5 mm (thin and wide, it warps without one) | 52 | 3 h |
| `bracket.stl` | 4: 2 as is + 2 mirrored | 3 | 40% | no | 16 | 1 h |
| `gear24.stl` | 4 | 4 | 100% | no | 3 | 10 min |
| `motor_mount.stl` | 2 | 3 | 50% | no | 7 | 25 min |
| `hoop_clip.stl` | 4 | 3 | 50% | no | 4 | 15 min |
| `tray.stl` | 1 | 2 | 15% | no | 13 | 45 min |
| `bumper_arm.stl` | 1 | 2 | 20% | no | 4 | 15 min |
| Total | 20 parts | | | | ~330 g (~350 g with brims) | ~19 h |

Mirrored brackets: in the slicer, mirror on X (Cura: Mirror tool, PrusaSlicer/Orca: right click -> Mirror -> Along X).
The two plain ones go on the right side of the robot, the two mirrored ones on the left.

Why these numbers:
- **Wheel:** the rim and spokes are only 3.5-6 mm thick, so 2 walls already make them almost solid. The infill only matters in the hub.
- **Bracket:** it carries the hoop's thrust and the wheel axle, so it gets 3 walls (1.2 mm around every hole) and 40%.
- **Gear:** small and loaded at the teeth, so it's solid.
- **Motor mount and hoop clip:** motor vibration and full thrust go through them, so 50%.
- **Tray and bumper arm:** light jobs, light infill.

Grams for every part at 15/25/40/100% are in PARTS_REPORT.md if you change anything.

## Print order

Print a test pair first, then everything else in 6 plates:

| Plate | What | Time |
|---|---|---|
| 0 (test) | 1 bracket + 1 gear | ~1.2 h |
| 1-4 | 1 wheel each | 3 h each |
| 5 | the 3 other brackets (2 mirrored) + 3 gears | ~3.5 h |
| 6 | 2 motor mounts, 4 hoop clips, tray, bumper arm | ~2.5 h |

Do the wheels overnight. If the test plate fits, the rest will too.

## Test fit (plate 0)

Holes print about 0.2 mm small. Check these on the test bracket and gear before printing the rest:

| Check | Pass | Fix |
|---|---|---|
| 624ZZ bearing seat | bearing presses in with thumb force | drill to 13 mm |
| 693ZZ hoop pivot seat | bearing presses in | drill to 8 mm |
| Wheel axle hole | M4 bolt slides through | drill to 4.2 mm |
| M3 holes | M3 bolt slides through | drill to 3.4 mm |
| Servo pocket | MG90S sits flat on the inner face, shaft through the 9 mm hole | file the pocket |
| Gear on servo horn / pivot pin | snug, no wobble | adjust horizontal expansion in the slicer, reprint |
| Two gears meshed | turn smoothly with no slop | same |

If every hole is tight, set the slicer's hole/horizontal expansion to +0.1 mm rather than drilling 20 parts.

## After printing

1. Pull the brims off the wheels and trim the edges with a knife.
2. Drill the holes to size (table above) with a hand drill, slowly, so the plastic doesn't melt.
3. Press 2 x 624ZZ into each wheel hub, one from each side. A vise or a bolt + washers works, not a hammer.
4. Weigh everything together: it should be about 330 g. Over 380 g means the slicer used more walls or infill than this table.
5. Write the real grams in `PRINTED` in `design/blender/build_robot.py` if they're off by more than a few grams, rebuild, and rerun `python sim/climb.py --min-thrust`.

## Spares

Worth printing once everything works: 1 extra gear pair and 2 extra hoop clips (they break first in a fall).
About 30 min and 15 g.

## When prints go wrong

| Problem | Fix |
|---|---|
| Wheel corners lift off the bed | bigger brim (8 mm), clean the bed with alcohol, bed 65 °C |
| Gear teeth blobby | slow the outer wall to 25 mm/s, check cooling is on |
| First layer bulges at the bottom of the holes (elephant foot) | lower the first-layer flow or turn on elephant-foot compensation |
| Wheel cracks when dropped | reprint in PETG, or 3 walls |
| Bracket splits along the layers | 4 walls, nozzle 5 °C hotter |
