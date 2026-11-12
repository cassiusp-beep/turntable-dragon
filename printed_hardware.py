# -*- coding: utf-8 -*-
"""Printed replacements for the dowels and pins (no wood or steel needed except the camshaft).
Run in Rhino AFTER dragon_automaton.py (shaft angle 0). Reads rod/post sizes from the model, builds every part
lying flat on its print face, checks the wing T-piece against everything it could touch over its full stroke,
and writes 08_*.stl into ./STL.

Parts (all printed lying down, so pin holes print vertical = round):
  push rods x5   6.0 mm, 0.4 mm flat underside, 1.9 mm hole 3 mm below the top for a 1.75 mm filament pin,
                 bottom 6 mm necked to 5.7 mm so it glues into the foot socket without forcing
  wing rod + crossbar as ONE T-piece; crossbar ends have bosses with 2.25 mm holes for filament links
  shoulder posts x2  top 8 mm necked to 5.7 mm for the chest-mount glue socket
  3 mm pins x4  (2 wing hinges + 2 spare; the laser-cut box needs no seam pins), 16 mm, chamfered
Filament (1.75 mm, the stuff you print with) replaces the 2 mm cross pins and the brass link wire.
"""
import rhinoscriptsyntax as rs
import Rhino
import math
import os
import struct

OUT = "/Users/cassiuspalacio/Documents/UC Berkeley TDF/PhysComp/Nov 9/STL"
R = 3.0              # rod radius (same as the dowel it replaces)
FLAT = 0.4           # flat on the underside for bed contact
NECK_R = 2.85        # glue ends: 5.7 mm into a 6.3 mm design socket (prints ~6.1)
FIL_R = 0.875        # 1.75 mm filament
PIN_HOLE_R = 1.4     # rod cross-pin hole: 2.8 design. Measured: 2.3 drawn printed < 1.75 on this printer (~0.6 mm shrink), so +0.5
LINK_HOLE_R = 1.55   # crossbar link holes: 3.1 design -> ~2.5 printed with the measured shrink, filament turns freely
CB_R = 2.8           # crossbar radius (was a 5 mm dowel); center shares the rod's center height
BOSS_R = 3.5
PIN3_R, PIN3_L, PIN3_FLAT = 1.5, 16.0, 0.3
PIN_BELOW_TOP = 3.0  # cradle slot centre is 3 mm under the socket ceiling the rod top touches

ZC = R - FLAT        # rod axis height above the bed


def P(x, y, z):
    return Rhino.Geometry.Point3d(x, y, z)


def cylb(p0, p1, r):
    ax = p1 - p0
    c = Rhino.Geometry.Circle(Rhino.Geometry.Plane(p0, ax), r)
    return Rhino.Geometry.Cylinder(c, ax.Length).ToBrep(True, True)


def boxb(x0, y0, z0, x1, y1, z1):
    return Rhino.Geometry.Box(Rhino.Geometry.BoundingBox(P(x0, y0, z0), P(x1, y1, z1))).ToBrep()


TOLR = 0.001


def union(bs):
    r = Rhino.Geometry.Brep.CreateBooleanUnion(bs, TOLR)
    if not r or len(r) != 1:
        raise Exception("union gave {}".format(len(r) if r else 0))
    return r[0]


def diff(a, cutters):
    r = Rhino.Geometry.Brep.CreateBooleanDifference([a], cutters, TOLR)
    if not r or len(r) != 1:
        raise Exception("difference gave {}".format(len(r) if r else 0))
    return r[0]


def bed_cut(b, xmax, ymax):
    return diff(b, [boxb(-20, -ymax - 20, -20, xmax + 20, ymax + 20, 0)])


