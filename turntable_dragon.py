"""Turntable dragon (pivot, Nov 11). Run in Rhino 8 (RhinoCommon).

The dragon curls on a platter. The platter has an INTERNAL ring gear underneath, driven by a pinion on the
Mini-300 gearmotor (5 mm dual-D shaft, 4 mm across the flats, 32 mm round gearbox, ears 46.6 tip to tip).
Origin = centre of the base, z = 0 on the deck's top face. The motor slides along +X.

Tolerances (this printer: small vertical holes print ~0.2-0.6 mm undersize, XY comp 0):
  gear backlash 0.3 mm arc per gear (0.6 total); marks sit 0.15 mm closer to the centre (opens an internal mesh)
  post 16.0 in a 16.8 hub; gearbox 32 in a 32.6 tube; carriage 56 between rails 56.6 apart
  pinion bore 2 sizes: TIGHT 5.2/4.2 flats, LOOSE 5.5/4.5 flats; leg pegs 8.0 in 8.4 holes
"""
import math
import Rhino
import scriptcontext as sc
import rhinoscriptsyntax as rs
from Rhino.Geometry import Point3d as P, Vector3d as V, Plane, Brep, Box, Interval, Cylinder, Circle, Sphere, Transform

TOL = 0.001
OUT = "/Users/cassiuspalacio/Documents/UC Berkeley TDF/PhysComp/Nov 9/STL_turntable"

M = 1.5                       # gear module (small, so everything fits one 256 plate)
NR = 80                       # internal ring teeth (pitch dia 120)
PINIONS = [17, 28]            # 4.7:1 (slower) and 2.86:1 (faster)
BACKLASH = 0.3                # arc mm taken off each gear's teeth at the pitch circle (0.6 total)
CD_EXTRA = -0.15              # internal gear: a SMALLER centre distance opens the mesh
PA = math.radians(20)

DECK_X0, DECK_X1, DECK_HY, DECK_T = -35.0, 80.0, 35.0, 4.0   # compact 3-leg base
POST_R = 8.0
PLAT_R, PLAT_T = 75.0, 3.0
PLAT_Z = 54.0                 # platter underside (= post dome apex)
HUB_IR, HUB_OR, HUB_Z0 = 8.4, 11.0, 36.0
RING_Z0 = 41.5                # bottom of the internal teeth (2.5 mm above the gearbox top edge)
SKIRT_OR = 65.0
LEG_R, LEG_H, PEG_R, PEG_H, LEG_HOLE_R = 12.0, 45.0, 4.0, 3.8, 4.2
LEGS = [(-25.0, 25.0), (-25.0, -25.0), (70.0, 0.0)]   # tripod: never rocks

TUBE_IR, TUBE_OR, TUBE_TOP = 16.3, 18.7, 37.0   # motor ears rest on the tube rim
PLATE_T, CAR_HX, CAR_HY = 3.0, 23.0, 28.0
RAIL_IN, RAIL_W, RAIL_X0, RAIL_X1 = 28.3, 4.0, 15.0, 80.0
PIN_H, BORE_D = 9.0, 6.0      # pinion height, shaft engagement (shaft sticks out 5.5)
BORES = {"TIGHT": (2.6, 2.1), "LOOSE": (2.75, 2.25)}


def cyl(x, y, z0, z1, r):
    return Cylinder(Circle(Plane(P(x, y, z0), V.ZAxis), r), z1 - z0).ToBrep(True, True)


def box(x0, y0, z0, x1, y1, z1):
    return Box(Plane.WorldXY, Interval(x0, x1), Interval(y0, y1), Interval(z0, z1)).ToBrep()


def union(bs):
    r = Brep.CreateBooleanUnion(bs, TOL)
    if not r:
        raise Exception("union failed")
    return r[0] if len(r) == 1 else union(list(r))


def diff(a, cuts):
    r = Brep.CreateBooleanDifference([a], cuts, TOL)
    if not r:
        raise Exception("difference failed")
    return r[0]


def inter(a, b):
    return Brep.CreateBooleanIntersection(a, b, TOL)[0]


def inv(a):
    return math.tan(a) - a


def gear_outline(N, r_tip, r_root, thicker):
    """closed polyline of an involute gear; thicker>0 widens teeth (used as the internal-gear cutter)"""
    rp = N * M / 2.0
    rb = rp * math.cos(PA)
    psi_p = math.pi / (2 * N) + thicker / rp

    def psi(r):
        r = max(r, rb)
        return psi_p + inv(PA) - inv(math.acos(rb / r))

    pts = []
    rs_ = [r_root + (r_tip - r_root) * i / 12.0 for i in range(13)]
    for k in range(N):
        th = 2 * math.pi * k / N
        flank = [(r, psi(r)) for r in rs_]
        for r, s in flank:                       # leading flank, root -> tip
            pts.append(P(r * math.cos(th - s), r * math.sin(th - s), 0))
        st = psi(r_tip)
        for i in range(1, 4):                    # tip land
            a = th - st + 2 * st * i / 4.0
            pts.append(P(r_tip * math.cos(a), r_tip * math.sin(a), 0))
        for r, s in reversed(flank):             # trailing flank, tip -> root
            pts.append(P(r * math.cos(th + s), r * math.sin(th + s), 0))
        # root land to the next tooth
        a0, a1 = th + psi(r_root), th + 2 * math.pi / N - psi(r_root)
        for i in range(1, 4):
            a = a0 + (a1 - a0) * i / 4.0
            pts.append(P(r_root * math.cos(a), r_root * math.sin(a), 0))
    pts.append(pts[0])
    return Rhino.Geometry.PolylineCurve(pts)


