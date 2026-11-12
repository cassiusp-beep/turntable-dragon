# -*- coding: utf-8 -*-
"""
Dragon Cam Automaton  -  parametric Rhino model (units: mm)
"Cognitive offloading in educational contexts" - the mechanism is the lesson,
so the front panel is clear acrylic and the linkages stay visible.

HOW TO RUN
  Rhino 7/8:  command  RunPythonScript  ->  pick this file
  (or ScriptEditor -> open -> Run)
Change ANGLE and re-run to see the machine in another pose
(the script wipes and rebuilds everything on the "Automaton" layers).

MECHANISM (left -> right, dragon faces +X)
  DC gearmotor (outside left wall) -> 8 mm dowel camshaft
  R1, R2, R3, R4 : eccentric cams 90 deg apart -> push rods -> body segments
                   = travelling wave along the body (the "wavy" line in the sketch)
  W              : eccentric cam under a FIXED shoulder block -> wing rod ->
                   crossbar + 2 links -> wings hinged on the shoulder (flap)
  H              : snail cam -> head dowel (slow rise, sudden drop = head "snap")
  Support        : A-frame bearing in the middle of the shaft
  Guide bar + top plate : two holes per rod keep every rod vertical
"""
import rhinoscriptsyntax as rs
import math

# ------------------------------------------------------------------ PARAMETERS
ANGLE = 0.0           # shaft angle (deg). Try 0, 90, 180, 270.
DRAGON_MODE = "flexi" # "flexi": imported MakerWorld flexi dragon on printed cradles | "procedural": scripted dragon
FLEXI_LAYER = "FlexiDragon_ref"   # layer holding the imported STL (import it once, untouched)
CRADLE_T = 3.0        # cradle pad thickness under a flexi segment
WINGS = True          # wing linkage (forced off in flexi mode)
DRAGON_SCALE = 1.25   # flexi dragon print scale (its print-in-place clearances scale too)
HEAD_X_TARGET = 268.0 # flexi: head rod lands near here (snail cam must stay inside the right wall)

BOX_L, BOX_D, BOX_H = 300.0, 120.0, 130.0   # outer box X, Y, Z
T = 6.0               # plywood thickness (walls / floor / top / cams)
SHAFT_Z = 50.0        # camshaft axis height
SHAFT_Y = BOX_D / 2.0 # camshaft axis Y (all rods sit on this line)
SHAFT_R = 4.0         # 8 mm dowel
ROD_R = 3.0           # 6 mm dowel push rods
HOLE_R = 3.4          # guide holes: ROD_R + FIT_ROD_GUIDE (set below too)
GUIDE_Z = 95.0        # bottom of the internal guide bar
TOP_Z = BOX_H - T     # bottom of the top plate

# body cams: (name, x-centre, eccentricity, disc radius, phase deg)
BODY_CAMS = [
    ("R1_tail",   45.0, 7.0, 20.0,   0.0),
    ("R2_back",   78.0, 7.0, 20.0, 270.0),
    ("R3_belly", 165.0, 7.0, 20.0, 180.0),
    ("R4_neck",  205.0, 7.0, 20.0,  90.0),
]   # +/-7 mm wave: simulated worst hinge bend 25 deg over a full turn
BODY_ROD_TOP_MID = 193.0      # rod-top height at mid stroke

# wing cam + linkage
WING_X, WING_E, WING_R, WING_PHASE = 120.0, 12.0, 22.0, 45.0
WING_ROD_TOP_MID = 222.0      # crossbar height at mid stroke
HINGE_Y = 18.0                # hinge pins at SHAFT_Y +/- HINGE_Y
HINGE_Z = 203.0               # hinge-pin height (ears on the chest)
CROSSBAR_PIN = 6.0            # link pins on crossbar at +/- this (Y)
WING_LEVER = 20.0             # link attaches this far out along the wing
WING_REST_DEG = 20.0          # wing angle at mid stroke (dihedral)

# head snail cam
HEAD_X, SNAIL_T = 252.0, 8.0
SNAIL_RMIN, SNAIL_RMAX = 18.0, 38.0     # 20 mm of head lift
HEAD_ROD_TOP_LOW = 191.0

SUPPORT_X = 140.0

# 3D-printing
CLEAR = 0.3           # (legacy procedural mode)
# ---- FITS: radial clearances in mm, for FDM PLA/PETG, 0.4 mm nozzle. Print FitTest coupons first and nudge these.
FIT_SHAFT_CAM = 0.20   # cam bore on 8 mm steel D-shaft, locked by M3 grub on the flat (slip fit)
FIT_SHAFT_RUN = 0.35   # shaft turning in end walls + A-frame (running fit)
FIT_ROD_GUIDE = 0.40   # 6 mm dowel sliding through guide holes (dowels vary +/-0.1)
FIT_ROD_SOCKET = 0.40  # rod top in a cradle socket (cradle rocks on the cross pin)
FIT_GLUE = 0.15        # dowel posts glued into the mount / guide bar
FIT_PIN_FREE = 0.25    # pins that must turn: wing knuckle, link wire, cradle cross-pin slot (holes print undersize)
FIT_PIN_PRESS = 0.10   # pins pressed into fixed parts: wing ears (0.05 + Bambu's ~0.1-0.2 mm hole shrink risked cracking)
FIT_PANEL_PIN = 0.10   # 3 mm alignment pins across split-panel seams (+ glue)
FIT_SEG = 0.30         # gap between a dragon segment's base and the cradle side lips, each side
SHAFT_FLAT = 3.5       # D-shaft: flat 0.5 mm deep on an 8 mm rod (centre -> flat)
M3_PILOT_R = 1.3       # M3 self-tapping pilot: screw OD - 0.4 = 2.6 mm
# Slicer: leave Bambu Studio 'X-Y hole compensation' at 0 - the clearances above already allow for hole shrink.
BED = 250.0           # print-bed limit: panels longer than this get split in half
HUB_R, HUB_L = 9.0, 7.0   # cam hub (M3 set-screw goes radially through it)

if DRAGON_MODE == "flexi":
    # lower, bigger dragon: rods spread to carry the 1.25x body; cradles stay >=10 mm above the top plate
    BODY_ROD_TOP_MID = 161.0
    HEAD_ROD_TOP_LOW = 156.0
    BODY_CAMS = [(nm, x, e, r, ph) for (nm, x, e, r, ph), x in
                 zip(BODY_CAMS, (34.0, 70.0, 175.0, 225.0))]
    WING_E, WING_ROD_TOP_MID = 6.0, 143.0   # wing crossbar runs under the chest mount (sweep: clears plate + mount)

# ------------------------------------------------------------------ HELPERS
def P(x, y, z):
    return (float(x), float(y), float(z))

def box(x0, y0, z0, x1, y1, z1):
    pts = [P(x0, y0, z0), P(x1, y0, z0), P(x1, y1, z0), P(x0, y1, z0),
           P(x0, y0, z1), P(x1, y0, z1), P(x1, y1, z1), P(x0, y1, z1)]
    return rs.AddBox(pts)

def cyl(p0, p1, r):
    return rs.AddCylinder(p0, p1, r, True)

def ellipsoid(c, rx, ry, rz):
    s = rs.AddSphere(c, 1.0)
    rs.ScaleObject(s, c, (rx, ry, rz))
    return s

def prism(profile_pts, vec):
    """closed polyline (list of 3D pts) extruded along vec, capped"""
    pts = list(profile_pts) + [profile_pts[0]]
    crv = rs.AddPolyline(pts)
    srf = rs.ExtrudeCurveStraight(crv, (0, 0, 0), vec)
    rs.CapPlanarHoles(srf)
    rs.DeleteObject(crv)
    return srf

def tag(obj, name, color=None):
    if obj:
        rs.ObjectName(obj, name)
        if color:
            rs.ObjectColor(obj, color)
    return obj

def layer(name, color):
    full = "Automaton::" + name
    if not rs.IsLayer(full):
        rs.AddLayer(name, color, parent="Automaton")
    rs.CurrentLayer(full)

def eccentric(e, phase):
    """cam disc centre (y, z) for the current ANGLE"""
    w = math.radians(ANGLE + phase)
    return SHAFT_Y + e * math.sin(w), SHAFT_Z + e * math.cos(w)

def snail_r(t):
    t = t % 360.0
    if t <= 300.0:
        return SNAIL_RMIN + (SNAIL_RMAX - SNAIL_RMIN) * t / 300.0
    return SNAIL_RMAX - (SNAIL_RMAX - SNAIL_RMIN) * (t - 300.0) / 60.0

def snail_h(a):
    """height of a FLAT follower above the shaft axis at shaft angle a: the follower rests on the cam's highest
    point, which on a spiral is not straight above the axis (support function of the mirrored profile)"""
    return max(snail_r(-t) * math.cos(math.radians(t + a)) for t in [i * 0.5 for i in range(720)])

SNAIL_HMIN = min(snail_h(a) for a in range(0, 360, 2))

def tear_cut(obj, p0, p1, r, up):
    """cut a horizontal hole as a teardrop (45 deg roof toward 'up' = print-up direction) so it doesn't sag shut"""
    ax = rs.VectorUnitize(rs.VectorCreate(p1, p0))
    side = rs.VectorUnitize(rs.VectorCrossProduct(ax, up))
    upv = rs.VectorUnitize(rs.VectorCrossProduct(side, ax))
    k = r * 0.7071

    def q(sx, uy):
        return P(p0[0] + side[0] * sx + upv[0] * uy, p0[1] + side[1] * sx + upv[1] * uy, p0[2] + side[2] * sx + upv[2] * uy)
    roof = prism([q(-k, k), q(0, 0), q(k, k), q(0, r * 1.4142)], rs.VectorCreate(p1, p0))
    for cutter in (cyl(p0, p1, r), roof):
        res = rs.BooleanDifference([obj], [cutter], True)
        obj = res[0] if res else obj
    return obj


def push_rod(name, x, foot_z, length, color):
    """foot disc + glue collar (socket for the dowel) + rod; returns rod-top z"""
    foot = cyl(P(x, SHAFT_Y, foot_z), P(x, SHAFT_Y, foot_z + 3), 9.0)
    u = rs.BooleanUnion([foot, cyl(P(x, SHAFT_Y, foot_z + 2.9), P(x, SHAFT_Y, foot_z + 9), 5.0)], True)
    foot = u[0] if u else foot
    res = rs.BooleanDifference([foot], [cyl(P(x, SHAFT_Y, foot_z + 3), P(x, SHAFT_Y, foot_z + 10), ROD_R + FIT_GLUE)], True)
    tag(res[0] if res else foot, name + "_foot (glue socket)", color)
    top = foot_z + 3 + length
    tag(cyl(P(x, SHAFT_Y, foot_z + 3), P(x, SHAFT_Y, top), ROD_R), name + "_rod", color)
    return top


