"""The bench top the machine stands on.

Only the top surface is modelled. Nothing mounts to the legs, and the deck
rests on this face, so the top is the only part that carries a dimension
anything else depends on.

The machine sits hard against the left end, so the free area to the right is
where the electronics live. `free_zone()` reports it.
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from build123d import BuildPart, BuildSketch, Pos, Rectangle, extrude

from params import (  # noqa: F401  -- re-exported for the viewer payload
    FRAME_OUTER_X,
    FRAME_OUTER_Y,
    TABLE_MACHINE_AT_LEFT,
    TABLE_T,
    TABLE_X,
    TABLE_Y,
)


def x_bounds():
    """(min, max) X of the table top, in the machine's coordinate system.

    The machine is centred on the origin, so pushing it to the left end of the
    table means the table reaches much further in +X than -X.
    """
    if TABLE_MACHINE_AT_LEFT:
        left = -FRAME_OUTER_X / 2
        return left, left + TABLE_X
    return -TABLE_X / 2, TABLE_X / 2


def free_zone():
    """The clear area beside the machine: (x_min, x_max, width, depth)."""
    _, right = x_bounds()
    machine_right = FRAME_OUTER_X / 2
    return machine_right, right, right - machine_right, TABLE_Y


def overhang_y():
    """How far the machine sticks out past the table front/back, per side.

    Negative means the machine sits inside the table.
    """
    return (FRAME_OUTER_Y - TABLE_Y) / 2


def build():
    lo, hi = x_bounds()

    with BuildPart() as top:
        with BuildSketch(Pos((lo + hi) / 2, 0, 0)):
            Rectangle(TABLE_X, TABLE_Y)
        extrude(amount=-TABLE_T)      # top face at Z = 0, so the deck sits on it

    part = top.part
    part.label = "table"
    return part


def report():
    lo, hi = x_bounds()
    x0, x1, w, d = free_zone()
    return [
        f"table top            {TABLE_X:.0f} x {TABLE_Y:.0f} x {TABLE_T:g} mm",
        f"spans X              {lo:+.0f} .. {hi:+.0f} mm",
        f"machine occupies X   {-FRAME_OUTER_X/2:+.0f} .. {FRAME_OUTER_X/2:+.0f} mm",
        f"free zone            X {x0:+.0f} .. {x1:+.0f}  =  {w:.0f} x {d:.0f} mm",
        f"machine overhang Y   {overhang_y():+.1f} mm each side",
    ]


if __name__ == "__main__":
    for line in report():
        print(" ", line)
