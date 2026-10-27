"""R06 Beacon: compact arm (no dowels), wall plate v4 and tip hanger v4.

The arm is now one stack, centred on y = 0, clamped by M4 bolts:
    tie | beam strip | 6.4 mm gap (two M4 nuts as spacers) | beam strip | tie
The beam is two 42 cm strips rising 11.5 deg from the wall plate's lower fin; the ties are two 32 cm strips hanging
from the plate's upper block to the beam's 31 cm holes. The tip hanger is one fin in the beam gap at the 41 cm
holes, hanging plumb, with the 32 cm crossbar bolted under its base through the 11 and 21 cm holes.

Every printed pivot is clamped between strips (no designed play): tighten the bolts and friction holds the joint.

    python3 beacon_compact.py           # writes out/beacon_wall_plate_v4.* and out/beacon_tip_hanger_v4.*

Frames as before. Wall plate: x out from the wall, y along the wall, z up, upper pivot at (22, 0, 0), lower at
(22, 0, -120). Tip hanger: x along the arm, y along the batten, z up, pivot at the origin.
Print: wall plate flat on its back; tip hanger on its side (profile flat on the bed). No supports for either.
"""
import math
import pathlib

from build123d import Box, Cone, Cylinder, Pos, Rot, BuildPart, BuildSketch, Plane, Polygon, extrude, export_stl, export_step
from shapely.geometry import LineString, Point, Polygon as SPoly, box as sbox
from shapely.ops import unary_union

OUT = pathlib.Path(__file__).resolve().parents[2] / "out" / "beacon"

STRIP_T = 7.5
GAP = 6.4                                       # two M4 nuts (3.2 each) between the beam strips
FIN_T = GAP - 0.2                               # printed fin in the gap; the strips clamp onto it
BLOCK_T = 2 * (GAP / 2 + STRIP_T) - 0.2         # upper block between the ties (they sit outside the beam)
BOLT = 4.4
PIVOT_X, PIVOT_DZ, SLOT = 22.0, 120.0, 5.0      # pivot distance from the wall; pivot spacing; lower slot +/-
TIP_R = 10.0                                    # round end around each pivot

# wall plate
BASE_T = 6.0                                    # wall face thickness (Allwin: at least 5)
TOP, BOTTOM = 20.0, -162.0
SCREW = dict(d=4.5, head=9.0, at=((-24.0, 0.0), (24.0, 0.0), (0.0, -152.0)))   # (y, z): 4 mm screws in plugs
SPINE_HALF, BAND_HALF = 13.0, 33.0
FILLET, ROUND = 12.0, 3.0

# tip hanger
DEPTH = 18.0                                    # along the arm
DROP = 35.0                                     # pivot to the crossbar bosses' top region (as v3)
BASE_BOT = -44.0                                # crossbar face
CROSS_Y = 50.0                                  # crossbar bolts (its 11 and 21 cm holes)
BOSS = dict(half_y=8.0, top=-31.0)
ARM_W = 8.0
KEEP_OUT = dict(y_in=GAP / 2 - 0.1, y_out=GAP / 2 + STRIP_T + 1.0, z=-20.0)   # beam strips and their swing
NUT = dict(af=7.4, t=3.4, skin=3.0)


def prism(poly, plane, a0, a1):
    pts = list(poly.exterior.coords)[:-1]
    with BuildPart() as p:
        with BuildSketch(plane.offset(a0)):
            Polygon(*pts, align=None)
        extrude(amount=a1 - a0)
    part = p.part
    for ring in poly.interiors:
        with BuildPart() as h:
            with BuildSketch(plane.offset(a0 - 1)):
                Polygon(*list(ring.coords)[:-1], align=None)
            extrude(amount=a1 - a0 + 2)
        part -= h.part
    return part


def prism_xz(poly, y0, y1):
    """Shapely outline in (x, z), extruded along y from y0 to y1 (Plane.XZ's normal is -y)."""
    pts = list(poly.exterior.coords)[:-1]
    with BuildPart() as p:
        with BuildSketch(Plane.XZ.offset(-y0)):
            Polygon(*pts, align=None)
        extrude(amount=-(y1 - y0))
    return p.part