def extrude(crv, z0, z1):
    c = crv.DuplicateCurve()
    c.Translate(V(0, 0, z0))
    b = Rhino.Geometry.Surface.CreateExtrusion(c, V(0, 0, z1 - z0)).ToBrep()
    b = b.CapPlanarHoles(TOL)
    if b.GetVolume() < 0:
        b.Flip()
    return b


parts = {}

# ---------------------------------------------------------------- deck (base) with centre post, rails, marks
deck = box(DECK_X0, -DECK_HY, -DECK_T, DECK_X1, DECK_HY, 0)
cap_c = PLAT_Z - 12.0
post = union([cyl(0, 0, -0.5, cap_c + math.sqrt(144 - POST_R ** 2) + 0.01, POST_R),
              inter(Brep.CreateFromSphere(Sphere(P(0, 0, cap_c), 12.0)), cyl(0, 0, cap_c, PLAT_Z, POST_R))])
rails = [box(RAIL_X0, s * RAIL_IN, -0.5, RAIL_X1, s * (RAIL_IN + RAIL_W), PLATE_T) for s in (1,)] + \
        [box(RAIL_X0, -(RAIL_IN + RAIL_W), -0.5, RAIL_X1, -RAIL_IN, PLATE_T)]
deck = union([deck, post] + rails)
cd = {n: (NR - n) * M / 2.0 + CD_EXTRA for n in PINIONS}
marks = []
for n in PINIONS:
    x = cd[n] + CAR_HX                                  # carriage OUTER edge lines up with this groove
    for s in (1, -1):
        marks.append(box(x - 0.5, s * RAIL_IN - (0 if s > 0 else RAIL_W), PLATE_T - 0.6,
                         x + 0.5, s * RAIL_IN + (RAIL_W if s > 0 else 0), PLATE_T + 1))
holes = [box(min(cd.values()) - 13, -12.5, -DECK_T - 1, max(cd.values()) + 13, 12.5, 1)]   # motor/wire slot
for lx, ly in LEGS:
    holes.append(cyl(lx, ly, -DECK_T - 1, 1, LEG_HOLE_R))
deck = diff(deck, marks + holes)
parts["T1_Base_deck_with_post"] = deck

leg = union([cyl(0, 0, 0, LEG_H, LEG_R), cyl(0, 0, LEG_H - 0.5, LEG_H + PEG_H, PEG_R)])
parts["T1_Leg"] = leg

# ---------------------------------------------------------------- platter: disk + hub + internal ring gear
rp_r = NR * M / 2.0
cutter = gear_outline(NR, rp_r + 1.25 * M, rp_r - M, BACKLASH / 2.0)
ring = diff(cyl(0, 0, RING_Z0, PLAT_Z + 0.5, SKIRT_OR), [extrude(cutter, RING_Z0 - 1, PLAT_Z + 1)])
hub = diff(cyl(0, 0, HUB_Z0, PLAT_Z + 0.5, HUB_OR), [cyl(0, 0, HUB_Z0 - 1, PLAT_Z, HUB_IR)])
platter = union([cyl(0, 0, PLAT_Z, PLAT_Z + PLAT_T, PLAT_R), ring, hub])
guide = diff(cyl(0, 0, PLAT_Z + PLAT_T - 0.4, PLAT_Z + PLAT_T + 1, 60.5), [cyl(0, 0, PLAT_Z, PLAT_Z + PLAT_T + 2, 59.5)])
platter = diff(platter, [guide])                       # 1 mm guide line where the curled dragon sits
parts["T2_Platter_with_ring_gear"] = platter


# ---------------------------------------------------------------- pinions (each sits on the motor collar)
def pinion(N, bore):
    rp = N * M / 2.0
    g = extrude(gear_outline(N, rp + M, rp - 1.25 * M, -BACKLASH / 2.0), 0, PIN_H)
    br, bf = BORES[bore]
    d = inter(cyl(0, 0, -1, BORE_D, br), box(-5, -bf, -2, 5, bf, BORE_D + 1))
    cuts = [d, cyl(0, 0, -1, PIN_H + 1, 1.6), cyl(0, 0, PIN_H - 1.5, PIN_H + 1, 3.0)]
    a = math.pi / N                                    # grub-screw pilot (M3 self-taps) through a tooth gap
    cuts.append(Cylinder(Circle(Plane(P(0, 0, 3.0), V(math.cos(a), math.sin(a), 0)), 1.3), rp + 5).ToBrep(True, True))
    for i in range(2 if bore == "LOOSE" else 1):       # dimples on top: 1 = tight, 2 = loose
        aa = -math.pi / 2 + i * 0.5
        cuts.append(cyl(6.5 * math.cos(aa), 6.5 * math.sin(aa), PIN_H - 0.6, PIN_H + 1, 0.9))
    return diff(g, cuts)


