# -*- coding: utf-8 -*-
"""Motor bracket, coupler size set and drop-over cover for the JS-30 (300-series) gear motor.
Run in Rhino. World frame = dragon_automaton.py: left end wall outer face at x = 0, box depth y 0..120,
camshaft axis y = 60, z = 50. The camshaft now sticks out 30 mm past the wall (printed shaft A is 16 mm longer).

Designed to NOT depend on the motor's exact size (no datasheet; sellers disagree):
  - bracket: C-channel glued to the wall, motor face plate 50 mm out. The motor's ears are glued (CA) to the plate
    AFTER the coupler has lined the shafts up, so the shaft position and ear spacing don't need to be known.
  - coupler: D-bore slides on the camshaft; the motor end comes in 4 bore sizes (3.5 / 4.5 / 5.5 / 6.5 mm drawn,
    marked with 1-4 rings). Use the one that slips onto the motor shaft, then CA it.
  - cover: open bottom and open wall side; it drops over motor, Uno and H-bridge and can be lifted off.
"""
import rhinoscriptsyntax as rs
import Rhino
import os
import struct
import math

OUT = "/Users/cassiuspalacio/Documents/UC Berkeley TDF/PhysComp/Nov 9/STL"
SY, SZ = 60.0, 50.0
FACE_X = -50.0            # motor mounting face (plate outer face)
PLATE_T = 4.0
CAM_END = -30.0           # left end of the camshaft
D_R, D_FLAT = 4.0 + 0.20, 3.5 + 0.20     # camshaft D-bore (same fit as the cams)
COUP_R, COUP_L, MOTOR_DEPTH, WEB = 8.0, 36.0, 14.0, 2.0
MOTOR_BORES = [3.5, 4.5, 5.5, 6.5]
COVER = dict(x0=-118.0, x1=0.0, y0=0.0, y1=120.0, z1=84.0, t=2.4)


def P(x, y, z):
    return Rhino.Geometry.Point3d(x, y, z)


def boxb(x0, y0, z0, x1, y1, z1):
    return Rhino.Geometry.Box(Rhino.Geometry.BoundingBox(P(x0, y0, z0), P(x1, y1, z1))).ToBrep()


def cylb(p0, p1, r):
    ax = p1 - p0
    return Rhino.Geometry.Cylinder(Rhino.Geometry.Circle(Rhino.Geometry.Plane(p0, ax), r), ax.Length).ToBrep(True, True)


TOL = 0.001


def union(bs):
    r = Rhino.Geometry.Brep.CreateBooleanUnion(bs, TOL)
    if not r or len(r) != 1:
        raise Exception("union -> %d" % (len(r) if r else 0))
    return r[0]


def diff(a, cs):
    r = Rhino.Geometry.Brep.CreateBooleanDifference([a], cs, TOL)
    if not r or len(r) != 1:
        raise Exception("diff -> %d" % (len(r) if r else 0))
    return r[0]


# ---------------------------------------------------------------- bracket (world position)
bx0, bx1 = FACE_X, FACE_X + PLATE_T
plate = boxb(bx0, SY - 30, SZ - 30, bx1, SY + 30, SZ + 30)
flange_lo = boxb(bx0, SY - 30, SZ - 30, 0.0, SY + 30, SZ - 26)
flange_hi = boxb(bx0, SY - 30, SZ + 26, 0.0, SY + 30, SZ + 30)
ribs = [boxb(bx0, y, SZ - 26, bx1 + 6, y + 4, SZ + 26) for y in (SY - 30, SY + 26)]
bracket = union([plate, flange_lo, flange_hi] + ribs)
bracket = diff(bracket, [cylb(P(bx0 - 1, SY, SZ), P(bx1 + 7, SY, SZ), 12.0)])     # boss + coupler clearance