def rod(L, neck_bottom=0.0, neck_top=0.0, pin_hole=True):
    """rod along +X from 0..L, axis at z=ZC, flat underside at z=0"""
    parts = [cylb(P(neck_bottom, 0, ZC), P(L - neck_top, 0, ZC), R)]
    if neck_bottom:
        parts.append(cylb(P(0, 0, ZC), P(neck_bottom + 0.5, 0, ZC), NECK_R))
    if neck_top:
        parts.append(cylb(P(L - neck_top - 0.5, 0, ZC), P(L, 0, ZC), NECK_R))
    b = union(parts) if len(parts) > 1 else parts[0]
    b = bed_cut(b, L, 10)
    if pin_hole:
        b = diff(b, [cylb(P(L - PIN_BELOW_TOP, 0, -1), P(L - PIN_BELOW_TOP, 0, 10), PIN_HOLE_R)])
    return b


def pin3(PIN3_R=PIN3_R, PIN3_L=PIN3_L):
    """3 mm pin with 0.3 mm end chamfers: revolve a profile about the pin axis, then cut the flat"""
    zc = PIN3_R - PIN3_FLAT
    c = 0.3
    prof = [P(0, 0, zc), P(0, 0, zc + PIN3_R - c), P(c, 0, zc + PIN3_R), P(PIN3_L - c, 0, zc + PIN3_R),
            P(PIN3_L, 0, zc + PIN3_R - c), P(PIN3_L, 0, zc), P(0, 0, zc)]
    crv = Rhino.Geometry.PolylineCurve(prof)
    srf = Rhino.Geometry.RevSurface.Create(crv, Rhino.Geometry.Line(P(0, 0, zc), P(1, 0, zc)))
    b = Rhino.Geometry.Brep.CreateFromRevSurface(srf, True, True)
    if b.SolidOrientation == Rhino.Geometry.BrepSolidOrientation.Inward:
        b.Flip()
    return bed_cut(b, PIN3_L, 5)


# ------------------------------------------------------------------ read the assembled model
def obj_by_name(prefix, layer=None):
    for lay in ([layer] if layer else rs.LayerChildren("Automaton")):
        for o in rs.ObjectsByLayer(lay) or []:
            if (rs.ObjectName(o) or "").startswith(prefix):
                return o
    return None


def zspan(o):
    bb = rs.BoundingBox(o)
    return bb[0][2], bb[4][2], (bb[0][0] + bb[6][0]) / 2.0, (bb[0][1] + bb[6][1]) / 2.0


rods = {}
for nm in ("R1_tail", "R2_back", "R3_belly", "R4_neck", "HeadRod", "WingRod"):
    o = obj_by_name(nm + "_rod", "Automaton::Followers")
    z0, z1, x, y = zspan(o)
    rods[nm] = (z1 - z0, z0, x, y)
posts = {}
for i in (1, 2):
    z0, z1, x, y = zspan(obj_by_name("ShoulderPost_{}".format(i), "Automaton::Followers"))
    posts[i] = (z1 - z0, z0, x, y)
cb = rs.BoundingBox(obj_by_name("Wing_crossbar", "Automaton::FlexiWings"))
CB_HALF = (cb[6][1] - cb[0][1]) / 2.0          # includes the 3 mm overhang past each link
CB_Y = CB_HALF - 3.0
WING_E, WING_ROD_TOP_MID = 6.0, 143.0   # same as dragon_automaton.py (flexi)

# ------------------------------------------------------------------ build print-oriented parts
parts = {}   # file -> list of breps (already on the bed)
for nm in ("R1_tail", "R2_back", "R3_belly", "R4_neck", "HeadRod"):
    L = rods[nm][0]
    parts["08_Rod_{}.stl".format(nm.replace("Rod", "") if nm == "HeadRod" else nm)] = [rod(L, neck_bottom=6.0)]

# wing T: rod 0..Lw along X, crossbar along Y at x = Lw (its centre = old rod top)
Lw = rods["WingRod"][0]
t_parts = [cylb(P(6.0, 0, ZC), P(Lw, 0, ZC), R), cylb(P(0, 0, ZC), P(6.5, 0, ZC), NECK_R),
           cylb(P(Lw, -CB_HALF, ZC), P(Lw, CB_HALF, ZC), CB_R)]
for s in (-1, 1):
    t_parts.append(cylb(P(Lw, s * CB_Y, ZC - R + FLAT - 1), P(Lw, s * CB_Y, ZC + (ZC - 0.0)), BOSS_R))
