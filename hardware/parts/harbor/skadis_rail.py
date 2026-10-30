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
Print: hook upright as modelled (lip and flange stand on the bed, the neck bridges 5.4 mm). Plate front face down,
sleeves up; the grooves' dovetail flanks overhang 34 deg, so no supports.
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


def sleeve(x, clr, z_top):
    """Boss with a dovetail groove: open at the bottom, roof at z_top + clr (the rail's top)."""
    zr = z_top + clr
    b = box(x - BOSS["w"] / 2, x + BOSS["w"] / 2, Y_RAIL, Y_BODY + 0.1, zr - FLANGE["h"] - 2, zr + BOSS["roof"])
    groove = [(px + x, py) for px, py in dovetail(RAIL["root"] + 2 * clr, RAIL["front"] + 2 * clr, Y_RAIL - 0.1,
                                                  RAIL["d"] + clr + 0.1)]
    b -= prism_xy(groove, zr - FLANGE["h"] - 3, zr)
    lead = [(px + x, py) for px, py in dovetail(RAIL["front"] + 2 * clr + 2, RAIL["front"] + 2 * clr, Y_RAIL - 0.1, 1.0)]
    b -= prism_xy(lead, zr - FLANGE["h"] - 3, zr - FLANGE["h"] - 2 + 1.0)                 # flared mouth
    return b


def plate(sleeves, w, z0, z1):
    """Plate body (back face at Y_BODY) from z0 to z1, centred on x = 0, with sleeves [(x, clr)] and a foot that
    reaches back to the board at the bottom so the plate can't tip in."""
    part = box(-w / 2, w / 2, Y_BODY, Y_BODY + PLATE_T, z0, z1)
    part += box(-w / 2, w / 2, 0.0, Y_BODY + 0.1, z0, z0 + 4.0)
    for x, clr in sleeves:
        part += sleeve(x, clr, FLANGE["h"])
    return part


def fit_strip():
    """Three sleeves at 0.15 / 0.25 / 0.35 clearance on a 40 mm pitch, labelled on the back."""
    sl = [(-40.0, 0.15), (0.0, 0.25), (40.0, 0.35)]
    part = plate(sl, 3 * 40 - GAP, -12.0, FLANGE["h"] + 0.35 + BOSS["roof"])
    for x, clr in sl:
        with BuildPart() as t:
            with BuildSketch(Plane.XZ.offset(-Y_BODY)):
                with Locations((x, -5.0)):
                    Text(f"{clr:.2f}".lstrip("0"), font_size=4.0)
            extrude(amount=-0.6)
        part -= t.part
    return part


def board_piece():
    """A 140 x 90 piece of SKÅDIS around the three test hooks, for the 3D inspector (not printed)."""
    b = box(-70, 70, -BOARD["t"], 0, -30, 60)
    for cx in range(-60, 61, 20):
        zc0 = NECK["z"] + BOARD["slot_h"] / 2 - (0 if (cx // 20) % 2 == 0 else 20)   # hook slots: floor at the neck
        for zc in (zc0 + 40 * k for k in range(-2, 3)):
            if -22 < zc < 52:
                b -= box(cx - BOARD["slot_w"] / 2, cx + BOARD["slot_w"] / 2, -BOARD["t"] - 1, 1,
                         zc - BOARD["slot_h"] / 2, zc + BOARD["slot_h"] / 2)
    return b


def main():
    import numpy as np, trimesh
    from trimesh.transformations import rotation_matrix
    OUT.mkdir(parents=True, exist_ok=True)
    for name, part, rot in (("skadis_hook", hook(), None), ("skadis_fit_strip", fit_strip(), -90)):
        bb = part.bounding_box()
        print(f"{name}: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm, volume {part.volume / 1000:.2f} cm3")
        export_stl(part, str(OUT / f"{name}.stl"))
        export_step(part, str(OUT / f"{name}.step"))
        m = trimesh.load(str(OUT / f"{name}.stl"))
        if rot is not None:
            m.apply_transform(rotation_matrix(np.radians(rot), [1, 0, 0]))   # front face down on the bed
        m.apply_translation(-m.bounds[0])
        m.export(str(OUT / f"{name}_print.stl"))
    export_stl(board_piece(), str(OUT / "skadis_board_piece.stl"))


if __name__ == "__main__":
    main()
