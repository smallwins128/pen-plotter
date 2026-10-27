"""R06 Beacon: tip hanger v3, an organic version of v2 drawn from a 2D topology-optimisation run (topo/topo_tip.py).

The run showed the batten's weight goes almost straight from the crossbar bolts up the legs to the pivots; the slab
between the bolts only ties the two sides against a sideways knock. So v3 keeps two legs and one
arched tie, every member at least 6 mm, with large fillets.

    python3 beacon_tip_hanger_organic.py      # writes out/beacon_tip_hanger_v3.stl and .step

Frame as v2: x along the arm, y along the batten, z up, pivot at the origin.
Print ON ITS SIDE: the -x face on the bed, so the whole front profile is one flat outline and needs no support.
Holes then run sideways (y and z), so each has a 45 deg roof toward +x; the crossbar nut slots open on the top face.
"""
import math
import pathlib

from build123d import Box, Cylinder, Pos, Rot, BuildPart, BuildSketch, Plane, Polygon, extrude, export_stl, export_step
from shapely.geometry import LineString, Point, Polygon as SPoly, box as sbox
from shapely.ops import unary_union

OUT = pathlib.Path(__file__).resolve().parents[2] / "out" / "beacon"

DEPTH = 18.0                                   # extent along the arm (x = +/-9); v2 was 44 at its base
PIVOT_Y = 58.0                                 # tab centre line (tabs 53..63, just outside the rails)
TAB_IN, TAB_OUT = 53.0, 63.0
MEMBER = 6.0                                   # minimum member width in the front profile
FILLET = 6.0                                   # inside-corner fillet radius
ARCH_LIFT = 7.0                                # tie centre line rises this much at mid-span
KEEP_OUT = dict(y=53.0, z=-20.0)               # rails and their swing: no material at |y| < 53 above z = -20
BOLT = 4.4
PIV_NUT = dict(af=7.3, depth=3.4)              # M4 nut pocket on each tab's outer face
CROSS_Y, BASE_BOT = 50.0, -44.0                # crossbar bolts; crossbar sits on the plane z = -44
BOSS = dict(half_y=8.0, top=-31.0)             # crossbar bolt bosses
NUT = dict(af=7.4, t=3.4, skin=3.0)            # crossbar nut slots (open toward +x, the top as printed)


