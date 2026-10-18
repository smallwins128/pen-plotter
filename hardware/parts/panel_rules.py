"""Shared features for every printed panel that screws onto the steel (Allwin's rules, 2026-10-18).

1. Countersunk M3 screws (flat heads sit flush with the panel face).
2. A relief in the panel's back over each rivnut flange, so the panel sits flat on the steel.
3. A 2 mm lip on the back that drops into the steel opening and locates the panel.

Frame: x, y on the wall (u, v of the steel model), z = 0 at the panel's front face, z = PLATE_T at its back (on
the steel), the lip from PLATE_T to PLATE_T + LIP_H. Print face down: the lip and the reliefs end up on top.
"""
import pathlib
import sys

from build123d import Cone, Cylinder, Pos
from shapely.geometry import Point

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fit_kit import FIT  # noqa: E402
from window_inserts import slab  # noqa: E402

PLATE_T = 3.0                         # panel plate
CSK_D, CSK_ANGLE = 6.4, 90.0          # M3 flat head Ø6.0 (ISO 10642 max 6.72; 6.4 keeps a typical head just under flush)
RELIEF_D, RELIEF_H = FIT["rivnut_recess"], 1.2   # rivnut flange Ø8 measured, thickness unmeasured (1.0 assumed) + 0.2
LIP_H, LIP_W, LIP_GAP = 2.0, 2.0, 0.3            # lip into the steel opening: 2 tall, 2 wide, 0.3 per side smaller


def csk_screw(part, x, y):
    """Ø3.4 through + 90° countersink on the front face."""
    part -= Pos(x, y, PLATE_T / 2) * Cylinder(FIT["m3_clear"] / 2, PLATE_T + 2)
    h = (CSK_D - FIT["m3_clear"]) / 2                       # 45° cone
    part -= Pos(x, y, h / 2 - 0.01) * Cone(CSK_D / 2 + 0.01, FIT["m3_clear"] / 2, h + 0.02)
    return part


def rivnut_relief(part, x, y):
    """Flange relief in the back face."""
    return part - Pos(x, y, PLATE_T - RELIEF_H / 2 + 0.01) * Cylinder(RELIEF_D / 2, RELIEF_H + 0.02)


def lip(opening):
    """2 mm locating lip: a frame just inside the steel opening (a shapely polygon in x, y)."""
    outer = opening.buffer(-LIP_GAP, join_style=2)
    ring = outer.difference(outer.buffer(-LIP_W, join_style=2))
    return slab(ring, PLATE_T - 0.01, PLATE_T + LIP_H)


def panel(outline, opening, screws, holes=()):
    """Plate on `outline`, lip in `opening`, countersunk screws + flange reliefs at `screws`, round `holes` [(x, y, d)]."""
    part = slab(outline, 0, PLATE_T) + lip(opening)
    for x, y in screws:
        part = rivnut_relief(csk_screw(part, x, y), x, y)
    for x, y, d in holes:
        part -= Pos(x, y, PLATE_T / 2) * Cylinder(d / 2, PLATE_T + 2)
    return part


def check(outline, opening, screws):
    """Each screw's relief sits inside the plate with 1 mm to spare and clear of the lip."""
    lipzone = opening.buffer(-LIP_GAP, join_style=2)
    out = []
    for x, y in screws:
        r = Point(x, y).buffer(RELIEF_D / 2)
        out.append((x, y, outline.buffer(-1.0).contains(r), not r.intersects(lipzone)))
    return out
