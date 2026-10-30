"""R06 Beacon: rigid batten clip (replaces the stock T5 spring clips, which let the batten fold; 2026-10-31).

A thick PLA clip can't spring open like the steel one (its 9 mm legs would strain far past PLA's limit), so this is
a two-part clamp. The BASE screws up into the crossbar strip with the stock 3.8 mm countersunk screw and carries a
fixed tooth on one side. The JAW carries the other tooth and slides across on the base; an M4 x 12 down through the
base's slot into the jaw's nut locks it. Hook the batten's rail on the fixed tooth, push the jaw in, tighten.

The rail profile is copied from the stock clip (Allwin's photo of the T5 bracket): 25.5 across where it meets the
clip's base, pinched to about 20 at the wave, 9 tall, opening to 24.5 at the lips. Groove depth is read off the
clip, not measured on the batten: print one pair and test-fit first.

    python3 beacon_batten_clip.py       # writes out/beacon_clip_base*.stl, out/beacon_clip_jaw*.stl

Frame: x across the batten, y along it, z up; the rail's top face (against the base) at z = 0, rail centre x = 0.
Print: both parts on their side (the x-z outline flat on the bed), no supports.
"""
import pathlib

from build123d import Box, Cone, Cylinder, Plane, Pos, Rot, export_stl, export_step
from shapely.geometry import Polygon as SPoly, box as sbox
from shapely.ops import unary_union

from beacon_compact import prism

OUT = pathlib.Path(__file__).resolve().parents[2] / "out" / "beacon"

RAIL = dict(top=25.5, throat=20.0, depth=9.0, wave_z=-4.5)   # from the stock clip
CLR = 0.3                          # per side, between the teeth and the rail
WIDTH = 20.0                       # along the batten (y); stock clip is 9-11
BASE_T = 5.0                       # base plate above the rail
WALL = 4.0                         # tooth arm thickness outside the rail
TOOTH = dict(h=3.0)                # tooth height (z) at the wave
SLOT = dict(len=6.0, x=19.0)       # jaw bolt slot in the base, along x, centred at x = +19
SCREW = dict(d=4.2, head=7.6)      # stock 3.8 mm CSK screw into the crossbar

HALF = RAIL["top"] / 2 + CLR       # inner face of each arm
TIP = RAIL["throat"] / 2 + CLR     # tooth tip


def arm_outline(s):
    """One side's arm in (x, z): straight down outside the rail, a tooth into the wave groove."""
    x_in, x_out = s * HALF, s * (HALF + WALL)
    arm = sbox(min(x_in, x_out), -RAIL["depth"], max(x_in, x_out), 0.0)
    z0 = RAIL["wave_z"]
    tooth = SPoly([(x_in, z0 + TOOTH["h"] / 2 + 1.5), (s * TIP, z0 + TOOTH["h"] / 2 * 0.3),
                   (s * TIP, z0 - TOOTH["h"] / 2 * 0.3), (x_in, z0 - TOOTH["h"] / 2 - 1.5)])
    return unary_union([arm, tooth])


def base_outline():
    """Base in (x, z): plate over the rail, reaching right to carry the jaw's slot; fixed arm on the left (-x)."""
    plate = sbox(-(HALF + WALL), 0.0, SLOT["x"] + SLOT["len"] / 2 + 6.0, BASE_T)
    return unary_union([plate, arm_outline(-1)]).buffer(-0.8, 16).buffer(0.8, 16)


def jaw_outline():
    """Jaw in (x, z): the right arm plus a block up beside the base's slot; it sits under the base's right end."""
    block = sbox(HALF, -RAIL["depth"], SLOT["x"] + SLOT["len"] / 2 + 6.0, -0.4)   # 0.4 under the base: it slides
    return unary_union([block, arm_outline(1)]).buffer(-0.8, 16).buffer(0.8, 16)


def base():
    part = prism(base_outline(), Plane.XZ, -WIDTH / 2, WIDTH / 2)
    part -= Pos(0, 0, BASE_T / 2) * Cylinder(SCREW["d"] / 2, BASE_T + 2)          # crossbar screw, CSK from below
    part -= Pos(0, 0, SCREW["head"] / 4 - 0.01) * Rot(180, 0, 0) * Cone(SCREW["d"] / 2, SCREW["head"] / 2, SCREW["head"] / 2)
    part -= Pos(SLOT["x"], 0, BASE_T / 2) * (Box(SLOT["len"], 4.4, BASE_T + 2) +
                                             Pos(SLOT["len"] / 2, 0, 0) * Cylinder(2.2, BASE_T + 2) +
                                             Pos(-SLOT["len"] / 2, 0, 0) * Cylinder(2.2, BASE_T + 2))
    return part


def jaw():
    part = prism(jaw_outline(), Plane.XZ, -WIDTH / 2, WIDTH / 2)
    part -= Pos(SLOT["x"], 0, -RAIL["depth"] / 2) * Cylinder(2.2, RAIL["depth"] + 2)  # M4 up from the base
    part -= Pos(SLOT["x"], 0, -RAIL["depth"] + 3.0) * Box(7.4, 30, 3.4)               # nut slot, open both sides
    return part


def main():
    import numpy as np, trimesh
    from trimesh.transformations import rotation_matrix
    OUT.mkdir(parents=True, exist_ok=True)
    for name, part in (("beacon_clip_base", base()), ("beacon_clip_jaw", jaw())):
        bb = part.bounding_box()
        print(f"{name}: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm, volume {part.volume / 1000:.2f} cm3")
        export_stl(part, str(OUT / f"{name}.stl"))
        export_step(part, str(OUT / f"{name}.step"))
        m = trimesh.load(str(OUT / f"{name}.stl"))
        m.apply_transform(rotation_matrix(np.radians(90), [1, 0, 0]))          # on its side: x-z outline flat
        m.apply_translation(-m.bounds[0])
        m.export(str(OUT / f"{name}_print.stl"))


if __name__ == "__main__":
    main()