# ------------------------------------------------------------------ WING "A" BUILDER (refined bat wing, built flat)
# local coords: u along the body (+u toward head), v outward from the hinge, membrane on z = 0..WA_MT
WA_MT = 1.4
WA_KZ = 3.3   # knuckle radius = hinge-axis height above the print bed


def _wp(x, y, z=0.0):
    return (float(x), float(y), float(z))


def _wframe(pt, tan):
    t = rs.VectorUnitize(tan)
    ref = (0, 0, 1) if abs(t[2]) < 0.95 else (1, 0, 0)
    xa = rs.VectorUnitize(rs.VectorCrossProduct(ref, t))
    return rs.PlaneFromFrame(pt, xa, rs.VectorCrossProduct(t, xa))


def _wtaper(p0, p1, r0, r1):
    d = rs.VectorCreate(p1, p0)
    crvs = [rs.AddCircle(_wframe(p0, d), r0), rs.AddCircle(_wframe(p1, d), r1)]
    lo = rs.AddLoftSrf(crvs)
    rs.DeleteObjects(crvs)
    if not lo:
        return None
    rs.CapPlanarHoles(lo[0])
    return lo[0]


def _wchain(pts, radii, z0=None):
    """tapered bone through pts, resting ON the membrane (centre at MT + 0.65 r, so it never dips below the bed)"""
    out = []
    zr = lambda r: WA_MT + 0.65 * r
    for i in range(len(pts) - 1):
        a = _wp(pts[i][0], pts[i][1], zr(radii[i]))
        b = _wp(pts[i + 1][0], pts[i + 1][1], zr(radii[i + 1]))
        out.append(_wtaper(a, b, radii[i], radii[i + 1]))
        if 0 < i + 1 < len(pts) - 1:
            out.append(rs.AddSphere(b, radii[i + 1] * 1.15))
    return out


def _wleaf(base, tip, width, thick, z):
    c = rs.AddCone(_wp(base[0], base[1], z), _wp(tip[0], tip[1], z), width)
    ang = math.degrees(math.atan2(tip[1] - base[1], tip[0] - base[0]))
    c = rs.RotateObject(c, _wp(base[0], base[1], z), -ang, (0, 0, 1)) or c
    rs.ScaleObject(c, _wp(base[0], base[1], z), (1, 1, thick / (2.0 * width)))
    c = rs.RotateObject(c, _wp(base[0], base[1], z), ang, (0, 0, 1)) or c
    return c


def build_wing_A(lever):
    """returns (structural membrane+knuckle+lug, [detail bodies]) in flat local coords"""
    MT = WA_MT
    S, E, WR = (0, 3), (13, 50), (4, 96)
    F = [(-6, 152), (-38, 134), (-60, 98), (-62, 54)]
    KN = [(-2, 120), (-20, 118), (-33, 92), (-36, 62)]
    outline = [
        [(2.5, 2.4), (2.5, 8), (12, 30), E, (10, 75), WR],
        [WR, (2, 125), F[0]],
        [F[0], (-17, 128), (-26, 125), F[1]],
        [F[1], (-41, 112), (-46, 104), F[2]],
        [F[2], (-48, 80), (-51, 70), F[3]],
        [F[3], (-46, 36), (-36, 18), (-26, 3), (-2.5, 8)],
        [(-2.5, 8), (-2.5, 2.4)], [(-2.5, 2.4), (2.5, 2.4)],
    ]
    crvs = []
    for seg in outline:
        if len(seg) == 2:
            crvs.append(rs.AddLine(_wp(*seg[0]), _wp(*seg[1])))
        else:
            crvs.append(rs.AddInterpCurve([_wp(*q) for q in seg], 3 if len(seg) > 3 else 2))
    loop = rs.JoinCurves(crvs, True)
    memb = rs.ExtrudeCurveStraight(loop[0], (0, 0, 0), (0, 0, MT))
    rs.CapPlanarHoles(memb)
    rs.DeleteObjects(loop)
    zc = WA_KZ   # hinge axis height: knuckle bottom flush with the membrane underside -> prints flat, no supports
    for extra in (rs.AddCylinder(_wp(-2.6, 0, zc), _wp(2.6, 0, zc), WA_KZ),                # hinge knuckle
                  rs.AddCylinder(_wp(-3, lever, zc), _wp(3, lever, zc), 2.4)):            # link lug, top side, in hinge plane
        r = rs.BooleanUnion([memb, extra], True)
        memb = r[0] if r else memb
    # slot through the membrane beside the lug: the link wire comes up from below and hooks into the lug hole
    slot = rs.AddBox([_wp(3.2, lever - 2, -1), _wp(6.5, lever - 2, -1), _wp(6.5, lever + 2, -1), _wp(3.2, lever + 2, -1),
                      _wp(3.2, lever - 2, MT + 1), _wp(6.5, lever - 2, MT + 1), _wp(6.5, lever + 2, MT + 1),
                      _wp(3.2, lever + 2, MT + 1)])
    r = rs.BooleanDifference([memb], [slot], True)
    memb = r[0] if r else memb
    zb = MT + 0.4
    det = _wchain([S, E, WR], [3.0, 2.4, 2.0], zb)
    for kn, tip in zip(KN, F):
        det += _wchain([WR, kn, tip], [1.7, 1.3, 0.5], zb)
        d = rs.VectorUnitize((tip[0] - kn[0], tip[1] - kn[1], 0))
        zt = WA_MT + 0.65 * 1.0
        det.append(rs.AddCone(_wp(tip[0], tip[1], zt), _wp(tip[0] + d[0] * 5, tip[1] + d[1] * 5, zt - 0.4), 1.0))
    zw, ze = WA_MT + 0.65 * 1.6, WA_MT + 0.65 * 1.3
    det.append(rs.AddCone(_wp(WR[0], WR[1], zw), _wp(WR[0] + 9, WR[1] + 6, zw), 1.6))     # thumb claw
    det.append(rs.AddCone(_wp(E[0], E[1], ze), _wp(E[0] + 5, E[1] - 2, ze), 1.3))           # elbow spur
    for a, b, c in (((-8, 104), (-18, 122), (-24, 126)), ((-14, 100), (-36, 108), (-44, 106)),
                    ((-12, 92), (-42, 80), (-50, 74)), ((-8, 60), (-30, 40), (-38, 22))):
        crv = rs.AddInterpCurve([_wp(a[0], a[1], MT), _wp(b[0], b[1], MT), _wp(c[0], c[1], MT)], 2)
        pp = rs.AddPipe(crv, [rs.CurveDomain(crv)[0], rs.CurveDomain(crv)[1]], [0.7, 0.3], 0, 1)
        rs.DeleteObject(crv)
        if pp:
            det.append(pp[0])
    for i in range(9):
        f = i / 8.0
        a, b, g = (S, E, f / 0.5) if f < 0.5 else (E, WR, (f - 0.5) / 0.5)
        base = (a[0] + (b[0] - a[0]) * g + 2.0, a[1] + (b[1] - a[1]) * g)
        det.append(_wleaf(base, (base[0] - 7, base[1] - 3), 2.6 - 1.0 * f, 1.6, WA_MT + 0.65 * 3.0 + 1.0))
    return memb, [o for o in det if o]


# ------------------------------------------------------------------ RESET
rs.EnableRedraw(False)
rs.UnitSystem(2)  # millimetres
if not rs.IsLayer("Automaton"):
    rs.AddLayer("Automaton")
for child in (rs.LayerChildren("Automaton") or []):
    objs = rs.ObjectsByLayer(child)
    if objs:
        rs.DeleteObjects(objs)

cut_list = []
WOOD, ACRYL, DOWEL = (205, 170, 125), (170, 220, 235), (230, 205, 160)
CAMC, STEEL = (200, 120, 60), (140, 140, 150)


# ------------------------------------------------------------------ FLEXI DRAGON: read the imported model
# The MakerWorld "Flexi Dragon" (D3Craft) STL is imported once onto layer FlexiDragon_ref (printed coil, 340 meshes).
# It is never modified: we group its pieces per segment, uncoil it along the mechanism, and add printed
# cradles that glue under chosen segments. Rod/cam X positions snap to those segments.
flexi = None
if DRAGON_MODE == "flexi" and rs.IsLayer(FLEXI_LAYER) and rs.ObjectsByLayer(FLEXI_LAYER):
    import Rhino
    pcs = []
    for o in rs.ObjectsByLayer(FLEXI_LAYER):
        b = rs.BoundingBox(o)
        m = rs.coercemesh(o)
        pcs.append({"id": o, "c": ((b[0][0] + b[6][0]) / 2.0, (b[0][1] + b[6][1]) / 2.0),
                    "size": max(b[6][0] - b[0][0], b[6][1] - b[0][1]), "zmin": b[0][2], "zmax": b[6][2],
                    "faces": m.Faces.Count if m else 0})
    head_pc = max(pcs, key=lambda p: p["faces"])
    legs = [p for p in pcs if p is not head_pc and p["size"] >= 19 and abs(p["faces"] - 23149) <= 3]
    segs_pc = [p for p in pcs if p is not head_pc and p not in legs and p["size"] >= 12 and p["zmin"] < 1.0]
    # order body segments head -> tail by nearest-neighbour chaining
    order, cur, left = [], head_pc["c"], list(segs_pc)
    while left:
        nxt = min(left, key=lambda p: math.hypot(p["c"][0] - cur[0], p["c"][1] - cur[1]))
        order.append(nxt)
        left.remove(nxt)
        cur = nxt["c"]
    nodes = [head_pc] + order                     # node 0 = head
    s_acc = [0.0]
    for i in range(1, len(nodes)):
        a, b = nodes[i - 1]["c"], nodes[i]["c"]
        s_acc.append(s_acc[-1] + DRAGON_SCALE * math.hypot(b[0] - a[0], b[1] - a[1]))
    groups = dict((i, []) for i in range(len(nodes)))
    for p in pcs:   # every piece rides with its nearest node (scales, horns, legs)
        k = min(range(len(nodes)), key=lambda i: math.hypot(p["c"][0] - nodes[i]["c"][0], p["c"][1] - nodes[i]["c"][1]))
        groups[k].append(p)
    flexi = {"nodes": nodes, "s": s_acc, "groups": groups}

    # snap the mechanism to segments: chest segment over WING_X, head rod under the head, rods under segments
    def nearest_node(s_target):
        return min(range(1, len(nodes)), key=lambda i: abs(s_acc[i] - s_target))
    chest_i = nearest_node(HEAD_X_TARGET - WING_X)
    HEAD_X = WING_X + s_acc[chest_i]
    snapped = []
    flexi["saddle"] = {}
    for nm, x, e, r, ph in BODY_CAMS:
        i = nearest_node(HEAD_X - x)
        snapped.append((nm, HEAD_X - s_acc[i], e, r, ph))
        flexi["saddle"][nm] = i
    BODY_CAMS = snapped
    flexi["chest"] = chest_i

