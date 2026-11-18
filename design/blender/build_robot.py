# Wall-climbing robot BODY ONLY (no electronics), based on the design doc:
# star-spoke wheels, propeller hoop frames, chassis spine.
# Exports one STL per physics part (for MuJoCo) + an assembled .blend/.glb + preview render.
# Run from the repo root: blender -b --factory-startup -P design/blender/build_robot.py
# Units: metres. X = forward, Y = left, Z = up.
import bpy, bmesh, math, os
from mathutils import Vector, Matrix

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, "design", "assets")
MESH = os.path.join(REPO, "sim", "meshes")
os.makedirs(OUT, exist_ok=True)
os.makedirs(MESH, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene

# keep in sync with sim/wall_climber.xml
WHEEL_R, WHEEL_T = 0.11, 0.014
WHEEL_X, WHEEL_Y = 0.16, 0.175
RING_R, RING_X, RING_Z = 0.125, 0.135, 0.03
PROP_R = 0.1016  # 8 in


def mat(name, rgb, metal=0.0, rough=0.5):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Metallic"].default_value = metal
    b.inputs["Roughness"].default_value = rough
    return m

M = {
    "plate": mat("PlatePly", (0.45, 0.2, 0.08), 0, 0.6),
    "carbon": mat("Carbon", (0.04, 0.04, 0.045), 0.2, 0.35),
    "alu": mat("Aluminium", (0.72, 0.73, 0.75), 1, 0.35),
    "wheel": mat("WheelPLA", (0.55, 0.8, 0.6), 0, 0.5),
    "tire": mat("Tire", (0.35, 0.22, 0.12), 0, 0.8),
    "prop": mat("Prop", (0.6, 0.6, 0.62), 0, 0.45),
}


def new_obj(name, bm, material):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(material)
    o = bpy.data.objects.new(name, me)
    scn.collection.objects.link(o)
    return o


def box(name, size, loc, material, rot=None):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    if rot:
        bmesh.ops.rotate(bm, verts=bm.verts, matrix=rot)
    bmesh.ops.translate(bm, vec=Vector(loc), verts=bm.verts)
    return new_obj(name, bm, material)


def cyl(name, r, depth, loc, material, axis="Z", seg=24):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=depth)
    if axis != "Z":
        bmesh.ops.rotate(bm, verts=bm.verts, matrix=Matrix.Rotation(math.pi / 2, 3, "X" if axis == "Y" else "Y"))
    bmesh.ops.translate(bm, vec=Vector(loc), verts=bm.verts)
    o = new_obj(name, bm, material)
    for p in o.data.polygons:
        p.use_smooth = len(p.vertices) == 4
    return o


def annulus(name, r_out, r_in, depth, material, axis="Z", seg=72, loc=(0, 0, 0)):
    bm = bmesh.new()
    ring = []
    for z in (-depth / 2, depth / 2):
        for r in (r_out, r_in):
            ring.append([bm.verts.new((r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg), z)) for i in range(seg)])
    bo, bi, to, ti = ring
    for i in range(seg):
        j = (i + 1) % seg
        bm.faces.new((to[i], to[j], ti[j], ti[i]))
        bm.faces.new((bo[j], bo[i], bi[i], bi[j]))
        bm.faces.new((bo[i], bo[j], to[j], to[i]))
        bm.faces.new((ti[i], ti[j], bi[j], bi[i]))
    if axis == "Y":
        bmesh.ops.rotate(bm, verts=bm.verts, matrix=Matrix.Rotation(math.pi / 2, 3, "X"))
    bmesh.ops.translate(bm, vec=Vector(loc), verts=bm.verts)
    o = new_obj(name, bm, material)
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def bar_xz(name, p0, p1, w, t, material):
    """flat bar between two XZ points, thickness along Y"""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    return box(name, (d.length, t, w), (p0 + p1) / 2, material, Matrix.Rotation(-math.atan2(d.z, d.x), 3, "Y"))


