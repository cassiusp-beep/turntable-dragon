"""Lots of small dragon eggs to scatter on the turntable. Pure Python + numpy -> STL/3MF. (Nest code kept but unused.)

3 eggs, flat-bottomed (print standing, no supports), each with a different dragon texture:
  egg A 34 mm wide: overlapping scales     egg B 30 mm: spiral ridges     egg C 26 mm: gem studs
Nest: 84 mm disk with 3 socket rings + a twiggy rim. It sits inside the dragon's curl (inner edge ~ r47).
Tolerance: socket inner = egg diameter at socket height + texture + 0.6 mm (eggs drop in and lift out).
"""
import math, os, struct, zipfile
import numpy as np

OUT = "/Users/cassiuspalacio/Documents/UC Berkeley TDF/PhysComp/Nov 9/STL_eggs"
PLATE = "/Users/cassiuspalacio/Documents/UC Berkeley TDF/PhysComp/Nov 9/Turntable_Dragon_Files/XX_2_3D_PRINT/XX_EGGS_30_small_dragon_eggs.3mf"
MAX_OVERHANG = 50.0      # deg from vertical at the flat base cut
SOCKET_H, CLEAR = 5.0, 0.6
AMP = 0.8


def amp(W):
    return max(0.35, 0.032 * W)   # texture depth scales with egg size (0.35 mm min so it still shows)


def egg_r(s, W):
    """radius at s in [-1,1] (bottom..top); wider low, pointier top"""
    return (W / 2.0) * math.sqrt(max(0.0, 1 - s * s)) * (1 - 0.16 * s)


def cut_s(W, H):
    """lowest s where the wall overhangs <= MAX_OVERHANG (so the egg prints standing on a flat base)"""
    for i in range(1000):
        s = -0.999 + i * 0.002
        ds = 1e-4
        dr = egg_r(s + ds, W) - egg_r(s, W)
        dz = ds * H / 2.0
        if math.degrees(math.atan2(dr, dz)) <= MAX_OVERHANG:
            return s
    return -0.5