rod_xs = [c[1] for c in BODY_CAMS] + ([WING_X] if WINGS else []) + [HEAD_X]
post_pts = ([(WING_X - 12.0, SHAFT_Y), (WING_X + 12.0, SHAFT_Y)] if flexi else
            [(WING_X, SHAFT_Y - 10.0), (WING_X, SHAFT_Y + 10.0)])

# ------------------------------------------------------------------ BOX
MID = BOX_L / 2.0

def split_x(x0, x1):
    """ranges to print: whole if it fits the bed, else two halves at the box centre"""
    if x1 - x0 <= BED:
        return [(x0, x1, "")]
    return [(x0, MID, "_A"), (MID, x1, "_B")]

layer("Box", WOOD)
def seam_pins(obj, sfx, yz, up=(0, 0, 1)):
    """3 mm alignment-pin holes across the split seam (8 mm into each half), teardrop toward the print-up side"""
    if not sfx:
        return obj
    for (y, z) in yz:
        obj = tear_cut(obj, P(MID - 8, y, z), P(MID + 8, y, z), 1.5 + FIT_PANEL_PIN, up)
    return obj

for a, b, sfx in split_x(0, BOX_L):
    tag(seam_pins(box(a, 0, 0, b, BOX_D, T), sfx, [(30, T / 2), (90, T / 2)]), "Floor" + sfx, WOOD)
for nm, x0 in (("EndWall_L", 0.0), ("EndWall_R", BOX_L - T)):
    w = box(x0, 0, T, x0 + T, BOX_D, TOP_Z)
    hole = cyl(P(x0 - 1, SHAFT_Y, SHAFT_Z), P(x0 + T + 1, SHAFT_Y, SHAFT_Z), SHAFT_R + FIT_SHAFT_RUN)
    res = rs.BooleanDifference([w], [hole])
    tag(res[0] if res else w, nm, WOOD)
for a, b, sfx in split_x(T, BOX_L - T):
    tag(seam_pins(box(a, BOX_D - T, T, b, BOX_D, TOP_Z), sfx, [(BOX_D - T / 2, 35), (BOX_D - T / 2, 95)], up=(0, 1, 0)),
        "BackPanel" + sfx, WOOD)
tag(box(T, 0, T, BOX_L - T, 3, TOP_Z), "FrontPanel_clear_acrylic_3mm (laser cut)", ACRYL)

def plate_with_holes(nm, x0, y0, z0, x1, y1, z1, pins=()):
    for a, b, sfx in split_x(x0, x1):
        plate = box(a, y0, z0, b, y1, z1)
        holes = [(x, SHAFT_Y) for x in rod_xs] + list(post_pts)
        cutters = [cyl(P(x, y, z0 - 1), P(x, y, z1 + 1), HOLE_R)
                   for (x, y) in holes if a + HOLE_R < x < b - HOLE_R]
        res = rs.BooleanDifference([plate], cutters) if cutters else None
        tag(seam_pins(res[0] if res else plate, sfx, pins), nm + sfx, WOOD)

plate_with_holes("TopPlate", 0, 0, TOP_Z, BOX_L, BOX_D, BOX_H, pins=[(20, TOP_Z + T / 2), (100, TOP_Z + T / 2)])
plate_with_holes("RodGuideBar", T, SHAFT_Y - 15, GUIDE_Z, BOX_L - T, SHAFT_Y + 15, GUIDE_Z + T,
                 pins=[(SHAFT_Y - 9.5, GUIDE_Z + T / 2), (SHAFT_Y + 9.5, GUIDE_Z + T / 2)])
# guide bar rests on two blocks glued to the end walls
tag(box(T, SHAFT_Y - 15, GUIDE_Z - 15, T + 15, SHAFT_Y + 15, GUIDE_Z), "GuideBlock_L", WOOD)
tag(box(BOX_L - T - 15, SHAFT_Y - 15, GUIDE_Z - 15, BOX_L - T, SHAFT_Y + 15, GUIDE_Z), "GuideBlock_R", WOOD)

# A-frame shaft support
_af = prism([P(SUPPORT_X - T / 2, SHAFT_Y - 40, T), P(SUPPORT_X - T / 2, SHAFT_Y + 40, T),
             P(SUPPORT_X - T / 2, SHAFT_Y + 8, SHAFT_Z + 12), P(SUPPORT_X - T / 2, SHAFT_Y - 8, SHAFT_Z + 12)], (T, 0, 0))
_r = rs.BooleanDifference([_af], [cyl(P(SUPPORT_X - T, SHAFT_Y, SHAFT_Z), P(SUPPORT_X + T, SHAFT_Y, SHAFT_Z),
                                      SHAFT_R + FIT_SHAFT_RUN)], True)
tag(_r[0] if _r else _af, "Support_Aframe (shaft bore {:.1f})".format(2 * (SHAFT_R + FIT_SHAFT_RUN)), WOOD)

# ------------------------------------------------------------------ SHAFT
layer("Shaft", DOWEL)
tag(cyl(P(-14, SHAFT_Y, SHAFT_Z), P(BOX_L + 12, SHAFT_Y, SHAFT_Z), SHAFT_R), "Camshaft_8mm_steel_D-shaft", STEEL)
# hand-crank on the right end (backup / demo without power)
tag(box(BOX_L + 6, SHAFT_Y - 4, SHAFT_Z - 4, BOX_L + 12, SHAFT_Y + 4, SHAFT_Z + 30), "HandCrank_arm", WOOD)
tag(cyl(P(BOX_L + 12, SHAFT_Y, SHAFT_Z + 25), P(BOX_L + 30, SHAFT_Y, SHAFT_Z + 25), 4), "HandCrank_knob", DOWEL)
cut_list.append("Camshaft: 8mm steel D-shaft (0.5mm flat), {:.0f} mm - or file a flat on 8mm rod where cams sit".format(BOX_L + 26))
cut_list.append("Turn the shaft CLOCKWISE seen from the hand-crank (right) end: wave runs tail->head, head rises slowly then drops")

# ------------------------------------------------------------------ MOTOR
layer("Motor", STEEL)
tag(cyl(P(-22, SHAFT_Y, SHAFT_Z), P(-10, SHAFT_Y, SHAFT_Z), 6.5), "ShaftCoupler", STEEL)
tag(cyl(P(-72, SHAFT_Y, SHAFT_Z), P(-22, SHAFT_Y, SHAFT_Z), 12.5), "DC_gearmotor_25mm (5-12V, ~30-60rpm)", STEEL)
tag(box(-72, SHAFT_Y - 16, SHAFT_Z - 15.5, 0, SHAFT_Y + 16, SHAFT_Z - 12.5), "MotorShelf", WOOD)
jack = cyl(P(25, BOX_D - T - 4, 20), P(25, BOX_D + 4, 20), 4.0)
tag(jack, "BarrelJack_5.5x2.1 (wall power)", (40, 40, 40))
tag(box(20, 70, T, 70, 105, T + 12), "SpeedController_placeholder (pot + driver)", (40, 120, 60))
wire = rs.AddInterpCurve([P(25, BOX_D - T - 4, 20), P(45, 100, T + 12), P(30, 60, 25),
                          P(3, 60, 30), P(-30, 60, SHAFT_Z - 13)])
tag(wire, "Wire_path", (200, 30, 30))

# ------------------------------------------------------------------ CAMS + FOLLOWERS
layer("Cams", CAMC)

def printed_cam(name, disc, x_face):
    """union cam disc + hub on the shaft axis, then cut shaft bore + M3 set-screw hole"""
    hub = cyl(P(x_face, SHAFT_Y, SHAFT_Z), P(x_face + HUB_L, SHAFT_Y, SHAFT_Z), HUB_R)
    u = rs.BooleanUnion([disc, hub])
    body = u[0] if u else disc
    # D-bore: round bore with a flat on the grub-screw side (-Y), matching an 8 mm D-shaft
    rb = SHAFT_R + FIT_SHAFT_CAM
    bore = cyl(P(x_face - 20, SHAFT_Y, SHAFT_Z), P(x_face + HUB_L + 1, SHAFT_Y, SHAFT_Z), rb)
    keep = box(x_face - 21, SHAFT_Y - SHAFT_FLAT - FIT_SHAFT_CAM, SHAFT_Z - rb - 1, x_face + HUB_L + 2,
               SHAFT_Y + rb + 1, SHAFT_Z + rb + 1)
    d = rs.BooleanIntersection([bore], [keep], True)
    bore = d[0] if d else bore
    xs = x_face + HUB_L / 2.0
    screw = cyl(P(xs, SHAFT_Y, SHAFT_Z), P(xs, SHAFT_Y - HUB_R - 2, SHAFT_Z), M3_PILOT_R)   # M3 self-taps
    res = rs.BooleanDifference([body], [bore, screw])
    return tag(res[0] if res else body, name, CAMC)

cams_out = {}
for nm, x, e, r, ph in BODY_CAMS:
    cy, cz = eccentric(e, ph)
    printed_cam("Cam_" + nm, cyl(P(x - T / 2, cy, cz), P(x + T / 2, cy, cz), r), x + T / 2)
    cams_out[nm] = cz + r
    cut_list.append("PRINT Cam {}: eccentric D{:.0f}, bore offset {:.0f} mm, phase {:.0f} deg, hub+M3 grub".format(nm, 2 * r, e, ph))
