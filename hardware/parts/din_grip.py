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


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for c in (0.1, 0.2, 0.3):
        part = coupon(c)
        export_stl(part, str(OUT / f"din_grip_coupon_c{c:g}.stl"))
        print(f"din_grip_coupon_c{c:g}: {part.volume / 1000:.1f} cm3")


if __name__ == "__main__":
    main()
