# Wall-climbing robot, body only (no electronics shown), from Wall Climbing Design.docx:
# star-spoke wheels, propeller hoops, light frame.
#
# Makes:
#   design/print/*.stl          printable parts in mm, already lying flat for the slicer
#   design/assets/*.blend/.glb  assembled model + renders
#   sim/meshes/*.stl            meshes for the MuJoCo sim (metres)
#   design/mass_properties.json weights + centre of mass, read by sim/climb.py
#   design/PARTS_REPORT.md      volumes, grams per infill, print settings
# and runs a clearance check: the hoops sweep -40..140 deg, nothing may be in the way.
#
# Run from the repo root: blender -b --factory-startup -P design/blender/build_robot.py
# Units: metres. Body frame: X forward, Y left, Z up, origin = centre of the axles.
import bpy, bmesh, math, os, json
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DESIGN = os.path.join(REPO, "design")
ASSETS = os.path.join(DESIGN, "assets")
PRINT = os.path.join(DESIGN, "print")
MESH = os.path.join(REPO, "sim", "meshes")
for p in (ASSETS, PRINT, MESH):
    os.makedirs(p, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene

# ---------------- key dimensions (keep sim/wall_climber.xml in sync) ----------------
WHEEL_R = 0.106          # printed rim; the inner-tube tire adds ~2 mm -> 108 mm rolling radius
TIRE = 0.002
WHEEL_W = 0.010
HUB_W = 0.014            # hub sticks out 4 mm on the inner side (spacer)
WHEEL_X, WHEEL_Y = 0.165, 0.175
RAIL_Y = 0.146           # centre of the 8x8 rails
BRACKET_Y = 0.150        # inner face of the corner brackets (= outer face of the rails)
RING_X, RING_Z = 0.140, 0.032
HOOP_R, HOOP_IN, HOOP_H = 0.127, 0.119, 0.010   # 10" embroidery hoop, 8 x 10 mm section
AXLE_DROP = 0.030        # roll axle sits 30 mm under the hoop so the prop spins in the hoop
PROP_R = 0.1143          # 9045 = 9 inch
PROP_Z = 0.010           # prop plane, in the hoop frame (motor + adapter = 32 mm above its plate)
GEAR_GAP = 0.024         # 24T module-1 gears: servo shaft 24 mm under the pivot
SERVO_DEG = {1: (-4, 140), -1: (-40, 140)}   # front hoop must not tip back past -4 deg (hits the battery)

M = {}
def mat(key, rgb, metal=0.0, rough=0.5):
    m = bpy.data.materials.new(key)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Metallic"].default_value = metal
    b.inputs["Roughness"].default_value = rough
    M[key] = m
mat("pla_green", (0.42, 0.75, 0.5), 0, 0.55)
mat("pla_dark", (0.12, 0.13, 0.14), 0, 0.5)
mat("wood", (0.74, 0.55, 0.33), 0, 0.6)
mat("alu", (0.78, 0.79, 0.81), 1, 0.3)
mat("carbon", (0.05, 0.05, 0.055), 0.3, 0.3)
mat("rubber", (0.06, 0.06, 0.06), 0, 0.85)
mat("prop", (0.22, 0.22, 0.24), 0, 0.4)


# ---------------- mesh helpers ----------------
def new_obj(name, bm, material):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(M[material])
    o = bpy.data.objects.new(name, me)
    scn.collection.objects.link(o)
    return o


def bx(name, x0, x1, y0, y1, z0, z1, material="pla_dark"):
    x0, x1 = sorted((x0, x1)); y0, y1 = sorted((y0, y1)); z0, z1 = sorted((z0, z1))
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    bmesh.ops.scale(bm, vec=(x1 - x0, y1 - y0, z1 - z0), verts=bm.verts)
    bmesh.ops.translate(bm, vec=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), verts=bm.verts)
    return new_obj(name, bm, material)


def cyl(name, r, c, z0, z1, material="pla_dark", axis="Z", seg=32):
    """cylinder of radius r along axis, centre c (2 coords across the axis), from z0 to z1 along it"""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=z1 - z0)
    bmesh.ops.translate(bm, vec=(0, 0, (z0 + z1) / 2), verts=bm.verts)
    if axis == "Y":   # c = (x, z)
        bmesh.ops.rotate(bm, verts=bm.verts, matrix=Matrix.Rotation(-math.pi / 2, 3, "X"))
        bmesh.ops.translate(bm, vec=(c[0], 0, c[1]), verts=bm.verts)
    elif axis == "X":  # c = (y, z)
        bmesh.ops.rotate(bm, verts=bm.verts, matrix=Matrix.Rotation(math.pi / 2, 3, "Y"))
        bmesh.ops.translate(bm, vec=(0, c[0], c[1]), verts=bm.verts)
    else:              # c = (x, y)
        bmesh.ops.translate(bm, vec=(c[0], c[1], 0), verts=bm.verts)
    return new_obj(name, bm, material)