def bezier(p0, c, p1, n=24):
    """Points on a quadratic Bezier from p0 to p1, bending toward c."""
    return [((1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * c[0] + u * u * p1[0],
             (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * c[1] + u * u * p1[1]) for u in (k / n for k in range(n + 1))]


def front_profile():
    """Outline in (y, z): two legs into the bolt bosses, joined by an arched tie, smoothed.

    The rails' keep-out leaves only 24 mm between z = -20 and the crossbar face, too little for a truss with open
    cells at a 6 mm member floor (the cells close up under the fillets). So the tie is one arch: it meets the
    bosses at the crossbar face and lifts 7 mm at the centre, leaving a single open span the cable passes through.
    """
    w = MEMBER / 2
    parts = []
    for s in (-1, 1):                     # one smooth leg per side: tab, then curves into the bolt boss
        bx = CROSS_Y + BOSS["half_y"]
        outer = bezier((TAB_OUT, -22.0), (TAB_OUT, -40.0), (bx - 1.0, BASE_BOT))         # convex, sheds the corner
        inner = bezier((CROSS_Y - BOSS["half_y"] - 6.0, -36.0), (TAB_IN, -36.0), (TAB_IN, KEEP_OUT["z"] - 1.0))  # cove
        pts = [(TAB_IN, 11.0), (TAB_OUT, 11.0)] + outer + [(CROSS_Y - BOSS["half_y"] - 6.0, BASE_BOT)] + inner
        parts.append(SPoly([(s * y, z) for y, z in pts]))
    half = CROSS_Y - BOSS["half_y"] + 2.0
    arch = LineString([(y, BASE_BOT + w + ARCH_LIFT * (1 - (y / half) ** 2))
                       for y in [-half + k * (2 * half) / 40 for k in range(41)]]).buffer(w, 32)
    shape = unary_union(parts + [arch])
    shape = shape.buffer(FILLET, 32).buffer(-FILLET, 32)                    # fillet every inside corner
    keep_out = sbox(-KEEP_OUT["y"], KEEP_OUT["z"], KEEP_OUT["y"], 20.0)
    floor = sbox(-100, -100, 100, BASE_BOT)                                 # crossbar face stays flat
    sides = unary_union([sbox(TAB_OUT, -100, 100, 100), sbox(-100, -100, -TAB_OUT, 100)])
    shape = shape.difference(unary_union([keep_out, floor, sides]))
    shape = shape.buffer(-2.5, 32).buffer(2.5, 32)                          # round the outside corners too
    assert shape.geom_type == "Polygon", "profile must stay one piece"
    return shape


def side_profile():
    """Outline in (x, z): full depth, 45 deg chamfers on top so the print never overhangs past 45 deg."""
    h, c = DEPTH / 2, 6.0
    return SPoly([(-h, BASE_BOT), (h, BASE_BOT), (h, 11.0 - c), (h - c, 11.0), (-h + c, 11.0), (-h, 11.0 - c)])


def prism(poly, plane, a0, a1):
    pts = list(poly.exterior.coords)[:-1]
    with BuildPart() as p:
        with BuildSketch(plane.offset(a0)):
            Polygon(*pts, align=None)
        extrude(amount=a1 - a0)
    return p.part


def roofed(r, length, axis):
    """Round hole of radius r with a 45 deg roof toward +x, along y or z, centred on the origin."""
    c = r / math.sqrt(2)                                     # tangent points of the 45 deg roof lines
    diamond = Rot(0, 0, 45) * Box(2 * r, 2 * r, length)       # sides tangent to the circle
    roof = diamond & (Pos((c + 2 * r) / 2, 0, 0) * Box(2 * r - c, 2 * r, length + 1))
    hole = Cylinder(r, length) + roof
    return Rot(90, 0, 0) * hole if axis == "y" else hole


def hex_prism(af, depth):
    """Hex pocket along y, a vertex toward +x (up, as printed)."""
    r = af / math.sqrt(3)
    pts = [(r * math.cos(math.radians(60 * k)), r * math.sin(math.radians(60 * k))) for k in range(6)]
    with BuildPart() as p:
        with BuildSketch(Plane.XZ):
            Polygon(*pts, align=None)
        extrude(amount=depth, both=False)
    return p.part                                   # Plane.XZ normal is -y: runs from y = 0 to y = -depth


def build():
    front = front_profile()
    # Plane.YZ: local (x, y) = global (y, z), normal +x
    part = prism(front, Plane.YZ, -DEPTH / 2, DEPTH / 2)
    side = side_profile()
    big = 2 * TAB_OUT + 2
    with BuildPart() as sp:
        with BuildSketch(Plane.XZ.offset(-big / 2)):
            Polygon(*list(side.exterior.coords)[:-1], align=None)
        extrude(amount=big)
    part = part & sp.part
    part -= roofed(BOLT / 2, 2 * TAB_OUT + 2, "y")                        # pivot holes through both tabs
    for s in (-1, 1):
        pocket = hex_prism(PIV_NUT["af"], PIV_NUT["depth"] + 0.01)          # runs y 0 .. -depth
        part -= Pos(0, s * (TAB_OUT + 0.01), 0) * (pocket if s > 0 else Rot(0, 0, 180) * pocket)
        y = s * CROSS_Y
        part -= Pos(0, y, (BASE_BOT - 1 - 20.0) / 2) * roofed(BOLT / 2, 20.0 - BASE_BOT + 1, "z")   # room for M4 x 25
        nz = BASE_BOT + NUT["skin"] + NUT["t"] / 2
        x0, x1 = -NUT["af"] / 2 - 0.3, DEPTH / 2 + 1
        part -= Pos((x0 + x1) / 2, y, nz) * Box(x1 - x0, NUT["af"], NUT["t"])
    return part


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    part = build()
    bb = part.bounding_box()
    print(f"tip hanger v3: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm, volume {part.volume / 1000:.1f} cm3, "
          f"profile area {front_profile().area:.0f} mm2")
    export_stl(part, str(OUT / "beacon_tip_hanger_v3.stl"))
    export_step(part, str(OUT / "beacon_tip_hanger_v3.step"))


if __name__ == "__main__":
    main()
