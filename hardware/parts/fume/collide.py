"""Assemble the fume extractor (printed parts + bought-part stand-ins) and report every overlapping pair.

    python3 hardware/parts/fume/collide.py     # about 1 min. An overlap 0 mm deep is two faces touching (by design).
"""
import itertools, math, sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import fume as F
from build123d import Box, Cone, Cylinder, Pos, Rot, extrude, Polygon as BPoly
from window_inserts import slab
from shapely.geometry import box as sbox, Point

Z1, Z2, Z3 = 0.0, F.T6, F.T6 + F.T5               # face, filter, base front faces
parts = {}
parts["face"] = Pos(0, 0, Z1) * F.p1_face()
parts["filter"] = Pos(0, 0, Z2) * F.p2_filter()
parts["base"] = Pos(0, 0, Z3) * F.p3_body()
# fan: 80 x 80 x 25 frame, Ø76 bore, Ø4.3 corner holes; back face on the tab tops
fan_sec = sbox(-40, F.CY - 40, 40, F.CY + 40).difference(Point(0, F.CY).buffer(38))
for x, y in F.FAN_SCREWS: fan_sec = fan_sec.difference(Point(x, y).buffer(2.15))
parts["fan"] = slab(fan_sec, Z3 + F.FT - 25.0, Z3 + F.FT)
# pads: 9 mm, octagon 80 / 16 clip; front against the filter's rib grid, rear on the base's grille plate (+1 plate)
pad = F.pad_poly(80, 16); pad = __import__("shapely").affinity.translate(pad, 0, F.CY)
parts["pad_front"] = slab(pad, Z2 + F.LIP_H + F.PAD_T - 9.0, Z2 + F.LIP_H + F.PAD_T)
parts["pad_rear"] = slab(pad, Z3 + F.FT, Z3 + F.FT + 9.0)
# screws: M3 x 50 CSK, head flush in the filter's front face; shank Ø2.9 (clears a 3.0 insert thread)
for i, (x, y) in enumerate(F.SCREWS):
    head = Pos(x, y, Z2 + 0.85) * Cone(2.95, 1.45, 1.7)
    shank = Pos(x, y, Z2 + 25) * Cylinder(1.45, 50)
    parts[f"screw{i+1}"] = head + shank
# M3 inserts (4 long, OD = bore, ID 3.0): 4 on the corner tab tops, 2 in the chin tabs' front face
for i, (x, y) in enumerate(F.FAN_SCREWS):
    parts[f"insert_fan{i+1}"] = Pos(x, y, Z3 + F.FT + 2) * (Cylinder(F.INSERT_BORE / 2, 4) - Cylinder(1.5, 5))
for i, (x, y) in enumerate(F.CHIN_SCREWS):
    parts[f"insert_chin{i+1}"] = Pos(x, y, Z3 + 2) * (Cylinder(F.INSERT_BORE / 2, 4) - Cylinder(1.5, 5))
# magnets Ø6 x 1.5: face back and filter front
for i, (x, y) in enumerate(F.MAGNET_XY):
    parts[f"mag_face{i+1}"] = Pos(x, y, Z2 - 0.75) * Cylinder(3.0, 1.5)
    parts[f"mag_filt{i+1}"] = Pos(x, y, Z2 + 0.75) * Cylinder(3.0, 1.5)
# jack (Ø12 x 14) and switch (12.7 x 7.9 x 15) behind the back panel, in the chin
zb = Z3 + F.FT + F.PAD_T                            # inner face of the back panel
parts["jack"] = Pos(*F.JACK_XY, zb - 7) * Cylinder(5.9, 14)
parts["switch"] = Pos(*F.SWITCH_XY, zb - 7.5) * Box(12.7, 7.9, 15)
# handle inserts (M3, 4 long) and M5 side inserts (Ø6.4 x 8)
hx = F.HANDLE_PITCH / 2
for sx in (-1, 1):
    parts[f"insert_top{'LR'[sx>0]}"] = Pos(sx * hx, F.H - 2, Z3 + F.FT / 2) * (Rot(90, 0, 0) * (Cylinder(F.TOP_INSERT_BORE / 2, 4) - Cylinder(1.5, 5)))
    parts[f"standoff{'LR'[sx>0]}"] = Pos(sx * hx, F.H + 2.5, Z3 + F.FT / 2) * (Rot(90, 0, 0) * Cylinder(2.75, 5))
    for k, z in enumerate(F.MOUNT_ZS):
        parts[f"m5_{'LR'[sx>0]}{k+1}"] = Pos(sx * (F.W / 2 - 4), F.MOUNT_Y, Z3 + z) * (Rot(0, 90, 0) * (Cylinder(F.MOUNT_BORE / 2, 8) - Cylinder(2.5, 9)))

names = list(parts)
bb = {n: parts[n].bounding_box() for n in names}
def boxes_meet(a, b):
    A, B = bb[a], bb[b]
    return all(tuple(A.min)[k] < tuple(B.max)[k] and tuple(B.min)[k] < tuple(A.max)[k] for k in range(3))
hits, n_pairs = [], 0
for a, b in itertools.combinations(names, 2):
    if not boxes_meet(a, b): continue
    n_pairs += 1
    v = (parts[a] & parts[b]).volume
    if v > 0.05: hits.append((a, b, v))
print(f"{len(names)} parts, {n_pairs} pairs close enough to test")
for a, b, v in sorted(hits, key=lambda h: -h[2]): print(f"OVERLAP {a} x {b}: {v:.2f} mm3")
if not hits: print("no overlaps")
# outline check: nothing pokes outside the outline (except the standoffs, above the top)
from build123d import Box as B
env = slab(F.OUTLINE, -0.01, Z3 + F.T3 + 0.01)
for n in names:
    if n.startswith("standoff"): continue
    out = (parts[n] - env).volume
    if out > 0.05: print(f"OUTSIDE {n}: {out:.2f} mm3")
for a, b, v in hits:
    if v < 0.5 and a == "base" and b.startswith("m5"): continue
    ov = parts[a] & parts[b]
    for s in (ov.solids() if hasattr(ov, "solids") else [ov]):
        if s.volume > 0.01:
            bb_ = s.bounding_box()
            print(f"  {a} x {b}: {s.volume:.2f} mm3  x {bb_.min.X:.1f}..{bb_.max.X:.1f}  y {bb_.min.Y:.1f}..{bb_.max.Y:.1f}  z {bb_.min.Z:.1f}..{bb_.max.Z:.1f}")
