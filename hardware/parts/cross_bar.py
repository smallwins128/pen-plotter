"""The moving cross bar (the gantry beam).

A length of 2020 spanning Y, riding along the two 1000 mm frame rails on
OpenBuilds gantry plates. The pen carriage runs along it in Y; the whole bar
travels in X.

Datum matches frame.py: origin at the centre of the frame's outer envelope,
Z = 0 at the tabletop. The bar is drawn parked at CROSS_BAR_X (0 = mid-travel).

The gantry plates themselves are NOT modelled yet -- their stack height is the
GANTRY_RISE placeholder in params.py. Every Z dimension above the frame depends
on that number, so measure it before cutting anything.
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from build123d import Pos

from params import (
    ALUMINIUM_DENSITY,
    FRAME_BASE_Z,
    CROSS_BAR_H,
    CROSS_BAR_LEN,
    CROSS_BAR_W,
    CROSS_BAR_X,
    FRAME_OUTER_X,
    FRAME_OUTER_Y,
    GANTRY_PLATE_LEN,
    GANTRY_RISE,
    PROFILE_H,
    PROFILE_W,
)
from profiles import section_moments, tslot_bar

# Young's modulus for aluminium, N/mm^2.
E_ALUMINIUM = 69000.0
G = 9.81


def underside_z():
    """Z of the bottom face of the cross bar."""
    return FRAME_BASE_Z + PROFILE_H + GANTRY_RISE


def support_span():
    """Distance between the two gantry plates, i.e. the supported span.

    The plates sit over the frame rails, so this is the rail centreline
    spacing. Bar length beyond this is overhang, not span.
    """
    return FRAME_OUTER_Y - PROFILE_W


def overhang():
    """How far each end of the bar sticks out past the supported span."""
    return (CROSS_BAR_LEN - support_span()) / 2.0


def x_travel():
    """Usable travel of the bar along X, before end stops."""
    return FRAME_OUTER_X - GANTRY_PLATE_LEN


def deflection(payload_kg=0.4):
    """Mid-span sag of the bar, mm.

    Simply supported over `support_span()`, carrying its own weight as a
    uniform load plus the carriage as a central point load. The overhanging
    ends are ignored -- they reduce mid-span sag slightly, so this is the
    conservative case.
    """
    m = section_moments(CROSS_BAR_W, CROSS_BAR_H)
    ei = E_ALUMINIUM * m["ix"]
    span = support_span()

    udl = m["area"] * ALUMINIUM_DENSITY / 1000.0 * G   # N per mm of length
    self_weight = 5.0 * udl * span**4 / (384.0 * ei)
    point = (payload_kg * G) * span**3 / (48.0 * ei)

    return {"self_weight": self_weight, "payload": point,
            "total": self_weight + point, "ix": m["ix"], "area": m["area"]}


def build():
    bar = Pos(CROSS_BAR_X, 0, underside_z() + CROSS_BAR_H / 2) * tslot_bar(
        CROSS_BAR_LEN, CROSS_BAR_W, CROSS_BAR_H, axis="Y"
    )
    bar.label = "cross_bar"
    return bar


def cut_list():
    return [(1, CROSS_BAR_LEN, f"cross bar ({CROSS_BAR_W:g}x{CROSS_BAR_H:g}, spans Y)")]


def report():
    d = deflection()
    lines = [
        f"span between gantry plates   {support_span():6.1f} mm",
        f"bar length                   {CROSS_BAR_LEN:6.1f} mm",
        f"overhang each end            {overhang():6.1f} mm",
        f"underside sits at Z          {underside_z():6.1f} mm",
        f"X travel (less plate length) {x_travel():6.1f} mm",
        f"section Ix                   {d['ix']:6.0f} mm^4",
        f"sag, self weight             {d['self_weight']:6.3f} mm",
        f"sag, +0.4 kg carriage        {d['payload']:6.3f} mm",
        f"sag, total                   {d['total']:6.3f} mm",
    ]
    return lines


if __name__ == "__main__":
    for line in report():
        print(" ", line)
