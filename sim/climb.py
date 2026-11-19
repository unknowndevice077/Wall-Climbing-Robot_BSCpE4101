"""Wall climbing robot in MuJoCo: drive to the wall, tip onto it, climb using only prop thrust.

  python sim/climb.py              -> opens the 3D viewer (live)
  python sim/climb.py --video      -> headless run, writes sim/climb.mp4 + prints a log
  add --real                       -> real-world limits (see REAL block below)
  add --thrust-gf 820              -> your measured max thrust per motor (kitchen-scale test)
  python sim/climb.py --min-thrust -> smallest thrust per motor that still climbs in --real
  python sim/climb.py --walls      -> tries lots of walls (angles, grip, bumps), prints what climbs
  wall options: --wall-angle 75 (90 = vertical, >90 = overhang), --mu 0.4, --bumps 20 (mm)
Masses come from design/mass_properties.json (made by design/blender/build_robot.py).
"""
import argparse, json, math, os, subprocess, sys
import numpy as np
import mujoco

HERE = os.path.dirname(os.path.abspath(__file__))
G = 9.81

ap = argparse.ArgumentParser()
ap.add_argument("--video", action="store_true")
ap.add_argument("--real", action="store_true", help="servo/motor limits, IMU noise, heavier, worse grip, a bump")
ap.add_argument("--seconds", type=float, default=None)
ap.add_argument("--thrust-gf", type=float, default=755, help="max thrust per motor in grams-force (measure it)")
ap.add_argument("--check", action="store_true", help="headless pass/fail, no video")
ap.add_argument("--min-thrust", action="store_true")
ap.add_argument("--walls", action="store_true", help="run the wall sweep")
ap.add_argument("--record", action="store_true", help="save the run as sim/climb_anim.json for design/blender/animate_robot.py")
ap.add_argument("--wall-angle", type=float, default=90, help="deg from the floor: 60 = ramp, 90 = vertical, 110 = overhang")
ap.add_argument("--mu", type=float, default=None, help="wheel-on-wall grip (default 0.9, 0.6 with --real)")
ap.add_argument("--bumps", type=float, default=0, help="height of ridges across the wall in mm (tiles, trim, cables)")
ARGS = ap.parse_args()

# wall: hinged at the floor line x = 1 m, tilted to --wall-angle. 3 m long.
A = math.radians(ARGS.wall_angle)
WALL_BASE = np.array([1.0, 0, 0])
WALL_UP = np.array([math.cos(A), 0, math.sin(A)])      # up along the wall face
WALL_OUT = np.array([-math.sin(A), 0, math.cos(A)])    # face normal, toward the robot
MU = ARGS.mu if ARGS.mu is not None else (0.6 if ARGS.real else 0.9)

spec = mujoco.MjSpec.from_file(os.path.join(HERE, "wall_climber.xml"))
wall_rot = np.column_stack([-WALL_OUT, [0, 1, 0], WALL_UP])
wall_quat = np.zeros(4)
mujoco.mju_mat2Quat(wall_quat, wall_rot.flatten())
wg = spec.geom("wall")
wg.size = [0.1, 1.5, 1.5]
wg.pos = WALL_BASE + WALL_UP * 1.5 - WALL_OUT * 0.1
wg.quat = wall_quat
wg.friction = [MU, 0.02, 0.002]
if ARGS.bumps > 0:
    hb = ARGS.bumps / 2000
    for i, s_up in enumerate((0.45, 0.8, 1.15, 1.5)):   # ridges across the wall, every 35 cm
        spec.worldbody.add_geom(name=f"bump{i}", type=mujoco.mjtGeom.mjGEOM_BOX, size=[hb, 1.4, 0.01],
                                pos=WALL_BASE + WALL_UP * s_up + WALL_OUT * hb, quat=wall_quat,
                                friction=[MU, 0.02, 0.002], rgba=[.6, .62, .66, 1])
m = spec.compile()
d = mujoco.MjData(m)


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

TMAX = ARGS.thrust_gf * G / 1000
for n in ("thrust_F", "thrust_R"):
    m.actuator_ctrlrange[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_ACTUATOR, n)] = [0, TMAX]
mujoco.mj_setConst(m, d)
MASS = sum(m.body_mass[bid("chassis"):])
TOP_S = 1.75           # stop climbing this far up the wall (wall is 3 m)
CLIMB_SPEED = 0.18     # m/s
PRESS_F, PRESS_R = 1.0, 2.0   # N into the wall per prop on a vertical wall (see controller)