wy, wz = eccentric(WING_E, WING_PHASE)
if WINGS:
    printed_cam("Cam_Wing", cyl(P(WING_X - T / 2, wy, wz), P(WING_X + T / 2, wy, wz), WING_R), WING_X + T / 2)
    cut_list.append("PRINT Cam Wing: eccentric D{:.0f}, bore offset {:.0f} mm, phase {:.0f} deg".format(2 * WING_R, WING_E, WING_PHASE))

snail_pts = []
for i in range(120):
    t = i * 3.0
    r = snail_r(-t)          # mirrored: slow rise / quick drop for the run direction (+ANGLE)
    w = math.radians(t + ANGLE)
    snail_pts.append(P(HEAD_X - SNAIL_T / 2, SHAFT_Y + r * math.sin(w), SHAFT_Z + r * math.cos(w)))
printed_cam("Cam_Head_snail", prism(snail_pts, (SNAIL_T, 0, 0)), HEAD_X + SNAIL_T / 2)
cut_list.append("PRINT Cam Head: snail R{:.0f}->R{:.0f} over 300 deg, drop over 60 deg (softer), {:.0f}mm thick, D-bore".format(
    SNAIL_RMIN, SNAIL_RMAX, SNAIL_T))

layer("Followers", DOWEL)
body_tops = {}
for nm, x, e, r, ph in BODY_CAMS:
    L = BODY_ROD_TOP_MID - (SHAFT_Z + r + 3)
    body_tops[nm] = push_rod(nm, x, cams_out[nm], L, DOWEL)
    cut_list.append("Rod {}: 6mm dowel x {:.0f} mm + D18 foot disc".format(nm, L))

Lw = WING_ROD_TOP_MID - (SHAFT_Z + WING_R + 3)
if WINGS:
    zc = push_rod("WingRod", WING_X, wz + WING_R, Lw, DOWEL)
    cut_list.append("Rod Wing: 6mm dowel x {:.0f} mm".format(Lw))

r_top = snail_h(ANGLE)
Lh = HEAD_ROD_TOP_LOW - (SHAFT_Z + SNAIL_HMIN + 3)
head_top = push_rod("HeadRod", HEAD_X, SHAFT_Z + r_top, Lh, DOWEL)
cut_list.append("Rod Head: 6mm dowel x {:.0f} mm".format(Lh))

CHEST_POST_TOP = (BODY_ROD_TOP_MID - 1.0) if flexi else 192.0
for i, (x, y) in enumerate(post_pts):
    tag(cyl(P(x, y, GUIDE_Z), P(x, y, CHEST_POST_TOP), ROD_R), "ShoulderPost_{}".format(i + 1), DOWEL)
    cut_list.append("Shoulder post {}: 6mm dowel x {:.0f} mm (glued into chest + guide bar)".format(
        i + 1, CHEST_POST_TOP - GUIDE_Z))

