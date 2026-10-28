"""R06 Beacon: wall plate v3, an organic version of v2 drawn from a coarse 3D topology run (topo/topo_wall3d.py).

The run kept four things: a band across the top that carries the ties' pull into the top screw (with a deep rib
under the nut-access zone), pads behind the lower ears where the rails press the plate into the wall, two slim legs
joining them, and a thin bar out to the lower screw. The middle of v2's 8 mm back plate and its bottom centre
carried almost nothing, so v3 opens a window in the middle and a notch at the bottom.
Ears, nut pockets, the levelling slot and the screw countersinks are v2's, unchanged.

    python3 beacon_wall_plate_organic.py      # writes out/beacon_wall_plate_v3.stl and .step

Frame as v2: x out from the wall (wall face x = 0), y along the wall, z up (upper pivot z = 0).
Print: flat on its back, no supports.
"""
import pathlib

from build123d import Box, Cone, Cylinder, Pos, Rot, BuildPart, BuildSketch, Plane, Polygon, extrude, export_stl, export_step
from shapely.geometry import LineString, Point, Polygon as SPoly, box as sbox
from shapely.ops import unary_union

import beacon_wall_plate as W

OUT = pathlib.Path(__file__).resolve().parents[2] / "out" / "beacon"

MEMBER = 10.0                    # leg width (y)
BAR = 9.0                        # height of the bar carrying the lower screw boss
FILLET, ROUND = 16.0, 3.0        # inside fillets; outside corner rounding
RIB = dict(x1=20.0, w=6.0)       # arched rib under the nut-access zone: depth out from the wall, width
BOSS_R = 9.0                     # screw boss radius in the back plate


def rib_z(y):
    """Centre line of the arched rib: level with the band's edge at the ears, 16 mm lower at mid-span."""
    return -16.0 - 16.0 * (1 - (y / W.TIE_EAR[0]) ** 2)


def back_outline():
    """Back plate in (y, z): a top band, two legs behind the lower ears, pads under the lower ears' roots, and a
    slim bar carrying the lower screw boss. The run left the middle and the bottom centre empty, so both open."""
    hw = W.HALF_W
    y_in = W.TIE_EAR[0]                                          # top band's lower edge follows the rib's arch
    arch = [(y, rib_z(y) - RIB["w"] / 2) for y in [y_in - k * 2 * y_in / 40 for k in range(41)]]
    top = SPoly([(-hw, W.TOP), (hw, W.TOP), (hw, -22.0), (y_in, -22.0)] + arch + [(-y_in, -22.0), (-hw, -22.0)])
    parts = [top]
    for s in (-1, 1):
        ly0, ly1 = W.RAIL_EAR[1] - MEMBER, W.RAIL_EAR[1]          # legs run straight down behind the lower ears
        parts.append(sbox(min(s * ly0, s * ly1), -110.0, max(s * ly0, s * ly1), -18.0))
        py0, py1 = W.RAIL_EAR[0] - 2.0, W.RAIL_EAR[1] + 2.0        # pads back the lower ears' whole root
        parts.append(sbox(min(s * py0, s * py1), W.BOTTOM, max(s * py0, s * py1), -95.0))
    parts.append(sbox(-W.RAIL_EAR[0], -120.0 - BAR / 2, W.RAIL_EAR[0], -120.0 + BAR / 2))
    parts += [Point(0, z).buffer(BOSS_R, 48) for z in W.SCREW["z"]]
    shape = unary_union(parts)
    shape = shape.buffer(FILLET, 48).buffer(-FILLET, 48)       # fillet every inside corner
    shape = shape.buffer(-ROUND, 48).buffer(ROUND, 48)         # round the outside corners
    assert shape.geom_type == "Polygon" and len(shape.interiors) == 1, "expect one plate with one window"
    return shape


def rib_outline():
    """Arched rib in (y, z): from the inner faces of the upper ears, dipping under the top screw's access."""
    y_in = W.TIE_EAR[0]
    pts = [(y, rib_z(y)) for y in [-y_in + k * 2 * y_in / 40 for k in range(41)]]
    return LineString(pts).buffer(RIB["w"] / 2, 32)


def prism_yz(poly, x0, x1, holes=True):
    with BuildPart() as p:
        with BuildSketch(Plane.YZ.offset(x0)):
            Polygon(*list(poly.exterior.coords)[:-1], align=None)
        extrude(amount=x1 - x0)
    part = p.part
    if holes:
        for r in poly.interiors:
            with BuildPart() as h:
                with BuildSketch(Plane.YZ.offset(x0 - 1)):
                    Polygon(*list(r.coords)[:-1], align=None)
                extrude(amount=x1 - x0 + 2)
            part -= h.part
    return part


def build():
    plate = prism_yz(back_outline(), 0.0, W.BASE_T)
    plate += prism_yz(rib_outline(), W.BASE_T - 0.5, RIB["x1"], holes=False)
    for side in (-1, 1):
        for (zc, slot, span) in ((0.0, 0.0, W.TIE_EAR), (-W.PIVOT_DZ, W.SLOT, W.RAIL_EAR)):
            y0, y1 = sorted((side * span[0], side * span[1]))
            plate += W.prism_xz(W.ear_outline(zc, slot), y0, y1)
    for (zc, slot) in ((0.0, 0.0), (-W.PIVOT_DZ, W.SLOT)):
        plate -= W.prism_xz(W.hole_outline(zc, slot), -W.HALF_W - 1, W.HALF_W + 1)
    for side in (-1, 1):
        for (zc, slot, span) in ((0.0, 0.0, W.TIE_EAR), (-W.PIVOT_DZ, W.SLOT, W.RAIL_EAR)):
            y0, y1 = sorted((side * span[0], side * (span[0] + W.NUT["depth"])))
            plate -= W.prism_xz(W.nut_pocket_outline(zc, slot), y0 - (0.01 if side < 0 else 0), y1 + (0.01 if side > 0 else 0))
    for z in W.SCREW["z"]:
        plate -= Pos(W.BASE_T / 2, 0, z) * Rot(0, 90, 0) * Cylinder(W.SCREW["d"] / 2, W.BASE_T + 2)
        k = W.SCREW["head"] / 2
        plate -= Pos(W.BASE_T - k / 2 + 0.01, 0, z) * Rot(0, 90, 0) * Cone(W.SCREW["d"] / 2 - 0.01, k + 0.01, k)
    for y in (-9.0, 9.0):                                    # cable-tie slots, as v2
        plate -= Pos(W.BASE_T / 2, y, 12.0) * Box(W.BASE_T + 2, 3.0, 6.0)
    return plate


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    part = build()
    bb = part.bounding_box()
    print(f"wall plate v3: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm, volume {part.volume / 1000:.1f} cm3 "
          f"(v2 {W.build().volume / 1000:.1f})")
    export_stl(part, str(OUT / "beacon_wall_plate_v3.stl"))
    export_step(part, str(OUT / "beacon_wall_plate_v3.step"))


if __name__ == "__main__":
    main()
