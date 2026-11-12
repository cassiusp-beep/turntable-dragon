# -*- coding: utf-8 -*-
"""Wing concepts for the flexi-dragon automaton, laid flat (print orientation) beside the box.
Local coords: u along the body (+u = toward the head), v outward from the hinge, z up (membrane on z=0).
Each wing = separate bodies per colour (membrane / bones / scales) so it can print multi-colour like the dragon.
"""
import rhinoscriptsyntax as rs
import math

LAYER = "WingConcepts"
BLUE, DEEP, WHITE, CLAW = (40, 95, 200), (30, 60, 150), (240, 240, 245), (60, 60, 70)


def P(x, y, z=0.0):
    return (float(x), float(y), float(z))


def frame(pt, tan):
    t = rs.VectorUnitize(tan)
    ref = (0, 0, 1) if abs(t[2]) < 0.95 else (1, 0, 0)
    xa = rs.VectorUnitize(rs.VectorCrossProduct(ref, t))
    return rs.PlaneFromFrame(pt, xa, rs.VectorCrossProduct(t, xa))


def loft_solid(crvs):
    lo = rs.AddLoftSrf(crvs)
    rs.DeleteObjects(crvs)
    if not lo:
        return None
    rs.CapPlanarHoles(lo[0])
    return lo[0]


def tapered(p0, p1, r0, r1):
    d = rs.VectorCreate(p1, p0)
    return loft_solid([rs.AddCircle(frame(p0, d), r0), rs.AddCircle(frame(p1, d), r1)])


def bone_chain(pts, radii, z0):
    """tapered bone through pts with knuckle spheres; returns list of solids"""
    out = []
    for i in range(len(pts) - 1):
        a, b = P(pts[i][0], pts[i][1], z0), P(pts[i + 1][0], pts[i + 1][1], z0)
        out.append(tapered(a, b, radii[i], radii[i + 1]))
        if 0 < i + 1 < len(pts) - 1:
            out.append(rs.AddSphere(b, radii[i + 1] * 1.25))
    return out


def fuse(objs):
    objs = [o for o in objs if o]
    if not objs:
        return None
    res = rs.BooleanUnion(objs, True)
    if res:
        res = sorted(res, key=lambda q: -rs.SurfaceVolume(q)[0])
        for q in res[1:]:
            rs.ObjectName(q, "LOOSE_piece")
        return res[0]
    return objs[0]


def leaf(base, tip, width, thick, z):
    """flat leaf scale lying in the wing plane (a flattened cone), pointing base -> tip"""
    c = rs.AddCone(P(base[0], base[1], z), P(tip[0], tip[1], z), width)
    rs.ScaleObject(c, P(base[0], base[1], z), (1, 1, 1))
    d = rs.VectorUnitize((tip[0] - base[0], tip[1] - base[1], 0))
    ang = math.degrees(math.atan2(d[1], d[0]))
    # flatten in z about the leaf axis: rotate to X, scale z, rotate back
    c = rs.RotateObject(c, P(base[0], base[1], z), -ang, (0, 0, 1)) or c
    rs.ScaleObject(c, P(base[0], base[1], z), (1, 1, thick / (2.0 * width)))
    c = rs.RotateObject(c, P(base[0], base[1], z), ang, (0, 0, 1)) or c
    return c


def place(objs, dx, dy):
    return [rs.MoveObject(o, (dx, dy, 0)) or o for o in objs if o]


def membrane(outline_pts_list, thick):
    """closed outline from a list of point-lists (each an interp curve segment), extruded up"""
    crvs = []
    for seg in outline_pts_list:
        if len(seg) == 2:
            crvs.append(rs.AddLine(P(*seg[0]), P(*seg[1])))
        else:
            crvs.append(rs.AddInterpCurve([P(*q) for q in seg], 3 if len(seg) > 3 else 2))
    loop = rs.JoinCurves(crvs, True)
    srf = rs.ExtrudeCurveStraight(loop[0], (0, 0, 0), (0, 0, thick))
    rs.CapPlanarHoles(srf)
    rs.DeleteObjects(loop)
    return srf