if not flexi:
    # ------------------------------------------------------------------ DRAGON (flexi-style articulated chain)
    # A chain of vertebrae joined by print-in-place hinges (tongue + captive pin, pivot about Y).
    # "Saddle" vertebrae ride on the push rods; the plain links in between just follow the wave.
    DRAGON, EYE, MEMB = (165, 35, 40), (250, 200, 30), (130, 30, 60)
    layer("Dragon", DRAGON)

    SOCK_R = ROD_R + 0.4     # rod socket
    SLIDE = 3.0              # rod sockets slotted +/- this in X (chain length vs wave)
    LINK_STRETCH = 0.04      # in-between links 4% long: centres rod offsets over a full turn (simulated: within +/-1.7)
    PIN_R = 1.1              # 2 mm cross pin, rod -> saddle vertebra
    GAP = 1.6                # gap between vertebra bodies
    J_PIN_R, J_HOLE_R = 1.5, 1.9          # print-in-place hinge: 0.4 mm radial clearance
    TONGUE_W, TONGUE_H = 2.2, 2.4
    SLOT_W, SLOT_H = 2.6, 5.0     # tall slot: tongue can swing ~+/-20 deg
    CHEST_Z = 195.0
    SADDLE_L, SOCK_LOCAL, SOCK_TOP = 22.0, 9.9, -2.0
    LINK_L = 12.0
    SIZE = 0.9               # overall body slimming vs the table

    def lerp_table(tab, x):
        if x <= tab[0][0]:
            return tab[0][1:]
        for i in range(1, len(tab)):
            if x <= tab[i][0]:
                x0, x1 = tab[i - 1][0], tab[i][0]
                f = (x - x0) / (x1 - x0)
                return tuple(tab[i - 1][k] + f * (tab[i][k] - tab[i - 1][k]) for k in range(1, len(tab[i])))
        return tab[-1][1:]

    def frame(pt, tan):
        t = rs.VectorUnitize(tan)
        xa = rs.VectorUnitize(rs.VectorCrossProduct((0, 0, 1), t))
        ya = rs.VectorCrossProduct(t, xa)
        return rs.PlaneFromFrame(pt, xa, ya)

    def loft_solid(curves):
        lo = rs.AddLoftSrf(curves)
        rs.DeleteObjects(curves)
        if not lo:
            return None
        rs.CapPlanarHoles(lo[0])
        return lo[0]

    def tapered(p0, p1, r0, r1):
        d = rs.VectorCreate(p1, p0)
        return loft_solid([rs.AddCircle(frame(p0, d), r0), rs.AddCircle(frame(p1, d), r1)])

    def subtract(obj, cutter):
        if obj is None or cutter is None:
            if cutter:
                rs.DeleteObject(cutter)
            return obj
        res = rs.BooleanDifference([obj], [cutter], True)
        if res:
            if len(res) > 1:
                rs.DeleteObjects(res[1:])
            return res[0]
        rs.DeleteObject(cutter)
        return obj

    def add_into(obj, extra):
        if extra is None:
            return obj
        res = rs.BooleanUnion([obj, extra], True)
        if res and len(res) == 1:
            return res[0]
        if res:   # pieces didn't touch: keep the biggest, flag the rest
            res = sorted(res, key=lambda o: -rs.SurfaceVolume(o)[0])
            for o in res[1:]:
                rs.ObjectName(o, "LOOSE_piece (did not fuse)")
            return res[0]
        rs.DeleteObject(extra)
        return obj

    def union(objs):
        objs = [o for o in objs if o]
        out = objs[0]
        for o in objs[1:]:
            out = add_into(out, o)
        return out

    BODY_TAB = [(0, 5.2, 5.0), (28, 5.6, 5.2), (45, 8.0, 7.5), (63, 10.0, 9.0), (82, 11.5, 10.5),
                (101, 14.0, 11.5), (120, 16.0, 12.5), (140, 14.0, 11.5), (160, 12.0, 10.5), (180, 10.5, 9.5),
                (200, 9.0, 8.5), (215, 8.0, 7.5), (232, 7.5, 7.0)]
    HEAD_TAB = [(224.5, 6.8, 6.3, -0.5), (230, 7.6, 7.0, -0.8), (238, 8.5, 8.0, -0.8), (246, 10.5, 10.0, 0.0),
                (254, 13.0, 12.0, 1.0), (262, 12.5, 10.5, 0.5), (270, 9.5, 8.0, -1.5), (279, 7.5, 6.5, -3.0),
                (288, 6.0, 5.0, -4.0), (295, 3.5, 3.0, -4.5), (299, 1.2, 1.2, -4.5)]
    J_HEAD = 228.0

    def vertebra(L, w, h, rear=True, front=True, socket=False, dorsal=True, lateral=True, legs=False, tail=False):
        """built in local coords: rear hinge pin at x=0, front hinge at x=L, centreline on the X axis"""
        a, b = -3.5, L - 3.5 - GAP
        cx, rx = (a + b) / 2.0, (b - a) / 2.0
        seg = ellipsoid(P(cx, 0, 0), rx, w, h)
        s = max(0.55, h / 10.0)
        if front:
            seg = add_into(seg, box(b - 3, -TONGUE_W, -TONGUE_H, L, TONGUE_W, TONGUE_H))
            seg = add_into(seg, cyl(P(L, -TONGUE_W, 0), P(L, TONGUE_W, 0), TONGUE_H))
            seg = subtract(seg, cyl(P(L, -6, 0), P(L, 6, 0), J_HOLE_R))
        # ring of swept-back leaf scales (flexi look): angle from top, size factor
        ring = []
        if dorsal:
            ring += [(0, 1.0), (40, 0.8), (-40, 0.8)]
        if lateral:
            ring += [(80, 0.7), (-80, 0.7)]
        back = min(rx * 0.6, 3.5) + 1.5 * s
        for ang, k in ring:
            r_ = math.radians(ang)
            lh = h * 0.3 + 6.0 * s * k
            leaf = rs.AddCone(P(0, 0, 0), P(-back, 0, lh), min(rx * 0.85, 4.2 * s * k))
            rs.ScaleObject(leaf, P(0, 0, 0), (1, 0.4, 1))
            leaf = rs.RotateObject(leaf, P(0, 0, 0), -ang, (1, 0, 0)) or leaf
            leaf = rs.MoveObject(leaf, (cx, w * 0.7 * math.sin(r_), h * 0.7 * math.cos(r_))) or leaf
            seg = add_into(seg, leaf)
        if legs:     # short clawed legs
            for sy in (-1, 1):
                hip, knee = P(cx, sy * w * 0.6, -h * 0.3), P(cx + 3, sy * (w + 5), -h * 0.6)
                foot = P(cx + 5, sy * (w + 6), -h - 5)
                seg = union([seg, tapered(hip, knee, 3.4, 2.5), rs.AddSphere(knee, 2.5),
                             tapered(knee, foot, 2.5, 1.9), rs.AddSphere(foot, 2.7)])
                for ang in (-35, 0, 35):
                    r_ = math.radians(ang)
                    seg = add_into(seg, rs.AddCone(foot, P(foot[0] + 5 * math.cos(r_), foot[1] + sy * 5 * math.sin(r_) + sy * 1.0,
                                                           foot[2] - 1.5), 1.1))
        if rear:   # cut last so no scale/leg material sits inside the hinge slot
            seg = subtract(seg, box(a - 0.6, -SLOT_W, -SLOT_H, TONGUE_H + 0.5, SLOT_W, SLOT_H))
            half = 0.85 * w * math.sqrt(max(0.0, 1 - (cx / rx) ** 2))
            seg = add_into(seg, cyl(P(0, -half, 0), P(0, half, 0), J_PIN_R))
        if socket:
            seg = subtract(seg, box(SOCK_LOCAL - SOCK_R - SLIDE, -SOCK_R, -h - 10, SOCK_LOCAL + SOCK_R + SLIDE, SOCK_R, SOCK_TOP))
            seg = subtract(seg, box(SOCK_LOCAL - PIN_R - SLIDE, -w - 10, SOCK_TOP - 3 - PIN_R,
                                    SOCK_LOCAL + PIN_R + SLIDE, w + 10, SOCK_TOP - 3 + PIN_R))
        if tail:     # tapering tail tip + spade fin
            seg = add_into(seg, rs.AddCone(P(a + 1.5, 0, 0), P(a - 16, 0, -2), 4.0))
            seg = add_into(seg, prism([P(a - 9, -1.25, -1), P(a - 17, -1.25, 6), P(a - 27, -1.25, -1.5),
                                       P(a - 17, -1.25, -8)], (0, 2.5, 0)))
        return seg

    # ---- chain layout (flat reference: rod sockets sit exactly over their rods)
    J_R = dict((nm, x - SOCK_LOCAL) for (nm, x, e, r, ph) in BODY_CAMS)
    CHEST_L = 26.0
    J_C = WING_X - (CHEST_L - 7 - GAP) / 2.0
    fixed = [(J_R["R1_tail"], SADDLE_L, "R1_tail"), (J_R["R2_back"], SADDLE_L, "R2_back"), (J_C, CHEST_L, "CHEST"),
             (J_R["R3_belly"], SADDLE_L, "R3_belly"), (J_R["R4_neck"], SADDLE_L, "R4_neck")]
    chain = [(J_R["R1_tail"] - 3 * LINK_L, LINK_L, "TAIL"),
             (J_R["R1_tail"] - 2 * LINK_L, LINK_L, "LINK"), (J_R["R1_tail"] - LINK_L, LINK_L, "LINK")]
    ends = [f[0] for f in fixed[1:]] + [J_HEAD]
    for (j, L, kind), nxt in zip(fixed, ends):
        chain.append((j, L, kind))
        gap = nxt - (j + L)
        n = max(1, int(round(gap / LINK_L)))
        for k in range(n):
            chain.append((j + L + k * gap / n, gap / n * (1 + LINK_STRETCH), "LINK"))
    ci = [i for i, c in enumerate(chain) if c[2] == "CHEST"][0]

    # ---- pose: spine through the rod tops, chain walked along it from the fixed chest
    seg_c = dict((nm, P(x, SHAFT_Y, body_tops[nm] + 2)) for (nm, x, e, r, ph) in BODY_CAMS)
    z1 = seg_c["R1_tail"][2]
    spine = rs.AddInterpCurve([P(-30, SHAFT_Y, z1 - 12), P(5, SHAFT_Y, z1 - 6), seg_c["R1_tail"], seg_c["R2_back"],
                               P(WING_X - 12, SHAFT_Y, CHEST_Z), P(WING_X, SHAFT_Y, CHEST_Z),
                               P(WING_X + 12, SHAFT_Y, CHEST_Z), seg_c["R3_belly"], seg_c["R4_neck"],
                               P(HEAD_X, SHAFT_Y, head_top + 2), P(HEAD_X + 30, SHAFT_Y, head_top + 4)], 3)
    tag(spine, "Spine_centreline (reference)", (90, 20, 20))

    def walk(Q, L, forward):
        tq = rs.CurveClosestPoint(spine, Q)
        d = rs.CurveDomain(spine)
        lo, hi = (tq, d[1]) if forward else (d[0], tq)
        for _ in range(50):
            m = (lo + hi) / 2.0
            near = rs.Distance(rs.EvaluateCurve(spine, m), Q) < L
            if forward:
                lo, hi = (m, hi) if near else (lo, m)
            else:
                lo, hi = (lo, m) if near else (m, hi)
        return rs.EvaluateCurve(spine, (lo + hi) / 2.0)

    joints = [None] * (len(chain) + 1)
    joints[ci] = P(J_C, SHAFT_Y, CHEST_Z)
    joints[ci + 1] = P(J_C + CHEST_L, SHAFT_Y, CHEST_Z)
    for i in range(ci + 1, len(chain)):
        joints[i + 1] = walk(joints[i], chain[i][1], True)
    for i in range(ci - 1, -1, -1):
        joints[i] = walk(joints[i + 1], chain[i][1], False)

    def place(objs, J, pitch):
        """rotate about world Y then move; returns the (new) object ids"""
        out = []
        for o in objs:
            if o:
                o = rs.RotateObject(o, (0, 0, 0), -math.degrees(pitch), (0, 1, 0)) or o
                o = rs.MoveObject(o, (J[0], J[1], J[2])) or o
            out.append(o)
        return out

    report = []
    parts = []
    for i, (j0, L, kind) in enumerate(chain):
        J, Jn = joints[i], joints[i + 1]
        pitch = math.atan2(Jn[2] - J[2], Jn[0] - J[0])
        w, h = lerp_table(BODY_TAB, j0 + (L - 7 - GAP) / 2.0)
        w, h = max(5.2, w * SIZE), max(5.0, h * SIZE)
        if kind == "CHEST":
            v = vertebra(L, w, h, dorsal=False, lateral=False, legs=True)
        elif kind == "TAIL":
            v = vertebra(L, w, h, rear=False, tail=True)
        elif kind == "LINK":
            v = vertebra(L, w, h)
        else:
            v = vertebra(L, w, h, socket=True, legs=(kind == "R2_back"))
            sx = J[0] + SOCK_LOCAL * math.cos(pitch) - SOCK_TOP * math.sin(pitch)
            rod_x = [c[1] for c in BODY_CAMS if c[0] == kind][0]
            report.append("{} rod offset in its slot: {:+.1f} mm (allowed +/-{})".format(kind, rod_x - sx, SLIDE))
        v = place([v], J, pitch)[0]
        nm = {"CHEST": "V{:02d}_chest (fixed shoulder)", "TAIL": "V{:02d}_tail", "LINK": "V{:02d}_link"}.get(
            kind, "V{:02d}_saddle_" + kind).format(i + 1)
        parts.append((v, nm))

    # chest = fixed shoulder: hinge ears, hinge-pin bores, post sockets, wing-rod bore (chest is level, so world coords)
    chest = parts[ci][0]
    for s in (-1, 1):
        for (xa, xb) in ((WING_X - 12, WING_X - 6), (WING_X + 6, WING_X + 12)):
            ya, yb = sorted((SHAFT_Y + s * 5.0, SHAFT_Y + s * 21.0))   # reaches into the body so it fuses
            chest = add_into(chest, box(xa, ya, HINGE_Z - 4, xb, yb, HINGE_Z + 3.5))
    for s in (-1, 1):
        chest = subtract(chest, cyl(P(WING_X - 16, SHAFT_Y + s * HINGE_Y, HINGE_Z),
                                    P(WING_X + 16, SHAFT_Y + s * HINGE_Y, HINGE_Z), 1.65))
    for (x, y) in post_pts:
        chest = subtract(chest, cyl(P(x, y, 170), P(x, y, CHEST_POST_TOP), ROD_R + 0.15))
    chest = subtract(chest, cyl(P(WING_X, SHAFT_Y, 170), P(WING_X, SHAFT_Y, 240), HOLE_R))
    parts[ci] = (chest, parts[ci][1])

    # ---- head (local frame: rear hinge pin at origin, head axis along +X)
    def hx(x):
        return x - J_HEAD

    def head_at(x):
        return lerp_table(HEAD_TAB, x)

    hs = [rs.AddEllipse(frame(P(hx(x), 0, dz), (1, 0, 0)), w, h) for (x, w, h, dz) in HEAD_TAB]
    head = loft_solid(hs)
    eyes = []
    for s in (-1, 1):
        hp = rs.AddInterpCurve([P(hx(252), s * 6, 8), P(hx(244), s * 8.5, 14), P(hx(234), s * 11, 18),
                                P(hx(222), s * 13, 19)], 3)        # horns swept back, flexi-style
        circ = []
        d = rs.CurveDomain(hp)
        for f, rr in ((0.0, 3.6), (0.3, 2.9), (0.6, 2.0), (0.85, 1.2), (1.0, 0.4)):
            t = d[0] + f * (d[1] - d[0])
            circ.append(rs.AddCircle(frame(rs.EvaluateCurve(hp, t), rs.CurveTangent(hp, t)), rr))
        rs.DeleteObject(hp)
        head = add_into(head, loft_solid(circ))
        head = add_into(head, ellipsoid(P(hx(262), s * 6.5, 8.5), 6.0, 3.2, 2.6))           # brow
        for k, (x0, z0) in enumerate(((246, 6), (240, 4), (234, 2))):                          # cheek frills
            base = P(hx(x0), s * 8.5, z0 - 4)
            c = rs.AddCone(base, P(hx(x0 - 9), s * 15, z0 - 6), 2.6)
            rs.ScaleObject(c, base, (1, 1, 0.45))
            head = add_into(head, c)
        w, h, dz = head_at(292)
        mz = dz - 0.35 * h
        head = add_into(head, rs.AddCone(P(hx(292), s * 2.6, mz + 1.0), P(hx(292), s * 2.6, mz - 3.0), 1.0))  # fang
    for x0 in (250, 241, 232):                                                                     # mane leaves
        w, h, dz = head_at(x0)
        base = P(hx(x0), 0, dz + h * 0.8)
        c = rs.AddCone(base, P(hx(x0 - 8), 0, dz + h + 6), 4.0)
        rs.ScaleObject(c, base, (1, 0.4, 1))
        head = add_into(head, c)
    for s in (-1, 1):
        mpts = []
        for x in (266, 272, 278, 284, 290, 296, 299.5):
            w, h, dz = head_at(x)
            mpts.append(P(hx(x), s * 0.94 * w, dz - 0.35 * h))
        mc = rs.AddInterpCurve(mpts, 3)
        mp = rs.AddPipe(mc, [rs.CurveDomain(mc)[0]], [0.7], 0, 1)
        rs.DeleteObject(mc)
        head = subtract(head, mp[0] if mp else None)
        w, h, dz = head_at(266)
        ec = P(hx(266), s * 0.8 * w, dz + 0.45 * h)
        head = subtract(head, rs.AddSphere(ec, 2.8))
        eyes.append(rs.AddSphere(ec, 2.5))
        head = subtract(head, cyl(P(hx(298), s * 1.6, -0.5), P(hx(293), s * 1.6, -5.0), 0.7))
    # rear hinge (receives the last link's tongue) + rod socket
    head = subtract(head, box(-4.1, -SLOT_W, -SLOT_H, TONGUE_H + 0.5, SLOT_W, SLOT_H))
    head = add_into(head, cyl(P(0, -5.5, 0), P(0, 5.5, 0), J_PIN_R))
    hsock = HEAD_X - J_HEAD
    head = subtract(head, box(hsock - SOCK_R - SLIDE, -SOCK_R, -25, hsock + SOCK_R + SLIDE, SOCK_R, SOCK_TOP))
    head = subtract(head, box(hsock - PIN_R - SLIDE, -20, SOCK_TOP - 3 - PIN_R, hsock + PIN_R + SLIDE, 20, SOCK_TOP - 3 + PIN_R))
    Jh = joints[-1]
    tgt = P(HEAD_X, SHAFT_Y, head_top - SOCK_TOP)
    hpitch = math.atan2(tgt[2] - Jh[2], tgt[0] - Jh[0])
    placed = place([head] + eyes, Jh, hpitch)
    head, eyes = placed[0], placed[1:]
    report.append("Head rod offset in its slot: {:+.1f} mm".format(
        HEAD_X - (Jh[0] + hsock * math.cos(hpitch) - SOCK_TOP * math.sin(hpitch))))
    parts.append((head, "V{:02d}_head (snail cam)".format(len(chain) + 1)))
    for e_ in eyes:
        tag(e_, "Eye_bead_D5", EYE)

    for obj, nm in parts:
        tag(obj, nm, DRAGON)
    cut_list.append("PRINT dragon: {} vertebrae + head, print-in-place hinges (print the chain flat in one go)".format(len(chain)))
    cut_list.append("Hardware: 2mm cross pins x5 (rods -> saddles/head), 2x 5mm eye beads")
    for line in report:
        cut_list.append(line)

    # ------------------------------------------------------------------ WINGS (solved linkage)
    layer("Wings", MEMB)
    th0 = math.radians(WING_REST_DEG)
    LINK = math.hypot(HINGE_Y + WING_LEVER * math.cos(th0) - CROSSBAR_PIN,
                      HINGE_Z + WING_LEVER * math.sin(th0) - WING_ROD_TOP_MID)

    def wing_theta(zcb):
        def f(deg):
            t = math.radians(deg)
            return math.hypot(HINGE_Y + WING_LEVER * math.cos(t) - CROSSBAR_PIN,
                              HINGE_Z + WING_LEVER * math.sin(t) - zcb) - LINK
        best, prev = None, None
        for i in range(-120, 181):
            d = i * 0.5
            v = f(d)
            if prev is not None and (v > 0) != (prev[1] > 0):
                root = prev[0] + (d - prev[0]) * prev[1] / (prev[1] - v)
                if best is None or abs(root - WING_REST_DEG) < abs(best - WING_REST_DEG):
                    best = root
            prev = (d, v)
        return best if best is not None else WING_REST_DEG

    theta_deg = wing_theta(zc)
    th = math.radians(theta_deg)
    MEMB_T = 1.6
    # root stays within |u|<=5.5 until v>=8 so it clears the chest hinge ears through the full flap
    LE = [(4.5, 3), (5.5, 8), (14, 16), (15, 35), (10, 62), (0, 92), (-12, 118)]   # leading edge, root -> tip
    F1, F2, F3 = (-32, 92), (-44, 62), (-44, 30)
    WRIST = (10, 62)

    for s, side in ((1, "Back"), (-1, "Front")):
        n = (0.0, -s * math.sin(th), math.cos(th))

        def W(u, v, off=0.0):
            return P(WING_X + u, SHAFT_Y + s * (HINGE_Y + v * math.cos(th)) + n[1] * off,
                     HINGE_Z + v * math.sin(th) + n[2] * off)

        o = -MEMB_T / 2
        edge = [rs.AddInterpCurve([W(u, v, o) for (u, v) in LE], 3),
                rs.AddInterpCurve([W(-12, 118, o), W(-19, 99, o), W(*F1, off=o)], 2),
                rs.AddInterpCurve([W(*F1, off=o), W(-31, 73, o), W(*F2, off=o)], 2),
                rs.AddInterpCurve([W(*F2, off=o), W(-35, 46, o), W(*F3, off=o)], 2),
                rs.AddInterpCurve([W(*F3, off=o), W(-26, 18, o), W(-12, 10.5, o), W(-5.5, 8, o)], 3),
                rs.AddLine(W(-5.5, 8, o), W(-4.5, 3, o)),
                rs.AddLine(W(-4.5, 3, o), W(4.5, 3, o))]
        loop = rs.JoinCurves(edge, True)
        memb = rs.ExtrudeCurveStraight(loop[0], (0, 0, 0), (n[0] * MEMB_T, n[1] * MEMB_T, n[2] * MEMB_T))
        rs.CapPlanarHoles(memb)
        rs.DeleteObjects(loop)

        bo = MEMB_T / 2 + 0.6
        parts = [memb,
                 cyl(P(WING_X - 4.6, SHAFT_Y + s * HINGE_Y, HINGE_Z), P(WING_X + 4.6, SHAFT_Y + s * HINGE_Y, HINGE_Z), 3.5),
                 tapered(W(0, 2, bo), W(WRIST[0], WRIST[1], bo), 2.4, 1.8),
                 rs.AddSphere(W(WRIST[0], WRIST[1], bo), 2.2),
                 tapered(W(WRIST[0], WRIST[1], bo), W(-12, 118, bo), 1.6, 0.6),
                 rs.AddCone(W(WRIST[0], WRIST[1], bo), W(18, 69, bo), 1.3),   # thumb claw
                 cyl(W(-3, WING_LEVER, 3.0), W(3, WING_LEVER, 3.0), 2.6)]     # link lug
        for fu, fv in (F1, F2, F3):
            parts.append(tapered(W(WRIST[0], WRIST[1], bo), W(fu * 0.97, fv * 0.97, bo), 1.5, 0.6))
        wing = union(parts)
        wing = subtract(wing, cyl(P(WING_X - 8, SHAFT_Y + s * HINGE_Y, HINGE_Z),
                                  P(WING_X + 8, SHAFT_Y + s * HINGE_Y, HINGE_Z), 1.65))
        wing = subtract(wing, cyl(W(-5, WING_LEVER, 3.0), W(5, WING_LEVER, 3.0), PIN_R))
        tag(wing, "Wing_{} (print flat, membrane {}mm)".format(side, MEMB_T), MEMB)
        tag(cyl(P(WING_X - 14, SHAFT_Y + s * HINGE_Y, HINGE_Z), P(WING_X + 14, SHAFT_Y + s * HINGE_Y, HINGE_Z), 1.5),
            "Wing_{}_hinge_pin_3mm".format(side), STEEL)
        tag(cyl(P(WING_X, SHAFT_Y + s * CROSSBAR_PIN, zc), W(0, WING_LEVER, 3.0), 1.5), "Wing_{}_link".format(side), STEEL)
        cut_list.append("PRINT Wing_{}".format(side))
    tag(cyl(P(WING_X, SHAFT_Y - CROSSBAR_PIN - 3, zc), P(WING_X, SHAFT_Y + CROSSBAR_PIN + 3, zc), 2.5),
        "Wing_crossbar", DOWEL)
    cut_list.append("Hardware: 3mm hinge pins x2 (28mm), links x2 ({:.1f}mm c-c)".format(LINK))

