"""DIN-rail adapter plates for the control box: a flat printed plate between a bought DIN clip and the part.

Stack (bottom up): 35 mm rail on the base plate grid -> bought DIN clip (25 x 69, 2 x Ø3.4 holes 58.5 apart,
countersunk on the rail side) -> printed adapter plate -> part. Flat-head M3 screws go up from the clip's rail side
into M3 heat-set inserts pressed into raised pads from the plate's underside (8 tall, insert 4 deep), so clip and
plate screw together before the part goes on, and come apart again without touching the part.

    python3 hardware/parts/din_mounts.py     # writes hardware/out/din_mounts/*.stl + preview PNG

Plate frame: x along the rail, y across the rail (box z, + = front), z up from the clip's top face.
Parts:
  tb6600_plate  one per driver. Driver lies flat (96 x 57 x 28) on two ribs over the insert pads; a wall on its left takes the flange: M3 through the
                flange's open U-slots into nuts that slide in a vertical channel (8-20 up), so label up or down fits.
  board_plate   FluidNC 6x (holes 78 along x, 118 along y). Two clips. Float holes (Ø6 in Ø9 bosses) give about
                ±1.3 mm for the measured hole pattern; M3 + washer + nut from below.
"""
import math
import pathlib
import sys

from build123d import Box, Cylinder, Pos, export_stl
from shapely.geometry import LineString, Point, Polygon, box as sbox
from shapely.ops import unary_union

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fit_kit import FIT  # noqa: E402
from window_inserts import rounded, slab  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent.parent / "out" / "din_mounts"

CLIP = dict(w=25.0, l=69.0, pitch=58.5)        # bought clip: width along the rail, length across it, hole pitch
NUT_AF, NUT_H = 5.8, 2.6                       # M3 nut pocket (5.5 AF + play), depth
M3 = FIT["m3_clear"]
# clip screws: M3 heat-set insert pressed in from the plate's underside (the clip face), in a raised pad
INS_BORE, INS_DEPTH = 4.0, 4.5                 # Allwin's inserts: M3 x 4, OD 4.3 (brass, knurled); bore 0.3 under OD
PAD_D, PAD_H = 10.0, 8.0                       # pad diameter, height above the clip face (2.5 solid over the bore)

TB = dict(l=96.0, w=57.0, h=28.0, hole_pitch=87.0)   # TB6600 body; flange holes 87 apart along its length
TB_BASE_T, TB_WALL_T, TB_SLOT = 3.0, 5.0, (8.0, 20.0)   # slot from 8 to 20 above the seat
TB_SEAT = PAD_H                                         # driver sits on two ribs that carry the insert pads

BOARD = dict(pcb=(87.0, 126.0), holes=(78.0, 118.0))    # FluidNC 6x, holes measured (best effort)
BOARD_T, BOSS_D, BOSS_H, FLOAT_D = 4.0, 9.0, 8.0, 6.0   # PCB sits 12 up: 4 over the insert pads
BOARD_CLIP_X = 30.0                                     # clip centres at x = ±30 under the board
BOARD_CLIP_DY = 10.0                                    # board centre sits 10 behind the rail centre


def hexagon(x, y, af):
    r = af / math.sqrt(3)
    return Polygon([(x + r * math.cos(math.radians(60 * i)), y + r * math.sin(math.radians(60 * i))) for i in range(6)])


