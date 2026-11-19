"""Wall climber controller for Webots: same logic as sim/climb.py (MuJoCo).

Phases: DRIVE -> TRANSITION (front wheels hit the wall) -> CLIMB -> HOLD at 1.75 m.
Each prop gets a wanted force in the world frame (X = toward the wall, Z = up); the IMU turns it
into a hoop angle + thrust. Args (controllerArgs in the .wbt):
  --real          battery sag, IMU bias + noise, a 1.5 N pull off the wall at 6 s
  --thrust-gf N   your measured thrust per motor (default 755)
  --check S       run S seconds, print RESULT PASS/FAIL, quit Webots
"""
import math
import os
import sys

from controller import Supervisor

G = 9.81
MASS = 1.039              # design/mass_properties.json
MOTOR_TAU = 0.08          # brushless + ESC spin-up lag (s), --real only
TOP_Z = 1.75
CLIMB_SPEED = 0.18
WALL_X = 1.0
PHI_MIN = {"F": math.radians(-4), "R": math.radians(-40)}   # front hoop hits the battery below -4 deg
PHI_MAX = math.radians(140)


def arg(name, default=None):
    if name in sys.argv:
        i = sys.argv.index(name)
        return sys.argv[i + 1] if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith("--") else True
    return default


REAL = bool(arg("--real", False)) and os.environ.get("CLIMB_REAL") != "0"
TMAX = float(arg("--thrust-gf", 755)) * G / 1000
if REAL:
    TMAX *= 0.89            # battery sag at 3.7 V/cell
CHECK = arg("--check") or os.environ.get("CLIMB_CHECK")   # env var: headless runs without editing the .wbt
CHECK = float(CHECK) if CHECK not in (None, True) else (14.0 if CHECK else None)

bot = Supervisor()
dt_ms = int(bot.getBasicTimeStep())
dt = dt_ms / 1000
me = bot.getSelf()
imu = bot.getDevice("imu"); imu.enable(dt_ms)
gps = bot.getDevice("gps"); gps.enable(dt_ms)
hoop = {n: bot.getDevice("pitch_" + n) for n in "FR"}
hoop_pos = {n: bot.getDevice("pitch_%s_sensor" % n) for n in "FR"}
prop = {n: bot.getDevice("prop_" + n) for n in "FR"}
hoop_node = {n: bot.getFromDef("HOOP_" + n) for n in "FR"}
thrust = {"F": 0.0, "R": 0.0}
for n in "FR":
    hoop_pos[n].enable(dt_ms)
    prop[n].setPosition(float("inf"))
    prop[n].setVelocity(0)
front_wheels = [bot.getFromDef(d).getField("endPoint").getSFNode() for d in ("WHEEL_FL", "WHEEL_FR")]

# fixed seed so --check gives the same answer every run
_seed = [12345]


def noise(sd):
    s = 0.0
    for _ in range(4):
        _seed[0] = (_seed[0] * 1103515245 + 12345) & 0x7FFFFFFF
        s += _seed[0] / 0x7FFFFFFF - 0.5
    return s * sd * math.sqrt(3)


def body_matrix():
    """chassis rotation matrix (columns = body X, Y, Z in world) from the IMU quaternion"""
    x, y, z, w = imu.getQuaternion()
    return [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]


def touching_wall(solids):
    return any(p.point[0] > WALL_X - 0.01 for s in solids for p in s.getContactPoints())


def set_prop(n, f, R):
    # world force -> body frame -> hoop angle about body Y + thrust
    fb = [sum(R[r][c] * f[r] for r in range(3)) for c in range(3)]
    phi = min(PHI_MAX, max(PHI_MIN[n], math.atan2(fb[0], fb[2])))
    mag = min(math.sqrt(fb[0] ** 2 + fb[2] ** 2), TMAX)
    err = abs(phi - hoop_pos[n].getValue())
    t = mag * max(0.0, 1 - err / 0.6)          # only push once the hoop is close to the angle
    hoop[n].setPosition(phi)
    if REAL:
        thrust[n] += (t - thrust[n]) * dt / MOTOR_TAU
    else:
        thrust[n] = t
    # the prop pushes the hoop along its own axis, at the prop centre (hoop frame)
    hoop_node[n].addForceWithOffset([0, 0, thrust[n]], [0, 0, 0.01], True)
    spin = 250 * min(1, thrust[n] / 2 + 0.1)
    prop[n].setVelocity(spin if n == "F" else -spin)   # looks only; rear spins the other way
    t = thrust[n]
    return t


phase, climb_i, last_phase, t_log = "DRIVE", 0.0, None, -1
imu_bias = math.radians(1.5) if REAL else 0.0
print(f"mass {MASS:.3f} kg, max thrust {2 * TMAX:.1f} N (T/W {2 * TMAX / (MASS * G):.2f}), real={REAL}")

while bot.step(dt_ms) != -1:
    t = bot.getTime()
    R = body_matrix()
    fwd = [R[0][0], R[1][0], R[2][0]]
    pitch = math.degrees(math.atan2(fwd[2], math.hypot(fwd[0], fwd[1])))
    z, vz = gps.getValues()[2], gps.getSpeedVector()[2]
    if REAL:
        pitch += math.degrees(imu_bias) + noise(1.0)
        vz += noise(0.03)
        if 6.0 < t < 6.25:
            me.addForce([-1.5, 0, 0], False)   # someone pulls it off the wall

    half_w = 0.5 * MASS * G
    if phase == "DRIVE":
        f_front = f_rear = [1.6, 0, 0]
        if touching_wall(front_wheels):
            phase = "TRANSITION"
    if phase != "DRIVE":
        w = min(1.0, max(0.0, pitch / 80))
        if phase == "TRANSITION" and pitch > 80:
            phase = "CLIMB"
        if phase == "CLIMB" and z > TOP_Z:
            phase = "HOLD"
        target_v = CLIMB_SPEED if phase == "CLIMB" else 0.0
        if phase != "TRANSITION":
            climb_i = max(-1, min(1, climb_i + (target_v - vz) * dt))
        up = half_w + 3.0 * (target_v - vz) + 4.0 * climb_i
        wall_front, wall_rear = [4.2, 0, up], [2.6, 0, up]   # top hoop pushes harder: peel moment
        tr_front, tr_rear = [1.0, 0, 7.0], [2.0, 0, 1.5]     # nose-up needs the front thrust going UP
        if phase == "TRANSITION":
            f_front = [a + (b - a) * w for a, b in zip(tr_front, wall_front)]
            f_rear = [a + (b - a) * w for a, b in zip(tr_rear, wall_rear)]
        else:
            f_front, f_rear = wall_front, wall_rear

    tf = set_prop("F", f_front, R)
    tr = set_prop("R", f_rear, R)

    if phase != last_phase or t - t_log >= 1.0:
        p = gps.getValues()
        print(f"t={t:5.2f}s {phase:<10} x={p[0]:.2f} z={p[2]:.2f} pitch={pitch:5.1f} "
              f"T_F={tf / G * 1000:4.0f}gf T_R={tr / G * 1000:4.0f}gf", flush=True)
        last_phase, t_log = phase, t

    if CHECK and t >= CHECK:
        z = gps.getValues()[2]
        ok = phase == "HOLD" and z > TOP_Z - 0.05
        print(f"RESULT {'PASS' if ok else 'FAIL'} phase={phase} z={z:.2f} thrust={TMAX * 1000 / G:.0f}gf real={REAL}", flush=True)
        bot.simulationQuit(0 if ok else 1)