if flexi:
    # ------------------------------------------------------------------ FLEXI DRAGON: pose + cradles
    import Rhino
    BLUE, WHITE, CRADLE = (40, 95, 200), (240, 240, 245), (230, 205, 160)
    layer("FlexiDragon", BLUE)
    BASE_ABOVE_ROD = CRADLE_T + 1.0          # dragon base sits this far above its rod top
    CHEST_BASE = BODY_ROD_TOP_MID + BASE_ABOVE_ROD
    nodes, s_acc, groups = flexi["nodes"], flexi["s"], flexi["groups"]

    # target spine for the dragon's BASE line, ordered head -> tail
    tops = dict((nm, body_tops[nm]) for nm, x, e, r, ph in BODY_CAMS)
    xs = dict((nm, x) for nm, x, e, r, ph in BODY_CAMS)
    pts = [P(HEAD_X + 25, SHAFT_Y, head_top + BASE_ABOVE_ROD + 1), P(HEAD_X, SHAFT_Y, head_top + BASE_ABOVE_ROD)]
    for nm in ("R4_neck", "R3_belly"):
        pts.append(P(xs[nm], SHAFT_Y, tops[nm] + BASE_ABOVE_ROD))
    pts += [P(WING_X + 10, SHAFT_Y, CHEST_BASE), P(WING_X, SHAFT_Y, CHEST_BASE), P(WING_X - 10, SHAFT_Y, CHEST_BASE)]
    for nm in ("R2_back", "R1_tail"):
        pts.append(P(xs[nm], SHAFT_Y, tops[nm] + BASE_ABOVE_ROD))
    z1 = tops["R1_tail"] + BASE_ABOVE_ROD
    pts += [P(xs["R1_tail"] - 35, SHAFT_Y, z1 - 4), P(xs["R1_tail"] - 80, SHAFT_Y, z1 - 12),
            P(xs["R1_tail"] - 130, SHAFT_Y, z1 - 22)]
    spine = rs.AddInterpCurve(pts, 3)
    s0 = rs.CurveLength(spine, -1, [rs.CurveDomain(spine)[0], rs.CurveClosestPoint(spine, pts[1])])

    def target_plane(s):
        pt = rs.CurveArcLengthPoint(spine, s0 + s, True)
        T = rs.VectorUnitize(rs.CurveTangent(spine, rs.CurveClosestPoint(spine, pt)))
        up = rs.VectorUnitize(rs.VectorSubtract((0, 0, 1), rs.VectorScale(T, T[2])))
        yv = rs.VectorCrossProduct(up, T)
        return Rhino.Geometry.Plane(Rhino.Geometry.Point3d(pt[0], pt[1], pt[2]), Rhino.Geometry.Vector3d(T[0], T[1], T[2]), Rhino.Geometry.Vector3d(yv[0], yv[1], yv[2]))

    planes = {}
    n_pieces = 0
    for i, nd in enumerate(nodes):
        a = nodes[max(0, i - 1)]["c"]
        b = nodes[min(len(nodes) - 1, i + 1)]["c"]
        t = rs.VectorUnitize((b[0] - a[0], b[1] - a[1], 0))
        src = Rhino.Geometry.Plane(Rhino.Geometry.Point3d(nd["c"][0], nd["c"][1], 0), Rhino.Geometry.Vector3d(t[0], t[1], 0),
                                   Rhino.Geometry.Vector3d(-t[1], t[0], 0))
        tgt = target_plane(s_acc[i])
        planes[i] = tgt
        xf = Rhino.Geometry.Transform.PlaneToPlane(src, tgt) * Rhino.Geometry.Transform.Scale(src.Origin, DRAGON_SCALE)
        ids = [p["id"] for p in groups[i]]
        new = rs.TransformObjects(ids, xf, True) or []
        for p, o in zip(groups[i], new):
            rs.ObjectLayer(o, "Automaton::FlexiDragon")
            rs.ObjectColor(o, WHITE if (p["size"] < 9 and p["zmin"] > 3) else BLUE)
        n_pieces += len(new)
    rs.DeleteObject(spine)

    # ---- printed cradles (built in a canonical frame: origin = segment base centre, X = head->tail, Z = up)
    layer("Cradles", CRADLE)

    # slot centres biased by the mean rod offset over a full turn (local +X = toward the tail)
    SLOT_BIAS = {"R1_tail": 3.55, "R2_back": 1.6, "R3_belly": 0.5, "R4_neck": 0.5, "head": 0.7}

    PAD_INSET = 0.5   # pad is this much narrower than the segment base on each side: hidden, never touches legs

    def base_halfwidth(node_i):
        """half-width of the segment's own flat base where the pad sits (section 0.3 mm above the bed), scaled"""
        nd = nodes[node_i]
        a = nodes[max(0, node_i - 1)]["c"]
        b = nodes[min(len(nodes) - 1, node_i + 1)]["c"]
        t = rs.VectorUnitize((b[0] - a[0], b[1] - a[1], 0))
        m = rs.coercemesh(nd["id"])
        pl = Rhino.Geometry.Plane(Rhino.Geometry.Point3d(0, 0, 0.3), Rhino.Geometry.Vector3d(0, 0, 1))
        best = None
        for poly in Rhino.Geometry.Intersect.Intersection.MeshPlane(m, pl) or []:
            for q in poly:
                dx, dy = q.X - nd["c"][0], q.Y - nd["c"][1]
                if abs(dx * t[0] + dy * t[1]) <= 4.0:
                    w = abs(-dx * t[1] + dy * t[0])
                    best = w if best is None else max(best, w)
        return (best or 9.0) * DRAGON_SCALE

    def cradle(name, node_i, rod_x, rod_top, pad_l=6.0 * DRAGON_SCALE, pad_w=None, socket=True, bias=0.0):
        hw = base_halfwidth(node_i)
        if pad_w is None:
            pad_w = 2 * (hw - PAD_INSET)
        # glue pad, hidden under the segment: flat 3 mm strip on the centre line, ends bevelled down 1.2 mm so the
        # neighbouring segments (their bases overlap this footprint) can tilt over it without touching
        parts = [prism([P(-pad_l / 2, -pad_w / 2, -CRADLE_T), P(pad_l / 2, -pad_w / 2, -CRADLE_T),
                        P(pad_l / 2, -pad_w / 2, -1.5), P(1.5, -pad_w / 2, 0), P(-1.5, -pad_w / 2, 0),
                        P(-pad_l / 2, -pad_w / 2, -1.5)], (0, pad_w, 0))]
        c = parts[0]
        for o in parts[1:]:
            r = rs.BooleanUnion([c, o], True)
            c = r[0] if r else c
        tgt = planes[node_i]
        if socket:
            # socket boss under the pad; slot runs along X so the rod can slide +/-SLIDE as the wave changes length
            # boss flares out to the pad width (<= 45 deg) so the cradle prints boss-down with no supports
            bx0, bw = bias - (SOCK_R + SLIDE + 2), SOCK_R + 2
            boss = prism([P(bx0, -bw, -CRADLE_T - 9), P(bx0, bw, -CRADLE_T - 9), P(bx0, pad_w / 2, -CRADLE_T),
                          P(bx0, -pad_w / 2, -CRADLE_T)], (2 * (SOCK_R + SLIDE + 2), 0, 0))
            r = rs.BooleanUnion([c, boss], True)
            c = r[0] if r else c
            for cut in (box(bias - (SOCK_R + SLIDE), -SOCK_R, -CRADLE_T - 20, bias + SOCK_R + SLIDE, SOCK_R, -CRADLE_T - 1),
                        box(bias - (PIN_R + SLIDE), -20, -CRADLE_T - 4 - PIN_R, bias + PIN_R + SLIDE, 20, -CRADLE_T - 4 + PIN_R)):
                r = rs.BooleanDifference([c], [cut], True)
                c = r[0] if r else c
        c = rs.TransformObject(c, Rhino.Geometry.Transform.PlaneToPlane(Rhino.Geometry.Plane.WorldXY, tgt)) or c
        tag(c, name, CRADLE)
        if socket:
            # rod position in the slot, plus how far the slot bottom swings because the cradle is tilted
            o = tgt.Origin
            sx = o.X + (-CRADLE_T - 4) * tgt.ZAxis.X + bias * tgt.XAxis.X
            tilt = math.degrees(math.acos(max(-1.0, min(1.0, tgt.ZAxis.Z))))
            off = rod_x - sx
            margin = SLIDE - (abs(off) + 5.0 * math.tan(math.radians(tilt)))
            fits.append((name.split(" ")[0], off, tilt, margin, pad_w, hw))
            return off
        fits.append((name.split(" ")[0], 0.0, 0.0, 99.0, pad_w, hw))
        return 0.0

    PIN_R = 1.0 + FIT_PIN_FREE      # 2 mm cross pin rides in this slot
    SLIDE = 4.5                     # slot half-travel; sweep: worst |offset| + tilt swing = 3.8 mm
    SOCK_R = ROD_R + FIT_ROD_SOCKET
    rep = []
    fits = []
    for nm, x, e, r, ph in BODY_CAMS:
        off = cradle("Cradle_" + nm + " (glue under segment {})".format(flexi["saddle"][nm]), flexi["saddle"][nm], x, tops[nm],
                     bias=SLOT_BIAS[nm])
        rep.append("{} rod offset in cradle slot: {:+.1f} mm (allowed +/-{})".format(nm, off, SLIDE))
    off = cradle("Cradle_head (glue under head)", 0, HEAD_X, head_top, pad_l=16.0 * DRAGON_SCALE,
                 bias=SLOT_BIAS["head"])
    rep.append("Head rod offset in cradle slot: {:+.1f} mm".format(off))

    # chest mount: fixed cradle on the two posts
    cc = cradle("ChestMount (glue under segment {}, sits on posts)".format(flexi["chest"]), flexi["chest"], WING_X,
                CHEST_BASE, socket=False)
    mount = box(WING_X - 16, SHAFT_Y - 20, CHEST_POST_TOP - 7, WING_X + 16, SHAFT_Y + 20, CHEST_BASE - CRADLE_T)
    for (x, y) in post_pts:
        r = rs.BooleanDifference([mount], [cyl(P(x, y, CHEST_POST_TOP - 8), P(x, y, CHEST_POST_TOP), ROD_R + FIT_GLUE)], True)
        mount = r[0] if r else mount
    if not WINGS:
        tag(mount, "ChestMount_block (on posts)", CRADLE)
    else:

        def frame(pt, tan):
            t = rs.VectorUnitize(tan)
            xa = rs.VectorUnitize(rs.VectorCrossProduct((0, 0, 1), t))
            return rs.PlaneFromFrame(pt, xa, rs.VectorCrossProduct(t, xa))

        def tapered(p0, p1, r0, r1):
            d = rs.VectorCreate(p1, p0)
            crvs = [rs.AddCircle(frame(p0, d), r0), rs.AddCircle(frame(p1, d), r1)]
            lo = rs.AddLoftSrf(crvs)
            rs.DeleteObjects(crvs)
            if not lo:
                return None
            rs.CapPlanarHoles(lo[0])
            return lo[0]


        # ---- wings: hinged on ears beside the fixed chest; wing rod -> crossbar under the mount -> 2 links -> wing lugs
        layer("FlexiWings", (30, 60, 150))
        WMEMB, WBONE = (35, 70, 170), (235, 235, 240)
        FH_Y, FH_Z = 18.5, CHEST_BASE + 4.0          # hinge axis (both sides), just above the dragon's base line
        LEVER, CB_Y = 12.0, 18.5 + 12.0               # lug distance from hinge; crossbar link pins at SHAFT_Y +/- CB_Y
        REST = 15.0
        zc_mid = WING_ROD_TOP_MID
        th0 = math.radians(REST)
        LINK_U = math.hypot(FH_Y + LEVER * math.cos(th0) - CB_Y, FH_Z + LEVER * math.sin(th0) - zc_mid)

        def fw_theta(zcb):
            best, prev = None, None
            for i in range(-160, 181):
                d = i * 0.5
                t = math.radians(d)
                v = math.hypot(FH_Y + LEVER * math.cos(t) - CB_Y, FH_Z + LEVER * math.sin(t) - zcb) - LINK_U
                if prev is not None and (v > 0) != (prev[1] > 0):
                    root = prev[0] + (d - prev[0]) * prev[1] / (prev[1] - v)
                    if best is None or abs(root - REST) < abs(best - REST):
                        best = root
                prev = (d, v)
            return best if best is not None else REST

        wth = math.radians(fw_theta(zc))
        # ears on the chest mount (wing knuckle sits between them)
        for sy in (-1, 1):
            ya, yb = sorted((SHAFT_Y + sy * (FH_Y - 3.5), SHAFT_Y + sy * (FH_Y + 3.5)))
            for (xa, xb) in ((WING_X - 6, WING_X - 3), (WING_X + 3, WING_X + 6)):
                r = rs.BooleanUnion([mount, box(xa, ya, CHEST_BASE - CRADLE_T - 2, xb, yb, FH_Z + 3.5)], True)
                mount = r[0] if r else mount
            mount = tear_cut(mount, P(WING_X - 9, SHAFT_Y + sy * FH_Y, FH_Z), P(WING_X + 9, SHAFT_Y + sy * FH_Y, FH_Z),
                             1.5 + FIT_PIN_PRESS, (0, 0, 1))
        tag(mount, "ChestMount_block (on posts, wing hinge ears)", CRADLE)

        MT = WA_MT
        nb = (0.0, -math.sin(wth), math.cos(wth))      # back-wing membrane normal

        def Wb(u, v, off=0.0):
            return P(WING_X + u, SHAFT_Y + FH_Y + v * math.cos(wth) + nb[1] * off, FH_Z + v * math.sin(wth) + nb[2] * off)

        memb, det = build_wing_A(LEVER)               # built flat, then mapped onto the hinge
        org = Wb(0, 0, -WA_KZ)   # local (0,0,WA_KZ) lands on the hinge axis
        tgt = Rhino.Geometry.Plane(Rhino.Geometry.Point3d(org[0], org[1], org[2]), Rhino.Geometry.Vector3d(1, 0, 0),
                                   Rhino.Geometry.Vector3d(0, math.cos(wth), math.sin(wth)))
        xf = Rhino.Geometry.Transform.PlaneToPlane(Rhino.Geometry.Plane.WorldXY, tgt)
        memb = rs.TransformObject(memb, xf) or memb
        det = [rs.TransformObject(o, xf) or o for o in det]
        memb = tear_cut(memb, P(WING_X - 6, SHAFT_Y + FH_Y, FH_Z), P(WING_X + 6, SHAFT_Y + FH_Y, FH_Z), 1.5 + FIT_PIN_FREE, nb)
        memb = tear_cut(memb, Wb(-5, LEVER, 0), Wb(5, LEVER, 0), 1.0 + FIT_PIN_FREE, nb)
        # front wing = mirror of the back wing across the body's vertical mid-plane
        memb_f = rs.MirrorObject(memb, P(0, SHAFT_Y, 0), P(1, SHAFT_Y, 0), True)
        det_f = [rs.MirrorObject(o, P(0, SHAFT_Y, 0), P(1, SHAFT_Y, 0), True) for o in det]
        lug_b = Wb(0, LEVER, 0)
        for side, m_, d_, sy in (("Back", memb, det, 1), ("Front", memb_f, det_f, -1)):
            tag(m_, "Wing_{} membrane+knuckle+lug (print flat, colour 1)".format(side), WMEMB)
            for o in d_:
                tag(o, "Wing_{} bones-claws-scales (colour 2)".format(side), WBONE)
            tag(cyl(P(WING_X - 8, SHAFT_Y + sy * FH_Y, FH_Z), P(WING_X + 8, SHAFT_Y + sy * FH_Y, FH_Z), 1.5),
                "Wing_{}_hinge_pin_3mm".format(side), STEEL)
            lug = P(lug_b[0], SHAFT_Y + sy * (lug_b[1] - SHAFT_Y), lug_b[2])
            tag(cyl(P(WING_X, SHAFT_Y + sy * CB_Y, zc), lug, 1.5), "Wing_{}_link".format(side), STEEL)
        tag(cyl(P(WING_X, SHAFT_Y - CB_Y - 3, zc), P(WING_X, SHAFT_Y + CB_Y + 3, zc), 2.5), "Wing_crossbar", DOWEL)
        cut_list.append("PRINT Wing_Back + Wing_Front: flat, 2 colours (membrane {}mm + bones/claws/scales); 3mm hinge pins x2; links x2 {:.1f}mm c-c".format(MT, LINK_U))
        cut_list.append("Wing angle now {:.1f} deg".format(math.degrees(wth)))


    cut_list.append("Flexi Dragon by D3Craft (MakerWorld, Standard Digital File License): print as-is, coiled, "
                    "{} pieces / {} segments, scaled {:.0%}".format(n_pieces, len(nodes) - 1, DRAGON_SCALE))
    cut_list.append("PRINT cradles x{} + chest mount; glue with CA under the listed segments".format(len(BODY_CAMS) + 1))
    cut_list.append("Hardware: 2mm cross pins x5 (rod -> cradle), drill 2mm through each rod 4mm below its top")
    for (nm_, off_, tilt_, mg_, pw_, hw_) in fits:
        cut_list.append("FIT {:<16s} pad {:4.1f} mm wide under a {:4.1f} mm segment base | rod {:+.1f} mm, tilt {:4.1f} deg, slot margin {:+.1f} mm".format(
            nm_, pw_, 2 * hw_, off_, tilt_, mg_))
    cut_list.extend(rep)



