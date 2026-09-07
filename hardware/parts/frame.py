"""The outer extrusion frame.

A rectangle of 2040 sitting on the LINNMON tabletop, sized to the tabletop's
100 x 60 cm footprint. This is the datum everything else on the machine hangs
off, so it is the first thing modelled.

Datum: origin at the centre of the outer envelope in X and Y, with Z = 0 at the
tabletop surface. The rails sit at FRAME_BASE_Z, which is the thickness of the
base deck they stand on. Orientation matches the README -- +X right, +Y away
from you, standing in front of the table.

Joinery: butt joints. The rails running along the long axis are full length and
the other pair fits between them, which is what corner brackets or end-tapped
M5s want. Nothing is modelled for the brackets themselves yet.
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from build123d import Compound, Pos

from params import (
    FRAME_BASE_Z,
    FRAME_JOINT,
    FRAME_LONG_RAILS_ALONG_X,
    FRAME_OUTER_X,
    FRAME_OUTER_Y,
    PROFILE_H,
    PROFILE_W,
)
from profiles import tslot_bar


def rail_lengths():
    """(x_rail_length, y_rail_length) for the configured joinery."""
    if FRAME_JOINT != "butt":
        raise NotImplementedError(f"joint style {FRAME_JOINT!r} is not modelled yet")

    if FRAME_LONG_RAILS_ALONG_X:
        return FRAME_OUTER_X, FRAME_OUTER_Y - 2 * PROFILE_W
    return FRAME_OUTER_X - 2 * PROFILE_W, FRAME_OUTER_Y


def cut_list():
    """What to actually cut, as (quantity, length_mm, label) rows."""
    x_len, y_len = rail_lengths()
    return [
        (2, x_len, "front / back rail (runs along X)"),
        (2, y_len, "left / right rail (runs along Y)"),
    ]


def build():
    """The frame as a Compound of four named rails."""
    x_len, y_len = rail_lengths()

    # Rails are centred on their own axis, so offset to the wall centreline and
    # lift so the underside sits on Z = 0.
    y_off = FRAME_OUTER_Y / 2 - PROFILE_W / 2
    x_off = FRAME_OUTER_X / 2 - PROFILE_W / 2
    z_off = FRAME_BASE_Z + PROFILE_H / 2

    rails = []
    for name, length, axis, pos in (
        ("rail_front", x_len, "X", (0, -y_off, z_off)),
        ("rail_back", x_len, "X", (0, y_off, z_off)),
        ("rail_left", y_len, "Y", (-x_off, 0, z_off)),
        ("rail_right", y_len, "Y", (x_off, 0, z_off)),
    ):
        bar = Pos(*pos) * tslot_bar(length, PROFILE_W, PROFILE_H, axis=axis)
        bar.label = name
        rails.append(bar)

    frame = Compound(children=rails)
    frame.label = "frame"
    return frame


if __name__ == "__main__":
    part = build()
    bb = part.bounding_box()
    print(f"frame bbox: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm")
    for qty, length, label in cut_list():
        print(f"  {qty} x {length:7.1f} mm  {label}")