def ring(name, r_out, r_in, z0, z1, material="pla_green", seg=96, c=(0, 0)):
    bm = bmesh.new()
    rings = []
    for z in (z0, z1):
        for r in (r_out, r_in):
            rings.append([bm.verts.new((c[0] + r * math.cos(2 * math.pi * i / seg), c[1] + r * math.sin(2 * math.pi * i / seg), z)) for i in range(seg)])
    bo, bi, to, ti = rings
    for i in range(seg):
        j = (i + 1) % seg
        bm.faces.new((to[i], to[j], ti[j], ti[i]))
        bm.faces.new((bo[j], bo[i], bi[i], bi[j]))
        bm.faces.new((bo[i], bo[j], to[j], to[i]))
        bm.faces.new((ti[i], ti[j], bi[j], bi[i]))
    return new_obj(name, bm, material)


def bar(name, p0, p1, w, z0, z1, material="pla_green"):
    """flat bar in the XY plane from p0 to p1, width w, from z0 to z1"""
    p0, p1 = Vector((*p0, 0)), Vector((*p1, 0))
    d = p1 - p0
    o = bx(name, -d.length / 2, d.length / 2, -w / 2, w / 2, z0, z1, material)
    o.data.transform(Matrix.Translation(((p0 + p1) / 2)) @ Matrix.Rotation(math.atan2(d.y, d.x), 4, "Z"))
    return o


def fuse(name, base, adds=(), subs=()):
    """boolean union then difference (exact solver) -> one watertight solid"""
    for ops, op in ((adds, "UNION"), (subs, "DIFFERENCE")):
        if not ops:
            continue
        col = bpy.data.collections.new(name + op)
        scn.collection.children.link(col)
        for o in ops:
            scn.collection.objects.unlink(o)
            col.objects.link(o)
        mod = base.modifiers.new(op, "BOOLEAN")
        mod.operation, mod.solver = op, "EXACT"
        mod.operand_type, mod.collection = "COLLECTION", col
        bpy.context.view_layer.objects.active = base
        bpy.ops.object.modifier_apply(modifier=mod.name)
        for o in list(col.objects):
            bpy.data.objects.remove(o)
        bpy.data.collections.remove(col)
    base.name = name
    return base


def stats(o, mw=None):
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.transform(mw or o.matrix_world)
    bad = sum(1 for e in bm.edges if not e.is_manifold)
    vol = bm.calc_volume(signed=False)
    area = sum(f.calc_area() for f in bm.faces)
    com = Vector()
    for f in bm.faces:
        com += f.calc_center_median() * f.calc_area()
    com = com / area if area else com
    lo = Vector([min(v.co[i] for v in bm.verts) for i in range(3)])
    hi = Vector([max(v.co[i] for v in bm.verts) for i in range(3)])
    bm.free()
    return {"bad_edges": bad, "vol": vol, "area": area, "com": com, "size": hi - lo}


# ---------------- printed parts (built lying flat, in the slicer's orientation) ----------------
def make_wheel():
    rim = ring("w_rim", WHEEL_R - 0.0025, WHEEL_R - 0.006, 0.0005, WHEEL_W - 0.0005)  # 3.5 mm rim
    lips = [ring("w_lip0", WHEEL_R, WHEEL_R - 0.003, 0, 0.0012), ring("w_lip1", WHEEL_R, WHEEL_R - 0.003, WHEEL_W - 0.0012, WHEEL_W)]
    hub = cyl("w_hub", 0.0105, (0, 0), 0, HUB_W, "pla_green")
    parts = lips + [hub]
    rr = WHEEL_R - 0.006
    outer = [(rr * math.cos(math.radians(90 + 72 * i)), rr * math.sin(math.radians(90 + 72 * i))) for i in range(5)]
    mid = [(0.0415 * math.cos(math.radians(126 + 72 * i)), 0.0415 * math.sin(math.radians(126 + 72 * i))) for i in range(5)]
    for i in range(5):
        parts.append(bar(f"w_spoke{i}", (0, 0), outer[i], 0.004, 0, 0.006))      # 5 spokes + the star from the doc
        parts.append(bar(f"w_star{i}", outer[i], outer[(i + 2) % 5], 0.003, 0, 0.005))
    # 624ZZ bearing seats (13 x 5 mm) both sides + 4.2 mm axle hole
    holes = [cyl("w_bore", 0.0021, (0, 0), -0.01, 0.03), cyl("w_seat0", 0.00655, (0, 0), -0.01, 0.005), cyl("w_seat1", 0.00655, (0, 0), HUB_W - 0.005, 0.03)]
    return fuse("wheel", rim, parts, holes)


def make_tire():
    return ring("tire", WHEEL_R + TIRE, WHEEL_R - 0.0005, 0.0012, WHEEL_W - 0.0012, "rubber")