for n in PINIONS:
    for b in BORES:
        parts["T3_Pinion_{}T_{}".format(n, b)] = pinion(n, b)

# ---------------------------------------------------------------- motor carriage (slides between the rails)
car = union([box(-CAR_HX, -CAR_HY, 0, CAR_HX, CAR_HY, PLATE_T), cyl(0, 0, PLATE_T - 0.5, TUBE_TOP, TUBE_OR)] +
            [box(-6.5, s * 15.5, TUBE_TOP - 6, -4.5, s * 24.5, TUBE_TOP + 3) for s in (1, -1)] +
            [box(4.5, s * 15.5, TUBE_TOP - 6, 6.5, s * 24.5, TUBE_TOP + 3) for s in (1, -1)] +
            [box(-4.5, s * 16.0, TUBE_TOP - 6, 4.5, s * 24.5, TUBE_TOP) for s in (1, -1)])
car = diff(car, [cyl(0, 0, -1, TUBE_TOP + 5, TUBE_IR), cyl(0, 0, -1, PLATE_T + 1, 12.0)])
parts["T3_Motor_carriage"] = car

# ---------------------------------------------------------------- put the assembly in the doc
LAY = "Turntable"
if not rs.IsLayer(LAY):
    rs.AddLayer(LAY)
for o in rs.ObjectsByLayer(LAY) or []:
    rs.DeleteObject(o)
for l in rs.LayerNames():
    if l != LAY and "::" not in l and rs.IsLayer(l):
        try:
            rs.LayerVisible(l, False)
        except Exception:
            pass


def place(name, brep, xf=None):
    b = brep.DuplicateBrep()
    if xf:
        b.Transform(xf)
    gid = sc.doc.Objects.AddBrep(b)
    rs.ObjectLayer(gid, LAY)
    rs.ObjectName(gid, name)
    return gid


place("Base deck", deck)
for lx, ly in LEGS:
    place("Leg", leg, Transform.Translation(lx, ly, -DECK_T - LEG_H))
place("Platter", platter)
USE = 17
place("Motor carriage", car, Transform.Translation(cd[USE], 0, 0))
MOTOR_FACE = TUBE_TOP + 2.0          # ears ~2 mm thick, flush with the gearbox face (assumed)
place("Pinion", parts["T3_Pinion_{}T_LOOSE".format(USE)], Transform.Translation(cd[USE], 0, MOTOR_FACE + 1.5))
place("Motor gearbox (ref)", cyl(cd[USE], 0, MOTOR_FACE - 22, MOTOR_FACE, 16.0))
place("Motor can (ref)", cyl(cd[USE], 0, MOTOR_FACE - 35.3, MOTOR_FACE - 22, 10.0))
place("Motor ears (ref)", box(cd[USE] - 3.5, -23.3, MOTOR_FACE - 2, cd[USE] + 3.5, 23.3, MOTOR_FACE))
sc.doc.Views.Redraw()
print("centre distances:", cd)
print("ratios:", dict((n, round(NR / float(n), 2)) for n in PINIONS))
for k, v in parts.items():
    print(k, "solid" if v.IsSolid else "NOT SOLID", round(v.GetVolume() / 1000.0, 1), "cm3")


# ---------------------------------------------------------------- export STLs in print orientation (centred on 0,0)
import os, struct


def to_mesh(b):
    p = Rhino.Geometry.MeshingParameters.QualityRenderMesh
    p.Tolerance = 0.02
    m = Rhino.Geometry.Mesh()
    for x in Rhino.Geometry.Mesh.CreateFromBrep(b, p):
        m.Append(x)
    m.Vertices.CombineIdentical(True, True)
    m.Faces.ConvertQuadsToTriangles()
    m.UnifyNormals()
    return m


def save(name, brep, xf):
    m = to_mesh(brep)
    for t in xf:
        m.Transform(t)
    bb = m.GetBoundingBox(True)
    m.Translate(0, 0, -bb.Min.Z)
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    with open(os.path.join(OUT, name + ".stl"), "wb") as f:
        f.write(b"\0" * 80)
        f.write(struct.pack("<I", m.Faces.Count))
        for fc in m.Faces:
            a, b_, c = [m.Vertices[i] for i in (fc.A, fc.B, fc.C)]
            f.write(struct.pack("<12fH", 0, 0, 0, a.X, a.Y, a.Z, b_.X, b_.Y, b_.Z, c.X, c.Y, c.Z, 0))
    print("saved", name, "closed" if m.IsClosed else "OPEN", m.Faces.Count)


flip = Transform.Rotation(math.pi, V.XAxis, P(0, 0, 0))
for k, v in parts.items():
    save(k, v, [flip] if k.startswith("T2_") else [])