# ---------------------------------------------------------------- couplers (world position for the check, then laid flat)
def coupler(bore_d, rings):
    c = cylb(P(0, 0, 0), P(0, 0, COUP_L), COUP_R)
    # camshaft D-bore from z = 0 (printed end down), motor bore from the top
    dcyl = cylb(P(0, 0, -1), P(0, 0, COUP_L - MOTOR_DEPTH - WEB), D_R)
    keep = boxb(-10, -D_FLAT, -2, 10, 10, COUP_L)
    dbore = Rhino.Geometry.Brep.CreateBooleanIntersection(dcyl, keep, TOL)[0]
    mb = cylb(P(0, 0, COUP_L - MOTOR_DEPTH), P(0, 0, COUP_L + 1), bore_d / 2.0)
    cut = [dbore, mb]
    for k in range(rings):           # size marks: shallow grooves near the motor end
        z = COUP_L - 3 - 3 * k
        ring = diff(cylb(P(0, 0, z - 0.6), P(0, 0, z + 0.6), COUP_R + 1), [cylb(P(0, 0, z - 1), P(0, 0, z + 1), COUP_R - 0.6)])
        cut.append(ring)
    return diff(c, cut)


couplers = [coupler(d, i + 1) for i, d in enumerate(MOTOR_BORES)]

# ---------------------------------------------------------------- cover (world position)
c = COVER
outer = boxb(c["x0"], c["y0"], 0.0, c["x1"], c["y1"], c["z1"])
inner = boxb(c["x0"] + c["t"], c["y0"] + c["t"], -1.0, c["x1"] + 1.0, c["y1"] - c["t"], c["z1"] - c["t"])
cover = diff(outer, [inner])
cuts = [
    boxb(c["x0"] - 1, 4.0, -1.0, c["x0"] + c["t"] + 1, 44.0, 20.0),          # Uno USB-B + barrel jack, outer end
    boxb(-90.0, c["y1"] - c["t"] - 1, -1.0, -66.0, c["y1"] + 1, 12.0),        # wall-adapter cable, back face
]
cuts += [boxb(-60.0 + 7 * k, c["y1"] - c["t"] - 1, 30.0, -57.0 + 7 * k, c["y1"] + 1, 60.0) for k in range(5)]  # vents by the H-bridge
cover = diff(cover, cuts)

# ---------------------------------------------------------------- checks against the model
lay = "Automaton::MotorCover_check"
if rs.IsLayer(lay):
    rs.DeleteObjects(rs.ObjectsByLayer(lay))
else:
    rs.AddLayer(lay, (40, 160, 120))
doc = Rhino.RhinoDoc.ActiveDoc
ids = {}
for nm, b in (("bracket", bracket), ("cover", cover)):
    i = doc.Objects.AddBrep(b)
    rs.ObjectLayer(i, lay)
    rs.ObjectName(i, "Motor " + nm)
    ids[nm] = i
cp = couplers[2].DuplicateBrep()
cp.Transform(Rhino.Geometry.Transform.PlaneToPlane(Rhino.Geometry.Plane.WorldXY,
             Rhino.Geometry.Plane(P(FACE_X + 1.0 + COUP_L, SY, SZ), Rhino.Geometry.Vector3d(0, -1, 0), Rhino.Geometry.Vector3d(0, 0, 1))))
# coupler axis: its local +z points toward -x (motor end at FACE_X + 1, D-bore end toward the wall)
i = doc.Objects.AddBrep(cp)
rs.ObjectLayer(i, lay)
rs.ObjectName(i, "Motor coupler (5.5)")
ids["coupler"] = i
cb = cp.GetBoundingBox(True)
report = []
dlo, dhi = FACE_X + 1 + MOTOR_DEPTH + WEB, FACE_X + 1 + COUP_L
report.append("coupler spans x %.1f..%.1f; D-bore on camshaft for %.1f mm; coupler end %.1f mm from the wall" % (
    cb.Min.X, cb.Max.X, min(dhi, 0.0) - max(dlo, CAM_END), -cb.Max.X))
mp_ = Rhino.Geometry.MeshingParameters.Default


def as_mesh(b):
    m = Rhino.Geometry.Mesh()
    for q in Rhino.Geometry.Mesh.CreateFromBrep(b, mp_) or []:
        m.Append(q)
    return m