def make_bracket():
    """corner bracket. Flat: x = robot X, y = robot Z, plate thickness along +z (outward)."""
    T = 0.004
    plate = bx("b_plate", RING_X - 0.017, WHEEL_X + 0.016, -0.020, 0.042, 0, T)
    adds = [
        cyl("b_axleBoss", 0.007, (WHEEL_X, 0), 0, 0.013),            # spacer to the wheel
        cyl("b_pivotBoss", 0.0065, (RING_X, RING_Z), 0, 0.007),
        bx("b_rib", RING_X - 0.017, WHEEL_X + 0.016, -0.020, -0.016, 0, 0.008),                          # stiff lip along the rail
    ]
    sx = RING_X + 0.0054   # MG90S body centre (shaft is 5.4 mm off-centre)
    subs = [
        cyl("b_axleHole", 0.0021, (WHEEL_X, 0), -0.01, 0.03),
        cyl("b_bearing", 0.004, (RING_X, RING_Z), -0.01, 0.03),                       # 693ZZ, 8 mm OD
        cyl("b_servoShaft", 0.0045, (RING_X, RING_Z - GEAR_GAP), -0.01, 0.03),
        cyl("b_servoTab0", 0.001, (sx - 0.0139, RING_Z - GEAR_GAP), -0.01, 0.03, seg=12),
        cyl("b_servoTab1", 0.001, (sx + 0.0139, RING_Z - GEAR_GAP), -0.01, 0.03, seg=12),
        cyl("b_rail0", 0.0017, (RING_X - 0.011, -0.012), -0.01, 0.03, seg=12),
        cyl("b_rail1", 0.0017, (WHEEL_X + 0.010, -0.012), -0.01, 0.03, seg=12),
        cyl("b_light0", 0.0085, (WHEEL_X, 0.027), -0.01, 0.03),                         # lightening holes
        cyl("b_light1", 0.004, (RING_X + 0.012, -0.008), -0.01, 0.03),
    ]
    return fuse("bracket", plate, adds, subs)


def make_gear(name="gear24", teeth=24, module=0.001, t=0.005, hole=0.0016):
    rp = teeth * module / 2
    base = cyl(name + "_b", rp - 0.6 * module, (0, 0), 0, t, "pla_dark", seg=48)
    adds = []
    for i in range(teeth):
        a = 2 * math.pi * i / teeth
        tooth = bx(f"{name}_t{i}", -0.55 * module, 0.55 * module, rp - 0.9 * module, rp + module, 0, t)
        tooth.data.transform(Matrix.Rotation(a, 4, "Z"))
        adds.append(tooth)
    adds.append(cyl(name + "_hubBoss", 0.006, (0, 0), 0, t + 0.002))
    return fuse(name, base, adds, [cyl(name + "_hole", hole, (0, 0), -0.01, 0.02, seg=16)])


def make_motor_mount():
    """flat plate (motor side down on the bed) + a bushing block that rides on the 6 mm roll axle"""
    plate = bx("mm_plate", -0.016, 0.016, -0.016, 0.016, 0, 0.003)
    block = bx("mm_block", -0.015, 0.015, -0.006, 0.006, 0.003, 0.013)
    subs = [cyl("mm_axle", 0.0032, (0, 0.008), -0.03, 0.03, axis="X"),
            cyl("mm_shaft", 0.004, (0, 0), -0.01, 0.006)]
    for a in range(4):   # 2212 pattern: 16 mm and 19 mm, M3
        r = (0.016 if a % 2 else 0.019) / 2
        subs.append(cyl(f"mm_h{a}", 0.0017, (r * math.cos(a * math.pi / 2 + math.pi / 4), r * math.sin(a * math.pi / 2 + math.pi / 4)), -0.01, 0.006, seg=12))
    return fuse("motor_mount", plate, [block], subs)


def make_hoop_clip():
    """clamps the hoop and drops the roll-axle bushing 40 mm below it. Flat: x = hoop radial, y = down."""
    jaw = bx("hc_jaw", -0.0065, 0.0065, -0.0067, 0.0067, 0, 0.010)
    leg = bx("hc_leg", -0.0045, 0.0045, 0.004, AXLE_DROP, 0, 0.010)
    end = cyl("hc_end", 0.0045, (0, AXLE_DROP), 0, 0.010)          # rounded end: no corner to hit the battery
    # slot runs along the hoop (part Z); axle hole runs radially (part X), 40 mm below the hoop
    subs = [bx("hc_slot", -0.0041, 0.0041, -0.0052, 0.0052, -0.01, 0.03),           # hoop section 8 x 10
            cyl("hc_axle", 0.0031, (AXLE_DROP, 0.005), -0.02, 0.02, axis="X")]
    return fuse("hoop_clip", jaw, [leg, end], subs)


def make_tray():
    """cradle: battery sits on the floor, velcro strap over it, ESP32 + MPU6050 foam-taped underneath.
    Two posts clamp the cross beam (zip ties)."""
    W, D, t = 0.042, 0.082, 0.0016
    floor_ = bx("t_floor", -W / 2, W / 2, -D / 2, D / 2, 0, t)
    adds = [bx("t_sideA", -W / 2, -W / 2 + t, -D / 2, D / 2, 0, 0.012), bx("t_sideB", W / 2 - t, W / 2, -D / 2, D / 2, 0, 0.012)]
    for sy in (1, -1):
        for sx in (1, -1):
            adds.append(bx(f"t_post{sy}{sx}", sx * 0.0042, sx * 0.0072, sy * 0.030 - 0.004, sy * 0.030 + 0.004, 0, 0.0316 + 0.012))
    subs = [bx("t_strap", -W, W, -0.006, 0.006, 0.004, 0.009),                    # velcro strap slot through the sides
            cyl("t_tie0", 0.0013, (0.030, 0.0316 + 0.006), -0.01, 0.01, axis="X"),
            cyl("t_tie1", 0.0013, (-0.030, 0.0316 + 0.006), -0.01, 0.01, axis="X"),
            bx("t_vent", -0.010, 0.010, -0.022, 0.022, -0.01, 0.01)]
    return fuse("tray", floor_, adds, subs)


