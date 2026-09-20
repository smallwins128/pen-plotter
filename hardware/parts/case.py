"""Electronics case: a UN4020 hard carry case beside the machine.

Replaces the extrusion enclosure. Moulded polypropylene, sits flat on the
bench, and runs CLOSED -- which is why the fans are not optional: three TB6600
heatsinks hang fin-down in still air otherwise.

Split of contents, settled with the packing numbers:

    base   the two 24 V supplies, the servo buck, the ground and 24 V buses,
           the IEC inlet and the intake fan    -- heavy things, low down

There is no 5 V rail in the case: the board regulates its own 5 V and 3.3 V
from VMot, so an external 5 V buck and bus would have fed nothing.
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
# The lid hinges along the +X edge, so that is where power crosses. The 24 V
# and ground buses sit nearest it and the drivers sit nearest it on the other
# side, which keeps the only heavy conductors in the machine short.
HINGE_EDGE = "+X"

# PSUs down the -X side, distribution down the +X side, mains in the -Y corner
# clear of the intake fan.
# Mains clustered in the -Y corner: IEC and both PSU inputs together, so the
# 220 V runs are short and stay out of the DC half. Before this the servo PSU
# sat diagonally opposite the inlet -- a 460 mm mains run that crossed both DC
# rails on its way. DC distribution lives up the +X side by the hinge.
BASE_PARTS = [
    ("iec_inlet",     ( 50,  30, 30), (-105, -180), "abs",   "panel-mount IEC, 220 V in"),
    ("psu_24v_main",  (115, 215, 30), ( -75,  -35), "steel", "LRS-350-24, ex-Ender 3"),
    ("psu_24v_servo", ( 51,  78, 28), (  70, -155), "steel", "RS-25-24, beside the inlet"),
    ("buck_servo",    ( 45,  65, 25), (  60,  -80), "pcb",   "24 -> 6.0 V, MG996R"),
    ("bus_ground",    ( 25, 150, 30), (  85,  100), "abs",   "ground terminal bus"),
    ("bus_24v",       ( 25, 150, 30), ( 120,  100), "abs",   "24 V bus, nearest the hinge"),
]

# TB6600: 96.5 flange to flange, 67.7 deep over the terminals, 57 tall.
TB6600 = (96.5, 67.7, 57.0)

# Drivers hard against the hinge edge, board opposite, and a clear lane down the
# middle. The board's ports face down into that lane, and every panel connector
# drops into it -- so nothing has to route over the top of a driver or the board
# to reach anything.
#
# The board's Y position is not a guess: wiring.py routes every bundle and
# scores the result, and moving the board from -120 to +60 -- up beside the
# drivers it talks to -- took the score from 20331 to 386 and cut a fifth off
# the total conductor length. Re-run `python3 hardware/wiring.py --search`
# after moving anything in here.
LID_PARTS = [
    ("tb6600_x1",  TB6600,        (  86,   25), "steel", "stepper driver"),
    ("tb6600_x2",  TB6600,        (  86,   95), "steel", "stepper driver"),
    ("tb6600_y",   TB6600,        (  86,  165), "steel", "stepper driver"),
    ("elecrow_6x", (85, 125, 25), ( -94,   60), "pcb",   "Elecrow 6-axis, 125 x 85"),
]

# Panel connectors sit in the lid's top face and their bodies hang ~25 mm into
# the bay, so they occupy floor like anything else -- which is why they are in
# the lane and not above a 57 mm driver.
PANEL_BODY = 22.0
PANEL_DEPTH = 25.0
LANE_X = -7.0

# Ordered along the lane so each lands beside what it wires to: board services
# at the board end, steppers opposite their own driver.
PANEL = [
    ("usb_c",            14, (LANE_X, -170), "USB-C to the board"),
    ("gx16_3_endstop_x", 16, (LANE_X, -120), "endstop X"),
    ("gx16_3_endstop_y", 16, (LANE_X,  -70), "endstop Y"),
    ("gx16_4_servo",     16, (LANE_X,  -20), "servo, 6 V + signal"),
    ("gx16_5_x1",        16, (LANE_X,   25), "stepper X1, 4 wires + shield"),
    ("gx16_5_x2",        16, (LANE_X,   95), "stepper X2, 4 wires + shield"),
    ("gx16_5_y",         16, (LANE_X,  160), "stepper Y, 4 wires + shield"),
]

# Intake low in the base at the cool end, exhaust in the LID at the driver end,
# so the path runs diagonally through both bays and leaves carrying the hottest
# air. Costs two more conductors across the hinge, which is a fair trade.
FANS = [
    ("fan_intake",  "base", (   0, -(CASE_INT[1] / 2 - FAN_THICK / 2)), "intake, filtered"),
    ("fan_exhaust", "lid",  ( -60,  (CASE_INT[1] / 2 - FAN_THICK / 2)), "exhaust, at the drivers"),
]


def origin_x():
    return FRAME_OUTER_X / 2 + CASE_GAP + CASE_EXT[0] / 2


def _half_cavity():
    return CASE_INT[0] / 2, CASE_INT[1] / 2


def check_layout():
    """Nothing outside the cavity, nothing overlapping its neighbours."""
    hx, hy = _half_cavity()
    problems = []

    # Fans and panel connectors occupy their bay like anything else, so they
    # take part in the collision check rather than being drawn in afterwards
    # and hoped for. The connectors are the reason the lane exists: their
    # bodies hang into the lid bay and cannot share floor with a driver.
    def fans_in(bay):
        return [(n, (FAN_SIZE, FAN_THICK, FAN_SIZE), xy, "abs", note)
                for n, b, xy, note in FANS if b == bay]

    panel_parts = [(n, (PANEL_BODY, PANEL_BODY, PANEL_DEPTH), xy, "abs", note)
                   for n, _, xy, note in PANEL]

    for bay, parts in (("base", BASE_PARTS + fans_in("base")),
                       ("lid", LID_PARTS + fans_in("lid") + panel_parts)):
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
    for name, bay, (x, y), _ in FANS:
        z0 = CAVITY_Z0 if bay == "base" else SPLIT_Z
        f = Pos(x, y, z0 + FAN_SIZE / 2) * Box(FAN_SIZE, FAN_THICK, FAN_SIZE)
        f.label = name
        out.append(f)
    return out


def build_panel():
    """Connectors through the lid's top face: a stub outside, a body inside."""
    out = []
    for name, dia, (x, y), _ in PANEL:
        outside = Pos(x, y, CASE_EXT[2] + 9) * Box(dia, dia, 18)
        inside = Pos(x, y, LID_CEILING - PANEL_DEPTH / 2) * Box(PANEL_BODY, PANEL_BODY, PANEL_DEPTH)
        c = Compound(children=[outside, inside])
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
    lines.append(f"lane at x = {LANE_X:+.0f}, {len(PANEL)} connectors dropping into it:")
    for name, _, (x, y), note in PANEL:
        lines.append(f"   {name:18s} at ({x:+4.0f}, {y:+4.0f})   {note}")
    lines.append("")
    for name, bay, (x, y), note in FANS:
        lines.append(f"   {name:18s} {bay:4s} at ({x:+4.0f}, {y:+4.0f})   {note}")
    lines.append(f"   hinge on the {HINGE_EDGE} edge -- power crosses there")
    return lines


if __name__ == "__main__":
    check_layout()
    for line in report():
        print(" ", line)


def blackbox_positioned():
    """The case as a plain solid with its connector stubs.

    For the machine-level view, where the case is context rather than subject:
    its footprint, its height and where the cables leave are all that matter
    there. The detail lives in its own page.
    """
    body = Pos(0, 0, CASE_EXT[2] / 2) * Box(*CASE_EXT)
    body.label = "case_body"

    stubs = []
    for name, dia, (x, y), _ in PANEL:
        st = Pos(x, y, CASE_EXT[2] + 9) * Box(dia, dia, 18)
        st.label = name
        stubs.append(st)

    return _at([body] + stubs, "case_blackbox")