def smooth(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def tex_scales(th, z, H, W):
    cols = 9
    hs = math.pi * W / cols * 0.75
    row = math.floor(z / hs)
    v = z / hs - row
    u = (th / (2 * math.pi) * cols + (0.5 if row % 2 else 0.0)) % 1.0
    half = 0.5 * (1 - 0.55 * v)                    # scale narrows toward its tip -> pointed U shape
    shape = max(0.0, 1 - ((u - 0.5) / half) ** 2)
    return amp(W) * smooth(v / 0.22) * (1 - v) ** 0.6 * shape ** 0.8


def tex_spiral(th, z, H, W):
    return amp(W) * max(0.0, math.cos(5 * th + z * 0.9)) ** 3


def tex_studs(th, z, H, W):
    cols = 8
    hs = math.pi * W / cols * 0.9
    row = round(z / hs)
    best = 0.0
    for r in (row - 1, row, row + 1):
        zc = r * hs
        off = 0.5 if r % 2 else 0.0
        c = round(th / (2 * math.pi) * cols - off)
        for cc in (c - 1, c, c + 1):
            tc = (cc + off) / cols * 2 * math.pi
            dx = ((th - tc + math.pi) % (2 * math.pi) - math.pi) * W / 2.0
            d2 = (dx * dx + (z - zc) ** 2) / (hs * 0.32) ** 2
            best = max(best, math.exp(-d2))
    return amp(W) * 1.4 * best


def egg_mesh(W, H, tex, nth=108, nz=100):
    s0 = cut_s(W, H)
    z0 = s0 * H / 2.0
    verts, tris = [], []
    rings = []
    for j in range(nz + 1):
        s = s0 + (1 - s0) * (1 - (1 - j / float(nz)) ** 1.0) if j < nz else 1.0
        s = s0 + (1 - s0) * j / float(nz)
        z = s * H / 2.0
        r = egg_r(s, W)
        fade = min(1.0, r / (W * 0.18))                 # no texture near the tip
        ring = []
        if j == nz:
            verts.append((0.0, 0.0, z - z0))
            rings.append([len(verts) - 1])
            break
        for i in range(nth):
            th = 2 * math.pi * i / nth
            rr = r + (tex(th, z - z0, H, W) * fade if j > 0 else 0.0)
            verts.append((rr * math.cos(th), rr * math.sin(th), z - z0))
            ring.append(len(verts) - 1)
        rings.append(ring)
    verts.append((0.0, 0.0, 0.0))
    bc = len(verts) - 1
    b = rings[0]
    for i in range(nth):
        tris.append((bc, b[(i + 1) % nth], b[i]))
    for j in range(len(rings) - 1):
        a, c = rings[j], rings[j + 1]
        for i in range(nth):
            i2 = (i + 1) % nth
            if len(c) == 1:
                tris.append((a[i], a[i2], c[0]))
            else:
                tris.append((a[i], a[i2], c[i2]))
                tris.append((a[i], c[i2], c[i]))
    base_r = egg_r(s0, W)
    sock_r = egg_r(s0 + SOCKET_H / (H / 2.0), W) + AMP + CLEAR
    return np.array(verts), tris, base_r, sock_r, H / 2.0 * (1 - s0)


def tube_mesh(path, rad, n=10):
    """closed tube along a closed polyline path (N,3)"""
    verts, tris = [], []
    N = len(path)
    for k in range(N):
        p, q = path[k], path[(k + 1) % N]
        t = q - path[k - 1]
        t /= np.linalg.norm(t)
        up = np.array([0, 0, 1.0])
        nrm = np.cross(t, up)
        nrm /= np.linalg.norm(nrm)
        bi = np.cross(nrm, t)
        for i in range(n):
            a = 2 * math.pi * i / n
            verts.append(tuple(p + rad * (math.cos(a) * nrm + math.sin(a) * bi)))
    for k in range(N):
        for i in range(n):
            a0, a1 = k * n + i, k * n + (i + 1) % n
            b0, b1 = ((k + 1) % N) * n + i, ((k + 1) % N) * n + (i + 1) % n
            tris += [(a0, b0, b1), (a0, b1, a1)]
    return np.array(verts), tris


def cyl_mesh(x, y, z0, z1, r, n=72, ri=None):
    """solid cylinder, or a ring if ri is given"""
    verts, tris = [], []
    if ri is None:
        for z in (z0, z1):
            for i in range(n):
                a = 2 * math.pi * i / n
                verts.append((x + r * math.cos(a), y + r * math.sin(a), z))
        verts += [(x, y, z0), (x, y, z1)]
        c0, c1 = 2 * n, 2 * n + 1
        for i in range(n):
            i2 = (i + 1) % n
            tris += [(c0, i2, i), (c1, n + i, n + i2), (i, i2, n + i2), (i, n + i2, n + i)]
    else:
        for rad in (r, ri):
            for z in (z0, z1):
                for i in range(n):
                    a = 2 * math.pi * i / n
                    verts.append((x + rad * math.cos(a), y + rad * math.sin(a), z))
        O0, O1, I0, I1 = 0, n, 2 * n, 3 * n
        for i in range(n):
            i2 = (i + 1) % n
            tris += [(O0 + i, O0 + i2, O1 + i2), (O0 + i, O1 + i2, O1 + i)]            # outer
            tris += [(I0 + i, I1 + i2, I0 + i2), (I0 + i, I1 + i, I1 + i2)]            # inner
            tris += [(O1 + i, O1 + i2, I1 + i2), (O1 + i, I1 + i2, I1 + i)]            # top
            tris += [(O0 + i, I0 + i2, O0 + i2), (O0 + i, I0 + i, I0 + i2)]            # bottom
    return np.array(verts), tris


def merge(meshes):
    V, T, off = [], [], 0
    for v, t in meshes:
        V.append(v)
        T += [(a + off, b + off, c + off) for a, b, c in t]
        off += len(v)
    return np.vstack(V), T


def write_stl(path, V, T):
    with open(path, "wb") as f:
        f.write(b"\0" * 80)
        f.write(struct.pack("<I", len(T)))
        for a, b, c in T:
            p, q, r = V[a], V[b], V[c]
            n = np.cross(q - p, r - p)
            ln = np.linalg.norm(n) or 1.0
            f.write(struct.pack("<12fH", *(n / ln), *p, *q, *r, 0))


TEX = [("scales", tex_scales), ("spiral", tex_spiral), ("studs", tex_studs)]
SIZES = [10.0, 12.0, 14.0]
os.makedirs(OUT, exist_ok=True)
for f in os.listdir(OUT):
    os.remove(os.path.join(OUT, f))
objs, made = [], {}
for tn, tex in TEX:
    for W in SIZES:
        V, T, br, sr, h = egg_mesh(W, W * 1.33, tex)
        nm = "Egg_%s_%dmm" % (tn, W)
        write_stl(os.path.join(OUT, nm + ".stl"), V, T)
        made[nm] = (V, T, W)
        print("%-18s %2.0f wide x %4.1f tall, flat base %.1f mm" % (nm, W, h, 2 * br))
# 30 eggs: 6 columns x 5 rows, sizes and textures mixed
names = list(made)
order = [names[(r * 6 + c) % len(names)] for r in range(5) for c in range(6)]
SP = 30.0
xml, items = [], []
for k, nm in enumerate(order):
    V, T, W = made[nm]
    dx, dy = 128 + (k % 6 - 2.5) * SP, 128 + (k // 6 - 2) * SP
    assert V[:, 0].min() + dx > 2 and V[:, 0].max() + dx < 254 and V[:, 1].min() + dy > 2 and V[:, 1].max() + dy < 254
    vx = "".join('<vertex x="%.3f" y="%.3f" z="%.3f"/>' % (p[0] + dx, p[1] + dy, p[2]) for p in V)
    tx = "".join('<triangle v1="%d" v2="%d" v3="%d"/>' % t for t in T)
    xml.append('<object id="%d" name="%s_%02d" type="model"><mesh><vertices>%s</vertices><triangles>%s</triangles></mesh></object>' % (k + 1, nm, k + 1, vx, tx))
    items.append(k + 1)
model = ('<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><resources>'
         + "".join(xml) + '</resources><build>' + "".join('<item objectid="%d"/>' % i for i in items) + '</build></model>')
for f in os.listdir(os.path.dirname(PLATE)):
    if f.startswith("XX_EGGS"):
        os.remove(os.path.join(os.path.dirname(PLATE), f))
with zipfile.ZipFile(PLATE, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    z.writestr("3D/3dmodel.model", model)
print("plate: %d eggs" % len(items))
