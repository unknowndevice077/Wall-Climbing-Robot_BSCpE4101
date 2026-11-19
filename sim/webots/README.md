# Webots sim

Same robot as the MuJoCo sim (`sim/wall_climber.xml`): CAD meshes from `sim/meshes/`, masses from
`design/mass_properties.json`, same controller logic as `sim/climb.py`, written as a Webots Python controller.

1. Install [Webots R2025a](https://cyberbotics.com) (free) and Python 3.
2. Open `worlds/wall_climber.wbt` in Webots and press play.

| File | What |
|---|---|
| `worlds/wall_climber.wbt` | Floor, 2.5 m wall at x = 1 m, robot: 4 free wheels, 2 hoops on servo hinges (MG90S: 0.22 N*m, 5 rad/s) |
| `controllers/climber/climber.py` | Drive -> tip onto the wall -> climb -> hold at 1.75 m |

- Controller args (Robot node -> `controllerArgs`): `--real` (default: battery sag, 80 ms motor lag, IMU bias and noise,
  a 1.5 N pull off the wall at 6 s), `--thrust-gf 780` (your measured thrust per motor).
- Thrust: the controller pushes each hoop at the prop centre, along the hoop axis, which is what a prop does.
  Webots' `Propeller` node gave almost no thrust in this setup, so it isn't used.
- Headless check (no window, prints `RESULT PASS/FAIL`):
  ```bash
  CLIMB_CHECK=16 webots --batch --mode=fast --no-rendering --minimize --stdout wall_climber.wbt
  ```
  Add `CLIMB_REAL=0` for the ideal run.

Results (755 gf per motor): ideal on the wall at 2.6 s and holding at 10.9 s; real on the wall at 2.9 s and holding at 11.2 s.
The MuJoCo sim gives about the same numbers.
