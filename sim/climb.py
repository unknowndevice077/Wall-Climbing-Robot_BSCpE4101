"""Wall climbing robot in MuJoCo: drive to the wall, tip onto it, climb using only prop thrust.

  python sim/climb.py              -> opens the 3D viewer (live)
  python sim/climb.py --video      -> headless run, writes sim/climb.mp4 + prints a log
  add --real                       -> real-world limits (see REAL block below)
  add --thrust-gf 820              -> your measured max thrust per motor (kitchen-scale test)
  python sim/climb.py --min-thrust -> smallest thrust per motor that still climbs in --real
Masses come from design/mass_properties.json (made by design/blender/build_robot.py).
"""
import argparse, json, math, os, subprocess, sys
import numpy as np
import mujoco

HERE = os.path.dirname(os.path.abspath(__file__))
m = mujoco.MjModel.from_xml_path(os.path.join(HERE, "wall_climber.xml"))
d = mujoco.MjData(m)
G = 9.81


def bid(name):
    return mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, name)


def set_body(name, kg, com=None):
    b = bid(name)
    if m.body_mass[b] > 0:
        m.body_inertia[b] *= kg / m.body_mass[b]
    m.body_mass[b] = kg
    if com is not None:
        m.body_ipos[b] = com

# weights + centres of mass from the CAD (every printed part and bought part)
MP_FILE = os.path.join(HERE, "..", "design", "mass_properties.json")
if os.path.exists(MP_FILE):
    mp = json.load(open(MP_FILE))
    set_body("chassis", mp["chassis"]["mass_kg"], mp["chassis"]["com_m"])
    hx, hy, hz = mp["hoop"]["com_m"]
    set_body("ring_F", mp["hoop"]["mass_kg"], [hx, hy, hz])
    set_body("ring_R", mp["hoop"]["mass_kg"], [-hx, hy, hz])   # roll servo is on the outer side of each hoop
    for w in ("FL", "FR", "RL", "RR"):
        set_body("wheel_" + w, mp["wheel"]["mass_kg"])

ap = argparse.ArgumentParser()
ap.add_argument("--video", action="store_true")
ap.add_argument("--real", action="store_true", help="servo/motor limits, IMU noise, heavier, worse grip, a bump")
ap.add_argument("--seconds", type=float, default=14.0)
ap.add_argument("--thrust-gf", type=float, default=755, help="max thrust per motor in grams-force (measure it)")
ap.add_argument("--check", action="store_true", help="headless pass/fail, no video")
ap.add_argument("--min-thrust", action="store_true")
ARGS = ap.parse_args()

TMAX = ARGS.thrust_gf * G / 1000
for n in ("thrust_F", "thrust_R"):
    m.actuator_ctrlrange[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_ACTUATOR, n)] = [0, TMAX]
mujoco.mj_setConst(m, d)
MASS = sum(m.body_mass[bid("chassis"):])
TOP_Z = 1.75           # stop climbing here (wall is 2.5 m)
CLIMB_SPEED = 0.18     # m/s

act = {n: mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_ACTUATOR, n) for n in ("pitch_F", "pitch_R", "thrust_F", "thrust_R", "spin_F", "spin_R")}
chassis = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "chassis")
wall = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, "wall")
front_wheels = {mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, n) for n in ("wFL", "wFR")}
all_wheels = front_wheels | {mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, n) for n in ("wRL", "wRR")}

state = {"phase": "DRIVE", "climb_i": 0.0}

# --real: stuff the clean sim ignores. Controller still thinks it's the clean robot.
REAL = ARGS.real
rng = np.random.default_rng(7)
SERVO_SLEW = 5.0        # rad/s, MG90S under load (~0.1 s/60deg no load)
MOTOR_TAU = 0.08        # s, prop spin-up lag
IMU_BIAS = 1.5          # deg, MPU6050 mounted slightly off
stats = {"phi_min": 9, "phi_max": -9, "t_peak": 0}
real = {"F": {"phi": 0.0, "T": 0.0}, "R": {"phi": 0.0, "T": 0.0}}
if REAL:
    set_body("chassis", m.body_mass[chassis] + 0.1 * MASS)        # 10% heavier than planned
    for n in ("thrust_F", "thrust_R"):
        m.actuator_ctrlrange[act[n]] = [0, TMAX * 0.89]           # battery sag at 3.7 V/cell: ~11% less thrust
    mujoco.mj_setConst(m, d)
    for n in ("wFL", "wFR", "wRL", "wRR"):
        m.geom_friction[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, n)][0] = 0.6   # tube rubber on painted wall