def make_bumper_arm():
    arm = bx("ba_arm", 0, 0.101, -0.004, 0.004, 0, 0.004)            # tip sits 3 mm past the front tires
    adds = [bx("ba_pad", 0.081, 0.101, -0.010, 0.010, 0, 0.004)]
    subs = [cyl("ba_m3", 0.0017, (0.006, 0), -0.01, 0.02, seg=12), cyl("ba_sw0", 0.0011, (0.086, -0.0047), -0.01, 0.02, seg=12),
            cyl("ba_sw1", 0.0011, (0.086, 0.0047), -0.01, 0.02, seg=12)]
    return fuse("bumper_arm", arm, adds, subs)


def make_prop():
    bm = bmesh.new()
    for side in (1, -1):
        prev = None
        for i in range(13):
            r = 0.01 + (PROP_R - 0.01) * i / 12
            chord = 0.021 * (1 - 0.55 * i / 12)
            tw = math.radians(32 - 20 * i / 12)
            c, s = math.cos(tw) * chord / 2, math.sin(tw) * chord / 2
            row = [bm.verts.new((side * r, side * c, s)), bm.verts.new((side * r, -side * c, -s))]
            if prev:
                bm.faces.new((prev[0], prev[1], row[1], row[0]))
            prev = row
    o = new_obj("prop_blades", bm, "prop")
    o.modifiers.new("t", "SOLIDIFY").thickness = 0.003
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier="t")
    return fuse("prop", o, [cyl("prop_hub", 0.007, (0, 0), -0.006, 0.006, "prop")])


PRINTED = {
    # name: qty, walls, infill, why
    "wheel": (4, 2, 0.20, "4-6 mm thick spokes/rim are almost all wall anyway; 20 % gyroid in the hub."),
    "bracket": (4, 3, 0.40, "Carries the hoop thrust and the wheel axle; 3 walls = 1.2 mm around every hole."),
    "gear24": (4, 4, 1.00, "Small and loaded at the teeth: print solid."),
    "motor_mount": (2, 3, 0.50, "Motor vibration + full thrust go through it."),
    "hoop_clip": (4, 3, 0.50, "Holds the roll axle; thin, so mostly walls."),
    "tray": (1, 2, 0.15, "Only holds the battery; light."),
    "bumper_arm": (1, 2, 0.20, "Light knock only."),
}
parts = {
    "wheel": make_wheel(), "bracket": make_bracket(), "gear24": make_gear(), "motor_mount": make_motor_mount(),
    "hoop_clip": make_hoop_clip(), "tray": make_tray(), "bumper_arm": make_bumper_arm(),
}
tire, prop = make_tire(), make_prop()

# ---------------- bought parts (visual + sim) ----------------
hoop = ring("hoop", HOOP_R, HOOP_IN, -HOOP_H / 2, HOOP_H / 2, "wood")
rail = bx("rail", -0.19, 0.19, -0.004, 0.004, -0.004, 0.004, "alu")
beam = bx("beam", -0.004, 0.004, -RAIL_Y + 0.004, RAIL_Y - 0.004, -0.004, 0.004, "alu")
roll_axle = cyl("roll_axle", 0.003, (0, -AXLE_DROP), -0.126, 0.126, "carbon", axis="X")
pivot_pin = cyl("pivot_pin", 0.0015, (0, 0), HOOP_R - 0.002, BRACKET_Y + 0.009, "alu", axis="Y")


# ---------------- where everything goes (flat part -> robot) ----------------
def T(x=0, y=0, z=0):
    return Matrix.Translation((x, y, z))

RX90, RXm90 = Matrix.Rotation(math.pi / 2, 4, "X"), Matrix.Rotation(-math.pi / 2, 4, "X")
RX180, RY = Matrix.Rotation(math.pi, 4, "X"), (lambda deg: Matrix.Rotation(math.radians(deg), 4, "Y"))
MIR_Y, MIR_X = Matrix.Scale(-1, 4, (0, 1, 0)), Matrix.Scale(-1, 4, (1, 0, 0))

# chassis frame
br = T(0, -BRACKET_Y, 0) @ RX90          # right-front bracket: plate in XZ, bosses point out (-Y)
CHASSIS = [("bracket", br), ("bracket", MIR_X @ br), ("bracket", MIR_Y @ br), ("bracket", MIR_X @ MIR_Y @ br),
           ("gear24", T(RING_X, BRACKET_Y + 0.007, RING_Z - GEAR_GAP) @ RXm90),     # pitch servo gears, left side
           ("gear24", T(-RING_X, BRACKET_Y + 0.007, RING_Z - GEAR_GAP) @ RXm90),
           ("rail", T(0, RAIL_Y, -0.012)), ("rail", T(0, -RAIL_Y, -0.012)), ("beam", T(0, 0, -0.012)),
           ("tray", T(0, 0, -0.016 - 0.0316)),
           ("bumper_arm", T(WHEEL_X + 0.010, BRACKET_Y, 0.030) @ RX90)]