# ------------------------------------------------------------------ CONCEPT A: refined bat wing
def concept_a():
    MT = 1.4
    S, E, WR = (0, 3), (13, 50), (4, 96)                        # shoulder, elbow, wrist
    F = [(-6, 152), (-38, 134), (-60, 98), (-62, 54)]           # finger tips (leading -> trailing)
    KN = [(-2, 120), (-20, 118), (-33, 92), (-36, 62)]          # finger knuckles
    ROOT_BACK = (-26, 3)
    outline = [
        [(2.5, 2.4), (2.5, 8), (12, 30), E, (10, 75), WR],                        # leading edge along the arm
        [WR, (2, 125), F[0]],                                                      # outer leading edge
        [F[0], (-17, 128), (-26, 125), F[1]],                                      # deep scallops
        [F[1], (-41, 112), (-46, 104), F[2]],
        [F[2], (-48, 80), (-51, 70), F[3]],
        [F[3], (-46, 36), (-36, 18), ROOT_BACK, (-2.5, 8)],
        [(-2.5, 8), (-2.5, 2.4)], [(-2.5, 2.4), (2.5, 2.4)],
    ]
    memb = membrane(outline, MT)
    rs.ObjectColor(memb, DEEP)
    rs.ObjectName(memb, "A_membrane (colour 1)")
    zb = MT + 0.4
    bones = bone_chain([S, E, WR], [3.0, 2.4, 2.0], zb)
    for kn, tip in zip(KN, F):
        bones += bone_chain([WR, kn, tip], [1.7, 1.3, 0.5], zb)
        d = rs.VectorUnitize((tip[0] - kn[0], tip[1] - kn[1], 0))
        bones.append(rs.AddCone(P(tip[0], tip[1], zb), P(tip[0] + d[0] * 5, tip[1] + d[1] * 5, zb - 0.5), 1.0))  # claw
    bones.append(rs.AddCone(P(WR[0], WR[1], zb), P(WR[0] + 9, WR[1] + 6, zb), 1.6))     # thumb claw
    bones.append(rs.AddCone(P(E[0], E[1], zb), P(E[0] + 5, E[1] - 2, zb), 1.3))           # elbow spur
    # veins between the fingers (low ridges on the membrane)
    for a, b, c in (((-8, 104), (-18, 122), (-24, 126)), ((-14, 100), (-36, 108), (-44, 106)),
                    ((-12, 92), (-42, 80), (-50, 74)), ((-8, 60), (-30, 40), (-38, 22))):
        crv = rs.AddInterpCurve([P(a[0], a[1], MT), P(b[0], b[1], MT), P(c[0], c[1], MT)], 2)
        pp = rs.AddPipe(crv, [rs.CurveDomain(crv)[0], rs.CurveDomain(crv)[1]], [0.7, 0.3], 0, 1)
        rs.DeleteObject(crv)
        if pp:
            bones.append(pp[0])
    # leaf scales along the arm (match the body)
    for i in range(9):
        f = i / 8.0
        if f < 0.5:
            a, b = S, E
            g = f / 0.5
        else:
            a, b = E, WR
            g = (f - 0.5) / 0.5
        base = (a[0] + (b[0] - a[0]) * g + 2.0, a[1] + (b[1] - a[1]) * g)
        bones.append(leaf(base, (base[0] - 7, base[1] - 3), 2.6 - 1.0 * f, 1.6, zb + 1.2))
    bones = [o for o in bones if o]
    for o in bones:
        rs.ObjectColor(o, WHITE)
        rs.ObjectName(o, "A_bones_scales (colour 2)")
    return [memb] + bones


