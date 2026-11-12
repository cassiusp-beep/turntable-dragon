# -*- coding: utf-8 -*-
"""Finger-jointed laser-cut box for the dragon automaton (plain python3: python3 laser_box_fingers.py).

Sheet: 1/8 in plywood, 30 x 18 in, laid out HORIZONTALLY (762 x 457 mm). Outer box 300 x 120 x 130 mm, same as the
CAD model; the shaft, rods and posts land exactly where the mechanism expects them.
  floor, back panel  : one layer  (T1 = 1/8 in)
  top plate, end walls: two layers glued face to face (T2 = 2 x 1/8 in); both layers have the same fingers
  guide bar, A-frame : two layers, no fingers (they sit inside the box)
Finger joints on floor<->end walls, floor<->back, top<->end walls, top<->back, end walls<->back. The front is open
(clear acrylic window). Each 3-panel corner cube belongs to the floor (bottom) or the top plate (top).
Kerf: every finger is drawn KERF/2 wider on each side so the laser's cut width leaves a snug glue fit.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "Laser_Cut")
T1 = 3.175            # 1/8 in plywood (measure yours; Jacobs Baltic birch is usually 3.0-3.2)
T2 = 2 * T1           # laminated parts
KERF = 0.15           # laser cut width (Universal VLS on 1/8 in ply, typical 0.1-0.2)
FINGER = 15.0         # target finger width
L, D, H = 300.0, 120.0, 130.0
ROD_HOLE_D, SHAFT_HOLE_D = 6.4, 8.3
ROD_XS = [30.16, 74.83, 120.0, 173.68, 222.47, 273.89]   # R1 tail, R2 back, wing, R3 belly, R4 neck, head
POST_XS = [108.0, 132.0]
SHAFT_Y, SHAFT_Z = 60.0, 50.0
SHEET_W, SHEET_H = 762.0, 457.2   # 30 x 18 in, horizontal

# ------------------------------------------------------------------ panels (local u, v = world coords)
# name: (size_u, size_v, world axis of u, world axis of v)
PANELS = {
    "Floor":     (L, D, "x", "y"),
    "TopPlate":  (L, D, "x", "y"),
    "EndWall_L": (D, H, "y", "z"),
    "EndWall_R": (D, H, "y", "z"),
    "BackPanel": (L, H, "x", "z"),
}
# sides of a panel: bottom v=0 (param u), right u=W (param v), top v=H (param u), left u=0 (param v)
insets = dict((p, {"bottom": [], "right": [], "top": [], "left": []}) for p in PANELS)


def add(panel, side, a, b, d):
    if b - a > 1e-9:
        insets[panel][side].append((a, b, d))


def joint(A, sideA, dA, B, sideB, dB, lo, hi, ends):
    """fingers between panel A (its sideA notched dA deep where B owns) and panel B, over param lo..hi.
    ends: list of (a, b, owner) corner ranges along this edge owned by owner (A, B or a third panel)."""
    n = max(3, int(round((hi - lo) / FINGER)))
    if n % 2 == 0:
        n += 1
    w = (hi - lo) / n
    k = KERF / 2.0
    for i in range(n):
        a, b = lo + i * w, lo + (i + 1) * w
        owner = A if i % 2 == 0 else B
        # the non-owner is notched over this finger, narrowed by k at internal boundaries (kerf compensation)
        na = a + (k if i > 0 else 0.0)
        nb = b - (k if i < n - 1 else 0.0)
        if owner == A:
            add(B, sideB, na, nb, dB)
        else:
            add(A, sideA, na, nb, dA)
    for a, b, owner in ends:
        if owner != A:
            add(A, sideA, a, b, dA)
        if owner != B:
            add(B, sideB, a, b, dB)


# floor <-> end walls (edge along y), corner at the back owned by the floor
joint("Floor", "left", T2, "EndWall_L", "bottom", T1, 0.0, D - T1, [(D - T1, D, "Floor")])
joint("Floor", "right", T2, "EndWall_R", "bottom", T1, 0.0, D - T1, [(D - T1, D, "Floor")])
# floor <-> back (edge along x), corners owned by the floor
joint("Floor", "top", T1, "BackPanel", "bottom", T1, T2, L - T2, [(0.0, T2, "Floor"), (L - T2, L, "Floor")])
# top <-> end walls, top <-> back
joint("TopPlate", "left", T2, "EndWall_L", "top", T2, 0.0, D - T1, [(D - T1, D, "TopPlate")])
joint("TopPlate", "right", T2, "EndWall_R", "top", T2, 0.0, D - T1, [(D - T1, D, "TopPlate")])
joint("TopPlate", "top", T1, "BackPanel", "top", T2, T2, L - T2, [(0.0, T2, "TopPlate"), (L - T2, L, "TopPlate")])
# end walls <-> back (edge along z), bottom corner = floor, top corner = top plate
joint("EndWall_L", "right", T1, "BackPanel", "left", T2, T1, H - T2, [(0.0, T1, "Floor"), (H - T2, H, "TopPlate")])
joint("EndWall_R", "right", T1, "BackPanel", "right", T2, T1, H - T2, [(0.0, T1, "Floor"), (H - T2, H, "TopPlate")])
# EndWall_R is the mirror of EndWall_L about the box centre (its "right" side is still the back edge, y = D)


def profile(segs, length):
    """piecewise inset over 0..length (0 where nothing is notched), merged"""
    cuts = sorted(set([0.0, length] + [s[0] for s in segs] + [s[1] for s in segs]))
    out = []
    for a, b in zip(cuts, cuts[1:]):
        m = (a + b) / 2.0
        d = max([s[2] for s in segs if s[0] <= m <= s[1]] or [0.0])
        if out and abs(out[-1][2] - d) < 1e-9:
            out[-1] = (out[-1][0], b, d)
        else:
            out.append((a, b, d))
    return out


def inset_at(prof, c):
    for a, b, d in prof:
        if a - 1e-9 <= c <= b + 1e-9:
            return d
    return 0.0


def outline(name):
    W, Hh = PANELS[name][0], PANELS[name][1]
    P = dict((s, profile(insets[name][s], W if s in ("bottom", "top") else Hh)) for s in insets[name])
    pts = []
    for a, b, d in P["bottom"]:
        a2 = inset_at(P["left"], 0.0) if a == 0 else a
        b2 = W - inset_at(P["right"], 0.0) if abs(b - W) < 1e-9 else b
        pts += [(a2, d), (b2, d)]
    for a, b, d in P["right"]:
        a2 = inset_at(P["bottom"], W) if a == 0 else a
        b2 = Hh - inset_at(P["top"], W) if abs(b - Hh) < 1e-9 else b
        pts += [(W - d, a2), (W - d, b2)]
    for a, b, d in reversed(P["top"]):
        b2 = W - inset_at(P["right"], Hh) if abs(b - W) < 1e-9 else b
        a2 = inset_at(P["left"], Hh) if a == 0 else a
        pts += [(b2, Hh - d), (a2, Hh - d)]
    for a, b, d in reversed(P["left"]):
        b2 = Hh - inset_at(P["top"], 0.0) if abs(b - Hh) < 1e-9 else b
        a2 = inset_at(P["bottom"], 0.0) if a == 0 else a
        pts += [(d, b2), (d, a2)]
    clean = []
    for p in pts:
        p = (round(p[0], 4), round(p[1], 4))
        if not clean or p != clean[-1]:
            clean.append(p)
    if clean[0] == clean[-1]:
        clean.pop()
    # drop collinear points
    out = []
    n = len(clean)
    for i in range(n):
        a, b, c = clean[i - 1], clean[i], clean[(i + 1) % n]
        if abs((b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])) > 1e-9:
            out.append(b)
    return out


def inside(poly, x, y):
    c = False
    n = len(poly)
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            c = not c
    return c


outlines = dict((p, outline(p)) for p in PANELS)
# EndWall_R is built in the same local frame as EndWall_L (u = y, v = z); it's a separate cut part

# ------------------------------------------------------------------ check: every edge/corner cell owned exactly once
SLAB = {"Floor": ("z", 0.0, T1), "TopPlate": ("z", H - T2, H), "EndWall_L": ("x", 0.0, T2),
        "EndWall_R": ("x", L - T2, L), "BackPanel": ("y", D - T1, D)}


def owners(x, y, z):
    w = {"x": x, "y": y, "z": z}
    res = []
    for p, (ax, a, b) in SLAB.items():
        if not (a < w[ax] < b):
            continue
        U, V = PANELS[p][2], PANELS[p][3]
        if inside(outlines[p], w[U], w[V]):
            res.append(p)
    return res


bad, n_s = [], 0
step = 0.25
k = KERF / 2.0
for (axis, length, fixed) in (("y", D, [("x", T2 / 2), ("z", T1 / 2)]), ("y", D, [("x", L - T2 / 2), ("z", T1 / 2)]),
                              ("y", D, [("x", T2 / 2), ("z", H - T2 / 2)]), ("y", D, [("x", L - T2 / 2), ("z", H - T2 / 2)]),
                              ("x", L, [("y", D - T1 / 2), ("z", T1 / 2)]), ("x", L, [("y", D - T1 / 2), ("z", H - T2 / 2)]),
                              ("z", H, [("x", T2 / 2), ("y", D - T1 / 2)]), ("z", H, [("x", L - T2 / 2), ("y", D - T1 / 2)])):
    s = step / 2
    while s < length:
        c = dict(fixed)
        c[axis] = s
        o = owners(c.get("x"), c.get("y"), c.get("z"))
        n_s += 1
        if len(o) != 1:
            bad.append((axis, round(s, 2), tuple(sorted(o))))
        s += step
# with kerf compensation both panels overlap by KERF/2 at each finger boundary (that's the interference the laser
# removes); anything else is an error
real_bad = [b for b in bad if len(b[2]) != 2]
over = [b for b in bad if len(b[2]) == 2]


# ------------------------------------------------------------------ parts list
def rect(w, h):
    return [(0, 0), (w, 0), (w, h), (0, h)]


INNER_L = round(L - 2 * T2 - 0.6, 1)                  # guide bar + acrylic: between the end walls, 0.3 mm slack each end
FRONT_H = round(H - T1 - T2 - 0.6, 1)
top_holes = [(x, SHAFT_Y, ROD_HOLE_D) for x in ROD_XS + POST_XS]
af_h = (SHAFT_Z - T1) + 12.0                          # A-frame stands on the floor (top face z = T1)
parts = [
    ("TopPlate", 2, outlines["TopPlate"], top_holes, [(10, 8, "TOP  L=motor end")]),
    ("Floor", 1, outlines["Floor"], [], [(10, 8, "FLOOR  L=motor end")]),
    ("BackPanel", 1, outlines["BackPanel"], [], [(10, 8, "BACK  L=motor end")]),
    ("EndWall_L", 2, outlines["EndWall_L"], [(SHAFT_Y, SHAFT_Z, SHAFT_HOLE_D)], [(12, 10, "END L (motor)")]),
    ("EndWall_R", 2, outlines["EndWall_R"], [(SHAFT_Y, SHAFT_Z, SHAFT_HOLE_D)], [(12, 10, "END R (crank)")]),
    ("RodGuideBar", 2, rect(INNER_L, 30), [(x - (T2 + 0.3), 15.0, ROD_HOLE_D) for x in ROD_XS + POST_XS],
     [(3, 3, "GUIDE  L")]),
    ("Support_Aframe", 2, [(0, 0), (80, 0), (48, af_h), (32, af_h)], [(40.0, SHAFT_Z - T1, SHAFT_HOLE_D)],
     [(23, 4, "A-FRAME")]),
]


def size(poly):
    return max(p[0] for p in poly), max(p[1] for p in poly)


# horizontal sheet, rows
G = 5.0
rows = [[("TopPlate", 1), ("TopPlate", 2), ("EndWall_L", 1)],
        [("Floor", 0), ("BackPanel", 0), ("EndWall_L", 2)],
        [("EndWall_R", 1), ("EndWall_R", 2), ("RodGuideBar", 1), ("Support_Aframe", 1), ("Support_Aframe", 2)],
        [("RodGuideBar", 2)]]
byname = dict((p[0], p) for p in parts)
items, y, Wused = [], G, 0
for row in rows:
    x, rh = G, 0
    for nm, kk in row:
        _, cnt, poly, hl, lb = byname[nm]
        w, h = size(poly)
        items.append((poly, hl, [(a, b, t + (" %d/2" % kk if kk else "")) for a, b, t in lb], x, y))
        x += w + G
        rh = max(rh, h)
    Wused = max(Wused, x)
    y += rh + G
Hused = y

# ------------------------------------------------------------------ writers
MM = 72.0 / 25.4
KB = 0.5522847498


def dxf(path, items):
    Lx = ["0", "SECTION", "2", "HEADER", "9", "$ACADVER", "1", "AC1009", "9", "$INSUNITS", "70", "4", "0", "ENDSEC",
          "0", "SECTION", "2", "ENTITIES"]
    for poly, hl, labels, dx, dy in items:
        Lx += ["0", "POLYLINE", "8", "CUT", "66", "1", "70", "1"]
        for px, py in poly:
            Lx += ["0", "VERTEX", "8", "CUT", "10", "%.3f" % (px + dx), "20", "%.3f" % (py + dy), "30", "0"]
        Lx += ["0", "SEQEND", "8", "CUT"]
        for cx, cy, d in hl:
            Lx += ["0", "CIRCLE", "8", "CUT", "10", "%.3f" % (cx + dx), "20", "%.3f" % (cy + dy), "30", "0", "40", "%.3f" % (d / 2)]
        for tx, ty, t in labels:
            Lx += ["0", "TEXT", "8", "ENGRAVE", "10", "%.3f" % (tx + dx), "20", "%.3f" % (ty + dy), "30", "0", "40", "4", "1", t]
    Lx += ["0", "ENDSEC", "0", "EOF"]
    with open(path, "w") as fh:
        fh.write("\n".join(Lx) + "\n")


def svg(path, items, W, Hh):
    s = ['<svg xmlns="http://www.w3.org/2000/svg" width="%.1fmm" height="%.1fmm" viewBox="0 0 %.1f %.1f">' % (W, Hh, W, Hh)]
    for poly, hl, labels, dx, dy in items:
        s.append('<polygon points="%s" fill="none" stroke="#ff0000" stroke-width="0.1"/>' % " ".join(
            "%.3f,%.3f" % (px + dx, Hh - (py + dy)) for px, py in poly))
        for cx, cy, d in hl:
            s.append('<circle cx="%.3f" cy="%.3f" r="%.3f" fill="none" stroke="#ff0000" stroke-width="0.1"/>' % (
                cx + dx, Hh - (cy + dy), d / 2))
        for tx, ty, t in labels:
            s.append('<text x="%.2f" y="%.2f" font-family="Helvetica" font-size="4" fill="#0000ff">%s</text>' % (
                tx + dx, Hh - (ty + dy), t))
    s.append("</svg>")
    with open(path, "w") as fh:
        fh.write("\n".join(s))


def pdf(path, items, W, Hh, title):
    ops = ["1 0 0 RG 0.001 w 1 J 1 j"]
    for poly, hl, labels, dx, dy in items:
        pts = [((px + dx) * MM, (py + dy) * MM) for px, py in poly]
        ops.append("%.3f %.3f m " % pts[0] + " ".join("%.3f %.3f l" % p for p in pts[1:]) + " h S")
        for cx, cy, d in hl:
            cx, cy, r = (cx + dx) * MM, (cy + dy) * MM, d / 2.0 * MM
            q = KB * r
            ops.append("%.3f %.3f m %.3f %.3f %.3f %.3f %.3f %.3f c %.3f %.3f %.3f %.3f %.3f %.3f c "
                       "%.3f %.3f %.3f %.3f %.3f %.3f c %.3f %.3f %.3f %.3f %.3f %.3f c h S" % (
                           cx + r, cy, cx + r, cy + q, cx + q, cy + r, cx, cy + r, cx - q, cy + r, cx - r, cy + q, cx - r, cy,
                           cx - r, cy - q, cx - q, cy - r, cx, cy - r, cx + q, cy - r, cx + r, cy - q, cx + r, cy))
    ops.append("0 0 1 rg")
    for poly, hl, labels, dx, dy in items:
        for tx, ty, t in labels:
            ops.append("BT /F1 %.2f Tf %.3f %.3f Td (%s) Tj ET" % (4 * MM, (tx + dx) * MM, (ty + dy) * MM,
                                                                   t.replace("(", "\\(").replace(")", "\\)")))
    content = "\n".join(ops).encode("latin-1")
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            ("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.3f %.3f] /Contents 4 0 R "
             "/Resources << /Font << /F1 5 0 R >> >> >>" % (W * MM, Hh * MM)).encode(),
            b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            ("<< /Title (%s) /Producer (laser_box_fingers.py) >>" % title).encode()]
    out = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    offs = []
    for i, o in enumerate(objs):
        offs.append(len(out))
        out += b"%d 0 obj\n" % (i + 1) + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1) + b"".join(b"%010d 00000 n \n" % o for o in offs)
    out += b"trailer\n<< /Size %d /Root 1 0 R /Info 6 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    for ext in (".pdf", ".ai"):
        with open(path + ext, "wb") as fh:
            fh.write(out)


if not os.path.isdir(OUT):
    os.makedirs(OUT)
for f in os.listdir(OUT):
    os.remove(os.path.join(OUT, f))
base = os.path.join(OUT, "Box_fingers_plywood_1-8in_30x18in_horizontal")
pdf(base, items, SHEET_W, SHEET_H, "Box, finger joints, 1/8 in plywood, 30 x 18 in sheet (horizontal)")
dxf(base + ".dxf", items)
svg(base + ".svg", items, SHEET_W, SHEET_H)
front = ("Front", 1, rect(INNER_L, FRONT_H), [], [])
ab = os.path.join(OUT, "Front_window_acrylic_1-16in_32x16in_horizontal")
pdf(ab, [(front[2], [], [], 5.0, 5.0)], 812.8, 406.4, "Acrylic 1/16 in, 32 x 16 in sheet (horizontal)")
dxf(ab + ".dxf", [(front[2], [], [], 5.0, 5.0)])
svg(ab + ".svg", [(front[2], [], [], 5.0, 5.0)], 812.8, 406.4)

print("joint check: %d samples, %d errors, %d kerf-overlap samples (expected, %.2f mm each side of a finger)" % (
    n_s, len(real_bad), len(over), KERF / 2))
for b in real_bad[:10]:
    print("   BAD", b)
for p in PANELS:
    print("  %-10s %3d corners" % (p, len(outlines[p])))
print("sheet used %.0f x %.0f of %.0f x %.0f mm: %s" % (Wused, Hused, SHEET_W, SHEET_H,
                                                        "fits" if Wused <= SHEET_W and Hused <= SHEET_H else "DOES NOT FIT"))
print("inner parts: guide bar %.1f long, acrylic front %.1f x %.1f, A-frame %.1f tall (bore %.1f up)" % (
    INNER_L, INNER_L, FRONT_H, af_h, SHAFT_Z - T1))
