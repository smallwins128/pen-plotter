"""R06 Beacon: tip hanger for the single lifted arm (Allwin's sketch, 2026-10-27).

A printed U that hangs from ONE M4 rod through the rails' 41 cm holes, its two tabs just outside the rails. It hangs
plumb whatever the rail angle, so the batten levels itself. The 32 cm crossbar bolts flat under the base through its
11 and 21 cm holes (50 mm either side of its centre); the batten clips go on the crossbar's end holes.

    python3 beacon_tip_hanger.py        # writes out/beacon_tip_hanger.stl and .step

Frame: x along the arm (+x toward the arm tip), y along the batten (centre y = 0), z up (pivot at the origin).
Print: base face down (the face the crossbar sits on), no supports. The pivot holes have a 45 deg roof; the nut
slots enter from the +x face and are 7.4 mm bridges.
"""
import math
import pathlib

from build123d import Box, Cylinder, Pos, BuildPart, BuildSketch, Plane, Polygon, extrude, export_stl, export_step
from shapely.geometry import Point, Polygon as SPoly, box as sbox
from shapely.ops import unary_union

OUT = pathlib.Path(__file__).resolve().parents[2] / "out" / "beacon"

STRIP_T, GAP = 7.5, 90.0                       # strip thickness; rail inner faces = dowel length
CLR = 0.5                                      # gap to each rail face (washers take it up)
TAB_T, TAB_HALF = 8.0, 10.0                    # tab thickness; half-width of its neck (and tip radius)
DROP = 35.0                                    # pivot to base top (Allwin 2026-10-27)
BASE_HALF_X, BASE_T = 22.0, 9.0                # base: 44 deep along the arm, 9 thick (room for a nut slot)
FLARE_Z = 13.0                                 # height of the neck-to-base flare
BOLT = 4.4                                     # M4 clearance
NUT = dict(af=7.4, t=3.4, skin=3.0)            # M4 nut slot: across-flats + clearance, height, floor under it
CROSS_Y = 50.0                                 # crossbar bolt holes, either side of centre
CABLE = (9.0, 18.0, 6.0)                       # cable slot: x from, x to, half-width in y
RAIL_RISE = math.asin(0.2)                     # 11.5 deg, from the wall-plate geometry

TAB_IN = GAP / 2 + STRIP_T + CLR               # tab inner face
TAB_OUT = TAB_IN + TAB_T
BASE_TOP = -DROP


def prism_xz(poly, y0, y1):
    """Extrude a shapely outline drawn in (x, z) along y from y0 to y1."""
    pts = list(poly.exterior.coords)[:-1]
    with BuildPart() as p:
        with BuildSketch(Plane.XZ.offset(-y0)):
            Polygon(*pts, align=None)
        extrude(amount=-(y1 - y0))
    return p.part


def tab_outline():
    """Tab in (x, z): round top around the pivot, a neck, then a flare out to the full base depth."""
    tip = Point(0, 0).buffer(TAB_HALF, 48)
    neck = sbox(-TAB_HALF, BASE_TOP + FLARE_Z, TAB_HALF, 0)
    flare = SPoly([(-TAB_HALF, BASE_TOP + FLARE_Z), (TAB_HALF, BASE_TOP + FLARE_Z),
                   (BASE_HALF_X, BASE_TOP + 0.5), (-BASE_HALF_X, BASE_TOP + 0.5)])
    return unary_union([tip, neck, flare])


def pivot_hole():
    r = BOLT / 2
    return unary_union([Point(0, 0).buffer(r, 32), SPoly([(-r, 0), (0, r * math.sqrt(2)), (r, 0)])])


def rail_clearance():
    """Gap from the rails' undersides to the base top, over the base's depth, with the hanger plumb."""
    lowest = -BASE_HALF_X * math.tan(RAIL_RISE) - (15.0 / 2) / math.cos(RAIL_RISE)
    return lowest - BASE_TOP


def build():
    assert rail_clearance() > 10.0, "base would touch the rails"
    assert TAB_OUT - 3 > CROSS_Y + NUT["af"] / 2, "nut slots must stay inside the base"
    base_bot = BASE_TOP - BASE_T
    part = Pos(0, 0, BASE_TOP - BASE_T / 2) * Box(2 * BASE_HALF_X, 2 * TAB_OUT, BASE_T)
    for s in (-1, 1):
        y0, y1 = sorted((s * TAB_IN, s * TAB_OUT))
        part += prism_xz(tab_outline(), y0, y1)
    part -= prism_xz(pivot_hole(), -TAB_OUT - 1, TAB_OUT + 1)
    for s in (-1, 1):
        y = s * CROSS_Y
        part -= Pos(0, y, BASE_TOP - BASE_T / 2) * Cylinder(BOLT / 2, BASE_T + 2)
        nz = base_bot + NUT["skin"] + NUT["t"] / 2                 # nut slot, open to the +x face
        sx0, sx1 = -NUT["af"] / 2 - 0.3, BASE_HALF_X + 1
        part -= Pos((sx0 + sx1) / 2, y, nz) * Box(sx1 - sx0, NUT["af"], NUT["t"])
    x0, x1, hw = CABLE
    part -= Pos((x0 + x1) / 2, 0, BASE_TOP - BASE_T / 2) * Box(x1 - x0, 2 * hw, BASE_T + 2)
    return part


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    part = build()
    bb = part.bounding_box()
    print(f"tip hanger: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm (x along arm, y along batten, z up), "
          f"volume {part.volume / 1000:.1f} cm3, rail clearance {rail_clearance():.1f} mm, tabs y +/-{TAB_IN}..{TAB_OUT}")
    export_stl(part, str(OUT / "beacon_tip_hanger.stl"))
    export_step(part, str(OUT / "beacon_tip_hanger.step"))


if __name__ == "__main__":
    main()
