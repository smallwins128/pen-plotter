"""Printed slide-on grip for 35 × 7.5 DIN rail (TS35, 1.0 mm edges), and its fit coupon.

Profile (looking along the rail): a flat top that rests on the rail's two edges, and a hook down each side that
reaches 2.2 mm under each 1.0 mm edge. Nothing flexes: plates slide on from the rail's end before the rail is
screwed down (rail screws go through the gaps between plates).

    python3 hardware/parts/din_grip.py      # writes hardware/out/din_grip/din_grip_coupon_c{0.1,0.2,0.3}.stl

Frame: x along the rail, y across it (rail centre y = 0), z up from the rail's mounting face (rail top = 7.5).
"""
import pathlib

from build123d import export_stl
from shapely.geometry import Polygon, box as sbox
from shapely.ops import unary_union

import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from window_inserts import slab  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent.parent / "out" / "din_grip"
RAIL = dict(w=35.0, h=7.5, lip=1.0, hat=27.0)      # TS35 × 7.5 (EN 60715); Allwin's rail checked 2026-10-20
REACH, WALL, TOOTH, TOP = 2.2, 2.5, 1.5, 3.0         # hook reach under the edge, side wall, tooth thickness, top plate


def profile(c):
    """Grip cross-section in (y, z) for clearance c (per side, and above/below the edge)."""
    e = RAIL["w"] / 2 + c                              # inner face of the side walls
    top = sbox(-e - WALL, RAIL["h"], e + WALL, RAIL["h"] + TOP)
    z_under = RAIL["h"] - RAIL["lip"] - c              # tooth top: just under the edge
    parts = [top]
    for s in (-1, 1):
        wall = sbox(min(s * e, s * (e + WALL)), z_under - TOOTH, max(s * e, s * (e + WALL)), RAIL["h"] + 0.01)
        tooth = sbox(min(s * e, s * (RAIL["w"] / 2 - REACH)), z_under - TOOTH, max(s * e, s * (RAIL["w"] / 2 - REACH)), z_under)
        parts += [wall, tooth]
    p = unary_union(parts)
    assert RAIL["w"] / 2 - REACH > RAIL["hat"] / 2 + 1.0, "tooth would hit the rail's side wall"
    return p


def coupon(c, length=20.0):
    """Profile extruded `length` along the rail (printed standing on the profile, so no overhangs)."""
    return slab(profile(c), 0, length)


ANCHOR = dict(len=10.0, half_w=8.0, z0=4.5, bore=4.0, depth=4.5)   # tab off the grip's end; M3 × 4 insert (OD 4.3)


def anchor_tab(x0):
    """Anchor tab starting at x = x0: sits over the rail's channel; an M3 screw down through an insert jacks on the
    rail floor, pulling the hooks up against the edges (locks position, kills rattle)."""
    from build123d import Box, Cylinder, Pos
    a = ANCHOR
    top = RAIL["h"] + TOP
    tab = Pos(x0 + a["len"] / 2, 0, (a["z0"] + top) / 2) * Box(a["len"], 2 * a["half_w"], top - a["z0"])
    cx = x0 + a["len"] / 2
    tab -= Pos(cx, 0, top - a["depth"] / 2 + 0.01) * Cylinder(a["bore"] / 2, a["depth"] + 0.02)
    tab -= Pos(cx, 0, (a["z0"] + top) / 2) * Cylinder(3.4 / 2, top - a["z0"] + 2)
    assert a["half_w"] < RAIL["hat"] / 2 - 1.0 - 0.5, "tab must fit inside the rail's channel"
    return tab


def grip_along_x(c, x0, x1):
    """The grip profile as a solid running along x from x0 to x1 (y across the rail, z up)."""
    from build123d import BuildPart, BuildSketch, Plane, Polygon as BPolygon, extrude
    pts = list(profile(c).exterior.coords)[:-1]
    with BuildPart() as bp:
        with BuildSketch(Plane.YZ.offset(x0)):
            BPolygon(*pts, align=None)
        extrude(amount=x1 - x0)
    return bp.part


def coupon_anchor(c=0.3, length=20.0):
    """Loose grip + anchor tab on one end. Print lying on its top face (hooks up)."""
    return grip_along_x(c, 0, length) + anchor_tab(length - 0.01)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for c in (0.1, 0.2, 0.3):
        part = coupon(c)
        export_stl(part, str(OUT / f"din_grip_coupon_c{c:g}.stl"))
        print(f"din_grip_coupon_c{c:g}: {part.volume / 1000:.1f} cm3")
    a = coupon_anchor(0.3)
    export_stl(a, str(OUT / "din_grip_anchor_c0.3.stl"))
    bb = a.bounding_box()
    print(f"din_grip_anchor_c0.3: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f}, {a.volume / 1000:.1f} cm3")


if __name__ == "__main__":
    main()
