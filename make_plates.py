# -*- coding: utf-8 -*-
"""Pack the print package onto 256 x 256 mm plates and write one 3MF per plate (plus an SVG preview).
Run with plain python3 from this folder:  python3 make_plates.py
Parts keep their print orientation (only moved / turned 90 deg about Z). The two wing files load as ONE object with
two parts (membrane + bones) so Bambu Studio can give them different colours.
"""
import os
import struct
import zipfile
import math

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "Print_Package")
OUT = os.path.join(HERE, "Print_Plates")
BED = 256.0
MARGIN = 5.0     # keep off the bed edge
GAP = 5.0        # between parts (room for a brim)
AREA = BED - 2 * MARGIN


def read_stl(path):
    with open(path, "rb") as fh:
        fh.read(80)
        n = struct.unpack("<I", fh.read(4))[0]
        tris = []
        for _ in range(n):
            d = struct.unpack("<12fH", fh.read(50))
            tris.append((d[3:6], d[6:9], d[9:12]))
    return tris


def bbox(tris_list):
    xs = [p[0] for tris in tris_list for t in tris for p in t]
    ys = [p[1] for tris in tris_list for t in tris for p in t]
    zs = [p[2] for tris in tris_list for t in tris for p in t]
    return min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)


def hull(pts):
    pts = sorted(set((round(x, 1), round(y, 1)) for x, y in pts))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


class Part(object):
    def __init__(self, name, meshes):
        self.name = name
        self.meshes = meshes          # list of (label, tris), shared frame
        x0, y0, z0, x1, y1, z1 = bbox([t for _, t in meshes])
        self.w, self.h, self.zmax = x1 - x0, y1 - y0, z1 - z0
        self.off = (x0, y0, z0)
        self.x = self.y = 0.0
        self.rot = False
        self.hull = hull([(p[0] - x0, p[1] - y0) for _, t in meshes for tri in t for p in tri])

    def dims(self):
        return (self.h, self.w) if self.rot else (self.w, self.h)

    def transform(self, p):
        x, y, z = p[0] - self.off[0], p[1] - self.off[1], p[2] - self.off[2]
        if self.rot:                     # 90 deg about Z, then shift back into +X
            x, y = self.h - y, x
        return (x + self.x, y + self.y, z)


def load_folder(folder):
    files = sorted(f for f in os.listdir(folder) if f.endswith(".stl"))
    parts, used = [], set()
    for f in files:
        if f in used:
            continue
        if "membrane_colour1" in f:
            g = f.replace("membrane_colour1", "bones_colour2")
            used.update([f, g])
            parts.append(Part(f.split("_membrane")[0], [("membrane", read_stl(os.path.join(folder, f))),
                                                        ("bones", read_stl(os.path.join(folder, g)))]))
        elif "bones_colour2" in f:
            continue
        else:
            used.add(f)
            parts.append(Part(f[:-4], [("body", read_stl(os.path.join(folder, f)))]))
    return parts


# ------------------------------------------------------------------ packing: MaxRects, best short-side fit, 90 deg turns
def pack(parts):
    plates = []
    todo = sorted(parts, key=lambda p: -(max(p.w, p.h) * 1000 + p.w * p.h))
    while todo:
        free = [(0.0, 0.0, AREA + GAP, AREA + GAP)]   # every part carries its gap on the +X/+Y side
        placed, left = [], []
        for p in todo:
            best = None
            for rot in (False, True):
                w, h = (p.h, p.w) if rot else (p.w, p.h)
                w, h = w + GAP, h + GAP
                for fx, fy, fw, fh in free:
                    if w <= fw + 1e-6 and h <= fh + 1e-6:
                        score = (min(fw - w, fh - h), fy, fx)
                        if best is None or score < best[0]:
                            best = (score, fx, fy, rot, w, h)
            if best is None:
                left.append(p)
                continue
            _, fx, fy, rot, w, h = best
            p.x, p.y, p.rot = fx, fy, rot
            placed.append(p)
            new = []
            for fr in free:
                rx, ry, rw, rh = fr
                if fx >= rx + rw or fx + w <= rx or fy >= ry + rh or fy + h <= ry:
                    new.append(fr)
                    continue
                if fx > rx:
                    new.append((rx, ry, fx - rx, rh))
                if fx + w < rx + rw:
                    new.append((fx + w, ry, rx + rw - fx - w, rh))
                if fy > ry:
                    new.append((rx, ry, rw, fy - ry))
                if fy + h < ry + rh:
                    new.append((rx, fy + h, rw, ry + rh - fy - h))
            free = [a for a in new if not any(a != b and b[0] <= a[0] and b[1] <= a[1] and
                                              a[0] + a[2] <= b[0] + b[2] and a[1] + a[3] <= b[1] + b[3] for b in new)]
        if not placed:
            raise Exception("does not fit the bed: " + ", ".join(p.name for p in left))
        # centre the group on the bed
        mx = max(p.x + p.dims()[0] for p in placed)   # real extents (without the trailing gap)
        my = max(p.y + p.dims()[1] for p in placed)
        dx, dy = MARGIN + (AREA - mx) / 2.0, MARGIN + (AREA - my) / 2.0
        for p in placed:
            p.x += dx
            p.y += dy
        plates.append(placed)
        todo = left
    return plates


