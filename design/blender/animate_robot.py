# Full robot with the bought parts (servos, motors, battery, ESCs, boards, bearings) + the climb animation.
# Needs design/assets/wall_climber_body.blend (build_robot.py) and sim/climb_anim.json (python sim/climb.py --record).
#   blender -b design/assets/wall_climber_body.blend --factory-startup -P design/blender/animate_robot.py
#   add "-- --preview" to also render design/assets/climb_preview.mp4 (quick workbench render)
# Writes design/assets/wall_climber_full.blend, wall_climber_full.glb (animated) and wall_climber_full.stl (static).
import bpy, bmesh, json, math, os, sys
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
DESIGN = os.path.dirname(HERE)
ASSETS = os.path.join(DESIGN, "assets")
ANIM = os.path.join(DESIGN, "..", "sim", "climb_anim.json")
PREVIEW = "--preview" in sys.argv

# same numbers as build_robot.py
WHEEL_X, WHEEL_Y, WHEEL_W = 0.165, 0.175, 0.010
LIFT = 0.108                     # axle height = wheel + tire radius
RING_X, RING_Z = 0.140, 0.032
BRACKET_Y, GEAR_GAP, AXLE_DROP, PROP_Z = 0.150, 0.024, 0.030, 0.010
REST_DEG = 25                    # build_robot.py places the hoops at 25 deg

scn = bpy.context.scene
M = {}


def mat(key, rgb, metal=0.0, rough=0.5):
    if key not in M:
        m = bpy.data.materials.get(key) or bpy.data.materials.new(key)
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (*rgb, 1)
        b.inputs["Metallic"].default_value = metal
        b.inputs["Roughness"].default_value = rough
        m.diffuse_color = (*rgb, 1)   # workbench preview uses this
        M[key] = m
    return M[key]


def obj(name, bm, material, parent):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    me.materials.append(material)
    o = bpy.data.objects.new(name, me)
    scn.collection.objects.link(o)
    o.parent = parent
    return o


def box(name, x0, x1, y0, y1, z0, z1, material, parent):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    bmesh.ops.scale(bm, vec=(x1 - x0, y1 - y0, z1 - z0), verts=bm.verts)
    bmesh.ops.translate(bm, vec=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), verts=bm.verts)
    return obj(name, bm, material, parent)


