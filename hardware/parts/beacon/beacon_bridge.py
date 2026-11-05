"""R06 Beacon: bridge between the two compact arms (Allwin doubled the arm, 2026-10-30).

A printed C. Each lip slots into one arm's 6.4 mm beam gap, in place of the two spacer nuts, and the beam bolt
runs strip | lip | strip. The back runs across under the beams, at 90 deg to them, from one arm to the other.
Two identical bridges go on the beams' 2nd and 3rd holes from the wall (11 and 21 cm).

The arm spacing comes from the tip hangers sharing one 32 cm strip (holes 1+11 and 21+31): 200 mm centre to centre.

    python3 beacon_bridge.py            # writes out/beacon_bridge.stl, .step and _print.stl

Frame: the beam's own frame. x along the beam, y across between the arms (arm centres at y = +/-100), z square to
the beam (up), the bolt axis on the y axis at the origin.
Print: on its side (the C outline flat on the bed), no supports; the bolt holes get a 45 deg roof toward +x.
"""
import pathlib

from build123d import Plane, export_stl, export_step
from shapely.geometry import box as sbox
from shapely.ops import unary_union

from beacon_compact import FIN_T, BOLT, prism, prism_xz, roofed_outline

OUT = pathlib.Path(__file__).resolve().parents[2] / "out" / "beacon"

ARM_PITCH = 200.0              # arm centre to centre
STRIP_H = 15.0                 # strip height (z), the lip fills the gap up to the strips' top edges
DEPTH = 24.0                   # along the beam (x)
BACK_T = 9.0                   # back thickness below the beams
CLEAR = 1.0                    # gap between the strips' bottom edges and the back
FILLET = 5.0


def c_outline():
    """C in (y, z): two lips up into the beam gaps, joined by a back under the beams."""
    half = ARM_PITCH / 2
    zb = -STRIP_H / 2 - CLEAR                                   # back's top face
    back = sbox(-half - FIN_T / 2, zb - BACK_T, half + FIN_T / 2, zb)
    lips = []
    for s in (-1, 1):
        y = s * half
        lips.append(sbox(y - FIN_T / 2, zb - 0.5, y + FIN_T / 2, STRIP_H / 2 - 0.5))   # fills the gap, 0.5 below the top
    # No fillet where a lip meets the back: the strips' bottom edges sit 1 mm above the back there.
    # Round only the back's outer corners.
    back = back.buffer(-3.0, 32).buffer(3.0, 32)
    return unary_union([back, *lips])


def bridge():
    part = prism(c_outline(), Plane.YZ, -DEPTH / 2, DEPTH / 2)
    for s in (-1, 1):
        part -= prism_xz(roofed_outline(0.0, 0.0, 0.0), s * ARM_PITCH / 2 - 10, s * ARM_PITCH / 2 + 10)
    return part


def main():
    import numpy as np, trimesh
    from trimesh.transformations import rotation_matrix
    OUT.mkdir(parents=True, exist_ok=True)
    part = bridge()
    bb = part.bounding_box()
    print(f"bridge: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm, volume {part.volume / 1000:.1f} cm3, "
          f"lips {FIN_T:.1f} thick at +/-{ARM_PITCH / 2:.0f}")
    export_stl(part, str(OUT / "beacon_bridge.stl"))
    export_step(part, str(OUT / "beacon_bridge.step"))
    m = trimesh.load(str(OUT / "beacon_bridge.stl"))           # on its side: -x face down
    m.apply_transform(rotation_matrix(np.radians(-90), [0, 1, 0]))
    m.apply_translation(-m.bounds[0])
    m.export(str(OUT / "beacon_bridge_print.stl"))


if __name__ == "__main__":
    main()
