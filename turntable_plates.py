"""Pack the turntable STLs (already in print orientation, centred at 0,0) into 3MF plates for a 256 mm bed."""
import struct, zipfile, os

SRC = "/Users/cassiuspalacio/Documents/UC Berkeley TDF/PhysComp/Nov 9/STL_turntable"
DST = "/Users/cassiuspalacio/Documents/UC Berkeley TDF/PhysComp/Nov 9/Turntable_Dragon_Files/XX_2_3D_PRINT"
C = 128.0


def read(name):
    with open(os.path.join(SRC, name + ".stl"), "rb") as f:
        f.read(80)
        n = struct.unpack("<I", f.read(4))[0]
        return [struct.unpack("<12fH", f.read(50))[3:12] for _ in range(n)]


def obj_xml(oid, name, tris, dx, dy):
    vid, verts, faces = {}, [], []
    for t in tris:
        ids = []
        for i in range(3):
            k = (round(t[3 * i] + dx, 4), round(t[3 * i + 1] + dy, 4), round(t[3 * i + 2], 4))
            if k not in vid:
                vid[k] = len(verts)
                verts.append(k)
            ids.append(vid[k])
        if len(set(ids)) == 3:
            faces.append(ids)
    return ('<object id="%d" name="%s" type="model"><mesh><vertices>%s</vertices><triangles>%s</triangles></mesh></object>' % (
        oid, name, "".join('<vertex x="%.4f" y="%.4f" z="%.4f"/>' % v for v in verts),
        "".join('<triangle v1="%d" v2="%d" v3="%d"/>' % tuple(f) for f in faces)), verts)


def write(fname, items):
    objs, ids, allv = [], [], []
    for i, (name, label, dx, dy) in enumerate(items):
        x, v = obj_xml(i + 1, label, read(name), C + dx, C + dy)
        objs.append(x)
        ids.append(i + 1)
        allv += v
    xs, ys = [p[0] for p in allv], [p[1] for p in allv]
    assert min(xs) >= 0 and min(ys) >= 0 and max(xs) <= 256 and max(ys) <= 256, (fname, min(xs), min(ys), max(xs), max(ys))
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><resources>' + "".join(objs) +
             '</resources><build>' + "".join('<item objectid="%d"/>' % i for i in ids) + '</build></model>')
    os.makedirs(DST, exist_ok=True)
    with zipfile.ZipFile(os.path.join(DST, fname), "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr("3D/3dmodel.model", model)
    print(fname, "x %.1f-%.1f  y %.1f-%.1f" % (min(xs), max(xs), min(ys), max(ys)))


# one plate: offsets are from the bed centre (128,128)
ITEMS = [
    ("T2_Platter_with_ring_gear", "Platter_with_ring_gear", -48, -48),          # 150 dia, bottom-left
    ("T1_Base_deck_with_post", "Base_deck_with_post", 43, 82),               # 115 x 70, right side
    ("T3_Motor_carriage", "Motor_carriage", 80, 0),
    ("T1_Leg", "Leg_1", -110, 50), ("T1_Leg", "Leg_2", -110, 80), ("T1_Leg", "Leg_3", -110, 110),
    ("T3_Pinion_28T_TIGHT", "Pinion_28T_TIGHT_1dimple", -70, 95),
    ("T3_Pinion_28T_LOOSE", "Pinion_28T_LOOSE_2dimples", -20, 95),
    ("T3_Pinion_17T_TIGHT", "Pinion_17T_TIGHT_1dimple", 62, -88),
    ("T3_Pinion_17T_LOOSE", "Pinion_17T_LOOSE_2dimples", 102, -88),
]
if __name__ == "__main__":
    import glob
    for f in glob.glob(os.path.join(DST, "*.3mf")):
        os.remove(f)
    write("XX_ONE_PLATE_turntable_dragon_all_parts.3mf", ITEMS)