# hoop frame: origin on the pivot axis, hoop flat in its own XY plane, prop pushes along +Z
HOOPF = [("hoop", Matrix()), ("roll_axle", Matrix()), ("pivot_pin", Matrix()), ("pivot_pin", MIR_Y),
         ("motor_mount", T(0, 0, -AXLE_DROP + 0.008) @ RX180),
         ("hoop_clip", T((HOOP_IN + HOOP_R) / 2, -0.005, 0) @ RXm90),
         ("hoop_clip", T(-(HOOP_IN + HOOP_R) / 2, -0.005, 0) @ RXm90),
         ("gear24", T(0, BRACKET_Y + 0.007, 0) @ RXm90)]
PROPF = [("prop", T(0, 0, PROP_Z))]
WHEEL_L = [("wheel", RX90 @ T(0, 0, -WHEEL_W / 2)), ("tire", RX90 @ T(0, 0, -WHEEL_W / 2))]
WHEEL_Rt = [("wheel", RXm90 @ T(0, 0, -WHEEL_W / 2)), ("tire", RXm90 @ T(0, 0, -WHEEL_W / 2))]
WHEELS = {"FL": (WHEEL_X, WHEEL_Y, WHEEL_L), "RL": (-WHEEL_X, WHEEL_Y, WHEEL_L),
          "FR": (WHEEL_X, -WHEEL_Y, WHEEL_Rt), "RR": (-WHEEL_X, -WHEEL_Y, WHEEL_Rt)}
SRC = dict(parts, tire=tire, hoop=hoop, rail=rail, beam=beam, roll_axle=roll_axle, pivot_pin=pivot_pin, prop=prop)


def hoop_world(sx, deg):
    return T(sx * RING_X, 0, RING_Z) @ RY(deg)


# ---------------- 1. check every printed part is a clean solid ----------------
report = {}
for k, o in parts.items():
    st = stats(o, Matrix())
    report[k] = st
    print(f"PART {k:12s} bad_edges={st['bad_edges']} vol={st['vol'] * 1e6:7.2f} cm3 size_mm={tuple(round(v * 1000) for v in st['size'])}")

# ---------------- 2. clearance: sweep both hoops through the servo range ----------------
KEEP_CHASSIS = [  # hardware that isn't drawn but takes space (chassis frame)
    ("pitch servo F", (RING_X - 0.006, RING_X + 0.0168), (0.1275, 0.150), (RING_Z - GEAR_GAP - 0.0061, RING_Z - GEAR_GAP + 0.0061)),
    ("pitch servo R", (-RING_X - 0.0168, -RING_X + 0.006), (0.1275, 0.150), (RING_Z - GEAR_GAP - 0.0061, RING_Z - GEAR_GAP + 0.0061)),
    ("battery", (-0.0185, 0.0185), (-0.039, 0.039), (-0.0459, -0.0189)),
    ("ESP32 + IMU", (-0.014, 0.014), (-0.026, 0.026), (-0.0575, -0.0485)),
    ("ESC front", (0.0075, 0.0525), (-0.158, -0.134), (-0.008, 0.000)),
    ("ESC rear", (-0.0525, -0.0075), (-0.158, -0.134), (-0.008, 0.000)),
    ("buck", (-0.0255, 0.0255), (0.133, 0.159), (-0.008, 0.006)),
]
KEEP_HOOP = [  # moves with the hoop
    ("motor 2212", "cyl", 0.0145, (-AXLE_DROP + 0.011, 0.003)),
    ("roll servo", "box", (0.094, 0.117), (-0.0061, 0.0061), (-0.047, -0.024)),
]


def bvh_of(items, extra=Matrix()):
    bm = bmesh.new()
    for key, m in items:
        tmp = bmesh.new()
        tmp.from_mesh(SRC[key].data)
        tmp.transform(extra @ m)
        me = bpy.data.meshes.new("tmp"); tmp.to_mesh(me); tmp.free()
        bm.from_mesh(me); bpy.data.meshes.remove(me)
    return bm


def keep_mesh(boxes, cyls=(), extra=Matrix()):
    objs = []
    for b in boxes:
        objs.append(bx("keep", b[1][0], b[1][1], b[2][0], b[2][1], b[3][0], b[3][1]))
    for c in cyls:
        objs.append(cyl("keepc", c[2], (0, 0), c[3][0], c[3][1]))
    bm = bmesh.new()
    for o in objs:
        tmp = bmesh.new(); tmp.from_mesh(o.data); tmp.transform(extra)
        me = bpy.data.meshes.new("tmp"); tmp.to_mesh(me); tmp.free(); bm.from_mesh(me); bpy.data.meshes.remove(me)
        bpy.data.objects.remove(o)
    return bm


