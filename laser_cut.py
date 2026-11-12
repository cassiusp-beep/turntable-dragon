# -*- coding: utf-8 -*-
"""Laser-cut files for the automaton box (plain python3: python3 laser_cut.py).
Writes ./Laser_Cut/<part>.dxf + .svg for each panel, and an all-parts layout on ONE 18 x 30 in sheet of 1/8 in plywood
(Jacobs Universal VLS 6.60 bed is 32 x 18 in). Positions come from dragon_automaton.py (box 300 x 120 x 130, glued
butt joints, 6 mm walls = two 1/8 in layers glued together).

Hole sizes are DRAWN slightly small because the laser beam (kerf, ~0.15 mm) opens every hole up a little:
  rod / post holes   6.4 drawn -> ~6.55 cut   printed 6.0 mm rods slide; posts get glued
  shaft holes        8.3 drawn -> ~8.45 cut   printed 8.0 mm shaft turns freely (rub with pencil graphite)
Panels that fit BETWEEN the end walls are drawn 1 mm short (287 instead of 288) so plywood that is a bit thicker
than 6 mm still fits; centre them.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "Laser_Cut")
T = 6.0
ROD_HOLE_D, SHAFT_HOLE_D = 6.4, 8.3
INNER_L = 288.0 - 1.0
ROD_XS = [30.16, 74.83, 120.0, 173.68, 222.47, 273.89]   # R1 tail, R2 back, wing, R3 belly, R4 neck, head
POST_XS = [108.0, 132.0]                                  # shoulder posts (chest mount)
SHAFT_Y, SHAFT_Z = 60.0, 50.0


def rect(w, h):
    return [(0, 0), (w, 0), (w, h), (0, h)]


# each part: (name, material, outline polygon, [holes (x, y, d)], [labels (x, y, text)])
parts = []
holes = [(x, 60.0, ROD_HOLE_D) for x in ROD_XS + POST_XS]
parts.append(("TopPlate", "6 mm ply", rect(300, 120), holes, [(6, 6, "TOP  L=motor end")]))
parts.append(("Floor", "6 mm ply", rect(300, 120), [], [(6, 6, "FLOOR  L=motor end")]))
x0 = T + 0.5
parts.append(("RodGuideBar", "6 mm ply", rect(INNER_L, 30), [(x - x0, 15.0, ROD_HOLE_D) for x in ROD_XS + POST_XS],
              [(3, 3, "GUIDE  L")]))
parts.append(("BackPanel", "6 mm ply", rect(INNER_L, 118), [], [(6, 6, "BACK")]))
for nm in ("EndWall_L", "EndWall_R"):
    parts.append((nm, "6 mm ply", rect(120, 118), [(SHAFT_Y, SHAFT_Z - T, SHAFT_HOLE_D)], [(6, 6, nm.replace("_", " "))]))
parts.append(("Support_Aframe", "6 mm ply", [(0, 0), (80, 0), (48, 56), (32, 56)], [(40.0, 44.0, SHAFT_HOLE_D)],
              [(22, 4, "A-FRAME")]))
parts.append(("FrontPanel_clear_acrylic_1-16in", "1/16 in clear acrylic", rect(INNER_L, 118), [], []))


# ------------------------------------------------------------------ writers
def dxf(path, items):
    """items: list of (polygon, holes, labels, dx, dy) -> R12 DXF, mm, layer CUT and ENGRAVE"""
    L = ["0", "SECTION", "2", "HEADER", "9", "$ACADVER", "1", "AC1009", "9", "$INSUNITS", "70", "4", "0", "ENDSEC",
         "0", "SECTION", "2", "ENTITIES"]
    for poly, hl, labels, dx, dy in items:
        L += ["0", "POLYLINE", "8", "CUT", "66", "1", "70", "1"]
        for x, y in poly:
            L += ["0", "VERTEX", "8", "CUT", "10", "%.3f" % (x + dx), "20", "%.3f" % (y + dy), "30", "0"]
        L += ["0", "SEQEND", "8", "CUT"]
        for x, y, d in hl:
            L += ["0", "CIRCLE", "8", "CUT", "10", "%.3f" % (x + dx), "20", "%.3f" % (y + dy), "30", "0", "40", "%.3f" % (d / 2)]
        for x, y, t in labels:
            L += ["0", "TEXT", "8", "ENGRAVE", "10", "%.3f" % (x + dx), "20", "%.3f" % (y + dy), "30", "0", "40", "4", "1", t]
    L += ["0", "ENDSEC", "0", "EOF"]
    with open(path, "w") as fh:
        fh.write("\n".join(L) + "\n")


def svg(path, items, W, H):
    s = ['<svg xmlns="http://www.w3.org/2000/svg" width="%.1fmm" height="%.1fmm" viewBox="0 0 %.1f %.1f">' % (W, H, W, H)]
    for poly, hl, labels, dx, dy in items:
        pts = " ".join("%.3f,%.3f" % (x + dx, H - (y + dy)) for x, y in poly)
        s.append('<polygon points="%s" fill="none" stroke="#ff0000" stroke-width="0.1"/>' % pts)
        for x, y, d in hl:
            s.append('<circle cx="%.3f" cy="%.3f" r="%.3f" fill="none" stroke="#ff0000" stroke-width="0.1"/>' % (
                x + dx, H - (y + dy), d / 2))
        for x, y, t in labels:
            s.append('<text x="%.2f" y="%.2f" font-family="Helvetica" font-size="4" fill="#0000ff">%s</text>' % (
                x + dx, H - (y + dy), t))
    s.append("</svg>")
    with open(path, "w") as fh:
        fh.write("\n".join(s))


def size(poly):
    return max(p[0] for p in poly), max(p[1] for p in poly)


if not os.path.isdir(OUT):
    os.makedirs(OUT)
for f in os.listdir(OUT):
    os.remove(os.path.join(OUT, f))
for nm, mat, poly, hl, lb in parts:
    w, h = size(poly)
    dxf(os.path.join(OUT, nm + ".dxf"), [(poly, hl, lb, 0, 0)])
    svg(os.path.join(OUT, nm + ".svg"), [(poly, hl, lb, 0, 0)], w, h)

# ------------------------------------------------------------------ one 18 x 30 in (457 x 762 mm) sheet of 1/8 in plywood
# 1/8 in ply is ~3.2 mm, so the parts that need the 6 mm thickness are cut TWICE and glued face to face (~6.3 mm):
#   top plate, guide bar (long guide for the rods), end walls + A-frame (shaft bearings, and they set the 288 mm
#   inside length). Floor and back panel stay single: everything stands on the floor, so a thinner floor only
#   lowers the whole box 3 mm, which changes nothing that moves.
SHEET_W, SHEET_H = 457.2, 762.0
G = 5.0
byname = dict((p[0], p) for p in parts)


def tagged(nm, k):
    n, m, poly, hl, lb = byname[nm]
    return (poly, hl, [(x, y, t + " %d/2" % k) for x, y, t in lb] if k else lb)


rows = [[("TopPlate", 1), ("EndWall_L", 1)], [("TopPlate", 2), ("EndWall_L", 2)], [("Floor", 0), ("EndWall_R", 1)],
        [("BackPanel", 0), ("EndWall_R", 2)], [("RodGuideBar", 1)], [("RodGuideBar", 2)],
        [("Support_Aframe", 1), ("Support_Aframe", 2)]]
items, y, W = [], G, 0
for row in rows:
    x, rh = G, 0
    for nm, k in row:
        poly, hl, lb = tagged(nm, k)
        w, h = size(poly)
        items.append((poly, hl, lb, x, y))
        x += w + G
        rh = max(rh, h)
    W = max(W, x)
    y += rh + G
H = y
# the files use the full sheet size so the layout lands where you expect on the bed
dxf(os.path.join(OUT, "ALL_parts_18x30in_sheet_1-8in_ply.dxf"), items)
svg(os.path.join(OUT, "ALL_parts_18x30in_sheet_1-8in_ply.svg"), items, SHEET_W, SHEET_H)
print("parts:", ", ".join("%s %.0fx%.0f" % (p[0], size(p[2])[0], size(p[2])[1]) for p in parts))
print("layout uses %.0f x %.0f mm of the %.0f x %.0f sheet (fits: %s), %d pieces" % (
    W, H, SHEET_W, SHEET_H, W <= SHEET_W and H <= SHEET_H, len(items)))


# ------------------------------------------------------------------ Illustrator-ready vector PDF (+ the same file as .ai)
# Illustrator opens a PDF-based .ai directly at true size. Cut lines: pure RGB red, 0.001 pt hairline (Universal
# laser driver = vector cut). Labels: pure RGB blue Helvetica text (raster engrave, or delete them).
MM = 72.0 / 25.4
K = 0.5522847498


def pdf(path, items, W, H, title):
    ops = ["1 0 0 RG 0.001 w 1 J 1 j"]
    for poly, hl, labels, dx, dy in items:
        pts = [((x + dx) * MM, (y + dy) * MM) for x, y in poly]
        ops.append("%.3f %.3f m " % pts[0] + " ".join("%.3f %.3f l" % p for p in pts[1:]) + " h S")
        for x, y, d in hl:
            cx, cy, r = (x + dx) * MM, (y + dy) * MM, d / 2.0 * MM
            k = K * r
            ops.append("%.3f %.3f m %.3f %.3f %.3f %.3f %.3f %.3f c %.3f %.3f %.3f %.3f %.3f %.3f c "
                       "%.3f %.3f %.3f %.3f %.3f %.3f c %.3f %.3f %.3f %.3f %.3f %.3f c h S" % (
                           cx + r, cy, cx + r, cy + k, cx + k, cy + r, cx, cy + r,
                           cx - k, cy + r, cx - r, cy + k, cx - r, cy,
                           cx - r, cy - k, cx - k, cy - r, cx, cy - r,
                           cx + k, cy - r, cx + r, cy - k, cx + r, cy))
    ops.append("0 0 1 rg")
    for poly, hl, labels, dx, dy in items:
        for x, y, t in labels:
            t = t.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            ops.append("BT /F1 %.2f Tf %.3f %.3f Td (%s) Tj ET" % (4 * MM, (x + dx) * MM, (y + dy) * MM, t))
    content = "\n".join(ops).encode("latin-1")
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            ("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.3f %.3f] /Contents 4 0 R "
             "/Resources << /Font << /F1 5 0 R >> >> >>" % (W * MM, H * MM)).encode(),
            b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            ("<< /Title (%s) /Producer (laser_cut.py) >>" % title).encode()]
    out = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    offs = []
    for i, o in enumerate(objs):
        offs.append(len(out))
        out += b"%d 0 obj\n" % (i + 1) + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offs)
    out += b"trailer\n<< /Size %d /Root 1 0 R /Info 6 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    for ext in (".pdf", ".ai"):
        with open(path + ext, "wb") as fh:
            fh.write(out)


pdf(os.path.join(OUT, "ALL_parts_18x30in_sheet_1-8in_ply"), items, SHEET_W, SHEET_H, "Plywood 1/8 in, 18 x 30 in sheet")
_n, _m, _poly, _hl, _lb = byname["FrontPanel_clear_acrylic_1-16in"]
pdf(os.path.join(OUT, "FrontPanel_clear_acrylic_1-16in"), [(_poly, _hl, _lb, 5.0, 5.0)], 406.4, 812.8,
    "Acrylic 1/16 in, 16 x 32 in sheet")
print("illustrator files written (.ai + .pdf)")
