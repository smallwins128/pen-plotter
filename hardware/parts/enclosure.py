"""Electronics enclosure: a 2020 box bolted alongside the machine.

Option B -- its own four uprights rather than sharing the machine's right-hand
rail, so either can be moved without dismantling the other.

What is modelled: the extrusion frame, and every component as a stand-in block
at its real outside dimensions. What is not: stainless covers, the joining
plates to the machine, wiring, and any mounting hardware. The point of this
stage is that the volumes are right and nothing collides -- `check_layout()`
enforces both on every build.

Layout follows the rule we settled on: mains at the far (+X) end, signal at the
machine-facing (-X) end, so 240 V and step/dir never run alongside each other.
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from build123d import Box, Compound, Pos

from params import (
    ENC_FLOOR_Z,
    ENC_GAP,
    ENC_PROFILE,
    ENC_X,
    ENC_Y,
    ENC_Z,
    FRAME_OUTER_X,
)
from profiles import tslot_bar

# name, (w, d, h), (x, y) centre in enclosure-local coords, zone
# Local origin is the centre of the enclosure footprint; z is measured from
# ENC_FLOOR_Z upwards.
COMPONENTS = [
    ("psu_24v_main",  (215, 115, 30), (-80,   75), "the Ender 3 supply, LRS-350-24 class"),
    ("psu_24v_servo", ( 51,  78, 28), ( 80,   95), "RS-25-24, feeds the buck only"),
    ("uno_cnc_shield", (110,  85, 45), (-140, -80), "Uno + CNC Shield V3 + 3x A4988"),
    ("lm2596_buck",   ( 65,  45, 25), (-50, -105), "servo 6.0 V -- keep, do not run servo off 5 V"),
    ("rail_12way_a",  (150,  45, 30), ( 90,  -40), "12-port lever rail"),
    ("rail_12way_b",  (150,  45, 30), ( 90,  -95), "12-port lever rail"),
    ("iec_and_split", ( 90,  60, 40), (155,   30), "panel-mount IEC inlet + mains splitters"),
]


def origin_x():
    """Enclosure centre in machine coordinates, sitting to the right."""
    return FRAME_OUTER_X / 2 + ENC_GAP + ENC_X / 2


def _inner():
    """Half-extents of the usable floor, local coords."""
    return ENC_X / 2 - ENC_PROFILE, ENC_Y / 2 - ENC_PROFILE


def check_layout():
    """Every block inside the frame, and none overlapping another.

    Cheap to run and it has already caught two collisions, so it runs on every
    build rather than being a thing to remember.
    """
    hx, hy = _inner()
    problems = []

    for name, (w, d, _), (x, y), _ in COMPONENTS:
        if abs(x) + w / 2 > hx + 1e-9 or abs(y) + d / 2 > hy + 1e-9:
            problems.append(f"{name} pokes outside the frame")

    for i, (n1, (w1, d1, _), (x1, y1), _) in enumerate(COMPONENTS):
        for n2, (w2, d2, _), (x2, y2), _ in COMPONENTS[i + 1:]:
            if (abs(x1 - x2) < (w1 + w2) / 2 - 1e-9
                    and abs(y1 - y2) < (d1 + d2) / 2 - 1e-9):
                problems.append(f"{n1} overlaps {n2}")

    if problems:
        raise ValueError("enclosure layout: " + "; ".join(problems))


def build_frame():
    """The twelve lengths of 2020: a bottom rectangle, a top one, four uprights."""
    p = ENC_PROFILE
    long_len = ENC_X
    short_len = ENC_Y - 2 * p
    post_len = ENC_Z - 2 * p

    x_off = ENC_X / 2 - p / 2
    y_off = ENC_Y / 2 - p / 2

    bars = []
    for z in (p / 2, ENC_Z - p / 2):
        for y in (-y_off, y_off):
            bars.append(("rail_x", Pos(0, y, z) * tslot_bar(long_len, p, p, axis="X")))
        for x in (-x_off, x_off):
            bars.append(("rail_y", Pos(x, 0, z) * tslot_bar(short_len, p, p, axis="Y")))

    for x in (-x_off, x_off):
        for y in (-y_off, y_off):
            bars.append(("post", Pos(x, y, ENC_Z / 2) * tslot_bar(post_len, p, p, axis="Z")))

    out = []
    for i, (kind, bar) in enumerate(bars):
        bar.label = f"{kind}_{i}"
        out.append(bar)
    return out


def build_components():
    blocks = []
    for name, (w, d, h), (x, y), _ in COMPONENTS:
        b = Pos(x, y, ENC_FLOOR_Z + h / 2) * Box(w, d, h)
        b.label = name
        blocks.append(b)
    return blocks


def build():
    check_layout()
    parts = build_frame() + build_components()
    asm = Compound(children=parts)
    asm.label = "enclosure"
    return Pos(origin_x(), 0, 0) * asm


def cut_list():
    p = ENC_PROFILE
    return [
        (4, ENC_X, f"enclosure long rail ({p:g}x{p:g})"),
        (4, ENC_Y - 2 * p, f"enclosure short rail ({p:g}x{p:g})"),
        (4, ENC_Z - 2 * p, f"enclosure upright ({p:g}x{p:g})"),
    ]


def report():
    hx, hy = _inner()
    used = sum(w * d for _, (w, d, _), _, _ in COMPONENTS)
    lines = [
        f"enclosure        {ENC_X:.0f} x {ENC_Y:.0f} x {ENC_Z:.0f} mm outer",
        f"usable floor     {2*hx:.0f} x {2*hy:.0f} mm",
        f"floor used       {used/100:.0f} cm^2  ({used/(4*hx*hy)*100:.0f}%)",
        f"sits at X        {origin_x()-ENC_X/2:+.0f} .. {origin_x()+ENC_X/2:+.0f} mm",
        "",
        "contents:",
    ]
    for name, (w, d, h), (x, y), note in COMPONENTS:
        lines.append(f"  {name:16s} {w:3.0f} x {d:3.0f} x {h:3.0f}  at ({x:+4.0f}, {y:+4.0f})  {note}")
    return lines


if __name__ == "__main__":
    check_layout()
    for line in report():
        print(" ", line)


def build_frame_positioned():
    """Just the extrusion, in machine coordinates -- for separate viewer toggles."""
    c = Compound(children=build_frame())
    c.label = "enclosure_frame"
    return Pos(origin_x(), 0, 0) * c


def build_components_positioned():
    """Just the component blocks, in machine coordinates."""
    check_layout()
    c = Compound(children=build_components())
    c.label = "enclosure_components"
    return Pos(origin_x(), 0, 0) * c
