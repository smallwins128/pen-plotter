"""R05 Harbor: SKÅDIS rail system, hooks plus plates (2026-10-30).

Allwin's idea: one hook type on the board, and every holder is a plate that drops onto the hooks. The hook pushes
into a SKÅDIS slot and drops; on its front it carries a dovetail RAIL (the wedge). Each plate has a SLEEVE boss per
hook on its back: a dovetail groove open at the bottom and closed at the top, so the plate slides down over the
rails and sits on its roof. Plates are generic (no tool-shaped pockets), so they can be swapped and re-used.

Grid rule: hooks go in one row of slots, so sleeves sit on a 40 mm pitch. A plate is 40 n - 4 wide (4 mm gap to its
neighbour). One sleeve is enough for a small plate (the 26 mm rail stops it turning); use two for anything wider.

SKÅDIS numbers are community measurements, not IKEA's: board 5 thick, slots 5 x 15 (measured up to 5.2 wide),
40 mm apart in a row, rows staggered 20 mm. Print the fit test (one strip, three hooks) before any real plate:
the groove clearance that slides on without rattling becomes CLR.

    python3 skadis_rail.py       # writes out/harbor/skadis_hook*.stl, skadis_fit_strip*.stl, .step, preview PNG

Frame: x along the board (slot centre x = 0), y out of the board (board front y = 0), z up (hook bottom z = 0).
Print: everything upright as modelled. Hook: lip and flange stand on the bed, the neck bridges 5.4 mm. Plates: stand
on their bottom edge; sleeves run from the bed, so the dovetail flanks are vertical walls and the roof a short bridge.
The fit strip prints the same way as the real plates, so the clearance it picks holds for them.
"""
import pathlib

from build123d import BuildPart, BuildSketch, Locations, Plane, Polygon, Text, export_step, export_stl, extrude

OUT = pathlib.Path(__file__).resolve().parents[2] / "out" / "harbor"

BOARD = dict(t=5.0, slot_w=5.0, slot_h=15.0, pitch=40.0)
NECK = dict(w=4.4, h=7.0, z=6.0, len=BOARD["t"] + 0.4)   # through the slot; drops 7 to sit on the slot's floor
LIP = dict(t=3.0, h=13.0, chamfer=1.5)                   # behind the board; 13 < 15 so it passes, then hangs 6 below
FLANGE = dict(w=16.0, t=2.0, h=28.0)                     # rests on the board's front
RAIL = dict(root=7.0, front=11.0, d=2.5, lead=1.0)       # dovetail, 34 deg flanks; lead-in chamfer on top
CLR = 0.25                                               # per side, groove over rail; the fit strip tests 0.15-0.35
BOSS = dict(w=22.0, wall=1.6, roof=2.5)                  # sleeve boss around each groove
PLATE_T = 2.4                                            # plate body
GAP = 4.0                                                # between neighbouring plates

Y_RAIL = FLANGE["t"]                                     # rail root = flange front = sleeve bosses' back face
Y_BODY = Y_RAIL + RAIL["d"] + 0.35 + BOSS["wall"]        # plate body's back face (deepest groove + wall)


def prism_xy(pts, z0, z1):
    """Outline in (x, y), extruded along z."""
    with BuildPart() as p:
        with BuildSketch(Plane.XY.offset(z0)):
            Polygon(*pts, align=None)
        extrude(amount=z1 - z0)
    return p.part


def prism_yz(pts, x0, x1):
    """Outline in (y, z), extruded along x."""
    with BuildPart() as p:
        with BuildSketch(Plane.YZ.offset(x0)):
            Polygon(*pts, align=None)
        extrude(amount=x1 - x0)
    return p.part