# ------------------------------------------------------------------ CONCEPT B: scaled (feathered) wing
def concept_b():
    MT = 1.2
    # base plate: broad, swept fan
    outline = [
        [(2.5, 2.4), (2.5, 8), (14, 34), (12, 70), (2, 110), (-14, 148)],
        [(-14, 148), (-30, 146), (-44, 130)],
        [(-44, 130), (-56, 108), (-62, 80)],
        [(-62, 80), (-62, 50), (-50, 26)],
        [(-50, 26), (-34, 12), (-22, 5), (-2.5, 8)],
        [(-2.5, 8), (-2.5, 2.4)], [(-2.5, 2.4), (2.5, 2.4)],
    ]
    plate = membrane(outline, MT)
    arm = bone_chain([(0, 3), (13, 50), (4, 96), (-12, 146)], [3.0, 2.4, 2.0, 0.8], MT + 0.6)
    rows = []
    # broad rounded leaf scales in staggered rows (shingles), pointing outward and back, inner rows on top
    crv = rs.DuplicateEdgeCurves(plate)
    bottom = [c for c in crv if abs(rs.CurveStartPoint(c)[2]) < 0.01 and abs(rs.CurveEndPoint(c)[2]) < 0.01]
    loop = rs.JoinCurves(bottom, True)
    rs.DeleteObjects(crv)
    k = 0
    v = 10.0
    while v < 150:
        L = 9.0 + 9.0 * (v / 150.0)                 # longer toward the tip
        Wd = 3.6 + 1.6 * (v / 150.0)
        step = Wd * 1.55
        u = -64.0 + (step / 2.0 if (k % 2) else 0.0)
        while u < 16:
            base = (u, v)
            tip = (u - 0.45 * L, v + 0.85 * L)
            tc = (base[0] + (tip[0] - base[0]) * 0.5, base[1] + (tip[1] - base[1]) * 0.5)
            if rs.PointInPlanarClosedCurve(P(tc[0], tc[1], 0), loop[0]) == 1 and \
               rs.PointInPlanarClosedCurve(P(tip[0], tip[1], 0), loop[0]) == 1:
                z = MT + 0.5 + 2.2 * (1.0 - v / 150.0)
                e = rs.AddSphere(P(0, 0, 0), 1.0)
                rs.ScaleObject(e, P(0, 0, 0), (L / 2.0, Wd / 2.0, 0.7))
                ang = math.degrees(math.atan2(tip[1] - base[1], tip[0] - base[0]))
                e = rs.RotateObject(e, P(0, 0, 0), ang, (0, 0, 1)) or e
                e = rs.MoveObject(e, (tc[0], tc[1], z)) or e
                rows.append(e)
            u += step
        v += L * 0.55
        k += 1
    rs.DeleteObjects(loop)
    for o in [plate] + [q for q in arm if q]:
        rs.ObjectColor(o, BLUE)
        rs.ObjectName(o, "B_plate_arm (colour 1)")
    for i, o in enumerate(rows):
        rs.ObjectColor(o, WHITE if i % 2 == 0 else (200, 215, 245))
        rs.ObjectName(o, "B_scales (colour 2)")
    return [plate] + [q for q in arm if q] + rows


if not rs.IsLayer(LAYER):
    rs.AddLayer(LAYER, BLUE)
for o in rs.ObjectsByLayer(LAYER) or []:
    rs.DeleteObject(o)
rs.CurrentLayer(LAYER)
rs.EnableRedraw(False)
a = place(concept_a(), 60, -200)
b = place(concept_b(), 220, -200)
for o in a + b:
    rs.ObjectLayer(o, LAYER)
rs.EnableRedraw(True)
for nm, grp in (("A", a), ("B", b)):
    bb = rs.BoundingBox(grp)
    print(nm, len(grp), "bodies", round(bb[6][0] - bb[0][0], 1), "x", round(bb[6][1] - bb[0][1], 1), "x",
          round(bb[6][2] - bb[0][2], 1), "open:", len([o for o in grp if rs.IsPolysurface(o) and not rs.IsPolysurfaceClosed(o)]))
print("loose:", len([o for o in rs.ObjectsByLayer(LAYER) if "LOOSE" in (rs.ObjectName(o) or "")]))