# pins go through the brackets and the gears mesh on purpose: leave them out of the check
chassis_bm = bvh_of([i for i in CHASSIS if i[0] != "gear24"])
for side, (x, y, items) in WHEELS.items():
    w = bvh_of(items, T(x, y, 0)); me = bpy.data.meshes.new("t"); w.to_mesh(me); w.free(); chassis_bm.from_mesh(me); bpy.data.meshes.remove(me)
k = keep_mesh(KEEP_CHASSIS); me = bpy.data.meshes.new("t"); k.to_mesh(me); k.free(); chassis_bm.from_mesh(me); bpy.data.meshes.remove(me)
chassis_tree = BVHTree.FromBMesh(chassis_bm)
diag_trees = []
for key, m in CHASSIS:
    if key != "gear24":
        b = bvh_of([(key, m)]); diag_trees.append((key, BVHTree.FromBMesh(b))); b.free()
for kname, *box_ in KEEP_CHASSIS:
    b = keep_mesh([(kname, *box_)]); diag_trees.append((kname, BVHTree.FromBMesh(b))); b.free()
for side, (x, y, items) in WHEELS.items():
    b = bvh_of(items, T(x, y, 0)); diag_trees.append(("wheel " + side, BVHTree.FromBMesh(b))); b.free()
moving = [i for i in HOOPF if i[0] not in ("gear24", "pivot_pin")] + [("prop_disc", None)]
disc = cyl("prop_disc", PROP_R, (0, 0), PROP_Z - 0.004, PROP_Z + 0.004, seg=48)
SRC["prop_disc"] = disc
moving = [(k_, m if m is not None else Matrix()) for k_, m in moving]
clashes = []
for sx in (1, -1):
    for deg in range(SERVO_DEG[sx][0], SERVO_DEG[sx][1] + 1, 2):
        hw = hoop_world(sx, deg)
        hb = bvh_of(moving, hw)
        # roll servo sits on the OUTER side of each hoop (front: +x, rear: -x), away from the battery
        kb = keep_mesh([("roll servo", (sx * 0.094, sx * 0.117), (-0.0061, 0.0061), (-AXLE_DROP - 0.007, -AXLE_DROP + 0.016))],
                       [("motor", "cyl", 0.0145, (-AXLE_DROP + 0.008, PROP_Z - 0.004))], hw)
        me = bpy.data.meshes.new("t"); kb.to_mesh(me); kb.free(); hb.from_mesh(me); bpy.data.meshes.remove(me)
        ht = BVHTree.FromBMesh(hb)
        if chassis_tree.overlap(ht):
            what = [n for n, t in diag_trees if t.overlap(ht)]
            movers = []
            for key, m in moving:
                b = bvh_of([(key, m)], hw); mt = BVHTree.FromBMesh(b); b.free()
                if chassis_tree.overlap(mt):
                    movers.append(key)
            if not movers:
                movers = ["motor/roll-servo space"]
            clashes.append(("front" if sx > 0 else "rear", deg, what, movers))
        hb.free()
bpy.data.objects.remove(disc)
if clashes:
    print("CLEARANCE FAIL", clashes[:12], "total", len(clashes))
else:
    print(f"CLEARANCE OK: hoops, motors, props clear the frame, wheels and electronics (front {SERVO_DEG[1]}, rear {SERVO_DEG[-1]} deg)")

# ---------------- 3. printable STLs (mm, lying flat) ----------------
for k, o in parts.items():
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.ops.wm.stl_export(filepath=os.path.join(PRINT, k + ".stl"), export_selected_objects=True, global_scale=1000.0)

# ---------------- 4. sim meshes (metres) ----------------
def export_group(name, items, extra=Matrix()):
    bm = bvh_of(items, extra)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); scn.collection.objects.link(o)
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True)
    bpy.ops.wm.stl_export(filepath=os.path.join(MESH, name + ".stl"), export_selected_objects=True)
    bpy.data.objects.remove(o)

export_group("chassis", CHASSIS)
export_group("ring", HOOPF)
export_group("prop", [("prop", Matrix())])
export_group("wheel_l", WHEEL_L)
export_group("wheel_r", WHEEL_Rt)

# ---------------- 5. weight ----------------
PLA = 1.24          # g/cm3 (PLA+); PETG is 1.27
LINE = 0.00042      # 0.4 nozzle line width, m


def printed_grams(st, walls, infill):
    vol = st["vol"] * 1e6                                     # cm3
    shell = min(vol, st["area"] * walls * LINE * 1e6)         # walls + top/bottom skin, approx
    return PLA * (shell + infill * (vol - shell)), shell, vol


rows, printed_total, filament_total, minutes_total = [], 0, 0, 0
for k, (qty, walls, infill, why) in PRINTED.items():
    st = report[k]
    g, shell, vol = printed_grams(st, walls, infill)
    alt = {f"{int(i * 100)}%": round(printed_grams(st, walls, i)[0], 1) for i in (0.15, 0.25, 0.40, 1.0)}
    minutes = (g / PLA) * 1000 / 5.0 / 60 * 1.3               # ~5 mm3/s on an Ender-3 class printer, +30 % travel
    rows.append(dict(part=k, qty=qty, walls=walls, infill=infill, grams_each=round(g, 1), grams_total=round(g * qty, 1),
                     solid_cm3=round(vol, 2), size_mm=[round(v * 1000) for v in st["size"]], at_infill=alt,
                     print_min_each=round(minutes), why=why, watertight=st["bad_edges"] == 0))
    printed_total += g * qty
    filament_total += g * qty * 1.05                          # brim/purge
    minutes_total += minutes * qty
