# -*- coding: utf-8 -*-
"""Export every printed part of the dragon automaton as a print-ready STL.
Run in Rhino AFTER dragon_automaton.py (shaft angle 0). Each part is laid on its print face
(the face chosen so horizontal teardrop holes point up and nothing needs supports), moved to
the bed origin, meshed finely, and written as binary STL into ./STL with a manifest.
Not exported: the flexi dragon (print D3Craft's original file at 125% in Bambu Studio),
the acrylic front (laser cut), dowels, shaft, pins, wire and electronics.
"""
import rhinoscriptsyntax as rs
import Rhino
import os
import struct
import math

OUT = "/Users/cassiuspalacio/Documents/UC Berkeley TDF/PhysComp/Nov 9/STL"
BED = 256.0
TOL = 0.01      # mm max mesh deviation

DOWN = {"z": (0, 0, -1), "x": (-1, 0, 0), "y": (0, -1, 0)}

# (layer, name prefix, file prefix, down-direction key, colour/note)
RULES = [
    ("FitTest", "FitTest_ladder", "00", "z", ""),
    ("Box", "Floor", "01", "z", ""), ("Box", "TopPlate", "01", "z", ""), ("Box", "RodGuideBar", "01", "z", ""),
    ("Box", "BackPanel", "01", "y", "teardrop seam pins face up"), ("Box", "EndWall", "01", "x", ""),
    ("Box", "GuideBlock", "01", "z", ""), ("Box", "Support_Aframe", "01", "x", ""),
    ("Cams", "Cam_", "02", "x", "hub up"),
    ("Followers", "", "03", "z", "feet: disc down"),
    ("Cradles", "Cradle_", "04", "z", "boss down"), ("Cradles", "ChestMount (glue", "04", "z", "pad"),
    ("Cradles", "ChestMount_block", "05", "z", "base down"), ("FlexiWings", "ChestMount_block", "05", "z", "base down, ears up"),
    ("Motor", "MotorShelf", "07", "z", ""), ("Shaft", "HandCrank_arm", "07", "x", ""),
    ("Shaft", "HandCrank_knob", "07", "x", ""),
]


def outward_normal(face):
    u = face.Domain(0).Mid
    v = face.Domain(1).Mid
    n = face.NormalAt(u, v)
    if face.OrientationIsReversed:
        n.Reverse()
    return n


def bed_plane(brep, down):
    """largest planar face whose outward normal points along 'down' -> plane with Z into the part"""
    d = Rhino.Geometry.Vector3d(*down)
    best, best_a = None, -1
    for f in brep.Faces:
        ok, pl = f.TryGetPlane(0.01)
        if not ok:
            continue
        n = outward_normal(f)
        n.Unitize()
        if n * d < 0.7:
            continue
        a = Rhino.Geometry.AreaMassProperties.Compute(f.DuplicateFace(False)).Area
        if a > best_a:
            best_a = a
            pz = -n
            xa = Rhino.Geometry.Vector3d.CrossProduct(pz, Rhino.Geometry.Vector3d.ZAxis)
            if xa.Length < 1e-6:
                xa = Rhino.Geometry.Vector3d.XAxis
            best = Rhino.Geometry.Plane(pl.Origin, xa, Rhino.Geometry.Vector3d.CrossProduct(pz, xa))
    return best


def to_mesh(brep):
    mp = Rhino.Geometry.MeshingParameters()
    mp.Tolerance = TOL
    mp.MinimumEdgeLength = 0.0001
    mp.RefineGrid = True
    mp.SimplePlanes = True
    m = Rhino.Geometry.Mesh()
    for q in Rhino.Geometry.Mesh.CreateFromBrep(brep, mp) or []:
        m.Append(q)
    m.Vertices.CombineIdentical(True, True)
    m.Weld(math.pi)
    m.Faces.ConvertQuadsToTriangles()
    if not m.IsClosed:
        m.HealNakedEdges(0.02)            # stitch hairline seams where teardrops meet other cuts
        m.Vertices.CombineIdentical(True, True)
    if not m.IsClosed:
        m.FillHoles()
    m.Normals.ComputeNormals()
    m.UnifyNormals()
    m.Compact()
    return m


def write_stl(meshes, path):
    tris = []
    for m in meshes:
        v = m.Vertices
        for f in m.Faces:
            a, b, c = v[f.A], v[f.B], v[f.C]
            tris.append((a, b, c))
    with open(path, "wb") as fh:
        fh.write(b"dragon automaton - binary STL, mm".ljust(80, b" "))
        fh.write(struct.pack("<I", len(tris)))
        for a, b, c in tris:
            ux, uy, uz = b.X - a.X, b.Y - a.Y, b.Z - a.Z
            vx, vy, vz = c.X - a.X, c.Y - a.Y, c.Z - a.Z
            nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
            ln = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            fh.write(struct.pack("<12fH", nx / ln, ny / ln, nz / ln, a.X, a.Y, a.Z, b.X, b.Y, b.Z, c.X, c.Y, c.Z, 0))
    return len(tris)


def safe(name):
    keep = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in name)
    while "__" in keep:
        keep = keep.replace("__", "_")
    return keep.strip("_")