# ------------------------------------------------------------------ 3MF writer (core spec; components = one object, several parts)
def mesh_xml(oid, name, tris, part):
    idx, verts, faces = {}, [], []
    for t in tris:
        f = []
        for p in t:
            q = part.transform(p)
            k = (round(q[0], 4), round(q[1], 4), round(q[2], 4))
            if k not in idx:
                idx[k] = len(verts)
                verts.append(k)
            f.append(idx[k])
        if len(set(f)) == 3:
            faces.append(f)
    v = "".join('<vertex x="%.4f" y="%.4f" z="%.4f"/>' % k for k in verts)
    tr = "".join('<triangle v1="%d" v2="%d" v3="%d"/>' % tuple(f) for f in faces)
    return '<object id="%d" name="%s" type="model"><mesh><vertices>%s</vertices><triangles>%s</triangles></mesh></object>' % (
        oid, name, v, tr)


def write_3mf(path, plate):
    objs, items, oid = [], [], 1
    for p in plate:
        if len(p.meshes) == 1:
            objs.append(mesh_xml(oid, p.name, p.meshes[0][1], p))
            items.append(oid)
            oid += 1
        else:
            comp = []
            for label, tris in p.meshes:
                objs.append(mesh_xml(oid, p.name + " " + label, tris, p))
                comp.append(oid)
                oid += 1
            objs.append('<object id="%d" name="%s" type="model"><components>%s</components></object>' % (
                oid, p.name, "".join('<component objectid="%d"/>' % c for c in comp)))
            items.append(oid)
            oid += 1
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><resources>' + "".join(objs) +
             '</resources><build>' + "".join('<item objectid="%d"/>' % i for i in items) + '</build></model>')
    ct = ('<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)


def write_svg(path, plate, title):
    s = 2.0
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">' % (
        BED * s + 20, BED * s + 50, BED * s + 20, BED * s + 50),
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="10" y="22" font-family="Helvetica" font-size="16">%s</text>' % title,
        '<rect x="10" y="40" width="%d" height="%d" fill="#eee" stroke="#333"/>' % (BED * s, BED * s)]
    for p in plate:
        pts = []
        for hx, hy in p.hull:
            q = p.transform((hx + p.off[0], hy + p.off[1], p.off[2]))
            pts.append("%.1f,%.1f" % (10 + q[0] * s, 40 + (BED - q[1]) * s))
        out.append('<polygon points="%s" fill="#f4a261" stroke="#333" stroke-width="1"/>' % " ".join(pts))
        w, h = p.dims()
        cx, cy = 10 + (p.x + w / 2) * s, 40 + (BED - p.y - h / 2) * s
        out.append('<text x="%.1f" y="%.1f" font-family="Helvetica" font-size="9" text-anchor="middle">%s</text>' % (
            cx, cy, p.name.split("_", 1)[1][:22] if "_" in p.name else p.name))
    out.append("</svg>")
    with open(path, "w") as fh:
        fh.write("\n".join(out))


def check(plate):
    """no two footprints (with the gap) overlap, everything inside the bed"""
    errs = []
    for i, a in enumerate(plate):
        aw, ah = a.dims()
        if a.x < MARGIN - 1e-6 or a.y < MARGIN - 1e-6 or a.x + aw > BED - MARGIN + 1e-6 or a.y + ah > BED - MARGIN + 1e-6:
            errs.append("off bed: " + a.name)
        for b in plate[i + 1:]:
            bw, bh = b.dims()
            if a.x < b.x + bw + GAP - 1e-6 and b.x < a.x + aw + GAP - 1e-6 and a.y < b.y + bh + GAP - 1e-6 and b.y < a.y + ah + GAP - 1e-6:
                errs.append("overlap: %s / %s" % (a.name, b.name))
    return errs


if __name__ == "__main__":
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    for f in os.listdir(OUT):
        os.remove(os.path.join(OUT, f))
    summary = []
    for folder in sorted(d for d in os.listdir(SRC) if os.path.isdir(os.path.join(SRC, d))):
        plates = pack(load_folder(os.path.join(SRC, folder)))
        for k, plate in enumerate(plates):
            nm = "%s_plate%d" % (folder, k + 1)
            write_3mf(os.path.join(OUT, nm + ".3mf"), plate)
            write_svg(os.path.join(OUT, nm + "_preview.svg"), plate, nm)
            used = sum(p.w * p.h for p in plate) / (BED * BED)
            summary.append("%-42s %2d parts, %3.0f%% of bed, %s" % (nm, len(plate), used * 100, check(plate) or "ok"))
    print("\n".join(summary))