def cyl(name, r, c, z0, z1, material, parent, axis="Z", r_in=0.0, seg=32):
    bm = bmesh.new()
    if r_in:   # tube: outer minus inner done as a ring of quads
        geom = bmesh.ops.create_circle(bm, segments=seg, radius=r)["verts"]
        inner = bmesh.ops.create_circle(bm, segments=seg, radius=r_in)["verts"]
        for i in range(seg):
            bm.faces.new((geom[i], geom[(i + 1) % seg], inner[(i + 1) % seg], inner[i]))
        f = list(bm.faces)
        ext = bmesh.ops.extrude_face_region(bm, geom=f)
        bmesh.ops.translate(bm, vec=(0, 0, z1 - z0), verts=[v for v in ext["geom"] if isinstance(v, bmesh.types.BMVert)])
        bmesh.ops.translate(bm, vec=(0, 0, z0), verts=bm.verts)
    else:
        bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=z1 - z0)
        bmesh.ops.translate(bm, vec=(0, 0, (z0 + z1) / 2), verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if axis == "Y":
        bmesh.ops.rotate(bm, matrix=Matrix.Rotation(-math.pi / 2, 3, "X"), verts=bm.verts)
        bmesh.ops.translate(bm, vec=(c[0], 0, c[1]), verts=bm.verts)
    elif axis == "X":
        bmesh.ops.rotate(bm, matrix=Matrix.Rotation(math.pi / 2, 3, "Y"), verts=bm.verts)
        bmesh.ops.translate(bm, vec=(0, c[0], c[1]), verts=bm.verts)
    else:
        bmesh.ops.translate(bm, vec=(c[0], c[1], 0), verts=bm.verts)
    return obj(name, bm, material, parent)


def empty(name, parent, loc=(0, 0, 0), size=0.03):
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = size
    scn.collection.objects.link(e)
    e.parent = parent
    e.location = loc
    return e


def reparent(o, parent):
    w = o.matrix_world.copy()
    o.parent = parent
    o.matrix_parent_inverse = Matrix()
    o.matrix_world = w


# ---------------- 1. clean up: drop the hidden source meshes, keep the placed parts ----------------
for o in list(scn.objects):
    if o.type == "MESH" and o.parent is None and o.name != "Floor" or o.type == "CAMERA":
        bpy.data.objects.remove(o)
old_root = bpy.data.objects["WallClimber"]
parts = list(old_root.children)

# ---------------- 2. rig: robot -> wheels / hoops -> props ----------------
robot = empty("Robot", None, (0, 0, LIFT), 0.1)
robot.rotation_mode = "QUATERNION"
bpy.context.view_layer.update()

wheel_rig, hoop_rig, prop_rig, gear_rig = {}, {}, {}, {}
for side, (x, y) in {"FL": (WHEEL_X, WHEEL_Y), "FR": (WHEEL_X, -WHEEL_Y), "RL": (-WHEEL_X, WHEEL_Y), "RR": (-WHEEL_X, -WHEEL_Y)}.items():
    wheel_rig[side] = empty(f"Wheel_{side}", robot, (x, y, 0))
for k, sx in (("F", 1), ("R", -1)):
    h = empty(f"Hoop_{k}", robot, (sx * RING_X, 0, RING_Z), 0.05)
    h.rotation_euler = (0, math.radians(REST_DEG), 0)
    hoop_rig[k] = h
    prop_rig[k] = empty(f"Prop_{k}", h, (0, 0, PROP_Z), 0.04)
    gear_rig[k] = empty(f"ServoGear_{k}", robot, (sx * RING_X, BRACKET_Y + 0.007, RING_Z - GEAR_GAP), 0.02)
bpy.context.view_layer.update()

for o in parts:
    n = o.name
    if n[:5] in ("wheel", "tire_"):
        reparent(o, wheel_rig[n.split("_")[1]])
    elif n.startswith("prop_"):
        reparent(o, prop_rig[n[5]])
    elif n.endswith(("_F", "_R")) or n[:-4].endswith(("_F", "_R")):
        reparent(o, hoop_rig[n.split(".")[0][-1]])
    elif n.startswith("gear24"):   # chassis-side gears on the pitch servos
        reparent(o, gear_rig["F" if o.matrix_world.translation.x > 0 else "R"])
    else:
        reparent(o, robot)
bpy.data.objects.remove(old_root)

# ---------------- 3. bought parts (not printed, so build_robot.py doesn't draw them) ----------------
blue = mat("servo_blue", (0.12, 0.25, 0.7), 0, 0.5)
black = mat("black", (0.03, 0.03, 0.035), 0, 0.6)
silver = mat("motor_silver", (0.75, 0.76, 0.78), 0.9, 0.3)
red = mat("motor_red", (0.7, 0.08, 0.06), 0.6, 0.35)
lipo = mat("lipo_wrap", (0.9, 0.75, 0.1), 0, 0.4)
esc = mat("esc_shrink", (0.15, 0.4, 0.75), 0, 0.5)
pcb = mat("pcb_green", (0.05, 0.35, 0.18), 0, 0.5)
pcb_b = mat("pcb_blue", (0.08, 0.2, 0.55), 0, 0.5)
steel = mat("steel", (0.6, 0.6, 0.62), 1.0, 0.25)
wall_m = mat("wall", (0.72, 0.74, 0.78), 0, 0.95)


def mg90s(name, x0, x1, y0, y1, z0, z1, parent, horn_axis="Y"):
    # MG90S: body + mounting tabs + output shaft
    s = box(name, x0, x1, y0, y1, z0, z1, blue, parent)
    zc = (z0 + z1) / 2
    if horn_axis == "Y":
        box(name + " tabs", x0 - 0.005, x1 + 0.005, y1 - 0.0045, y1 - 0.0020, z0, z1, blue, parent)
    else:
        box(name + " tabs", x0, x1, y0, y1, z1 - 0.004, z1 - 0.0015, blue, parent)
    return s


# pitch servos sit on the inner face of the left brackets, shaft in line with the servo gear
for k, sx in (("F", 1), ("R", -1)):
    xs = sorted((sx * (RING_X - 0.006), sx * (RING_X + 0.0168)))
    mg90s(f"MG90S pitch {k}", xs[0], xs[1], 0.1275, 0.150, RING_Z - GEAR_GAP - 0.0061, RING_Z - GEAR_GAP + 0.0061, robot)
box("3S 1500 mAh LiPo", -0.0185, 0.0185, -0.039, 0.039, -0.0459, -0.0189, lipo, robot)
box("ESP32 DevKit", -0.014, 0.014, -0.026, 0.026, -0.0505, -0.0485, black, robot)
box("MPU6050", -0.008, 0.008, 0.006, 0.026, -0.0525, -0.0505, pcb_b, robot)
box("ESC F", 0.0075, 0.0525, -0.158, -0.134, -0.008, 0.000, esc, robot)
box("ESC R", -0.0525, -0.0075, -0.158, -0.134, -0.008, 0.000, esc, robot)
box("XL4015 buck", -0.0255, 0.0255, 0.133, 0.159, -0.008, -0.006, pcb_b, robot)
box("XL4015 heatsink", -0.010, 0.010, 0.138, 0.152, -0.006, 0.006, silver, robot)
box("power switch", -0.19, -0.175, -0.150, -0.142, -0.008, 0.004, black, robot)
arm = next(o for o in robot.children if o.name.startswith("bumper_arm"))
bb = [arm.matrix_world @ Vector(c) for c in arm.bound_box]
ax = max(v.x for v in bb)   # world coords; robot sits at x 0, z LIFT
ay = sum(v.y for v in bb) / 8
az = sum(v.z for v in bb) / 8 - LIFT
box("bumper switch", ax - 0.014, ax, ay - 0.003, ay + 0.003, az - 0.005, az + 0.005, black, robot)

for side, w in wheel_rig.items():   # 2 x 624ZZ per wheel + M4 axle bolt
    sy = 1 if side[1] == "L" else -1
    for i, dy in enumerate((-0.0025, 0.0025)):
        b = cyl(f"624ZZ {side} {i}", 0.0065, (0, 0), -0.0025, 0.0025, steel, w, r_in=0.002, seg=24)
        b.rotation_euler = (math.pi / 2, 0, 0); b.location = (0, dy - sy * 0.002, 0)
    cyl(f"M4 axle {side}", 0.002, (0, 0), -0.03, 0.03, steel, w, axis="Y")

for k, sx in (("F", 1), ("R", -1)):
    h = hoop_rig[k]
    # A2212: stator can + red bell, sits on the motor mount under the prop
    cyl(f"A2212 can {k}", 0.0140, (0, 0), -AXLE_DROP + 0.011, -0.006, silver, h)
    cyl(f"A2212 bell {k}", 0.0145, (0, 0), -0.006, 0.003, red, h)
    cyl(f"A2212 shaft {k}", 0.0025, (0, 0), 0.003, PROP_Z + 0.004, silver, h)
    xs = sorted((sx * 0.094, sx * 0.117))
    mg90s(f"MG90S roll {k}", xs[0], xs[1], -0.0061, 0.0061, -AXLE_DROP - 0.007, -AXLE_DROP + 0.016, h, horn_axis="Z")
    for py in (-1, 1):   # 693ZZ in the brackets at each hoop pivot
        b = cyl(f"693ZZ {k} {py}", 0.004, (0, 0), -0.002, 0.002, steel, robot, r_in=0.0015, seg=20)
        b.rotation_euler = (math.pi / 2, 0, 0); b.location = (sx * RING_X, py * (BRACKET_Y + 0.004), RING_Z)

# wall from the sim (sim/wall_climber.xml): face at x = 1.0 m
box("Wall", 1.0, 1.2, -1.5, 1.5, 0, 2.5, wall_m, None)

# ---------------- 4. animation from the sim ----------------
data = json.load(open(ANIM))
fps, frames = data["fps"], data["frames"]
scn.render.fps = fps
scn.frame_start, scn.frame_end = 1, len(frames)
spin = {"F": 0.0, "R": 0.0}
bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"   # one key per sim frame, no easing
for i, f in enumerate(frames, start=1):
    robot.location = f["pos"]
    robot.rotation_quaternion = f["quat"]
    robot.keyframe_insert("location", frame=i); robot.keyframe_insert("rotation_quaternion", frame=i)
    for side in wheel_rig:
        wheel_rig[side].rotation_euler = (0, f[f"w_{side}"], 0)
        wheel_rig[side].keyframe_insert("rotation_euler", frame=i)
    for k in "FR":
        a = f[f"pitch_{k}"]
        hoop_rig[k].rotation_euler = (0, a, 0); hoop_rig[k].keyframe_insert("rotation_euler", frame=i)
        gear_rig[k].rotation_euler = (0, -a, 0); gear_rig[k].keyframe_insert("rotation_euler", frame=i)   # 1:1 gears turn the other way
        # real props spin ~150 rev/s; this is just enough to look like spinning (opposite ways, CW + CCW)
        spin[k] += (1.1 if f[f"thrust_{k}"] > 0.05 else 0.0) * (1 if k == "F" else -1)
        prop_rig[k].rotation_euler = (0, 0, spin[k]); prop_rig[k].keyframe_insert("rotation_euler", frame=i)
scn.frame_set(1)

# camera follows the robot from the side
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); scn.collection.objects.link(cam); scn.camera = cam
cam.location = (0.25, -1.7, 0.9); cam.data.lens = 35
tr = cam.constraints.new("TRACK_TO"); tr.target = robot; tr.track_axis = "TRACK_NEGATIVE_Z"; tr.up_axis = "UP_Y"

