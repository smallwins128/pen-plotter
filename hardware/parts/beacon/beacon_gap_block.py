"""R06 Beacon: gap block, the printed half of the cheap bridge between the doubled arms (2026-10-30).

Replaces the printed C bridge. Each bridge is a 32 cm strip laid flat across under the two beams, its holes 1 and
21 (200 mm apart = the arm pitch) bolted up into two gap blocks. Each gap block's fin slots into a beam's 6.4 mm gap
in place of the two spacer nuts, on the beam's 11 or 21 cm hole (M4 x 30 through strip | fin | strip). Its tab sits
under the beam; an M4 x 16 comes up through the cross strip into a nut slid into the tab. Four blocks, two bridges.

    python3 beacon_gap_block.py         # writes out/beacon_gap_block.stl, .step and _print.stl

Frame: the beam's own frame. x along the beam, y across (block centred in the gap), z square to the beam (up),
the beam bolt on the y axis at the origin.
Print: on its side (the y-z outline flat on the bed), no supports. Holes get a 45 deg roof toward +x; the nut slot
opens on the top face as printed.
"""
import pathlib

from build123d import Box, Plane, Pos, export_stl, export_step
from shapely.geometry import box as sbox
from shapely.ops import unary_union

from beacon_compact import FIN_T, BOLT, prism, prism_xz, roofed_outline

OUT = pathlib.Path(__file__).resolve().parents[2] / "out" / "beacon"

STRIP_H = 15.0                     # beam strip height (z)
DEPTH = 24.0                       # along the beam (x)
CLEAR = 1.0                        # below the beam strips' bottom edges
TAB = dict(half_y=12.0, t=10.0)    # tab under the beam; the cross strip (15 wide) bolts to its underside
NUT = dict(af=7.4, t=3.4, skin=3.0)


def outline():
    """Fin up into the beam gap, tab underneath, in (y, z)."""
    zt = -STRIP_H / 2 - CLEAR                                     # tab top face
    fin = sbox(-FIN_T / 2, zt - 0.5, FIN_T / 2, STRIP_H / 2 - 0.5)
    tab = sbox(-TAB["half_y"], zt - TAB["t"], TAB["half_y"], zt).buffer(-2.0, 16).buffer(2.0, 16)
    return unary_union([fin, tab])


def gap_block():
    zt = -STRIP_H / 2 - CLEAR
    zb = zt - TAB["t"]
    part = prism(outline(), Plane.YZ, -DEPTH / 2, DEPTH / 2)
    part -= prism_xz(roofed_outline(0.0, 0.0, 0.0), -10, 10)                    # beam bolt, through the fin
    up = -STRIP_H / 2 + 2.5                                                       # cross bolt hole stops 2.5 under the beam bolt's ring
    part -= prism(roofed_outline(0.0, 0.0, 0.0), Plane.XY, zb - 1, up)            # cross bolt, up from below
    nz = zb + NUT["skin"] + NUT["t"] / 2
    x0, x1 = -NUT["af"] / 2 - 0.3, DEPTH / 2 + 1
    part -= Pos((x0 + x1) / 2, 0, nz) * Box(x1 - x0, NUT["af"], NUT["t"])        # nut slot, open to +x
    return part


def main():
    import numpy as np, trimesh
    from trimesh.transformations import rotation_matrix
    OUT.mkdir(parents=True, exist_ok=True)
    part = gap_block()
    bb = part.bounding_box()
    print(f"gap block: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm, volume {part.volume / 1000:.1f} cm3")
    export_stl(part, str(OUT / "beacon_gap_block.stl"))
    export_step(part, str(OUT / "beacon_gap_block.step"))
    m = trimesh.load(str(OUT / "beacon_gap_block.stl"))
    m.apply_transform(rotation_matrix(np.radians(-90), [0, 1, 0]))            # on its side: -x face down
    m.apply_translation(-m.bounds[0])
    m.export(str(OUT / "beacon_gap_block_print.stl"))


if __name__ == "__main__":
    main()