def touching_wall(geoms):
    for i in range(d.ncon):
        c = d.contact[i]
        if (c.geom1 == wall and c.geom2 in geoms) or (c.geom2 == wall and c.geom1 in geoms):
            return True
    return False


def wheels_on_wall():
    return sum(1 for i in range(d.ncon) for g in (d.contact[i].geom1, d.contact[i].geom2)
               if g in all_wheels and wall in (d.contact[i].geom1, d.contact[i].geom2))


def lerp(a, b, t):
    return a + (b - a) * t


def set_prop(name, f_world, R):
    """turn a wanted world-frame force into hoop angle + thrust (hoop pivots about body Y)"""
    fb = R.T @ f_world
    phi = math.atan2(fb[0], fb[2])
    mag = min(np.linalg.norm(fb), TMAX)
    # only push once the hoop is close to the commanded angle
    cur = d.qpos[m.jnt_qposadr[m.actuator_trnid[act["pitch_" + name], 0]]]
    err = abs(math.atan2(math.sin(phi - cur), math.cos(phi - cur)))
    cmd = mag * max(0.0, 1 - err / 0.6)
    if REAL:
        r, dt = real[name], m.opt.timestep
        lo = -4 if name == "F" else -40                           # front hoop hits the battery below -4 deg (CAD check)
        phi = min(math.radians(140), max(math.radians(lo), phi))   # 180deg servo, 90 = prop pushes forward
        r["phi"] += max(-SERVO_SLEW * dt, min(SERVO_SLEW * dt, phi - r["phi"]))
        r["T"] += (cmd - r["T"]) * dt / MOTOR_TAU
        phi, cmd = r["phi"], r["T"]
    stats["phi_min"], stats["phi_max"] = min(stats["phi_min"], phi), max(stats["phi_max"], phi)
    stats["t_peak"] = max(stats["t_peak"], cmd)
    d.ctrl[act["pitch_" + name]] = phi
    d.ctrl[act["thrust_" + name]] = cmd


def controller():
    R = d.xmat[chassis].reshape(3, 3)
    fwd = R[:, 0]
    pitch = math.degrees(math.atan2(fwd[2], math.hypot(fwd[0], fwd[1])))   # 0 = flat, 90 = nose up
    z, vz = d.xpos[chassis][2], d.qvel[2]
    if REAL:
        pitch += IMU_BIAS + rng.normal(0, 1.0)
        vz += rng.normal(0, 0.03)
        # someone bumps it at 6 s: 1.5 N pull away from the wall for 0.25 s
        d.xfrc_applied[chassis][:3] = [-1.5, 0, 0] if 6.0 < d.time < 6.25 else [0, 0, 0]
    half_w = 0.5 * MASS * G
    ph = state["phase"]

    if ph == "DRIVE":
        f_front = f_rear = np.array([1.6, 0, 0.0])
        if touching_wall(front_wheels):
            state["phase"] = "TRANSITION"
    if ph in ("TRANSITION", "CLIMB", "HOLD"):
        w = min(1.0, max(0.0, pitch / 80))
        # on the wall: up-force for the weight + push into the wall so the top wheels don't peel
        if ph == "TRANSITION" and pitch > 80 and (REAL or wheels_on_wall() >= 3):
            state["phase"] = ph = "CLIMB"
        if ph == "CLIMB" and z > TOP_Z:
            state["phase"] = ph = "HOLD"
        target_v = CLIMB_SPEED if ph == "CLIMB" else 0.0
        if ph != "TRANSITION":
            state["climb_i"] += (target_v - vz) * m.opt.timestep
            state["climb_i"] = max(-1, min(1, state["climb_i"]))
        up = half_w + 3.0 * (target_v - vz) + 4.0 * state["climb_i"]
        wall_front = np.array([4.2, 0, up])    # top hoop pushes harder into the wall (peel moment)
        wall_rear = np.array([2.6, 0, up])
        # nose-up needs almost all front thrust going UP; pushing hard into the wall pitches the nose back down
        tr_front = np.array([1.0, 0, 7.0])
        tr_rear = np.array([2.0, 0, 1.5])       # roll the rear wheels in
        f_front = lerp(tr_front, wall_front, w) if ph == "TRANSITION" else wall_front
        f_rear = lerp(tr_rear, wall_rear, w) if ph == "TRANSITION" else wall_rear

    set_prop("F", f_front, R)
    set_prop("R", f_rear, R)
    spin = 250 * min(1, d.ctrl[act["thrust_F"]] / 2 + 0.1)
    d.ctrl[act["spin_F"]], d.ctrl[act["spin_R"]] = spin, -spin
    return pitch