def strut(p0, p1, bend=0.0, w=6.0, n=24):
    """A curved strut (quadratic Bézier) from p0 to p1, bowed sideways by `bend` mm, w wide."""
    (x0, y0), (x1, y1) = p0, p1
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    L = math.hypot(x1 - x0, y1 - y0) or 1.0
    cx, cy = mx - (y1 - y0) / L * bend, my + (x1 - x0) / L * bend
    pts = [((1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1, (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1)
           for t in (i / n for i in range(n + 1))]
    return LineString(pts).buffer(w / 2, quad_segs=8)


def organic(shapes, fillet=5.0):
    """Union, then close by `fillet` so every joint flows into a smooth web."""
    u = unary_union(shapes)
    return u.buffer(fillet, quad_segs=12).buffer(-fillet, quad_segs=12).buffer(0)


def clip_holes(part, cx, cy):
    """One clip centred at (cx, cy): a raised pad per screw with a heat-set insert bore from the underside."""
    for sgn in (-1, 1):
        y = cy + sgn * CLIP["pitch"] / 2
        part += Pos(cx, y, PAD_H / 2) * Cylinder(PAD_D / 2, PAD_H)
        part -= Pos(cx, y, INS_DEPTH / 2 - 0.5) * Cylinder(INS_BORE / 2, INS_DEPTH + 1)
        part -= Pos(cx, y, PAD_H / 2) * Cylinder(M3 / 2, PAD_H + 2)      # a longer screw runs on through
    return part


def tb6600_plate():
    L, W = TB["l"] + 4, TB["w"] + 3
    x0 = -TB_WALL_T                                   # wall outer face; driver body starts at x = 0
    cx = TB["w"] / 2                                  # clip under the driver's middle
    py = CLIP["pitch"] / 2
    posts = [(x0 / 2, sgn * TB["hole_pitch"] / 2) for sgn in (-1, 1)]
    pads = [(cx, sgn * py) for sgn in (-1, 1)]
    frame = [sbox(x0, -L / 2 + 2, 0, L / 2 - 2)]                                    # spine under the wall
    frame += [sbox(0, y - PAD_D / 2, W, y + PAD_D / 2) for _, y in pads]           # seat ribs
    for (px, py_), (qx, qy) in zip(posts, pads):                                    # post -> pad
        frame.append(strut((px, py_), (qx, qy), bend=-6 * (1 if py_ > 0 else -1), w=7))
    frame.append(strut((0, 0), (W - 4, -py), bend=8, w=6))                          # diagonals across the window
    frame.append(strut((0, 0), (W - 4, py), bend=-8, w=6))
    frame.append(strut((W - 4, -py), (W - 4, py), bend=-5, w=6))                    # outer edge, bowed in
    base = organic(frame, 4.0).intersection(rounded(sbox(x0, -L / 2, W, L / 2), 3))
    part = slab(base, 0, TB_BASE_T)
    for sgn in (-1, 1):                                                                        # seat ribs over the pads
        y = sgn * CLIP["pitch"] / 2
        part += slab(sbox(0, y - PAD_D / 2, W, y + PAD_D / 2), TB_BASE_T - 0.01, TB_SEAT)
    top = TB_SEAT + TB["h"]
    part += slab(sbox(x0, -L / 2, 0, L / 2), TB_BASE_T - 0.01, TB_SEAT + TB_SLOT[0])         # low web
    for sgn in (-1, 1):                                                                        # posts at the slots
        y = sgn * TB["hole_pitch"] / 2
        part += slab(rounded(sbox(x0, y - 8, 0, y + 8), 1.5).intersection(sbox(x0, -L / 2, 0, L / 2)), TB_BASE_T - 0.01, top)
    part = clip_holes(part, cx, 0.0)
    z0, z1 = TB_SEAT + TB_SLOT[0], TB_SEAT + TB_SLOT[1]
    for sgn in (-1, 1):
        y = sgn * TB["hole_pitch"] / 2
        part -= Pos(x0 / 2, y, (z0 + z1) / 2) * Box(TB_WALL_T + 2, M3, z1 - z0)
        # nut channel on the post's outer face, open at the top so the nut drops in
        zb = z0 - 3
        part -= Pos(x0 + NUT_H / 2 - 0.5, y, (zb + top + 1) / 2) * Box(NUT_H + 1, NUT_AF, top + 1 - zb)
    return part


def board_plate():
    hx, hy = BOARD["holes"][0] / 2, BOARD["holes"][1] / 2
    pw, pl = BOARD["pcb"][0] + 5, BOARD["pcb"][1] + 6
    cy = BOARD_CLIP_DY
    bosses = [(sx * hx, sy * hy) for sx in (-1, 1) for sy in (-1, 1)]
    pads = [(sx * BOARD_CLIP_X, cy + sy * CLIP["pitch"] / 2) for sx in (-1, 1) for sy in (-1, 1)]
    frame = [Point(p).buffer(BOSS_D / 2 + 1.5) for p in bosses] + [Point(p).buffer(PAD_D / 2 + 1.5) for p in pads]
    for sx in (-1, 1):
        frame.append(strut((sx * BOARD_CLIP_X, cy - CLIP["pitch"] / 2), (sx * BOARD_CLIP_X, cy + CLIP["pitch"] / 2), bend=sx * 6, w=8))   # along each clip
        frame.append(strut((sx * hx, -hy), (sx * BOARD_CLIP_X, cy - CLIP["pitch"] / 2), bend=sx * 3, w=7))                        # boss -> pad
        frame.append(strut((sx * hx, hy), (sx * BOARD_CLIP_X, cy + CLIP["pitch"] / 2), bend=-sx * 3, w=7))
    for sy in (-1, 1):
        frame.append(strut((-hx, sy * hy), (hx, sy * hy), bend=-sy * 10, w=6))                                             # end ties, bowed in
    frame.append(strut((-BOARD_CLIP_X, cy - CLIP["pitch"] / 2), (BOARD_CLIP_X, cy + CLIP["pitch"] / 2), bend=10, w=6))     # one sweeping brace
    frame.append(strut((-BOARD_CLIP_X, cy + CLIP["pitch"] / 2), (BOARD_CLIP_X, cy - CLIP["pitch"] / 2), bend=10, w=6))
    part = slab(organic(frame, 5.0), 0, BOARD_T)
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * hx, sy * hy
            part += Pos(x, y, BOARD_T + BOSS_H / 2 - 0.01) * Cylinder(BOSS_D / 2, BOSS_H)
            part -= Pos(x, y, (BOARD_T + BOSS_H) / 2) * Cylinder(FLOAT_D / 2, BOARD_T + BOSS_H + 2)
    for sx in (-1, 1):
        part = clip_holes(part, sx * BOARD_CLIP_X, BOARD_CLIP_DY)
    return part


def preview(parts, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import trimesh
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig = plt.figure(figsize=(12, 6), dpi=130)
    for i, (name, part, clips) in enumerate(parts):
        ax = fig.add_subplot(1, len(parts), i + 1, projection="3d")
        tmp = OUT / f"{name}.stl"
        m = trimesh.load(tmp)
        light = (m.face_normals @ [0.3, -0.5, 0.8] + 1.2) / 2.2
        col = [(0.12 * l + 0.05, 0.13 * l + 0.05, 0.15 * l + 0.06) for l in light]
        pc = Poly3DCollection(m.triangles, facecolors=[(0.25 + 0.6 * l * 0.6,) * 3 for l in light], linewidths=0)
        ax.add_collection3d(pc)
        for cx, cy in clips:   # bought clip, ghosted under the plate
            b = trimesh.creation.box((CLIP["w"], CLIP["l"], 10), transform=trimesh.transformations.translation_matrix((cx, cy, -5)))
            ax.add_collection3d(Poly3DCollection(b.triangles, facecolors=(0.47, 0.75, 0.94, 0.35), linewidths=0))
        lo, hi = m.bounds
        c = (lo + hi) / 2
        r = (hi - lo).max() / 2 + 5
        ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(c[2] - r, c[2] + r)
        ax.set_box_aspect((1, 1, 1)); ax.view_init(28, -125); ax.set_axis_off(); ax.set_title(name)
    fig.tight_layout()
    fig.savefig(path)


def dxf(name, levels, side=None):
    """1:1 DXF from the STL: plan sections at each height (one layer each), plus an optional side section."""
    import ezdxf
    import trimesh
    m = trimesh.load(OUT / f"{name}.stl")
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    msp = doc.modelspace()
    colours = [7, 1, 5, 3]
    lo, hi = m.bounds

    def put(section, layer, dx=0.0, dy=0.0, axes=(0, 1)):
        for ent in section.discrete:
            pts = [(float(p[axes[0]]) + dx, float(p[axes[1]]) + dy) for p in ent]
            msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": layer})

    for i, (z, label) in enumerate(levels):
        layer = f"Z{z:g} {label}".replace(".", "_")
        doc.layers.add(layer, color=colours[i % len(colours)])
        put(m.section(plane_origin=(0, 0, z), plane_normal=(0, 0, 1)), layer)
    if side:
        x, label = side
        layer = f"SIDE x{x:g} {label}".replace(".", "_")
        doc.layers.add(layer, color=6)
        put(m.section(plane_origin=(x, 0, 0), plane_normal=(1, 0, 0)), layer, dx=hi[0] + 20 - lo[1], dy=lo[1], axes=(1, 2))   # side view right of the plan
    doc.layers.add("TEXT", color=8)
    msp.add_text(f"{name}  1:1 mm  (plan sections by height; layers named by Z)", height=3,
                 dxfattribs={"layer": "TEXT"}).set_placement((lo[0], lo[1] - 8))
    doc.saveas(OUT / f"{name}.dxf")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tb, bd = tb6600_plate(), board_plate()
    export_stl(tb, str(OUT / "tb6600_plate.stl"))
    export_stl(bd, str(OUT / "board_plate.stl"))
    for n, p in (("tb6600_plate", tb), ("board_plate", bd)):
        bb = p.bounding_box()
        print(f"{n}: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm, {p.volume / 1000:.1f} cm3")
    dxf("tb6600_plate", [(1.5, "base frame"), (6.0, "seat ribs and insert bores"), (20.0, "flange posts")],
        side=(-2.5, "post face, slots and nut channel"))
    dxf("board_plate", [(2.0, "frame and insert bores"), (10.0, "bosses (float holes)")])
    preview([("tb6600_plate", tb, [(TB["w"] / 2, 0)]),
             ("board_plate", bd, [(-BOARD_CLIP_X, BOARD_CLIP_DY), (BOARD_CLIP_X, BOARD_CLIP_DY)])],
            OUT / "preview.png")


if __name__ == "__main__":
    main()