# ------------------------------------------------------------------ FIT-TEST LADDER (print this first, ~30 min)
# Each fit gets 3 holes: design size -0.05 / design / +0.05 mm (radial), left to right inside its group.
# Vertical holes are in the base (as printed on cams/plates); horizontal ones are teardrops in the wall (as on the
# wing knuckle, ears, seam pins). Pick the hole that feels right in each group and set that FIT_* in the table.
layer("FitTest", (255, 140, 0))
FX, FY = -10.0, -75.0
STEP = 0.05
vert = [("cam D-bore", SHAFT_R + FIT_SHAFT_CAM, True), ("shaft run", SHAFT_R + FIT_SHAFT_RUN, False),
        ("rod guide", ROD_R + FIT_ROD_GUIDE, False), ("post glue", ROD_R + FIT_GLUE, False),
        ("rod socket", ROD_R + FIT_ROD_SOCKET, False), ("panel pin", 1.5 + FIT_PANEL_PIN, False)]
horiz = [("2mm free", 1.0 + FIT_PIN_FREE), ("3mm free", 1.5 + FIT_PIN_FREE), ("3mm press", 1.5 + FIT_PIN_PRESS),
         ("panel pin", 1.5 + FIT_PANEL_PIN)]
L_base = 6 + sum(3 * (2 * r + 3) + 4 for _, r, _ in vert)
base = box(FX, FY, 0, FX + L_base, FY + 20, 6)
x = FX + 5
legend = []
for nm_, r0, is_d in vert:
    xs_ = []
    for k in (-1, 0, 1):
        r = r0 + k * STEP
        x += r + 1.5
        cut = cyl(P(x, FY + 10, -1), P(x, FY + 10, 7), r)
        if is_d:
            keep = box(x - r - 1, FY + 10 - (SHAFT_FLAT + FIT_SHAFT_CAM + k * STEP), -2, x + r + 1, FY + 10 + r + 1, 8)
            d = rs.BooleanIntersection([cut], [keep], True)
            cut = d[0] if d else cut
        rr = rs.BooleanDifference([base], [cut], True)
        base = rr[0] if rr else base
        x += r + 1.5
    legend.append(nm_)
    x += 4
    # a notch on the front edge marks the start of each group
    rr = rs.BooleanDifference([base], [box(x - 2.5, FY - 1, 4, x - 1.5, FY + 1, 7)], True)
    base = rr[0] if rr else base
