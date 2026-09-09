"""The base deck: a steel sheet across the frame footprint.

Laid on the tabletop, with the frame bolted down on top of it through drop-in
T-nuts in the rails' bottom slot. Clearance holes sit on the four rail
centrelines.

WHAT THIS SHEET DOES AND DOES NOT DO

It does not make anything flat by itself. A thin sheet has almost no flexural
rigidity: `plate_sag()` puts a 1.5 mm sheet spanning the 960 x 560 mm frame
opening at ~13 mm of sag under nothing but its own weight, and you would need
roughly 8 mm of plate -- 33 kg of it -- before the span held itself within half
a millimetre. So the sheet must be continuously supported by the tabletop; it
inherits the tabletop's flatness rather than improving on it.

What it does buy is a hard, uniform, non-absorbent writing surface that will
not dent under a pen or swell with humidity the way particleboard does, it
protects the tabletop, and -- if the steel is ferritic -- it lets magnets hold
the paper down. Austenitic stainless (304, 316) is not meaningfully magnetic;
430 stainless or zinc-plated mild steel is.
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from build123d import BuildPart, BuildSketch, Circle, Locations, Mode, Rectangle, extrude

from params import (
    DECK_EDGE_MARGIN,
    DECK_HOLE_D,
    DECK_HOLE_PITCH,
    DECK_T,
    DECK_X,
    DECK_Y,
    FRAME_OUTER_X,
    FRAME_OUTER_Y,
    PROFILE_W,
    STEEL_DENSITY,
    STEEL_E,
    STEEL_NU,
)

G = 9.81

DENSITY = STEEL_DENSITY   # not aluminium
LINEAR_STOCK = False      # a sheet, not lengths of bar

# Timoshenko coefficients for a uniformly loaded rectangular plate, simply
# supported on all four edges: w_max = alpha * q * b^4 / D, b the short side.
_ALPHA = {1.0: 0.04062, 1.2: 0.05383, 1.4: 0.06377, 1.6: 0.07038,
          1.8: 0.07454, 2.0: 0.07705, 3.0: 0.08019, 99.0: 0.08333}


def _alpha(ratio):
    keys = sorted(_ALPHA)
    if ratio <= keys[0]:
        return _ALPHA[keys[0]]
    for lo, hi in zip(keys, keys[1:]):
        if lo <= ratio <= hi:
            return _ALPHA[lo] + (ratio - lo) / (hi - lo) * (_ALPHA[hi] - _ALPHA[lo])
    return _ALPHA[keys[-1]]


def plate_sag(t=None, a=None, b=None):
    """Mid-span sag of an UNSUPPORTED sheet under its own weight, mm.

    This is the case to avoid, not the case to build. It is here so the
    reason the sheet needs continuous support is a number rather than an
    assertion.
    """
    t = DECK_T if t is None else t
    a = (FRAME_OUTER_X - 2 * PROFILE_W) if a is None else a
    b = (FRAME_OUTER_Y - 2 * PROFILE_W) if b is None else b
    if a < b:
        a, b = b, a

    rigidity = STEEL_E * t**3 / (12 * (1 - STEEL_NU**2))
    load = t * STEEL_DENSITY / 1000.0 * G          # N/mm^2 of self weight
    return _alpha(a / b) * load * b**4 / rigidity


def _spread(length, margin, pitch):
    """Hole positions along a centreline, evenly spread about zero."""
    usable = length - 2 * margin
    n = max(2, round(usable / pitch) + 1)
    step = usable / (n - 1)
    return [-usable / 2 + i * step for i in range(n)]


def hole_positions():
    """(x, y) of every clearance hole, on the four rail centrelines."""
    x_line = FRAME_OUTER_Y / 2 - PROFILE_W / 2      # front / back rail centreline
    y_line = FRAME_OUTER_X / 2 - PROFILE_W / 2      # left / right rail centreline

    holes = []
    for x in _spread(FRAME_OUTER_X, DECK_EDGE_MARGIN, DECK_HOLE_PITCH):
        holes += [(x, -x_line), (x, x_line)]

    # The side rails only span between the front and back rails, so their holes
    # have to stay inside that, clear of the corner joints.
    side_len = FRAME_OUTER_Y - 2 * PROFILE_W
    for y in _spread(side_len, DECK_EDGE_MARGIN, DECK_HOLE_PITCH):
        holes += [(-y_line, y), (y_line, y)]

    return holes


def build():
    with BuildPart() as deck:
        with BuildSketch():
            Rectangle(DECK_X, DECK_Y)
            with Locations(*hole_positions()):
                Circle(DECK_HOLE_D / 2, mode=Mode.SUBTRACT)
        extrude(amount=DECK_T)

    part = deck.part
    part.label = "deck"
    return part


def cut_list():
    return [(1, DECK_X, f"base deck, {DECK_T:g} mm steel sheet ({DECK_X:g} x {DECK_Y:g})",
             "sheet")]


def mass():
    return DECK_X * DECK_Y * DECK_T * STEEL_DENSITY / 1000.0


def report():
    holes = hole_positions()
    return [
        f"sheet                        {DECK_X:.0f} x {DECK_Y:.0f} x {DECK_T:g} mm",
        f"mass                         {mass():6.2f} kg",
        f"clearance holes              {len(holes):4d} x M{DECK_HOLE_D - 0.5:g} ({DECK_HOLE_D:g} mm)",
        f"writing surface at Z         {DECK_T:6.2f} mm",
        "",
        "unsupported sag over the frame opening (the case to AVOID):",
    ] + [
        f"  {t:>4.1f} mm sheet             {plate_sag(t):6.1f} mm"
        for t in (1.0, 1.5, 2.0, 3.0)
    ]


if __name__ == "__main__":
    for line in report():
        print(" ", line)