def join(name, objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.active_object
    o.name = name
    return o


# ---------------- parts (each built at its own origin) ----------------
def make_wheel():
    parts = [
        annulus("w_rim", WHEEL_R - 0.003, WHEEL_R - 0.012, WHEEL_T, M["wheel"], "Y"),
        annulus("w_tire", WHEEL_R, WHEEL_R - 0.003, WHEEL_T * 0.85, M["tire"], "Y"),
        annulus("w_inner", 0.045, 0.039, WHEEL_T * 0.6, M["wheel"], "Y"),
        cyl("w_hub", 0.017, WHEEL_T * 1.8, (0, 0, 0), M["wheel"], "Y"),
    ]
    rr = WHEEL_R - 0.01
    outer = [(rr * math.cos(math.radians(90 + 72 * i)), rr * math.sin(math.radians(90 + 72 * i))) for i in range(5)]
    mid = [(0.042 * math.cos(math.radians(126 + 72 * i)), 0.042 * math.sin(math.radians(126 + 72 * i))) for i in range(5)]
    for i in range(5):
        x, z = outer[i]
        # webbed spokes like the reference photo: each rim node ties to two inner-ring nodes and the hub
        parts.append(bar_xz(f"w_s{i}", (0, 0, 0), (x, 0, z), 0.006, WHEEL_T * 0.7, M["wheel"]))
        for k in (i, (i - 1) % 5):
            parts.append(bar_xz(f"w_t{i}{k}", mid[k] and (mid[k][0], 0, mid[k][1]), (x, 0, z), 0.004, WHEEL_T * 0.55, M["wheel"]))
        x2, z2 = outer[(i + 2) % 5]
        parts.append(bar_xz(f"w_p{i}", (x, 0, z), (x2, 0, z2), 0.004, WHEEL_T * 0.5, M["wheel"]))
    return join("wheel", parts)


def make_chassis():
    # H-frame: each hoop sweeps a 125 mm ball when it tilts, so nothing may sit inside that ball.
    # Side rails run outside the hoops, one cross beam sits between them, electronics hang under it.
    p = []
    for sy in (1, -1):
        p.append(box(f"rail{sy}", (0.36, 0.01, 0.018), (0, sy * 0.155, -0.012), M["carbon"]))
    p.append(box("crossBeam", (0.012, 0.32, 0.016), (0, 0, -0.045), M["carbon"]))
    for sy in (1, -1):
        p.append(box(f"beamDrop{sy}", (0.012, 0.006, 0.04), (0, sy * 0.155, -0.03), M["plate"]))
    # battery tray (holds a 3S pack sideways) + ESP32 plate, both under the beam
    p.append(box("trayFloor", (0.04, 0.09, 0.003), (0, 0, -0.088), M["plate"]))
    for sy in (1, -1):
        p.append(box(f"trayWall{sy}", (0.04, 0.003, 0.04), (0, sy * 0.045, -0.068), M["plate"]))
    for sx in (1, -1):
        for sy in (1, -1):
            y = sy * 0.155
            # tower: holds the hoop pivot (top) and links to the wheel axle plate
            p.append(box(f"tower{sx}{sy}", (0.03, 0.005, 0.07), (sx * RING_X, y, 0.005), M["plate"]))
            p.append(box(f"towerCap{sx}{sy}", (0.04, 0.012, 0.006), (sx * RING_X, y, RING_Z + 0.008), M["plate"]))
            # axle plate at the wheel
            p.append(box(f"axlePlate{sx}{sy}", (0.05, 0.005, 0.04), (sx * WHEEL_X, y, 0), M["plate"]))
            p.append(box(f"link{sx}{sy}", (abs(WHEEL_X - RING_X) + 0.03, 0.005, 0.014), (sx * (WHEEL_X + RING_X) / 2, y, -0.014), M["plate"]))
            p.append(cyl(f"axle{sx}{sy}", 0.004, 0.03, (sx * WHEEL_X, sy * 0.163, 0), M["alu"], "Y"))
            # suspension spring detail from the photo
            p.append(cyl(f"spring{sx}{sy}", 0.006, 0.03, (sx * (WHEEL_X + 0.02), sy * 0.149, 0.012), M["alu"], "Z", 10))
    return join("chassis", p)


def make_ring():
    p = [annulus("hoop", RING_R, RING_R - 0.008, 0.012, M["carbon"])]
    for sy in (1, -1):
        p.append(cyl(f"pivot{sy}", 0.004, 0.026, (0, sy * (RING_R + 0.009), 0), M["alu"], "Y"))
        # twin struts carrying the prop hub (like the photo's inner frame)
        p.append(box(f"strut{sy}", (2 * RING_R - 0.01, 0.005, 0.01), (0, sy * 0.014, 0), M["carbon"]))
    p.append(box("hubPlate", (0.036, 0.036, 0.004), (0, 0, 0.006), M["plate"]))
    p.append(cyl("hub", 0.014, 0.022, (0, 0, 0.019), M["alu"], "Z", 28))  # propeller hub (motor goes here)
    return join("ring", p)


def make_prop():
    bm = bmesh.new()
    for side in (1, -1):
        prev = None
        n = 10
        for i in range(n + 1):
            r = 0.01 + (PROP_R - 0.01) * i / n
            chord = 0.019 * (1 - 0.55 * i / n) * (0.8 if i == 0 else 1)
            tw = math.radians(30 - 20 * i / n)
            c, s = math.cos(tw) * chord / 2, math.sin(tw) * chord / 2
            row = [bm.verts.new((side * r, side * c, s)), bm.verts.new((side * r, -side * c, -s))]
            if prev:
                bm.faces.new((prev[0], prev[1], row[1], row[0]))
            prev = row
    o = new_obj("prop_blades", bm, M["prop"])
    o.modifiers.new("t", "SOLIDIFY").thickness = 0.003
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.object.modifier_apply(modifier="t")
    nut = cyl("prop_nut", 0.007, 0.012, (0, 0, 0), M["alu"], "Z", 16)
    return join("prop", [o, nut])


parts = {"wheel": make_wheel(), "chassis": make_chassis(), "ring": make_ring(), "prop": make_prop()}


def clearance_check():
    """sweep each hoop+prop through the servo range and look for hits on the chassis"""
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    def tree(obj, mw):
        bm = bmesh.new(); bm.from_object(obj, dg); bm.transform(mw)
        t = BVHTree.FromBMesh(bm); bm.free(); return t
    body = tree(parts["chassis"], Matrix.Identity(4))
    hits = []
    for sx in (1, -1):
        for deg in range(-40, 141, 2):
            mw = Matrix.Translation((sx * RING_X, 0, RING_Z)) @ Matrix.Rotation(math.radians(deg), 4, "Y")
            for k, extra in (("ring", Matrix.Identity(4)), ("prop", Matrix.Translation((0, 0, 0.034)))):
                for spin in ((0, 45, 90, 135) if k == "prop" else (0,)):
                    m2 = mw @ extra @ Matrix.Rotation(math.radians(spin), 4, "Z")
                    if body.overlap(tree(parts[k], m2)):
                        hits.append((("F" if sx > 0 else "R"), k, deg))
    if hits:
        print("CLEARANCE FAIL", sorted(set((h[0], h[1], h[2]) for h in hits))[:20], "... total", len(hits))
    else:
        print("CLEARANCE OK: hoops + props clear the chassis from -40 to 140 deg")

clearance_check()

for name, o in parts.items():
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.ops.wm.stl_export(filepath=os.path.join(MESH, name + ".stl"), export_selected_objects=True, apply_modifiers=True)

# ---------------- assembled robot ----------------
robot = bpy.data.objects.new("WallClimber", None)
scn.collection.objects.link(robot)
robot.location = (0, 0, WHEEL_R)
parts["chassis"].parent = robot


def inst(src, name, loc, rot=(0, 0, 0), parent=robot):
    o = src.copy()
    o.name = name
    scn.collection.objects.link(o)
    o.parent = parent
    o.location = loc
    o.rotation_euler = rot
    return o

for sx, fx in ((1, "F"), (-1, "R")):
    for sy, fy in ((1, "L"), (-1, "R")):
        inst(parts["wheel"], f"Wheel_{fx}{fy}", (sx * WHEEL_X, sy * WHEEL_Y, 0))
    ring = inst(parts["ring"], f"Ring_{fx}", (sx * RING_X, 0, RING_Z), (0, math.radians(25), 0))
    inst(parts["prop"], f"Prop_{fx}", (0, 0, 0.034), (0, 0, math.radians(20 + 70 * (sx > 0))), ring)
for k in ("wheel", "ring", "prop"):
    parts[k].hide_render = True
    parts[k].hide_set(True)
    parts[k].location = (5, 0, 0)   # keep the source parts out of the way

# preview
fl = bpy.data.meshes.new("Floor")
bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=3); bm.to_mesh(fl); bm.free()
fo = bpy.data.objects.new("Floor", fl); scn.collection.objects.link(fo)
fl.materials.append(mat("FloorMat", (0.85, 0.86, 0.88), 0, 0.85))
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); scn.collection.objects.link(cam)
cam.location = (0.62, -0.62, 0.42); cam.data.lens = 38
cam.rotation_euler = (Vector((0, 0, 0.1)) - cam.location).to_track_quat("-Z", "Y").to_euler()
scn.camera = cam
for loc, e in (((2, -2, 3), 700), ((-2, 1, 2), 300), ((0.5, 2, 1), 150)):
    L = bpy.data.objects.new("Light", bpy.data.lights.new("L", "AREA")); scn.collection.objects.link(L)
    L.data.energy = e; L.data.size = 2; L.location = loc
    L.rotation_euler = (Vector((0, 0, 0)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
w = bpy.data.worlds.new("W"); scn.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.8, 0.82, 0.85, 1)
w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.5
engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
scn.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engines else "BLENDER_EEVEE"
scn.view_settings.exposure = -0.6
scn.render.resolution_x, scn.render.resolution_y = 1400, 1000
scn.render.filepath = os.path.join(OUT, "robot_preview.png")
bpy.ops.render.render(write_still=True)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "wall_climber_body.blend"))
bpy.ops.object.select_all(action="DESELECT")
for o in scn.objects:
    if o == robot or o.parent == robot or (o.parent and o.parent.parent == robot):
        o.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "wall_climber_body.glb"), use_selection=True)
print("DONE")