L_wall = 6 + sum(3 * (2 * r + 4) + 4 for _, r in horiz)
wall = box(FX, FY + 20, 0, FX + max(L_wall, 40), FY + 28, 14)
x = FX + 5
for nm_, r0 in horiz:
    for k in (-1, 0, 1):
        r = r0 + k * STEP
        x += r + 2
        wall = tear_cut(wall, P(x, FY + 19, 7), P(x, FY + 29, 7), r, (0, 0, 1))
        x += r + 2
    x += 4
u = rs.BooleanUnion([base, wall], True)
tag(u[0] if u else base, "FitTest_ladder (print first)", (255, 140, 0))
cut_list.append("PRINT FitTest ladder first (no supports). Base, vertical holes, groups L->R: " + ", ".join(legend) +
                ". Wall, teardrop holes, groups L->R: " + ", ".join(n for n, _ in horiz) +
                ". In each group: tight / design / loose (0.05 mm radial steps).")

# ------------------------------------------------------------------ PRINT-BED CHECK (every printed part)
PRINT_BED = 256.0

def print_dims(o):
    """smallest bounding box over rotations about X (finds the flat orientation of tilted wings/cradles)"""
    best = None
    c = rs.BoundingBox(o)[0]
    for a in range(-90, 91, 5):
        pl = rs.RotatePlane(rs.WorldXYPlane(), a, (1, 0, 0))
        bb = rs.BoundingBox(o, pl)
        d = sorted([rs.Distance(bb[0], bb[1]), rs.Distance(bb[0], bb[3]), rs.Distance(bb[0], bb[4])])
        if best is None or d[0] < best[0]:
            best = d
    return best

printed = []
for lay, skip in (("Box", ("acrylic",)), ("Cams", ()), ("Cradles", ()), ("FitTest", ()), ("FlexiWings", ("pin", "link", "crossbar")),
                  ("Followers", ("_rod", "Post")), ("Motor", ("Coupler", "gearmotor", "Barrel", "Speed", "Wire")),
                  ("Shaft", ("dowel", "steel"))):
    full = "Automaton::" + lay
    if not rs.IsLayer(full):
        continue
    for o in rs.ObjectsByLayer(full) or []:
        nm = rs.ObjectName(o) or "?"
        if any(k in nm for k in skip) or not (rs.IsPolysurface(o) or rs.IsSurface(o)):
            continue
        printed.append((nm, print_dims(o)))
if flexi:
    rb = rs.BoundingBox(rs.ObjectsByLayer(FLEXI_LAYER))
    printed.append(("Flexi dragon (coiled print layout) x{:.2f}".format(DRAGON_SCALE),
                    sorted([(rb[1][0] - rb[0][0]) * DRAGON_SCALE, (rb[3][1] - rb[0][1]) * DRAGON_SCALE,
                            (rb[4][2] - rb[0][2]) * DRAGON_SCALE])))
too_big = [(n, d) for n, d in printed if d[2] > PRINT_BED]

rs.CurrentLayer("Automaton")
rs.EnableRedraw(True)
rs.ZoomExtents(all=True)

print("=== Dragon automaton @ shaft angle {:.0f} deg ===".format(ANGLE))
if not flexi and WINGS:
    print("Wing angle: {:.1f} deg   link length: {:.1f} mm".format(theta_deg, LINK))
print("Head lift: {:.1f} mm (flat follower, lowest {:.1f})".format(r_top - SNAIL_HMIN, SNAIL_HMIN))
print("--- cut list ---")
for line in cut_list:
    print(" - " + line)
print("--- print-bed check ({:.0f} mm cube): {} printed parts, {} too big ---".format(PRINT_BED, len(printed), len(too_big)))
for n, d in sorted(printed, key=lambda t: -t[1][2])[:8]:
    print("   {:<58s} {:6.1f} x {:6.1f} x {:6.1f}".format(n[:58], d[2], d[1], d[0]))
for n, d in too_big:
    print("   TOO BIG: " + n)

