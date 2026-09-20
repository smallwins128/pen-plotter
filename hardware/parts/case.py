"""Electronics case: a UN4020 hard carry case beside the machine.

Replaces the extrusion enclosure. Moulded polypropylene, sits flat on the
bench, and runs CLOSED -- which is why the fans are not optional: three TB6600
heatsinks hang fin-down in still air otherwise.

Split of contents, settled with the packing numbers:

    base   the two 24 V supplies, both bucks, the three terminal buses, the
           IEC inlet and the two fans          -- heavy things, low down
    lid    the control board and three TB6600s -- they hang from the lid
           ceiling, with the panel connectors directly above them

Only power crosses the hinge. Putting the connectors on the base instead would
send every signal wire across it, which is worse.

Not modelled: wiring, the sub-plate the lid parts really want to mount to, the
switches, or the moulded detail of the shell itself (handle, latches, hinge).
The shell here is a plain clamshell at the published cavity and external sizes.
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from build123d import Box, Compound, Mode, Pos

from params import (
    CASE_BASE_DEPTH,
    CASE_EXT,
    CASE_GAP,
    CASE_INT,
    CASE_LID_DEPTH,
    CASE_WALL_Z,
    FAN_SIZE,
    FAN_THICK,
    FRAME_OUTER_X,
)

# Local origin: centre of the case footprint, Z = 0 at the bench.
# X is the short axis (277 cavity), Y the long one (400 cavity).
CAVITY_Z0 = CASE_WALL_Z
CAVITY_Z1 = CASE_WALL_Z + CASE_INT[2]
LID_CEILING = CAVITY_Z1
SPLIT_Z = CAVITY_Z0 + CASE_BASE_DEPTH

# name, (w, d, h), (x, y), material, note
# PSUs down the -X side, distribution down the +X side, mains in the -Y corner
# clear of the intake fan.
BASE_PARTS = [
    ("psu_24v_main",  (115, 215, 30), ( -70,  -60), "steel", "LRS-350-24, ex-Ender 3"),
    ("psu_24v_servo", ( 51,  78, 28), ( -95,  140), "steel", "RS-25-24"),
    ("bus_24v",       ( 25, 150, 30), (  50,  -60), "abs",   "24 V terminal bus"),
    ("bus_5v",        ( 25, 150, 30), (  85,  -60), "abs",   "5 V terminal bus"),
    ("bus_ground",    ( 25, 150, 30), ( 120,  -60), "abs",   "ground terminal bus"),
    ("buck_5v",       ( 45,  65, 25), ( 110,   90), "pcb",   "24 -> 5 V, logic"),
    ("buck_servo",    ( 45,  65, 25), ( 110,  160), "pcb",   "24 -> 6.0 V, MG996R"),
    ("iec_inlet",     ( 50,  30, 30), (  95, -180), "abs",   "panel-mount IEC, 220 V in"),
]

# TB6600: 96.5 flange to flange, 67.7 deep over the terminals, 57 tall.
TB6600 = (96.5, 67.7, 57.0)

LID_PARTS = [
    ("tb6600_x1",   TB6600,          (-50,  -90), "steel", "stepper driver"),
    ("tb6600_x2",   TB6600,          (-50,    0), "steel", "stepper driver"),
    ("tb6600_y",    TB6600,          (-50,   90), "steel", "stepper driver"),
    ("elecrow_6x", (100, 100, 25),   ( 70,    0), "pcb",   "6-axis board -- SIZE IS A PLACEHOLDER"),
]

# 3x GX16-5 steppers, 2x GX16-3 endstops, 1x GX16-4 servo, 1x USB-C.
PANEL = [
    ("gx16_5_x1",   16, ( 95, -150), "stepper, 4 wires + shield"),
    ("gx16_5_x2",   16, ( 95, -100), "stepper, 4 wires + shield"),
    ("gx16_5_y",    16, ( 95,  -50), "stepper, 4 wires + shield"),
    ("gx16_3_endstop_x", 16, ( 95,   0), "endstop"),
    ("gx16_3_endstop_y", 16, ( 95,  50), "endstop"),
    ("gx16_4_servo",     16, ( 95, 100), "servo"),
    ("usb_c",            14, ( 95, 150), "panel-mount USB-C to the board"),
]

FANS = [
    ("fan_intake",  (0, -(CASE_INT[1] / 2 - FAN_THICK / 2)), "intake, filtered"),
    ("fan_exhaust", (0,  (CASE_INT[1] / 2 - FAN_THICK / 2)), "exhaust"),
]


def origin_x():
    return FRAME_OUTER_X / 2 + CASE_GAP + CASE_EXT[0] / 2


def _half_cavity():
    return CASE_INT[0] / 2, CASE_INT[1] / 2


def check_layout():
    """Nothing outside the cavity, nothing overlapping its neighbours."""
    hx, hy = _half_cavity()
    problems = []

    # Fans stand on the base floor like anything else, so they take part in the
    # collision check rather than being drawn in afterwards and hoped for.
    fan_parts = [(n, (FAN_SIZE, FAN_THICK, FAN_SIZE), xy, "abs", note)
                 for n, xy, note in FANS]

    for bay, parts in (("base", BASE_PARTS + fan_parts), ("lid", LID_PARTS)):
        for name, (w, d, h), (x, y), _, _ in parts:
            if abs(x) + w / 2 > hx + 1e-9 or abs(y) + d / 2 > hy + 1e-9:
                problems.append(f"{name} outside the cavity")
            if h > CASE_BASE_DEPTH + 1e-9:
                problems.append(f"{name} is {h:g} mm, deeper than the {CASE_BASE_DEPTH:g} mm bay")

        for i, (n1, (w1, d1, _), (x1, y1), _, _) in enumerate(parts):
            for n2, (w2, d2, _), (x2, y2), _, _ in parts[i + 1:]:
                if (abs(x1 - x2) < (w1 + w2) / 2 - 1e-9
                        and abs(y1 - y2) < (d1 + d2) / 2 - 1e-9):
                    problems.append(f"{n1} overlaps {n2} in the {bay}")

    if problems:
        raise ValueError("case layout: " + "; ".join(problems))


def build_shell():
    """Base tray and lid, as two hollow clamshell halves."""
    ex, ey, _ = CASE_EXT
    ix, iy, _ = CASE_INT

    base_h = CASE_WALL_Z + CASE_BASE_DEPTH
    base = Pos(0, 0, base_h / 2) * Box(ex, ey, base_h)
    base -= Pos(0, 0, CAVITY_Z0 + CASE_BASE_DEPTH / 2) * Box(ix, iy, CASE_BASE_DEPTH)
    base.label = "case_base"

    lid_h = CASE_EXT[2] - base_h
    lid = Pos(0, 0, base_h + lid_h / 2) * Box(ex, ey, lid_h)
    lid -= Pos(0, 0, SPLIT_Z + CASE_BASE_DEPTH / 2) * Box(ix, iy, CASE_BASE_DEPTH)
    lid.label = "case_lid"

    return [base, lid]


def build_parts(material=None):
    """Contents of both bays. Base parts stand on the floor, lid parts hang."""
    out = []
    for name, (w, d, h), (x, y), mat, _ in BASE_PARTS:
        if material and mat != material:
            continue
        b = Pos(x, y, CAVITY_Z0 + h / 2) * Box(w, d, h)
        b.label = name
        out.append(b)

    for name, (w, d, h), (x, y), mat, _ in LID_PARTS:
        if material and mat != material:
            continue
        b = Pos(x, y, LID_CEILING - h / 2) * Box(w, d, h)
        b.label = name
        out.append(b)
    return out


def build_fans():
    out = []
    for name, (x, y), _ in FANS:
        f = Pos(x, y, CAVITY_Z0 + FAN_SIZE / 2) * Box(FAN_SIZE, FAN_THICK, FAN_SIZE)
        f.label = name
        out.append(f)
    return out


def build_panel():
    """Connector bodies in the lid's top face, sticking up."""
    out = []
    for name, dia, (x, y), _ in PANEL:
        c = Pos(x, y, CASE_EXT[2] + 6) * Box(dia, dia, 24)
        c.label = name
        out.append(c)
    return out