T = bed_cut(union(t_parts), Lw + 10, CB_HALF + 5)
T = diff(T, [cylb(P(Lw, s * CB_Y, -1), P(Lw, s * CB_Y, 10), LINK_HOLE_R) for s in (-1, 1)])
parts["08_WingRod_T_with_crossbar.stl"] = [T]

for i in (1, 2):
    parts["08_ShoulderPost_{}.stl".format(i)] = [rod(posts[i][0], neck_top=8.0, pin_hole=False)]

pins = []
# size-coded hinge pins: printed-on-its-side pins come out oversize, so print a range and use the one that fits.
# Diameter is coded by LENGTH: 2.5 mm -> 16 mm long, 2.6 -> 17, 2.7 -> 18, 2.8 -> 19 (3 of each).
PIN_SIZES = [(1.25, 16.0), (1.30, 17.0), (1.35, 18.0), (1.40, 19.0)]
for j, (pr, pl) in enumerate(PIN_SIZES):
    for k in range(3):
        p = pin3(pr, pl)
        p.Translate(Rhino.Geometry.Vector3d(k * 24.0, j * 8.0, 0))
        pins.append(p)
parts["08_Pins_hinge_SIZE_SET_x12.stl"] = pins

# ------------------------------------------------------------------ check the wing T in the assembly over its stroke
lay = "Automaton::PrintedHW_check"
if rs.IsLayer(lay):
    rs.DeleteObjects(rs.ObjectsByLayer(lay))
else:
    rs.AddLayer(lay, (255, 120, 0))
_, wz0, wx, wy = rods["WingRod"]
src = Rhino.Geometry.Plane(P(0, 0, ZC), Rhino.Geometry.Vector3d.XAxis, Rhino.Geometry.Vector3d.YAxis)
dst = Rhino.Geometry.Plane(P(wx, wy, wz0), Rhino.Geometry.Vector3d.ZAxis, -Rhino.Geometry.Vector3d.YAxis)
T_asm = T.DuplicateBrep()
T_asm.Transform(Rhino.Geometry.Transform.PlaneToPlane(src, dst))
tid = rs.coerceguid(Rhino.RhinoDoc.ActiveDoc.Objects.AddBrep(T_asm))
rs.ObjectLayer(tid, lay)
rs.ObjectName(tid, "WingRod_T (printed, assembled at angle 0)")

mp = Rhino.Geometry.MeshingParameters.Default


def as_mesh(b):
    m = Rhino.Geometry.Mesh()
    for q in Rhino.Geometry.Mesh.CreateFromBrep(b, mp) or []:
        m.Append(q)
    return m


others = []
for l in ("Box", "Cradles", "FlexiWings", "FlexiDragon", "Followers"):
    for o in rs.ObjectsByLayer("Automaton::" + l) or []:
        nm = rs.ObjectName(o) or ""
        if nm.startswith("WingRod") or nm.startswith("Wing_crossbar") or "_link" in nm:
            continue
        g = rs.coercegeometry(o)
        m = as_mesh(g) if isinstance(g, Rhino.Geometry.Brep) else g if isinstance(g, Rhino.Geometry.Mesh) else None
        if m:
            others.append((nm, m, m.GetBoundingBox(True)))
# the wing rod passes through the top plate + guide bar holes on purpose: test the crossbar head only
head = diff(T_asm, [boxb(wx - 50, wy - 50, wz0 - 10, wx + 50, wy + 50, wz0 + Lw - BOSS_R - 0.5)])
hits, near = [], 99.0
zc_now = wz0 + Lw
dzs = [WING_ROD_TOP_MID - zc_now + WING_E * k / 6.0 for k in range(-6, 7)]
for dz in dzs:
    h = head.DuplicateBrep()
    h.Translate(0, 0, dz)
    hm = as_mesh(h)
    hb = hm.GetBoundingBox(True)
    hb.Inflate(5)
    for nm, m, bb in others:
        if not Rhino.Geometry.BoundingBox.Intersection(hb, bb).IsValid:
            continue
        x = Rhino.Geometry.Intersect.Intersection.MeshMeshFast(hm, m)
        if x and len(x):
            hits.append((dz, nm[:28]))
        else:
            for v in hm.Vertices:
                cp = m.ClosestPoint(Rhino.Geometry.Point3d(v))
                if cp.IsValid:
                    near = min(near, cp.DistanceTo(Rhino.Geometry.Point3d(v)))