def run_video(seconds=14.0, fps=30):
    out = os.path.join(HERE, "climb_real.mp4" if REAL else "climb.mp4")
    W, H = 1280, 720
    r = mujoco.Renderer(m, H, W)
    cam = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_CAMERA, "side")
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(fps), "-i", "-", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "20", out], stdin=subprocess.PIPE)
    steps_per_frame = int(round(1 / fps / m.opt.timestep))
    last_phase, t_log = None, 0
    for frame in range(int(seconds * fps)):
        for _ in range(steps_per_frame):
            pitch = controller()
            mujoco.mj_step(m, d)
        if state["phase"] != last_phase or d.time - t_log >= 1.0:
            p = d.xpos[chassis]
            print(f"t={d.time:5.2f}s  {state['phase']:<10} x={p[0]:.2f} z={p[2]:.2f} pitch={pitch:5.1f}  "
                  f"thrust F/R={d.ctrl[act['thrust_F']]:.1f}/{d.ctrl[act['thrust_R']]:.1f} N  wall-wheels={wheels_on_wall()}")
            last_phase, t_log = state["phase"], d.time
        r.update_scene(d, camera=cam)
        ff.stdin.write(r.render().tobytes())
    ff.stdin.close(); ff.wait()
    print("mass %.2f kg, max thrust %.1f N (T/W %.2f)" % (MASS, 2 * TMAX, 2 * TMAX / (MASS * G)))
    print("hoop servo range used: %.0f..%.0f deg (servo can do 0..180), peak thrust %.1f N per prop"
          % (math.degrees(stats["phi_min"]), math.degrees(stats["phi_max"]), stats["t_peak"]))
    print("video:", out)


def run_viewer():
    import mujoco.viewer, time
    with mujoco.viewer.launch_passive(m, d) as v:
        while v.is_running():
            t0 = time.time()
            for _ in range(10):
                controller(); mujoco.mj_step(m, d)
            v.sync()
            time.sleep(max(0, 10 * m.opt.timestep - (time.time() - t0)))


def run_check(seconds):
    while d.time < seconds:
        controller(); mujoco.mj_step(m, d)
    ok = state["phase"] == "HOLD" and d.xpos[chassis][2] > TOP_Z - 0.05
    print(f"RESULT {'PASS' if ok else 'FAIL'} phase={state['phase']} z={d.xpos[chassis][2]:.2f} mass={MASS:.3f}kg thrust={ARGS.thrust_gf:.0f}gf")
    return ok


def min_thrust():
    lo, hi = 500.0, 1200.0
    for _ in range(8):
        mid = (lo + hi) / 2
        out = subprocess.run([sys.executable, __file__, "--check", "--real", "--thrust-gf", f"{mid:.0f}"], capture_output=True, text=True).stdout
        ok = "RESULT PASS" in out
        print(f"  {mid:6.0f} gf per motor: {'climbs' if ok else 'fails'}")
        hi, lo = (mid, lo) if ok else (hi, mid)
    print(f"MIN THRUST (real-world run): {hi:.0f} gf per motor for a {MASS * 1000:.0f} g robot")


if __name__ == "__main__":
    if ARGS.min_thrust:
        min_thrust()
    elif ARGS.check:
        sys.exit(0 if run_check(ARGS.seconds) else 1)
    elif ARGS.video:
        run_video(ARGS.seconds)
    else:
        run_viewer()