def place(breps, plane):
    """lay breps on the bed using 'plane' (from the first brep), then move the group's min corner to origin"""
    xf = Rhino.Geometry.Transform.PlaneToPlane(plane, Rhino.Geometry.Plane.WorldXY)
    out = []
    for b in breps:
        b = b.DuplicateBrep()
        b.Transform(xf)
        out.append(b)
    bb = Rhino.Geometry.BoundingBox.Empty
    for b in out:
        bb.Union(b.GetBoundingBox(True))
    mv = Rhino.Geometry.Transform.Translation(-bb.Min.X, -bb.Min.Y, -bb.Min.Z)
    for b in out:
        b.Transform(mv)
    return out


if not os.path.isdir(OUT):
    os.makedirs(OUT)
ONLY = globals().get("ONLY")   # optional set of file names to re-export
if not ONLY:
    for fn in os.listdir(OUT):
        if fn.endswith(".stl") and not fn.startswith(("00_FitTest", "08_")):   # 08_ = printed_hardware.py
            os.remove(os.path.join(OUT, fn))

manifest = []


def export(group_breps, fname, note, plane):
    placed = place(group_breps, plane)
    meshes = [to_mesh(b) for b in placed]
    n = write_stl(meshes, os.path.join(OUT, fname))
    bb = Rhino.Geometry.BoundingBox.Empty
    for m in meshes:
        bb.Union(m.GetBoundingBox(True))
    dims = (bb.Max.X - bb.Min.X, bb.Max.Y - bb.Min.Y, bb.Max.Z - bb.Min.Z)
    closed = all(m.IsClosed for m in meshes)
    manifest.append((fname, dims, n, closed, note))
    return placed


used = set()
for lay, prefix, fpre, dkey, note in RULES:
    for o in rs.ObjectsByLayer("Automaton::" + lay) or []:
        nm = rs.ObjectName(o) or ""
        if o in used or not nm.startswith(prefix) or not rs.IsPolysurface(o):
            continue
        if lay == "Followers" and "_foot" not in nm:
            continue
        b = rs.coercebrep(o)
        pl = bed_plane(b, DOWN[dkey])
        if pl is None:
            print("NO BED FACE: " + nm)
            continue
        used.add(o)
        export([b], "{}_{}.stl".format(fpre, safe(nm.split(" (")[0])), note, pl)

# wings: membrane (colour 1) + bones/claws/scales (colour 2) share one frame -> load both as one multi-part object
for side in ("Back", "Front"):
    objs = rs.ObjectsByLayer("Automaton::FlexiWings") or []
    memb = [o for o in objs if (rs.ObjectName(o) or "").startswith("Wing_{} membrane".format(side))][0]
    det = [o for o in objs if (rs.ObjectName(o) or "").startswith("Wing_{} bones".format(side))]
    mb = rs.coercebrep(memb)
    pl = bed_plane(mb, DOWN["z"])
    xf = Rhino.Geometry.Transform.PlaneToPlane(pl, Rhino.Geometry.Plane.WorldXY)
    allb = [mb] + [rs.coercebrep(o) for o in det]
    moved = []
    for b in allb:
        b = b.DuplicateBrep()
        b.Transform(xf)
        moved.append(b)
    bb = Rhino.Geometry.BoundingBox.Empty
    for b in moved:
        bb.Union(b.GetBoundingBox(True))
    mv = Rhino.Geometry.Transform.Translation(-bb.Min.X, -bb.Min.Y, -bb.Min.Z)
    for b in moved:
        b.Transform(mv)
    ident = Rhino.Geometry.Plane.WorldXY
    for part, group, note in (("membrane_colour1", moved[:1], "membrane down; load with the colour2 file as one object"),
                              ("bones_colour2", moved[1:], "same frame as membrane")):
        meshes = [to_mesh(b) for b in group]
        fname = "06_Wing_{}_{}.stl".format(side, part)
        n = write_stl(meshes, os.path.join(OUT, fname))
        gb = Rhino.Geometry.BoundingBox.Empty
        for m in meshes:
            gb.Union(m.GetBoundingBox(True))
        manifest.append((fname, (gb.Max.X - gb.Min.X, gb.Max.Y - gb.Min.Y, gb.Max.Z - gb.Min.Z), n,
                         all(m.IsClosed for m in meshes), note))

with open(os.path.join(OUT, "MANIFEST.txt"), "w") as fh:
    fh.write("Dragon automaton - print files (mm, binary STL, each lies on its print face at the origin)\n")
    fh.write("Slicer: Bambu Studio, X-Y hole compensation 0, no supports. Qty 1 each.\n")
    fh.write("NOT included: Flexi Dragon (print D3Craft's MakerWorld file at 125%), acrylic front 288x118x3 (laser cut),\n")
    fh.write("dowels/shaft/pins/wire (see BUILD_NOTES.md hardware list).\n\n")
    for fname, d, n, closed, note in sorted(manifest):
        fh.write("{:<52s} {:6.1f} x {:6.1f} x {:6.1f}  {:>7d} tris  {}  {}\n".format(
            fname, d[0], d[1], d[2], n, "closed" if closed else "OPEN", note))
for fname, d, n, closed, note in sorted(manifest):
    print("{:<50s} {:6.1f} x {:6.1f} x {:6.1f} {}".format(fname, d[0], d[1], d[2], "" if closed else "OPEN"))
print("files:", len(manifest), "| over bed:", [m[0] for m in manifest if max(m[1]) > BED] or "none")
