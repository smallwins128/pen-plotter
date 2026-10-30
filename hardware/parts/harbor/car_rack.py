"""R05 Harbor: Hot Wheels rack on the SKÅDIS rail system (2026-10-30). Plan: Harbor Plans, Car rack.

Allwin's wood strips (300 x 35 x 6, not cut true) are the shelves. Each strip rests in the ledges of two BRACKETS
(rail-system plates on hooks 160 apart) and carries four SLIDERS dropped on from above: one at each end and two
between, so three 60 mm flats. A slider is a low ridge (25 deg ramps, so a car's overhang clears it) with tyre
grooves where the wheels sit, and short legs over the strip's front and back edges; each car sits in the dip between
two ridges. Car 75 x 32 x 35 is an estimate. Nothing grips the wood: 1 mm or more of slack everywhere.

    python3 car_rack.py       # writes out/harbor/car_bracket*.stl, car_slider*.stl, bed_car_rack.3mf/.stl

Frame as in skadis_rail.py (x along the board, y out of it, z up, hook bottom z = 0).
Print: both as modelled. Bracket upright (ledge and lip on the bed); slider standing on its legs, the top bridging
the strip's width (≈ 43 mm) under the ridge.
"""
import math

from build123d import export_step, export_stl

from skadis_rail import BOSS, OUT, PLATE_T, Y_BODY, board_piece, box, hook, plate, prism_xy, prism_yz
from skadis_plates import Z0, Z_ROOF, write_bed

STRIP = dict(w=35.0, t=6.0)          # Allwin's strips, nominal; real ones vary
SLACK = 1.5                          # per side, strip in the ledge and in the saddle
LEDGE, LIP, LIP_T = 4.0, 3.0, 2.0    # ledge floor, lip height over the strip top, lip thickness
SLIDER = dict(base=30.0, slope=25.0, top=2.0, leg=3.0, leg_h=4.0, slack=1.0, track=22.0, groove=7.0, groove_d=1.2)
BRACKET_X = 80.0                     # brackets on hooks at +-80 (160 apart); sliders at +-45 and +-135 clear them
SLIDER_X = (-135.0, -45.0, 45.0, 135.0)
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


def slider():
    """Use frame, centred on the strip: x along it, y across it (strip centre y = 0), z = 0 on the strip's top face.
    A ridge along y with 25 deg ramps toward each bay, on a 2 mm top plate; legs hang 4 mm over the strip's front
    and back edges. Tyre grooves run down both ramps where a car's wheels sit (track estimated at 22)."""
    sl = SLIDER
    half_in = STRIP["w"] / 2 + sl["slack"]
    half_out = half_in + sl["leg"]
    hb = sl["base"] / 2
    h = hb * math.tan(math.radians(sl["slope"]))
    ridge = [(-hb, sl["top"] - 0.1), (hb, sl["top"] - 0.1), (0.0, sl["top"] + h)]
    part = box(-hb, hb, -half_out, half_out, 0, sl["top"])
    for y0 in (-half_out, half_in):
        part += box(-hb, hb, y0, y0 + sl["leg"], -sl["leg_h"], 0.1)
    part += prism_xz_y(ridge, -half_out, half_out)
    d = sl["groove_d"]
    sunk = [(x, z - d) for x, z in ridge]
    for yc in (-sl["track"] / 2, sl["track"] / 2):
        y0, y1 = yc - sl["groove"] / 2, yc + sl["groove"] / 2
        part -= prism_xz_y(ridge, y0, y1) - prism_xz_y(sunk, y0 - 1, y1 + 1)       # the ramp's skin, d deep
    return part


def prism_xz_y(pts, y0, y1):
    """Outline in (x, z), extruded along y from y0 to y1."""
    from build123d import BuildPart, BuildSketch, Plane, Polygon, extrude
    with BuildPart() as p:
        with BuildSketch(Plane.XZ.offset(-y0)):
            Polygon(*pts, align=None)
        extrude(amount=-(y1 - y0))
    return p.part


def main():
    import numpy as np, trimesh
    from trimesh.transformations import rotation_matrix
    OUT.mkdir(parents=True, exist_ok=True)
    meshes = {}
    for name, part in (("car_bracket", bracket()), ("car_slider", slider()), ("_hook", hook())):
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
    items += [("car_slider", meshes["car_slider"].copy()) for _ in range(4 * STRIPS)]
    items += [("hook", meshes["_hook"].copy()) for _ in range(2 * STRIPS)]
    write_bed("bed_car_rack", items)
    export_stl(board_piece(-190, 190, -110, 75), str(OUT / "skadis_board_car.stl"))     # for the inspector


if __name__ == "__main__":
    main()
