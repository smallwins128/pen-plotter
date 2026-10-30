"""R05 Harbor: Hot Wheels rack on the SKÅDIS rail system (2026-10-30). Plan: Harbor Plans, Car rack.

Allwin's wood strips (300 x 35 x 6, not cut true) are the shelves. Each strip rests in the ledges of two BRACKETS
(rail-system plates on hooks 240 apart, 30 mm overhang each end) and carries four SADDLES that slide on from its ends:
one at each end and two between, so three bays of about 90 mm for cars of about 75 (estimate). Nothing grips the
wood: the ledge and the saddle tunnel leave 1.5 mm or more of slack.

    python3 car_rack.py       # writes out/harbor/car_bracket*.stl, car_saddle*.stl, bed_car_rack.3mf/.stl

Frame as in skadis_rail.py (x along the board, y out of it, z up, hook bottom z = 0).
Print: bracket upright as modelled (ledge and lip on the bed); saddle lying on its fin, the tunnel rising from it.
"""
from build123d import export_step, export_stl

from skadis_rail import BOSS, OUT, PLATE_T, Y_BODY, box, hook, plate, prism_xy
from skadis_plates import Z0, Z_ROOF, write_bed

STRIP = dict(w=35.0, t=6.0)          # Allwin's strips, nominal; real ones vary
SLACK = 1.5                          # per side, strip in the ledge and in the saddle
LEDGE, LIP, LIP_T = 4.0, 3.0, 2.0    # ledge floor, lip height over the strip top, lip thickness
SADDLE = dict(len=10.0, wall=1.6, fin=2.0, fin_h=25.0)
Y_F = Y_BODY + PLATE_T
BRACKET_W = 36.0
STRIPS = 2


def bracket():
    """One sleeve column; a ledge on the bed the strip rests on, a lip in front that stands 3 mm over its top."""
    d = STRIP["w"] + 2 * SLACK
    part = plate([0.0], BOSS["w"], Z0, Z_ROOF, strip=4.0)
    part += box(-BRACKET_W / 2, BRACKET_W / 2, Y_F - 0.1, Y_F + d + LIP_T, Z0, Z0 + LEDGE)
    part += box(-BRACKET_W / 2, BRACKET_W / 2, Y_F + d, Y_F + d + LIP_T, Z0, Z0 + LEDGE + STRIP["t"] + LIP)
    return part


def saddle():
    """Modelled in print position: the fin lies on the bed (x-y plane = the divider), the tunnel rises SADDLE len
    from it around the strip. On the strip, the fin stands up across it and the tunnel slides along it."""
    iw, ih, t = STRIP["w"] + 2 * SLACK + 0.5, STRIP["t"] + 1.5, SADDLE["wall"]
    ow, oh = iw + 2 * t, ih + 2 * t
    outer = [(-ow / 2, 0), (ow / 2, 0), (ow / 2, oh), (-ow / 2, oh)]
    part = prism_xy(outer, 0, SADDLE["len"])                                             # tunnel
    part += prism_xy([(-ow / 2, 0), (ow / 2, 0), (ow / 2, oh + SADDLE["fin_h"]), (-ow / 2, oh + SADDLE["fin_h"])],
                     0, SADDLE["fin"])                                                   # fin, on the bed
    part -= prism_xy([(-iw / 2, t), (iw / 2, t), (iw / 2, t + ih), (-iw / 2, t + ih)], -1, SADDLE["len"] + 1)
    return part


def main():
    import numpy as np, trimesh
    from trimesh.transformations import rotation_matrix
    OUT.mkdir(parents=True, exist_ok=True)
    meshes = {}
    for name, part in (("car_bracket", bracket()), ("car_saddle", saddle()), ("_hook", hook())):
        bb = part.bounding_box()
        if not name.startswith("_"):
            print(f"{name}: {bb.size.X:.0f} x {bb.size.Y:.0f} x {bb.size.Z:.0f} mm, about {part.volume / 1000 * 1.24:.1f} g PLA solid")
            export_step(part, str(OUT / f"{name}.step"))
        export_stl(part, str(OUT / f"{name}.stl"))
        m = trimesh.load(str(OUT / f"{name}.stl"))
        m.apply_translation(-m.bounds[0])
        if not name.startswith("_"):
            m.export(str(OUT / f"{name}_print.stl"))
        meshes[name] = m
    (OUT / "_hook.stl").unlink()
    turn = rotation_matrix(np.radians(90), [0, 0, 1])          # thin walls along the A1's bed travel
    items = [("car_bracket", meshes["car_bracket"].copy().apply_transform(turn)) for _ in range(2 * STRIPS)]
    items += [("car_saddle", meshes["car_saddle"].copy()) for _ in range(4 * STRIPS)]
    items += [("hook", meshes["_hook"].copy()) for _ in range(2 * STRIPS)]
    write_bed("bed_car_rack", items)


if __name__ == "__main__":
    main()