def _at(parts, label):
    c = Compound(children=parts)
    c.label = label
    return Pos(origin_x(), 0, 0) * c


def build():
    check_layout()
    return _at(build_shell() + build_parts() + build_fans() + build_panel(), "case")


def shell_positioned():
    return _at(build_shell(), "case_shell")


def parts_positioned(material=None):
    check_layout()
    p = build_parts(material)
    return _at(p, f"case_{material or 'parts'}") if p else None


def fans_positioned():
    return _at(build_fans(), "case_fans")


def panel_positioned():
    return _at(build_panel(), "case_panel")


def report():
    hx, hy = _half_cavity()
    floor = 4 * hx * hy
    lines = [f"case             {CASE_EXT[0]:.0f} x {CASE_EXT[1]:.0f} x {CASE_EXT[2]:.0f} mm outer",
             f"cavity           {CASE_INT[0]:.0f} x {CASE_INT[1]:.0f} x {CASE_INT[2]:.0f} mm  ({CASE_BASE_DEPTH:.0f} + {CASE_LID_DEPTH:.0f})",
             f"sits at X        {origin_x()-CASE_EXT[0]/2:+.0f} .. {origin_x()+CASE_EXT[0]/2:+.0f} mm", ""]
    for bay, parts in (("base", BASE_PARTS), ("lid", LID_PARTS)):
        used = sum(w * d for _, (w, d, _), _, _, _ in parts)
        lines.append(f"{bay}: {used/100:.0f} cm^2 of {floor/100:.0f}  ({used/floor*100:.0f}% packed)")
        for name, (w, d, h), (x, y), mat, note in parts:
            lines.append(f"   {name:16s} {w:5.1f} x {d:5.1f} x {h:4.1f}  at ({x:+4.0f}, {y:+4.0f})  {mat:5s}  {note}")
        lines.append("")
    lines.append(f"panel: {len(PANEL)} cutouts in the lid top; fans: {len(FANS)} x {FAN_SIZE:g} mm")
    return lines


if __name__ == "__main__":
    check_layout()
    for line in report():
        print(" ", line)