# workbench / viewport solid mode use diffuse_color, the printed-part materials only set the shader colour
for m in bpy.data.materials:
    if m.use_nodes and "Principled BSDF" in m.node_tree.nodes:
        m.diffuse_color = m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value

n_parts = sum(1 for o in scn.objects if o.type == "MESH")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ASSETS, "wall_climber_full.blend"))

# static assembly STL (robot only, frame 1) and animated GLB
bpy.ops.object.select_all(action="DESELECT")
robot_meshes = [o for o in scn.objects if o.type == "MESH" and o.name not in ("Floor", "Wall")]
for o in robot_meshes:
    o.select_set(True)
bpy.ops.wm.stl_export(filepath=os.path.join(ASSETS, "wall_climber_full.stl"), export_selected_objects=True, apply_modifiers=True)
for o in [robot, *wheel_rig.values(), *hoop_rig.values(), *gear_rig.values(), *prop_rig.values()]:
    o.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.join(ASSETS, "wall_climber_full.glb"), use_selection=True, export_animations=True)
print(f"FULL MODEL OK: {n_parts} meshes, {len(frames)} frames at {fps} fps, last phase {frames[-1]['phase']}")

if PREVIEW:
    scn.render.engine = "BLENDER_WORKBENCH"
    scn.display.shading.color_type = "MATERIAL"
    scn.display.shading.light = "STUDIO"
    scn.display.shading.show_shadows = True
    scn.render.resolution_x, scn.render.resolution_y = 960, 540
    # PNG frames + ffmpeg (Blender 5 moved video output around, this works on any version)
    import subprocess, tempfile
    tmp = tempfile.mkdtemp()
    scn.render.image_settings.file_format = "PNG"
    scn.render.filepath = os.path.join(tmp, "f")
    bpy.ops.render.render(animation=True)
    out = os.path.join(ASSETS, "climb_preview.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-start_number", "1", "-i", os.path.join(tmp, "f%04d.png"),
                    "-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "23", out], check=True)
    print("PREVIEW", out)
