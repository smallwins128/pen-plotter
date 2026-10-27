"""R06 Beacon: wall plate for the single lifted arm (option "B flipped") that holds the Philips WiZ batten.

The arm is a pinned truss. Two 42 cm rails (on edge, 90 mm apart on dowel rungs) pivot on the LOWER ears and rise
11.5 deg; two 32 cm ties (outside the rails) hang from the UPPER ears and bolt to the rails' 31 cm holes. Every
joint is an M4 bolt through a strip's existing 4 mm hole, washer, ear, washer, nut on the inside.

    python3 beacon_wall_plate.py        # writes out/beacon_wall_plate.stl and .step

Frame: x out from the wall (wall face x = 0), y along the wall (arm centre y = 0), z up (upper pivot z = 0).
Print: flat on its back (wall face on the bed). Loads are small (batten 400 g; about 20 N in the ties, about 15 N
on the top wall screw), so layer direction is not the limit; the flat back and upright countersinks matter more.
"""
import math
import pathlib

from build123d import Box, Cone, Cylinder, Pos, Rot, BuildPart, BuildSketch, Plane, Polygon, extrude, export_stl, export_step
from shapely.geometry import Point, Polygon as SPoly
from shapely.ops import unary_union

OUT = pathlib.Path(__file__).resolve().parents[2] / "out" / "beacon"

STRIP = dict(h=15.0, t=7.5, hole=4.0, end=10.0)   # Allwin's strips: 15 x 7.5, holes 10 mm in from the end
GAP = 90.0                                        # rail inner faces = dowel length (9 cm)
PIVOT_X, PIVOT_DZ = 22.0, 120.0                   # pivot distance from the wall; upper-to-lower pivot spacing
SLOT = 5.0                                        # lower pivot slot, +/- along z: closes the triangle, sets level
BOLT = 4.4                                        # M4 clearance
EAR_T, CLR = 8.0, 0.5                             # ear thickness; gap to each strip face (take up with washers)
EAR_R = 10.0                                      # ear tip radius around the pivot
BASE_T = 8.0                                      # plate thickness
TOP, BOTTOM = 20.0, -145.0                        # plate z extent
SCREW = dict(d=4.5, head=9.0, z=(0.0, -120.0))    # 4 mm wall screw in a 6 mm plug, countersunk

RAIL_EAR = (GAP / 2 - CLR - EAR_T, GAP / 2 - CLR)                       # y span of each lower ear (mirrored)
TIE_IN = GAP / 2 + STRIP["t"]                                           # ties sit on the rails' outer faces
TIE_EAR = (TIE_IN - CLR - EAR_T, TIE_IN - CLR)                          # y span of each upper ear (mirrored)
HALF_W = TIE_EAR[1]                                                     # plate half-width: flush with the tie ears


def prism_xz(poly, y0, y1):
    """Extrude a shapely outline drawn in (x, z) along y from y0 to y1."""
    pts = [(x, z) for x, z in list(poly.exterior.coords)[:-1]]
    with BuildPart() as p:
        with BuildSketch(Plane.XZ.offset(-y0)):
            Polygon(*pts, align=None)
        extrude(amount=-(y1 - y0))
    return p.part


def ear_outline(zc, slot):
    """Ear in (x, z): round tip around the pivot (a stadium if slotted), widening to a broad root on the plate."""
    tip = unary_union([Point(PIVOT_X, zc + d).buffer(EAR_R, 48) for d in (-slot, 0.0, slot)]).convex_hull
    root = SPoly([(BASE_T - 0.5, zc - slot - 18), (BASE_T - 0.5, zc + slot + 18),
                  (PIVOT_X, zc + slot + EAR_R), (PIVOT_X, zc - slot - EAR_R)])
    return unary_union([tip, root]).convex_hull


def hole_outline(zc, slot):
    """Bolt hole (or slot) in (x, z), with a 45 deg roof toward +x so it prints without support lying on its back."""
    r = BOLT / 2
    body = unary_union([Point(PIVOT_X, zc + d).buffer(r, 32) for d in (-slot, 0.0, slot)]).convex_hull
    roof = SPoly([(PIVOT_X, zc - slot - r), (PIVOT_X + r * math.sqrt(2), zc - slot),
                  (PIVOT_X + r * math.sqrt(2), zc + slot), (PIVOT_X, zc + slot + r)])
    return unary_union([body, roof])


def strip_end_clearance():
    """Smallest gap between a strip's back corners and the plate face, over the slot travel. Must stay positive."""
    worst = 99.0
    for dz in (-SLOT, 0.0, SLOT):                          # lower pivot anywhere in its slot
        # rail angle: tie (300 mm between holes) from the upper pivot meets the rail's hole 300 mm from its pivot
        d = PIVOT_DZ + dz
        a = math.asin((d * d) / (2 * d * 300.0))           # isosceles: both members 300 mm hole to hole
        for ang in (a, -a):                                # rail rises at +a from below, tie falls at -a from above
            c, s = math.cos(ang), math.sin(ang)
            for n in (-STRIP["h"] / 2, STRIP["h"] / 2):
                x = PIVOT_X - STRIP["end"] * c - n * s
                worst = min(worst, x - BASE_T)
    return worst


def build():
    assert strip_end_clearance() > 1.0, "strip ends would hit the plate face"
    plate = Pos(BASE_T / 2, 0, (TOP + BOTTOM) / 2) * Box(BASE_T, 2 * HALF_W, TOP - BOTTOM)
    for side in (-1, 1):
        for (zc, slot, span) in ((0.0, 0.0, TIE_EAR), (-PIVOT_DZ, SLOT, RAIL_EAR)):
            y0, y1 = sorted((side * span[0], side * span[1]))
            plate += prism_xz(ear_outline(zc, slot), y0, y1)
    for (zc, slot) in ((0.0, 0.0), (-PIVOT_DZ, SLOT)):
        plate -= prism_xz(hole_outline(zc, slot), -HALF_W - 1, HALF_W + 1)
    for z in SCREW["z"]:                                   # countersunk wall screws on the centre line
        plate -= Pos(BASE_T / 2, 0, z) * Rot(0, 90, 0) * Cylinder(SCREW["d"] / 2, BASE_T + 2)
        k = SCREW["head"] / 2
        plate -= Pos(BASE_T - k / 2 + 0.01, 0, z) * Rot(0, 90, 0) * Cone(SCREW["d"] / 2 - 0.01, k + 0.01, k)
    for y in (-9.0, 9.0):                                  # cable-tie slots above the top screw: strain relief
        plate -= Pos(BASE_T / 2, y, 12.0) * Box(BASE_T + 2, 3.0, 6.0)
    return plate


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    part = build()
    bb = part.bounding_box()
    print(f"wall plate: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm (x out, y along wall, z up), "
          f"volume {part.volume / 1000:.1f} cm3, strip-end clearance {strip_end_clearance():.1f} mm")
    print(f"ears: upper (ties) y +/-{TIE_EAR[0]:.1f}..{TIE_EAR[1]:.1f}, lower (rails) y +/-{RAIL_EAR[0]:.1f}..{RAIL_EAR[1]:.1f}")
    export_stl(part, str(OUT / "beacon_wall_plate.stl"))
    export_step(part, str(OUT / "beacon_wall_plate.step"))


if __name__ == "__main__":
    main()