def bezier(p0, c, p1, n=24):
    return [((1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * c[0] + u * u * p1[0],
             (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * c[1] + u * u * p1[1]) for u in (k / n for k in range(n + 1))]


def pivot_outline(zc, slot, root_half, x0):
    """Ear in (x, z): round end around the pivot (a stadium if slotted), widening to a broad root at x0."""
    tip = unary_union([Point(PIVOT_X, zc + d).buffer(TIP_R, 48) for d in (-slot, 0.0, slot)]).convex_hull
    root = SPoly([(x0 - 0.5, zc - slot - root_half), (x0 - 0.5, zc + slot + root_half),
                  (PIVOT_X, zc + slot + TIP_R), (PIVOT_X, zc - slot - TIP_R)])
    return unary_union([tip, root]).convex_hull


def roofed_outline(cx, cz, slot, r=BOLT / 2):
    """Hole (or slot along z) in (x, z) with a 45 deg roof toward +x."""
    body = unary_union([Point(cx, cz + d).buffer(r, 32) for d in (-slot, 0.0, slot)]).convex_hull
    roof = SPoly([(cx, cz - slot - r), (cx + r * math.sqrt(2), cz - slot), (cx + r * math.sqrt(2), cz + slot),
                  (cx, cz + slot + r)])
    return unary_union([body, roof])


# ---------------------------------------------------------------- wall plate v4
def wall_outline():
    """Wall face in (y, z): a band across the top for the two upper screws, a spine down to the lower fin, and a
    boss for the third screw at the bottom."""
    band = sbox(-BAND_HALF, -16.0, BAND_HALF, TOP)
    spine = sbox(-SPINE_HALF, BOTTOM + 8.0, SPINE_HALF, -10.0)
    bosses = [Point(y, z).buffer(9.0, 48) for y, z in SCREW["at"]]
    foot = Point(0.0, SCREW["at"][2][1]).buffer(11.0, 48)
    shape = unary_union([band, spine, foot, *bosses])
    shape = shape.buffer(FILLET, 48).buffer(-FILLET, 48).buffer(-ROUND, 48).buffer(ROUND, 48)
    assert shape.geom_type == "Polygon"
    return shape


def wall_plate():
    plate = prism(wall_outline(), Plane.YZ, 0.0, BASE_T)
    plate += prism_xz(pivot_outline(0.0, 0.0, 16.0, BASE_T), -BLOCK_T / 2, BLOCK_T / 2)          # upper block
    plate += prism_xz(pivot_outline(-PIVOT_DZ, SLOT, 16.0, BASE_T), -FIN_T / 2, FIN_T / 2)       # lower fin
    plate -= prism_xz(roofed_outline(PIVOT_X, 0.0, 0.0), -BLOCK_T, BLOCK_T)
    plate -= prism_xz(roofed_outline(PIVOT_X, -PIVOT_DZ, SLOT), -BLOCK_T, BLOCK_T)
    for y, z in SCREW["at"]:
        plate -= Pos(BASE_T / 2, y, z) * Rot(0, 90, 0) * Cylinder(SCREW["d"] / 2, BASE_T + 2)
        k = SCREW["head"] / 2
        plate -= Pos(BASE_T - k / 2 + 0.01, y, z) * Rot(0, 90, 0) * Cone(SCREW["d"] / 2 - 0.01, k + 0.01, k)
    for y in (-6.0, 6.0):                                                                     # cable-tie slots
        plate -= Pos(BASE_T / 2, y, -30.0) * Box(BASE_T + 2, 3.0, 6.0)
    return plate


def wall_checks():
    """Strip ends clear the wall face over the slot travel; the screws clear the block and fin."""
    worst = 99.0
    for dz in (-SLOT, 0.0, SLOT):
        a = math.asin((PIVOT_DZ + dz) / 600.0)
        for ang in (a, -a):
            for n in (-7.5, 7.5):
                worst = min(worst, PIVOT_X - 10.0 * math.cos(ang) - n * math.sin(ang) - BASE_T)
    assert worst > 1.0, "strip ends would hit the wall face"
    for y, z in SCREW["at"]:
        clear_block = abs(y) - SCREW["head"] / 2 - BLOCK_T / 2 if abs(z) < 30 else 99
        clear_fin = abs(z + PIVOT_DZ) - SLOT - 16.0 - SCREW["head"] / 2 if abs(y) < 10 else 99
        assert min(clear_block, clear_fin) > 2.0, f"screw at {(y, z)} crowds a pivot"
    return worst


# ---------------------------------------------------------------- tip hanger v4
def hanger_profile():
    """Front outline in (y, z): one fin up into the beam gap, then two curved arms out to the crossbar bosses."""
    fin = sbox(-FIN_T / 2, -24.0, FIN_T / 2, 11.0)
    neck = SPoly(bezier((-FIN_T / 2, -18.0), (-FIN_T / 2, -30.0), (-16.0, -34.0)) +
                 bezier((16.0, -34.0), (FIN_T / 2, -30.0), (FIN_T / 2, -18.0)))
    parts = [fin, neck]
    for s in (-1, 1):
        arm = LineString(bezier((0.0, -30.0), (s * 26.0, -30.0), (s * CROSS_Y, -37.0))).buffer(ARM_W / 2, 32)
        boss = sbox(s * CROSS_Y - BOSS["half_y"], BASE_BOT, s * CROSS_Y + BOSS["half_y"], BOSS["top"])
        parts += [arm, boss]
    shape = unary_union(parts).buffer(6.0, 32).buffer(-6.0, 32)
    keep = unary_union([sbox(KEEP_OUT["y_in"], KEEP_OUT["z"], 80, 20), sbox(-80, KEEP_OUT["z"], -KEEP_OUT["y_in"], 20)])
    shape = shape.difference(unary_union([keep, sbox(-100, -100, 100, BASE_BOT)]))
    shape = shape.buffer(-1.0, 32).buffer(1.0, 32)
    assert shape.geom_type == "Polygon", "hanger profile must stay one piece"
    return shape


def tip_hanger():
    part = prism(hanger_profile(), Plane.YZ, -DEPTH / 2, DEPTH / 2)
    h, c = DEPTH / 2, 6.0                                          # chamfer the fin's top corners (<= 45 deg)
    side = SPoly([(-h, BASE_BOT), (h, BASE_BOT), (h, 11.0 - c), (h - c, 11.0), (-h + c, 11.0), (-h, 11.0 - c)])
    part = part & prism_xz(side, -80, 80)
    part -= prism_xz(roofed_outline(0.0, 0.0, 0.0), -10, 10)       # pivot through the fin
    for s in (-1, 1):
        y = s * CROSS_Y
        part -= prism(roofed_outline(0.0, y, 0.0), Plane.XY, BASE_BOT - 1, -21.0)   # sideways in print: roofed
        nz = BASE_BOT + NUT["skin"] + NUT["t"] / 2
        x0, x1 = -NUT["af"] / 2 - 0.3, DEPTH / 2 + 1
        part -= Pos((x0 + x1) / 2, y, nz) * Box(x1 - x0, NUT["af"], NUT["t"])
    return part


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    clr = wall_checks()
    for name, part in (("beacon_wall_plate_v4", wall_plate()), ("beacon_tip_hanger_v4", tip_hanger())):
        bb = part.bounding_box()
        print(f"{name}: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm, volume {part.volume / 1000:.1f} cm3")
        export_stl(part, str(OUT / f"{name}.stl"))
        export_step(part, str(OUT / f"{name}.step"))
    print(f"fin {FIN_T:.1f} mm, block {BLOCK_T:.1f} mm, strip-end clearance {clr:.1f} mm")


if __name__ == "__main__":
    main()