# ------------------------------------------------------------------ printed camshaft: 2 D-profile pieces + glued sleeve
# 8 mm PLA, D flat printed straight onto the bed (so the flat is dead flat and the round part has no seam on it).
# The D drives the cams (no grub screws needed: glue each cam once it is in place; the D sets its phase).
SH_R, SH_FLAT, FIT_CAM = 4.0, 3.5, 0.20      # match dragon_automaton.py (SHAFT_R, SHAFT_FLAT, FIT_SHAFT_CAM)
SLV_R, SLV_L = 7.0, 24.0
sh = rs.BoundingBox(obj_by_name("Camshaft_8mm_steel_D-shaft", "Automaton::Shaft"))
SX0, SX1, SY, SZ = sh[0][0], sh[6][0], (sh[0][1] + sh[6][1]) / 2.0, (sh[0][2] + sh[6][2]) / 2.0
SX0 = -30.0   # camshaft now sticks out 30 mm past the left wall for the JS-30 motor coupler (motor_cover.py)
# joint: middle of the widest gap between parts that sit on the shaft (inside the box)
occ = []
for l in ("Cams", "Box", "Followers"):
    for o in rs.ObjectsByLayer("Automaton::" + l) or []:
        b_ = rs.BoundingBox(o)
        if b_ and b_[0][2] < SZ + 15 and b_[6][2] > SZ - 15 and b_[0][1] < SY + 15 and b_[6][1] > SY - 15:
            occ.append((b_[0][0], b_[6][0]))
occ.sort()
gaps, reach = [], occ[0][1]
for a_, b_ in occ[1:]:
    if a_ > reach:
        gaps.append((a_ - reach, reach, a_))
    reach = max(reach, b_)
# widest gap that fits the sleeve with 4 mm to spare and keeps both pieces under 250 mm
ok_gaps = [g for g in gaps if g[0] >= SLV_L + 8 and max((g[1] + g[2]) / 2 - SX0, SX1 - (g[1] + g[2]) / 2) <= 250]
glen, ga, gb = max(ok_gaps)
JX = (ga + gb) / 2.0


def d_shaft(L):
    b = cylb(P(0, 0, SH_FLAT), P(L, 0, SH_FLAT), SH_R)
    return bed_cut(b, L, 10)


def sleeve():
    b = cylb(P(0, 0, 0), P(0, 0, SLV_L), SLV_R)
    bore = cylb(P(0, 0, -1), P(0, 0, SLV_L + 1), SH_R + FIT_CAM)
    keep = boxb(-10, -(SH_FLAT + FIT_CAM), -2, 10, 10, SLV_L + 2)
    bore = Rhino.Geometry.Brep.CreateBooleanIntersection(bore, keep, TOLR)[0]
    return diff(b, [bore])


parts["08_Shaft_A_left.stl"] = [d_shaft(JX - SX0)]
parts["08_Shaft_B_right.stl"] = [d_shaft(SX1 - JX)]
parts["08_Shaft_joint_sleeve.stl"] = [sleeve()]

# sleeve in the assembly: anything it touches?
sl = cylb(P(JX - SLV_L / 2, SY, SZ), P(JX + SLV_L / 2, SY, SZ), SLV_R)
slm = as_mesh(sl)
sb = slm.GetBoundingBox(True)
sl_hits = []
for nm, m, bb in others:
    if Rhino.Geometry.BoundingBox.Intersection(sb, bb).IsValid:
        x = Rhino.Geometry.Intersect.Intersection.MeshMeshFast(slm, m)
        if x and len(x):
            sl_hits.append(nm[:28])
sid = rs.coerceguid(Rhino.RhinoDoc.ActiveDoc.Objects.AddBrep(sl))
rs.ObjectLayer(sid, lay)
rs.ObjectName(sid, "Shaft joint sleeve (printed)")

