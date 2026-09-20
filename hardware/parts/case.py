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
# A DIN terminal strip is about 58 mm tall once it is on its rail, not the
# 30 mm a bare bus bar would be. Both bays have 99 mm, so it fits -- but it is
# the tallest thing in the base now.
DIN_H = 58.0

# Ways per distribution strip, as (24 V positions, 0 V positions). The BOM
# counts blocks, end clamps and jumper combs off these.
DIST_WAYS = {"dist_base": (4, 4), "dist_lid": (6, 6)}

BASE_PARTS = [
    ("iec_inlet",      ( 50,  30, 30), (-110, -150), "abs",   "panel-mount IEC, fused + switched"),
    ("mains_splitter", ( 60,  50, 30), (-100,  -85), "abs",   "3-in/6-out lever splitter, L/N/E"),
    ("psu_24v_main",   (115, 215, 30), ( -60,   80), "steel", "LRS-350-24, ex-Ender 3"),
    ("psu_24v_servo",  ( 51,  78, 28), (  75, -160), "steel", "RS-25-24, servo supply"),
    ("buck_servo",     ( 45,  65, 25), (  75,  -55), "pcb",   "24 -> 6.0 V, MG996R"),
    ("dist_base",      ( 50,  58, DIN_H), (  85,   60), "abs", "DIN strip: 4x 24 V + 4x 0 V"),
]

# TB6600: 96.5 flange to flange, 67.7 deep over the terminals, 57 tall.
# Rotated from the first pass so its 96.5 mm dimension runs along Y: its two
# terminal blocks both sit on ONE 96 mm edge, and laid the other way that edge
# faced the next driver 2.3 mm away. Nothing could have been wired.
TB6600 = (67.7, 96.5, 57.0)

# Which faces a component's wires can actually leave from, in its local frame,
# and how much clearance that face needs in front of it.
#
# This is the constraint the router was missing. It had been free to take wires
# out of whichever face pointed at the destination, but almost nothing here has
# terminals on more than one side. Confidence is recorded because it varies:
# one of these is measured, most are the part's obvious convention, and one is
# genuinely unknown.
TERMINAL_CLEARANCE = 25.0       # mm in front of a terminal face for the wire to turn

TERMINALS = {
    "tb6600":         (("-x",),        "measured", "both blocks on one 96 mm edge, from the drawing"),
    "psu_24v_main":   (("-y",),        "convention", "Mean Well screw terminals in a row on one short end"),
    "psu_24v_servo":  (("+y",),        "convention", "same; turned to face inward, not the shell"),
    "buck_servo":     (("-y", "+y"),   "convention", "LM2596: IN one end, OUT the other"),
    "mains_splitter": (("-y", "+y"),   "convention", "3 in one face, 6 out the opposite"),
    "iec_inlet":      (("+y",),        "convention", "spade terminals on the rear face"),
    "dist_base":      (("-x", "+x"),   "convention", "DIN blocks take a wire each side"),
    "dist_lid":       (("-y", "+y"),   "convention", "same"),
    "fan_intake":     (("+y",),        "convention", "single lead out of one corner"),
    "fan_exhaust":    (("-y",),        "convention", "same"),
    "elecrow_6x":     (("-x", "+x", "-y", "+y"), "UNKNOWN",
                       "product page is blocked; header positions are a guess"),
}


def terminal_faces(name):
    """Faces a component's wires may leave from, and how sure we are."""
    for key, val in TERMINALS.items():
        if name.startswith(key):
            return val
    return (("-x", "+x", "-y", "+y"), "unconstrained", "")

# Drivers hard against the hinge edge, board opposite, and a clear lane down the
# middle. The board's ports face down into that lane, and every panel connector
# drops into it -- so nothing has to route over the top of a driver or the board
# to reach anything.
#
# Neither the board's position nor the connector order is a guess: wiring.py
# routes every bundle and scores the result, and both come from its search.
# Re-run `python3 hardware/wiring.py --search` after moving anything in here.
LID_PARTS = [
    ("tb6600_x1",  TB6600,          (  70,  -52), "steel", "stepper driver, terminals facing the lane"),
    ("tb6600_x2",  TB6600,          (  70, 48.5), "steel", "stepper driver, terminals facing the lane"),
    ("tb6600_y",   TB6600,          (  70,  149), "steel", "stepper driver, terminals facing the lane"),
    ("elecrow_6x", (85, 125, 25),   ( -94,    0), "pcb",   "Elecrow 6-axis, 125 x 85"),
    # One pair crosses the hinge and fans out here. Without this the five lid
    # loads had nothing to start from, or the first driver's screw terminal
    # would have carried all 9 A for the three of them.
    ("dist_lid",   (78, 47, DIN_H), (  50, -151), "abs",   "DIN strip: 6x 24 V + 6x 0 V"),
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
    ("gx16_3_endstop_y", 16, (LANE_X, -170), "endstop Y"),
    ("gx16_3_endstop_x", 16, (LANE_X, -120), "endstop X"),
    ("gx16_5_x1",        16, (LANE_X,  -70), "stepper X1, 4 wires + shield"),
    ("usb_c",            14, (LANE_X,  -20), "USB-C to the board"),
    ("gx16_4_servo",     16, (LANE_X,   25), "servo, 6 V + signal"),
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

    # A terminal face needs room in front of it for the wire to turn. This is
    # what caught the drivers stacked 2.3 mm apart on the very axis their
    # terminals face -- unbuildable, and invisible until the faces were declared.
    for bay, parts in (("base", BASE_PARTS + fans_in("base")), ("lid", LID_PARTS + fans_in("lid"))):
        for name, (w, d, _), (x, y), _, _ in parts:
            faces, conf, _why = terminal_faces(name)
            if conf == "UNKNOWN":
                continue
            for face in faces:
                axis, sign = face[1], (1 if face[0] == "+" else -1)
                half = (w if axis == "x" else d) / 2
                edge = (x if axis == "x" else y) + sign * half
                front = (edge + sign * TERMINAL_CLEARANCE)
                lo, hi = sorted((edge, front))

                limit = (CASE_INT[0] if axis == "x" else CASE_INT[1]) / 2
                if abs(front) > limit + 1e-9:
                    problems.append(
                        f"{name}'s {face} terminal face is under "
                        f"{TERMINAL_CLEARANCE:g} mm from the shell -- no room to wire it")

                for on, (ow, od, _), (ox, oy), _, _ in parts:
                    if on == name:
                        continue
                    if axis == "x":
                        clash = (abs(oy - y) < (od + d) / 2
                                 and lo < ox + ow / 2 and ox - ow / 2 < hi)
                    else:
                        clash = (abs(ox - x) < (ow + w) / 2
                                 and lo < oy + od / 2 and oy - od / 2 < hi)
                    if clash:
                        problems.append(
                            f"{name}'s {face} terminal face has {on} within "
                            f"{TERMINAL_CLEARANCE:g} mm -- no room to wire it")

    if problems:
        raise ValueError("case layout: " + "; ".join(sorted(set(problems))))


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