hits = []
for o in rs.ObjectsByLayer("Automaton::Box") or []:
    nm = rs.ObjectName(o) or ""
    g = rs.coercebrep(o)
    if g is None:
        continue
    gm = as_mesh(g)
    for k in ("bracket", "cover", "coupler"):
        b = rs.coercebrep(ids[k])
        if not Rhino.Geometry.BoundingBox.Intersection(b.GetBoundingBox(True), g.GetBoundingBox(True)).IsValid:
            continue
        bm = as_mesh(b)
        bm.Translate(-0.2, 0, 0)         # step off the glue face against the wall (away from it)
        x = Rhino.Geometry.Intersect.Intersection.MeshMeshFast(bm, gm)
        if x and len(x):
            hits.append((k, nm[:24]))
report.append("overlaps with the box (beyond the glue face): %s" % (hits or "none"))
cvb = cover.GetBoundingBox(True)
report.append("cover inside: x %.1f..0 (%.0f deep), y %.1f..%.1f, height %.1f" % (
    cvb.Min.X + c["t"], -(cvb.Min.X + c["t"]), c["t"], c["y1"] - c["t"], c["z1"] - c["t"]))
report.append("room behind the motor face for the motor body: %.0f mm (JS-30 gearbox + can are ~45-55)" % (FACE_X - (cvb.Min.X + c["t"])))
report.append("room under the camshaft axis for the Uno/H-bridge: %.0f mm to the motor's underside if the gearbox is 32 mm" % (SZ - 16))


# ---------------------------------------------------------------- export (print orientation)
def to_mesh(b):
    p = Rhino.Geometry.MeshingParameters()
    p.Tolerance = 0.01
    p.MinimumEdgeLength = 0.0001
    p.RefineGrid = True
    p.SimplePlanes = True
    m = as_mesh_p(b, p)
    m.Vertices.CombineIdentical(True, True)
    m.Weld(math.pi)
    m.Faces.ConvertQuadsToTriangles()
    if not m.IsClosed:
        m.HealNakedEdges(0.02)
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
        fh.write(b"dragon automaton motor parts, mm".ljust(80, b" "))
        fh.write(struct.pack("<I", len(tris)))
        for a, b, cc in tris:
            ux, uy, uz = b.X - a.X, b.Y - a.Y, b.Z - a.Z
            vx, vy, vz = cc.X - a.X, cc.Y - a.Y, cc.Z - a.Z
            nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
            ln = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            fh.write(struct.pack("<12fH", nx / ln, ny / ln, nz / ln, a.X, a.Y, a.Z, b.X, b.Y, b.Z, cc.X, cc.Y, cc.Z, 0))


def lay_down(b, xf):
    b = b.DuplicateBrep()
    b.Transform(xf)
    bb = b.GetBoundingBox(True)
    b.Transform(Rhino.Geometry.Transform.Translation(-bb.Min.X, -bb.Min.Y, -bb.Min.Z))
    return b


rot_y = Rhino.Geometry.Transform.Rotation(math.radians(-90), Rhino.Geometry.Vector3d.YAxis, P(0, 0, 0))   # -x face down
flip = Rhino.Geometry.Transform.Rotation(math.pi, Rhino.Geometry.Vector3d.XAxis, P(0, 0, 0))              # top face down
out = {
    "09_Motor_bracket.stl": [lay_down(bracket, rot_y)],
    "09_Motor_cover.stl": [lay_down(cover, flip)],
}
cs = []
for k, cpl in enumerate(couplers):
    cpl = cpl.DuplicateBrep()
    cpl.Translate(k * 22.0, 0, 0)
    cs.append(cpl)
out["09_Motor_couplers_x4_rings1-4.stl"] = cs
for fn, bs in out.items():
    ms = [to_mesh(b) for b in bs]
    bb = Rhino.Geometry.BoundingBox.Empty
    for m in ms:
        bb.Union(m.GetBoundingBox(True))
    mv = Rhino.Geometry.Transform.Translation(-bb.Min.X, -bb.Min.Y, -bb.Min.Z)
    for m in ms:
        m.Transform(mv)
    write_stl(ms, os.path.join(OUT, fn))
    d = bb.Max - bb.Min
    report.append("%-36s %5.1f x %5.1f x %5.1f  %s" % (fn, d.X, d.Y, d.Z, "closed" if all(m.IsClosed for m in ms) else "OPEN"))
print("\n".join(report))
