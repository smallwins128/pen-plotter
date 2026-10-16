"""DIN-rail adapter plates for the control box: a flat printed plate between a bought DIN clip and the part.

Stack (bottom up): 35 mm rail on the base plate grid -> bought DIN clip (25 x 69, 2 x Ø3.4 holes 58.5 apart,
countersunk on the rail side) -> printed adapter plate -> part. Flat-head M3 screws go up from the clip's rail side
into M3 nuts sunk in the top of the plate, so clip + plate are screwed together before the part goes on.

    python3 hardware/parts/din_mounts.py     # writes hardware/out/din_mounts/*.stl + preview PNG

Plate frame: x along the rail, y across the rail (box z, + = front), z up from the clip's top face.
Parts:
  tb6600_plate  one per driver. Driver lies flat (96 x 57 x 28); a wall on its left takes the flange: M3 through the
                flange's open U-slots into nuts that slide in a vertical channel (8-20 up), so label up or down fits.
  board_plate   FluidNC 6x (holes 78 along x, 118 along y). Two clips. Float holes (Ø6 in Ø9 bosses) give about
                ±1.3 mm for the measured hole pattern; M3 + washer + nut from below.
"""
import math
import pathlib
import sys

from build123d import Box, Cylinder, Pos, export_stl
from shapely.geometry import Point, Polygon, box as sbox

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fit_kit import FIT  # noqa: E402
from window_inserts import rounded, slab  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent.parent / "out" / "din_mounts"

CLIP = dict(w=25.0, l=69.0, pitch=58.5)        # bought clip: width along the rail, length across it, hole pitch
NUT_AF, NUT_H = 5.8, 2.6                       # M3 nut pocket (5.5 AF + play), depth
M3 = FIT["m3_clear"]

TB = dict(l=96.0, w=57.0, h=28.0, hole_pitch=87.0)   # TB6600 body; flange holes 87 apart along its length
TB_BASE_T, TB_WALL_T, TB_SLOT = 4.0, 5.0, (8.0, 20.0)   # slot from 8 to 20 above the base top

BOARD = dict(pcb=(87.0, 126.0), holes=(78.0, 118.0))    # FluidNC 6x, holes measured (best effort)
BOARD_T, BOSS_D, BOSS_H, FLOAT_D = 4.0, 9.0, 6.0, 6.0
BOARD_CLIP_X = 30.0                                     # clip centres at x = ±30 under the board
BOARD_CLIP_DY = 10.0                                    # board centre sits 10 behind the rail centre


def hexagon(x, y, af):
    r = af / math.sqrt(3)
    return Polygon([(x + r * math.cos(math.radians(60 * i)), y + r * math.sin(math.radians(60 * i))) for i in range(6)])


def clip_holes(part, cx, cy, top):
    """Ø3.4 through + M3 nut pocket from the top for one clip centred at (cx, cy)."""
    for s in (-1, 1):
        y = cy + s * CLIP["pitch"] / 2
        part -= Pos(cx, y, top / 2) * Cylinder(M3 / 2, top + 2)
        part -= slab(hexagon(cx, y, NUT_AF), top - NUT_H, top + 1)
    return part


def tb6600_plate():
    L, W = TB["l"] + 4, TB["w"] + 3
    x0 = -TB_WALL_T                                   # wall outer face; driver body starts at x = 0
    cx = TB["w"] / 2                                  # clip under the driver's middle
    base = rounded(sbox(x0, -L / 2, W, L / 2), 3).difference(rounded(sbox(6, -20, W - 6, 20), 4))
    part = slab(base, 0, TB_BASE_T)
    top = TB_BASE_T + TB["h"]
    part += slab(sbox(x0, -L / 2, 0, L / 2), TB_BASE_T - 0.01, TB_BASE_T + TB_SLOT[0])        # low web
    for s in (-1, 1):                                                                          # posts at the slots
        y = s * TB["hole_pitch"] / 2
        part += slab(rounded(sbox(x0, y - 8, 0, y + 8), 1.5).intersection(sbox(x0, -L / 2, 0, L / 2)), TB_BASE_T - 0.01, top)
    part = clip_holes(part, cx, 0.0, TB_BASE_T)
    z0, z1 = TB_BASE_T + TB_SLOT[0], TB_BASE_T + TB_SLOT[1]
    for s in (-1, 1):
        y = s * TB["hole_pitch"] / 2
        part -= Pos(x0 / 2, y, (z0 + z1) / 2) * Box(TB_WALL_T + 2, M3, z1 - z0)
        # nut channel on the post's outer face, open at the top so the nut drops in
        zb = z0 - 3
        part -= Pos(x0 + NUT_H / 2 - 0.5, y, (zb + top + 1) / 2) * Box(NUT_H + 1, NUT_AF, top + 1 - zb)
    return part


def board_plate():
    hx, hy = BOARD["holes"][0] / 2, BOARD["holes"][1] / 2
    pw, pl = BOARD["pcb"][0] + 5, BOARD["pcb"][1] + 6
    bars = [sbox(sx * 17, -pl / 2, sx * 45, pl / 2) for sx in (-1, 1)]                 # under the clips + bosses
    ties = [sbox(-pw / 2 + 4, y - 5, pw / 2 - 4, y + 5) for y in (-hy, BOARD_CLIP_DY, hy)]
    from shapely.ops import unary_union
    part = slab(rounded(unary_union(bars + ties), 2).buffer(0), 0, BOARD_T)
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * hx, sy * hy
            part += Pos(x, y, BOARD_T + BOSS_H / 2 - 0.01) * Cylinder(BOSS_D / 2, BOSS_H)
            part -= Pos(x, y, (BOARD_T + BOSS_H) / 2) * Cylinder(FLOAT_D / 2, BOARD_T + BOSS_H + 2)
    for sx in (-1, 1):
        part = clip_holes(part, sx * BOARD_CLIP_X, BOARD_CLIP_DY, BOARD_T)
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


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tb, bd = tb6600_plate(), board_plate()
    export_stl(tb, str(OUT / "tb6600_plate.stl"))
    export_stl(bd, str(OUT / "board_plate.stl"))
    for n, p in (("tb6600_plate", tb), ("board_plate", bd)):
        bb = p.bounding_box()
        print(f"{n}: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm, {p.volume / 1000:.1f} cm3")
    preview([("tb6600_plate", tb, [(TB["w"] / 2, 0)]),
             ("board_plate", bd, [(-BOARD_CLIP_X, BOARD_CLIP_DY), (BOARD_CLIP_X, BOARD_CLIP_DY)])],
            OUT / "preview.png")


if __name__ == "__main__":
    main()