act = {n: mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_ACTUATOR, n) for n in ("pitch_F", "pitch_R", "thrust_F", "thrust_R", "spin_F", "spin_R")}
chassis = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "chassis")
wall = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, "wall")
wall_geoms = {wall} | {i for i in range(m.ngeom) if (m.geom(i).name or "").startswith("bump")}
front_wheels = {mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, n) for n in ("wFL", "wFR")}
all_wheels = front_wheels | {mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, n) for n in ("wRL", "wRR")}

state = {"phase": "DRIVE", "climb_i": 0.0, "p_ref": 0.0, "t_ref": 0.0}

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

# MuJoCo takes the higher friction of the two geoms, so the wheels get MU too (floor stays 0.9)
for n in ("wFL", "wFR", "wRL", "wRR"):
    m.geom_friction[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, n)][0] = MU


def touching_wall(geoms):
    for i in range(d.ncon):
        c = d.contact[i]
        if (c.geom1 in wall_geoms and c.geom2 in geoms) or (c.geom2 in wall_geoms and c.geom1 in geoms):
            return True
    return False


def wheels_on_wall():
    return sum(1 for i in range(d.ncon) for g in (d.contact[i].geom1, d.contact[i].geom2)
               if g in all_wheels and (d.contact[i].geom1 in wall_geoms or d.contact[i].geom2 in wall_geoms))


def lerp(a, b, t):
    return a + (b - a) * t


def set_prop(name, fb):
    # wanted force in the robot's frame (x = nose, z = top) -> hoop angle + thrust. hoop pivots about body y
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
    # 0 = flat, 90 = nose straight up, >90 = leaning back under an overhang. the IMU gives this from gravity
    pitch = math.degrees(math.atan2(fwd[2], fwd[0]))
    v_up = float(d.qvel[:3] @ fwd)                         # speed along the nose = up the wall once on it
    vz = d.qvel[2]
    s_up = float((d.xpos[chassis] - WALL_BASE) @ WALL_UP)  # sim only: how far up the wall
    if REAL:
        pitch += IMU_BIAS + rng.normal(0, 1.0)
        v_up += rng.normal(0, 0.03)
        vz += rng.normal(0, 0.03)
        # someone pulls it off the wall at 6 s: 1.5 N for 0.25 s
        d.xfrc_applied[chassis][:3] = 1.5 * WALL_OUT if 6.0 < d.time < 6.25 else [0, 0, 0]
    p = math.radians(pitch)
    # gravity in the robot's frame. on the wall, body z points away from the wall
    g_x, g_z = -MASS * G * math.sin(p), -MASS * G * math.cos(p)
    ph = state["phase"]

    if ph == "DRIVE":
        f_front = f_rear = np.array([1.6, 0, 0.0])
        if touching_wall(front_wheels):
            state["phase"] = "TRANSITION"
            state["p_ref"], state["t_ref"] = pitch, d.time
    if ph in ("TRANSITION", "CLIMB", "HOLD"):
        if ph == "TRANSITION":
            # done when the nose is up (vertical wall) or the pitch stopped changing (ramp / overhang: it's flat on the face)
            if pitch > 80 and pitch < 100 and (REAL or wheels_on_wall() >= 3):
                state["phase"] = ph = "CLIMB"
            elif d.time - state["t_ref"] > 0.3:
                if pitch > 15 and abs(pitch - state["p_ref"]) < 3:
                    state["phase"] = ph = "CLIMB"
                state["p_ref"], state["t_ref"] = pitch, d.time
        if ph == "CLIMB" and s_up > TOP_S:
            state["phase"] = ph = "HOLD"
        target_v = CLIMB_SPEED if ph == "CLIMB" else 0.0
        if ph != "TRANSITION":
            state["climb_i"] = max(-1, min(1, state["climb_i"] + (target_v - v_up) * m.opt.timestep))
        # along the wall: cancel the weight's pull down the face + speed control
        along = -g_x + 2 * (3.0 * (target_v - v_up) + 4.0 * state["climb_i"])
        # into the wall: keep it light. the props sit 150 mm off the wall and the CG 109 mm, so the thrust tips
        # the top in and tries to lift the BOTTOM wheels -> rear pushes harder. pushing hard just wastes thrust
        # and jams the wheels on bumps. scales with how much weight hangs on the face; on a ramp gravity
        # already presses it on (g_z < 0), under an overhang it pulls it off (g_z > 0)
        k = max(0.4, -g_x / (MASS * G))
        press_f = max(0.5, PRESS_F * k + g_z / 2)
        press_r = max(0.5, PRESS_R * k + g_z / 2)
        wall_front = np.array([along / 2, 0, -press_f])
        wall_rear = np.array([along / 2, 0, -press_r])
        if ph == "TRANSITION":
            # world frame (x = toward the wall, z = up). nose-up needs almost all front thrust going UP,
            # rear rolls the back wheels in. blend toward "hang on a vertical wall" as the nose comes up
            c, sn = math.cos(p), math.sin(p)
            to_body = lambda f: np.array([f[0] * c + f[2] * sn, 0, -f[0] * sn + f[2] * c])
            w = min(1.0, max(0.0, pitch / 80))
            up = 0.5 * MASS * G - 3.0 * vz
            f_front = to_body(lerp(np.array([1.0, 0, 7.0]), np.array([4.2, 0, up]), w))
            f_rear = to_body(lerp(np.array([2.0, 0, 1.5]), np.array([2.6, 0, up]), w))
        else:
            f_front, f_rear = wall_front, wall_rear

    set_prop("F", f_front)
    set_prop("R", f_rear)
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
    s_up = float((d.xpos[chassis] - WALL_BASE) @ WALL_UP)
    ok = state["phase"] == "HOLD" and s_up > TOP_S - 0.05
    print(f"RESULT {'PASS' if ok else 'FAIL'} phase={state['phase']} up_wall={s_up:.2f}m mass={MASS:.3f}kg thrust={ARGS.thrust_gf:.0f}gf "
          f"wall={ARGS.wall_angle:.0f}deg mu={MU} bumps={ARGS.bumps:.0f}mm")
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


