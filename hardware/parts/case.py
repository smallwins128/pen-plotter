"""The two electronics cases: a power box and a control box, both UN4412.

Split from a single UN4020 so the box you actually open has nothing above
24 V in it. Three conductors run between them -- 24 V, 6 V and ground -- and
the ground is deliberately two sizes up, because the servo's 2.5 A return
shares it and at 0.75 mm^2 that puts ~94 mV on the logic reference every time
the pen lifts. That is the failure in FINDINGS.md section 7, and running it
down a shared 1.2 m wire would re-create it.

INTERNAL PLACEMENT IS PROVISIONAL. Contents are auto-packed onto the floor in
rows, not arranged -- the real positions come from actually laying the parts in
the case. The sizes, the counts, the panel and the box geometry are real; where
a block sits is not, and is not pretending to be.
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from build123d import Box, Compound, Pos

from params import (
    CASE_BASE_DEPTH,
    CASE_EXT,
    CASE_GAP,
    CASE_INT,
    CASE_LID_DEPTH,
    CASE_SPACING,
    CASE_WALL_Z,
    FAN_SIZE,
    FAN_THICK,
    FRAME_OUTER_X,
    LINK_WIRE,
)

CAVITY_Z0 = CASE_WALL_Z
CAVITY_Z1 = CASE_WALL_Z + CASE_INT[2]
SPLIT_Z = CAVITY_Z0 + CASE_BASE_DEPTH

TERMINAL_CLEARANCE = 25.0
MARGIN = 20.0            # kept clear inside the cavity wall

# name, (w, d, h), material, note
POWER_PARTS = [
    ("psu_24v_main",   (215, 115, 30), "steel", "LRS-350-24, ex-Ender 3"),
    ("psu_24v_servo",  ( 51,  78, 28), "steel", "RS-25-24, servo supply"),
    ("buck_servo",     ( 65,  45, 25), "pcb",   "24 -> 6.0 V, MG996R"),
    ("mains_splitter", ( 60,  50, 30), "abs",   "3-in/6-out lever splitter, L/N/E"),
    ("iec_inlet",      ( 50,  30, 30), "abs",   "panel-mount IEC, fused + switched"),
    ("gnd_bond",       ( 50,  40, 30), "abs",   "single point where the two PSU 0 V rails join"),
]

TB6600 = (67.7, 96.5, 57.0)

CONTROL_PARTS = [
    ("tb6600_x1",  TB6600,          "steel", "stepper driver"),
    ("tb6600_x2",  TB6600,          "steel", "stepper driver"),
    ("tb6600_y",   TB6600,          "steel", "stepper driver"),
    ("elecrow_6x", (125, 85, 25),   "pcb",   "Elecrow 6-axis"),
    # Lever blocks, not DIN. A DIN block on its rail stands 58 mm and its screw
    # sits near the top, leaving 4 mm of screwdriver access in a 62 mm bay. The
    # driver next to it is 57 mm and fine, because its terminals are down at
    # ~28 mm -- height alone does not tell you whether a thing can be wired.
    ("dist_24v",   (60, 50, 30),    "abs",   "lever block, 1-in/6-out: 24 V"),
    ("dist_gnd",   (75, 50, 30),    "abs",   "lever block, 1-in/8-out: ground"),
    ("dist_6v",    (40, 40, 25),    "abs",   "lever block, 1-in/3-out: 6 V"),
]

# Panel cutouts, per box. Spare rows are deliberate -- displays and switches
# are wanted later and the wall is where they go.
POWER_PANEL = [
    ("iec_c14",     "220 V in, fused + switched"),
    ("link_out",    "24 V / 6 V / ground to the control box"),
    ("mains_switch", "front-panel switch"),
    ("spare_a",     "spare: voltmeter or indicator"),
]
CONTROL_PANEL = [
    ("link_in",          "24 V / 6 V / ground from the power box"),
    ("usb_c",            "USB-C to the laptop"),
    ("gx16_5_x1",        "stepper X1, 4 wires + shield"),
    ("gx16_5_x2",        "stepper X2, 4 wires + shield"),
    ("gx16_5_y",         "stepper Y, 4 wires + shield"),
    ("gx16_3_endstop_x", "endstop X"),
    ("gx16_3_endstop_y", "endstop Y"),
    ("gx16_4_servo",     "servo, 6 V + signal"),
    ("spare_b",          "spare: display or e-stop"),
]

BOXES = {
    "power":   {"parts": POWER_PARTS,   "panel": POWER_PANEL,   "order": 1},
    "control": {"parts": CONTROL_PARTS, "panel": CONTROL_PANEL, "order": 0},
}


def origin_x(box):
    """Box centre in machine coordinates. Control box nearest the machine."""
    first = FRAME_OUTER_X / 2 + CASE_GAP + CASE_EXT[0] / 2
    return first + BOXES[box]["order"] * (CASE_EXT[0] + CASE_SPACING)


def pack(parts):
    """Lay the contents out in rows. Provisional, and deliberately so.

    Shelf packing: fill a row across, start a new one when it runs out. It
    makes no claim to be a good arrangement -- it exists so the model carries
    the right volumes in the right box until the real positions arrive.
    """
    hx = CASE_INT[0] / 2 - MARGIN
    hy = CASE_INT[1] / 2 - MARGIN

    placed, x, y, row_d = [], -hx, hy, 0.0
    for name, (w, d, h), mat, note in sorted(parts, key=lambda p: -p[1][1]):
        if x + w > hx:
            y -= row_d + TERMINAL_CLEARANCE
            x, row_d = -hx, 0.0
        placed.append((name, (w, d, h), (x + w / 2, y - d / 2), mat, note))
        x += w + TERMINAL_CLEARANCE
        row_d = max(row_d, d)

    lowest = min(c[1] - sz[1] / 2 for _, sz, c, _, _ in placed)
    if lowest < -hy:
        raise ValueError(f"contents overflow the floor by {-hy - lowest:.0f} mm")
    return placed


def check(box):
    """Everything inside the cavity, nothing overlapping, bay deep enough."""
    placed = pack(BOXES[box]["parts"])
    hx, hy = CASE_INT[0] / 2, CASE_INT[1] / 2
    problems = []

    for name, (w, d, h), (x, y), _, _ in placed:
        if abs(x) + w / 2 > hx or abs(y) + d / 2 > hy:
            problems.append(f"{name} outside the cavity")
        if h > CASE_BASE_DEPTH:
            problems.append(f"{name} is {h:g} mm in a {CASE_BASE_DEPTH:g} mm bay")

    for i, (n1, (w1, d1, _), (x1, y1), _, _) in enumerate(placed):
        for n2, (w2, d2, _), (x2, y2), _, _ in placed[i + 1:]:
            if abs(x1 - x2) < (w1 + w2) / 2 and abs(y1 - y2) < (d1 + d2) / 2:
                problems.append(f"{n1} overlaps {n2}")

    if problems:
        raise ValueError(f"{box} box: " + "; ".join(sorted(set(problems))))
    return placed


def build_shell(box):
    ex, ey, _ = CASE_EXT
    ix, iy, _ = CASE_INT
    base_h = CASE_WALL_Z + CASE_BASE_DEPTH

    base = Pos(0, 0, base_h / 2) * Box(ex, ey, base_h)
    base -= Pos(0, 0, CAVITY_Z0 + CASE_BASE_DEPTH / 2) * Box(ix, iy, CASE_BASE_DEPTH)
    base.label = f"{box}_base"

    lid_h = CASE_EXT[2] - base_h
    lid = Pos(0, 0, base_h + lid_h / 2) * Box(ex, ey, lid_h)
    lid -= Pos(0, 0, SPLIT_Z + CASE_LID_DEPTH / 2) * Box(ix, iy, CASE_LID_DEPTH)
    lid.label = f"{box}_lid"
    return [base, lid]


def build_parts(box, material=None):
    out = []
    for name, (w, d, h), (x, y), mat, _ in check(box):
        if material and mat != material:
            continue
        b = Pos(x, y, CAVITY_Z0 + h / 2) * Box(w, d, h)
        b.label = name
        out.append(b)
    return out


def build_fan(box):
    """One fan per box, in the lid face -- so bay depth never limits fan size."""
    f = Pos(0, CASE_INT[1] / 2 - FAN_SIZE, CASE_EXT[2] - FAN_THICK / 2) * \
        Box(FAN_SIZE, FAN_SIZE, FAN_THICK)
    f.label = f"{box}_fan"
    return [f]


def _at(box, parts, label):
    c = Compound(children=parts)
    c.label = label
    return Pos(origin_x(box), 0, 0) * c


def build(box=None):
    """One box, or both when make.py asks for the part called "case"."""
    if box is None:
        return build_all()
    return _at(box, build_shell(box) + build_parts(box) + build_fan(box), f"{box}_box")


def cut_list():
    return [(len(BOXES), CASE_INT[0], "UN4412 case (power + control)", "")]


LINEAR_STOCK = False


def mass():
    """Both empty cases. Contents are bought parts, counted in the BOM."""
    return 2 * 1.1


def build_all():
    c = Compound(children=[build(b) for b in BOXES])
    c.label = "electronics"
    return c


def shell_positioned(box):
    return _at(box, build_shell(box), f"{box}_shell")


def parts_positioned(box, material=None):
    p = build_parts(box, material)
    return _at(box, p, f"{box}_{material or 'parts'}") if p else None


def fan_positioned(box):
    return _at(box, build_fan(box), f"{box}_fan")


def report():
    lines = [f"UN4412 x2 -- internal {CASE_INT[0]:.0f} x {CASE_INT[1]:.0f} x {CASE_INT[2]:.0f} mm,"
             f" bays {CASE_BASE_DEPTH:.0f} + {CASE_LID_DEPTH:.0f}", ""]
    for box in ("power", "control"):
        placed = check(box)
        foot = sum(w * d for _, (w, d, _), _, _, _ in placed)
        floor = CASE_INT[0] * CASE_INT[1]
        lines.append(f"{box.upper()} BOX at X {origin_x(box):+.0f}"
                     f"   {foot/100:.0f} cm^2 of {floor/100:.0f}  ({foot/floor*100:.0f}% packed)")
        for name, (w, d, h), (x, y), mat, note in placed:
            lines.append(f"   {name:16s} {w:5.1f} x {d:5.1f} x {h:4.1f}  {mat:5s}  {note}")
        lines.append(f"   panel: {len(BOXES[box]['panel'])} cutouts")
        lines.append("")
    lines.append("link between boxes: " + ", ".join(f"{k} {v} mm^2" for k, v in LINK_WIRE.items()))
    return lines


if __name__ == "__main__":
    for line in report():
        print(" ", line)