grams = {r["part"]: r["grams_each"] for r in rows}

# bought parts: typical datasheet / measured-in-shop weights (grams). Weigh yours and edit.
HW_CHASSIS = [  # (name, grams, position in the chassis frame)
    ("rails 8x8x0.8 alu, 2 x 380 mm", 47, (0, 0, -0.012)), ("cross beam 8x8x0.8 alu, 284 mm", 18, (0, 0, -0.012)),
    ("MG90S pitch servo F", 13.4, (RING_X + 0.005, 0.139, RING_Z - GEAR_GAP)), ("MG90S pitch servo R", 13.4, (-RING_X - 0.005, 0.139, RING_Z - GEAR_GAP)),
    ("30A ESC F", 30, (0.03, -0.145, -0.003)), ("30A ESC R", 30, (-0.03, -0.145, -0.003)), ("XL4015 buck", 18, (0, 0.145, 0)),
    ("3S 1500 mAh LiPo", 125, (0, 0, -0.0324)), ("ESP32 DevKit", 10, (0, 0, -0.053)), ("MPU6050", 3, (0, 0.015, -0.053)),
    ("switch + XT60s", 12, (-0.17, -0.145, 0)), ("wiring", 25, (0, 0, -0.01)), ("limit switch", 2, (WHEEL_X + 0.1, 0.147, 0.03)),
    ("M4x40 axle bolts + lock nuts x4", 22, (0, 0, 0)), ("693ZZ bearings x4", 3, (0, 0, RING_Z)), ("M3/M2 screws, nuts", 20, (0, 0, -0.01)),
    ("zip ties, velcro", 8, (0, 0, -0.03)),
]
HW_HOOP = [  # per hoop, hoop frame
    ("10in wooden embroidery hoop (inner ring)", 38, (0, 0, 0)), ("carbon tube 6x4, 252 mm", 6, (0, 0, -AXLE_DROP)),
    ("A2212 1400KV motor + adapter", 50, (0, 0, -AXLE_DROP + 0.024)), ("9045 prop", 12, (0, 0, PROP_Z)),
    ("MG90S roll servo (outer side; rear hoop mirrors X)", 13.4, (0.105, 0, -AXLE_DROP + 0.004)), ("M3 pivot pins x2", 5, (0, 0, 0)), ("motor screws", 2, (0, 0, -0.03)),
]
HW_WHEEL = [("inner-tube tire strip", 9, (0, 0, 0)), ("624ZZ bearings x2", 5.8, (0, 0, 0))]


def group(items_printed, hw):
    m, mom = 0.0, Vector()
    for key, mw in items_printed:
        g = grams.get(key)
        if g is None:
            continue
        c = mw @ report[key]["com"]
        m += g; mom += c * g
    for _, g, p in hw:
        m += g; mom += Vector(p) * g
    return m, (mom / m if m else Vector())

g_ch, c_ch = group(CHASSIS, HW_CHASSIS)
g_hoopL, c_hoop = group(HOOPF, HW_HOOP)                       # left hoop carries the pivot gear
g_hoopR, _ = group([i for i in HOOPF if i[0] != "gear24"], HW_HOOP)
g_wh, c_wh = group(WHEEL_L, HW_WHEEL)
total = g_ch + g_hoopL + g_hoopR + 4 * g_wh
# whole-robot centre of mass with the hoops flat
mom = c_ch * g_ch + (Vector((RING_X, 0, RING_Z)) + c_hoop) * g_hoopL + (Vector((-RING_X, 0, RING_Z)) + c_hoop) * g_hoopR
mom += sum((Vector((x, y, 0)) * g_wh for x, y, _ in WHEELS.values()), Vector())
cg = mom / total
h_wall = cg.z + WHEEL_R + TIRE                               # distance from the wall when climbing
need = math.sqrt(1 + (2 * h_wall / (2 * WHEEL_X)) ** 2)
mp = {
    "chassis": {"mass_kg": g_ch / 1000, "com_m": list(c_ch)},
    "hoop": {"mass_kg": (g_hoopL + g_hoopR) / 2000, "com_m": list(c_hoop)},
    "wheel": {"mass_kg": g_wh / 1000},
    "total_g": round(total, 1), "cg_m": [round(v, 4) for v in cg], "cg_height_m": round(h_wall, 4),
    "hold_thrust_factor": round(need, 3), "printed": rows,
    "printed_total_g": round(printed_total, 1), "filament_g": round(filament_total), "print_hours": round(minutes_total / 60, 1),
}
with open(os.path.join(DESIGN, "mass_properties.json"), "w") as f:
    json.dump(mp, f, indent=1)