def box(x0, x1, y0, y1, z0, z1):
    return prism_xy([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1)


def dovetail(root, front, y0, d):
    """Trapezoid in (x, y): `root` wide at y0, `front` wide at y0 + d."""
    return [(-root / 2, y0), (root / 2, y0), (front / 2, y0 + d), (-front / 2, y0 + d)]


def hook():
    yb, c, w = -NECK["len"], LIP["chamfer"], NECK["w"] / 2
    lip = [(yb - LIP["t"], 0), (yb, 0), (yb, LIP["h"]), (yb - LIP["t"] + c, LIP["h"]), (yb - LIP["t"], LIP["h"] - c)]
    part = prism_yz(lip, -w, w)
    part += box(-w, w, yb - 0.1, 0.1, NECK["z"], NECK["z"] + NECK["h"])
    part += box(-FLANGE["w"] / 2, FLANGE["w"] / 2, 0, FLANGE["t"], 0, FLANGE["h"])
    part += prism_xy(dovetail(RAIL["root"], RAIL["front"], Y_RAIL - 0.1, RAIL["d"] + 0.1), 0, FLANGE["h"])
    ytop, l = Y_RAIL + RAIL["d"], RAIL["lead"]                                          # lead-in on the rail's top
    part -= prism_yz([(ytop - l, FLANGE["h"] + 0.01), (ytop + 0.1, FLANGE["h"] + 0.01), (ytop + 0.1, FLANGE["h"] - l - 0.1)],
                     -FLANGE["w"], FLANGE["w"])
    return part


def groove(x, clr, z_top, z_bot):
    """The dovetail groove a sleeve wraps: roof at z_top + clr (the rail's top), open below z_bot, flared mouth."""
    zr = z_top + clr
    g = prism_xy([(px + x, py) for px, py in dovetail(RAIL["root"] + 2 * clr, RAIL["front"] + 2 * clr, Y_RAIL - 0.1,
                                                      RAIL["d"] + clr + 0.1)], z_bot - 1, zr)
    g += prism_xy([(px + x, py) for px, py in dovetail(RAIL["front"] + 2 * clr + 2, RAIL["front"] + 2 * clr,
                                                       Y_RAIL - 0.1, 1.0)], z_bot - 1, z_bot + 1.0)
    return g


def sleeve(x, clr, z_top, z_bot):
    """Boss around a groove, from the plate's bottom edge (z_bot) to just over the roof. Reaching the bed means it
    prints upright with no overhang."""
    return box(x - BOSS["w"] / 2, x + BOSS["w"] / 2, Y_RAIL, Y_BODY + 0.1, z_bot, z_top + clr + BOSS["roof"])


def plate(sleeves, w, z0, z1, clr=CLR):
    """Plate body (back face at Y_BODY) from z0 to z1, centred on x = 0, with sleeves at x (a list of x, or of
    (x, clr) pairs) and a foot that reaches back to the board along the bottom, so a tall plate can't flex in.
    The foot is notched at each sleeve so the hook's flange passes through it as the plate slides down."""
    sleeves = [s if isinstance(s, tuple) else (s, clr) for s in sleeves]
    part = box(-w / 2, w / 2, Y_BODY, Y_BODY + PLATE_T, z0, z1)
    part += box(-w / 2, w / 2, 0.0, Y_BODY + 0.1, z0, z0 + 4.0)
    for x, c in sleeves:
        part -= box(x - FLANGE["w"] / 2 - 1, x + FLANGE["w"] / 2 + 1, -1, Y_RAIL + 0.3, z0 - 1, z1 + 1)
        part += sleeve(x, c, FLANGE["h"], z0)
        part -= groove(x, c, FLANGE["h"], z0)
    return part


def sleeve_xs(w):
    """Sleeve positions for a plate w wide: one per 40 mm, centred."""
    n = round((w + GAP) / 40)
    return [40.0 * (i - (n - 1) / 2) for i in range(n)]


def fit_strip():
    """Three sleeves at 0.15 / 0.25 / 0.35 clearance on a 40 mm pitch, each labelled on the front."""
    sl = [(-40.0, 0.15), (0.0, 0.25), (40.0, 0.35)]
    part = plate(sl, 3 * 40 - GAP, -12.0, FLANGE["h"] + 0.35 + BOSS["roof"])
    for x, clr in sl:
        with BuildPart() as t:
            with BuildSketch(Plane(origin=(0, Y_BODY + PLATE_T, 0), x_dir=(-1, 0, 0), z_dir=(0, 1, 0))):
                with Locations((-x, 8.0)):
                    Text(f"{clr:.2f}".lstrip("0"), font_size=4.0)
            extrude(amount=-0.6)
        part -= t.part
    return part


def board_piece(x0=-70, x1=70, z0=-30, z1=60):
    """A piece of SKÅDIS for the 3D inspector (not printed). Hook slots (columns at multiples of 40) have their floor
    at the neck, z = NECK z; the columns between are staggered 20 mm."""
    b = box(x0, x1, -BOARD["t"], 0, z0, z1)
    for cx in range(int(x0 // 20) * 20 + 20, int(x1), 20):
        zc0 = NECK["z"] + BOARD["slot_h"] / 2 - (0 if (cx // 20) % 2 == 0 else 20)
        for zc in (zc0 + 40 * k for k in range(-10, 11)):
            if z0 + 8 < zc < z1 - 8:
                b -= box(cx - BOARD["slot_w"] / 2, cx + BOARD["slot_w"] / 2, -BOARD["t"] - 1, 1,
                         zc - BOARD["slot_h"] / 2, zc + BOARD["slot_h"] / 2)
    return b


def main():
    import numpy as np, trimesh
    from trimesh.transformations import rotation_matrix
    OUT.mkdir(parents=True, exist_ok=True)
    for name, part, rot in (("skadis_hook", hook(), None), ("skadis_fit_strip", fit_strip(), None)):
        bb = part.bounding_box()
        print(f"{name}: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm, volume {part.volume / 1000:.2f} cm3")
        export_stl(part, str(OUT / f"{name}.stl"))
        export_step(part, str(OUT / f"{name}.step"))
        m = trimesh.load(str(OUT / f"{name}.stl"))
        if rot is not None:
            m.apply_transform(rotation_matrix(np.radians(rot), [1, 0, 0]))
        m.apply_translation(-m.bounds[0])
        m.export(str(OUT / f"{name}_print.stl"))
    export_stl(board_piece(), str(OUT / "skadis_board_piece.stl"))


if __name__ == "__main__":
    main()