def walls_sweep():
    # every run is --real. one thing changes at a time, the rest stays at: vertical, mu 0.6, flat
    from concurrent.futures import ThreadPoolExecutor
    runs = [("angle", f"{a} deg", ["--wall-angle", str(a)]) for a in (30, 45, 60, 75, 90, 95, 100, 110)]
    runs += [("grip", f"mu {mu}", ["--mu", str(mu)]) for mu in (0.9, 0.6, 0.4, 0.3, 0.2, 0.1)]
    runs += [("bumps", f"{b} mm", ["--bumps", str(b)]) for b in (5, 10, 15, 20, 25, 30)]

    def one(r):
        out = subprocess.run([sys.executable, __file__, "--check", "--real", "--thrust-gf", str(ARGS.thrust_gf)] + r[2],
                             capture_output=True, text=True).stdout
        return r, "climbs" if "RESULT PASS" in out else "FAILS  " + out.strip().splitlines()[-1].split(" mass")[0][12:]

    with ThreadPoolExecutor(max(1, os.cpu_count() - 1)) as ex:
        for (kind, label, _), res in ex.map(one, runs):
            print(f"  {kind:<6} {label:<8} {res}", flush=True)


def record(seconds=16.0, fps=30):
    # pose + joint angles per frame, the Blender animation plays these back
    q = lambda j: d.qpos[m.jnt_qposadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, j)]]
    steps_per_frame = int(round(1 / fps / m.opt.timestep))
    frames = []
    for _ in range(int(seconds * fps)):
        for _ in range(steps_per_frame):
            controller()
            mujoco.mj_step(m, d)
        frames.append({"pos": [round(float(v), 5) for v in d.xpos[chassis]],
                       "quat": [round(float(v), 5) for v in d.xquat[chassis]],
                       **{j: round(float(q(j)), 4) for j in ("pitch_F", "pitch_R", "w_FL", "w_FR", "w_RL", "w_RR")},
                       "thrust_F": round(float(d.ctrl[act["thrust_F"]]), 2), "thrust_R": round(float(d.ctrl[act["thrust_R"]]), 2),
                       "phase": state["phase"]})
    out = os.path.join(HERE, "climb_anim.json")
    json.dump({"fps": fps, "real": REAL, "frames": frames}, open(out, "w"))
    print(f"recorded {len(frames)} frames, last phase {state['phase']} -> {out}")


if __name__ == "__main__":
    if ARGS.walls:
        walls_sweep()
        sys.exit()
    if ARGS.min_thrust:
        min_thrust()
    elif ARGS.check:
        sys.exit(0 if run_check(ARGS.seconds or 18) else 1)
    elif ARGS.record:
        record(ARGS.seconds or 16)
    elif ARGS.video:
        run_video(ARGS.seconds or 16)
    else:
        run_viewer()