# ---------------- 6. human-readable report ----------------
L = ["# Parts report (generated by design/blender/build_robot.py, don't edit)", "",
     f"Total robot: {total:.0f} g (limit 1050 g). Centre of mass {h_wall * 1000:.0f} mm off the surface "
     f"-> hanging on a wall needs thrust = {need:.2f} x weight = {total * need:.0f} gf.", "",
     "## Printed parts (PLA+, 0.4 mm nozzle, 0.2 mm layers)", "",
     "| Part | Qty | Size mm | Walls | Infill | g each | g total | ~print time each | Why |", "|---|---|---|---|---|---|---|---|---|"]
for r in rows:
    L.append(f"| `{r['part']}.stl` | {r['qty']} | {'x'.join(map(str, r['size_mm']))} | {r['walls']} | {int(r['infill'] * 100)}% gyroid | "
             f"{r['grams_each']} | {r['grams_total']} | {r['print_min_each'] // 60}h{r['print_min_each'] % 60:02d} | {r['why']} |")
L += ["", f"Printed total {printed_total:.0f} g, filament with brims ~{filament_total:.0f} g, about {minutes_total / 60:.0f} h of printing.",
      "", "Same parts at other infills (g each):", "", "| Part | 15% | 25% | 40% | 100% |", "|---|---|---|---|---|"]
for r in rows:
    a = r["at_infill"]
    L.append(f"| {r['part']} | {a['15%']} | {a['25%']} | {a['40%']} | {a['100%']} |")
L += ["", "## Weight by group", "", "| Group | g |", "|---|---|",
      f"| Chassis (brackets, rails, tray, electronics, battery) | {g_ch:.0f} |",
      f"| Hoop + motor + prop, left | {g_hoopL:.0f} |", f"| Hoop + motor + prop, right | {g_hoopR:.0f} |",
      f"| Wheel + tire + bearings (x4) | {4 * g_wh:.0f} |", f"| Total | {total:.0f} |", "",
      "Bought-part weights are typical values; weigh yours and edit `HW_*` in the script.", ""]
open(os.path.join(DESIGN, "PARTS_REPORT.md"), "w", encoding="utf8").write("\n".join(L))
print(f"WEIGHT total={total:.0f} g printed={printed_total:.0f} g cg_h={h_wall * 1000:.0f} mm hold={total * need:.0f} gf print_h={minutes_total / 60:.1f}")

# ---------------- 7. assembled scene + renders ----------------
for o in list(scn.objects):
    o.hide_render = True
    o.hide_set(True)


def place(key, mw, parent=None, name=None):
    o = SRC[key].copy()
    o.name = name or key
    o.hide_render = False
    o.hide_set(False)
    scn.collection.objects.link(o)
    o.matrix_world = mw
    if parent:
        o.parent = parent
        o.matrix_parent_inverse = parent.matrix_world.inverted()
    return o

root = bpy.data.objects.new("WallClimber", None)
scn.collection.objects.link(root)
lift = T(0, 0, WHEEL_R + TIRE)
for key, m in CHASSIS:
    place(key, lift @ m, root)
for side, (x, y, items) in WHEELS.items():
    for key, m in items:
        place(key, lift @ T(x, y, 0) @ m, root, f"{key}_{side}")
for sx, deg in ((1, 25), (-1, 25)):
    for key, m in HOOPF + PROPF:
        if key == "gear24" and False:
            continue
        place(key, lift @ hoop_world(sx, deg) @ m, root, f"{key}_{'F' if sx > 0 else 'R'}")

fl = bpy.data.meshes.new("Floor")
bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=3); bm.to_mesh(fl); bm.free()
fo = bpy.data.objects.new("Floor", fl); scn.collection.objects.link(fo)
mat("floor", (0.86, 0.87, 0.88), 0, 0.9); fl.materials.append(M["floor"])
for loc, e in (((2, -2, 3), 650), ((-2, 1, 2), 280), ((0.5, 2, 1), 140)):
    Lt = bpy.data.objects.new("Light", bpy.data.lights.new("L", "AREA")); scn.collection.objects.link(Lt)
    Lt.data.energy = e; Lt.data.size = 2; Lt.location = loc
    Lt.rotation_euler = (Vector((0, 0, 0)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
w = bpy.data.worlds.new("W"); scn.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.8, 0.82, 0.85, 1)
w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.5
engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
scn.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engines else "BLENDER_EEVEE"
scn.view_settings.exposure = -0.6
scn.render.resolution_x, scn.render.resolution_y = 1400, 1000
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); scn.collection.objects.link(cam); scn.camera = cam
for fname, loc, target, lens in (("robot_preview.png", (0.6, -0.62, 0.42), (0, 0, 0.1), 38),
                                  ("robot_side.png", (0.02, -1.1, 0.12), (0, 0, 0.11), 45),
                                  ("robot_corner.png", (0.30, -0.30, 0.16), (0.145, -0.15, 0.13), 50)):
    cam.location = loc; cam.data.lens = lens
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    scn.render.filepath = os.path.join(ASSETS, fname)
    bpy.ops.render.render(write_still=True)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ASSETS, "wall_climber_body.blend"))
bpy.ops.object.select_all(action="DESELECT")
for o in root.children:
    o.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.join(ASSETS, "wall_climber_body.glb"), use_selection=True)
print("DONE")