# stiffness, simply supported spans between bearings, 2 N lumped at mid-span (generous: rods + dragon ~100 g total)
E_PLA, G_PLA = 3500.0, 1300.0
I_ = math.pi * (2 * SH_R) ** 4 / 64.0
J_ = 2 * I_
bearings = [0 + 3, 140, 300 - 3]
span = max(bearings[i + 1] - bearings[i] for i in range(len(bearings) - 1))
defl = 2.0 * span ** 3 / (48 * E_PLA * I_)
twist = math.degrees(50.0 * (SX1 - SX0) / (G_PLA * J_))   # 50 N.mm (0.05 N.m) end to end, worst case

# ------------------------------------------------------------------ export
def to_mesh(brep):
    p = Rhino.Geometry.MeshingParameters()
    p.Tolerance = 0.01
    p.MinimumEdgeLength = 0.0001
    p.RefineGrid = True
    p.SimplePlanes = True
    m = as_mesh_p(brep, p)
    m.Vertices.CombineIdentical(True, True)
    m.Weld(math.pi)
    m.Faces.ConvertQuadsToTriangles()
    if not m.IsClosed:
        m.HealNakedEdges(0.02)
        m.Vertices.CombineIdentical(True, True)
    m.Normals.ComputeNormals()
    m.UnifyNormals()
    m.Compact()
    return m


def as_mesh_p(b, p):
    m = Rhino.Geometry.Mesh()
    for q in Rhino.Geometry.Mesh.CreateFromBrep(b, p) or []:
        m.Append(q)
    return m


def write_stl(meshes, path):
    tris = []
    for m in meshes:
        v = m.Vertices
        for f in m.Faces:
            tris.append((v[f.A], v[f.B], v[f.C]))
    with open(path, "wb") as fh:
        fh.write(b"dragon automaton printed hardware, mm".ljust(80, b" "))
        fh.write(struct.pack("<I", len(tris)))
        for a, b, c in tris:
            ux, uy, uz = b.X - a.X, b.Y - a.Y, b.Z - a.Z
            vx, vy, vz = c.X - a.X, c.Y - a.Y, c.Z - a.Z
            nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
            ln = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            fh.write(struct.pack("<12fH", nx / ln, ny / ln, nz / ln, a.X, a.Y, a.Z, b.X, b.Y, b.Z, c.X, c.Y, c.Z, 0))


report = []
for fn in sorted(parts):
    ms = [to_mesh(b) for b in parts[fn]]
    bb = Rhino.Geometry.BoundingBox.Empty
    for m in ms:
        bb.Union(m.GetBoundingBox(True))
    mv = Rhino.Geometry.Transform.Translation(-bb.Min.X, -bb.Min.Y, -bb.Min.Z)
    for m in ms:
        m.Transform(mv)
    write_stl(ms, os.path.join(OUT, fn))
    d = bb.Max - bb.Min
    report.append("{:<34s} {:6.1f} x {:5.1f} x {:4.1f}  {}".format(fn, d.X, d.Y, d.Z,
                  "closed" if all(m.IsClosed for m in ms) else "OPEN"))

print("\n".join(report))
print("rod lengths:", dict((k, round(v[0], 1)) for k, v in rods.items()), "posts:", dict((k, round(v[0], 1)) for k, v in posts.items()))
print("crossbar link holes at +/-{:.1f} mm".format(CB_Y))
print("crossbar now z {:.1f}, mid {:.1f}; ".format(zc_now, WING_ROD_TOP_MID) + "wing T head over +/-{} mm stroke: hits {} | nearest other part {:.2f} mm".format(WING_E, hits or "none", near))
print("shaft joint at x {:.1f} (gap {:.1f}..{:.1f}); pieces {:.1f} + {:.1f} mm; sleeve touches: {}".format(
    JX, ga, gb, JX - SX0, SX1 - JX, sl_hits or "nothing"))
print("shaft: worst span {:.0f} mm -> {:.2f} mm sag under 2 N; twist {:.1f} deg end to end at 0.05 N.m".format(span, defl, twist))
