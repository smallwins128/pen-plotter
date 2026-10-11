#!/usr/bin/env python3
"""Whole-assembly clearance check: every physical thing in both boxes, not just the steel.

    python3 hardware/sheet/assembly_check.py

Each item is an axis-aligned box (cylinders by their bounding box) in the folded
frame of its box: x across, y up from the base underside, z toward the front.
Items carry tags; two items may touch or overlap only if the pair is listed in
ALLOWED (a rivnut in its lip, a plate on its standoffs...). Everything else must
keep GAP mm apart. Interior parts (drivers, board, PSUs) are placeholders on a
re-arrangeable grid: their clashes are reported as warnings, not failures.
"""
import itertools
import sys

import enclosure as E

GAP = 2.0
T, W, D = E.T, E.W, E.D


class Item:
    def __init__(self, name, tag, x0, x1, y0, y1, z0, z1, soft=False):
        self.name, self.tag, self.soft = name, tag, soft
        self.b = (min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1), min(z0, z1), max(z0, z1))


def gap(a, b):
    """Separation between two boxes (negative = overlap depth along the least-overlapping axis)."""
    d = []
    for k in (0, 2, 4):
        d.append(max(a.b[k] - b.b[k + 1], b.b[k] - a.b[k + 1]))
    return max(d)


ALLOWED = {   # tag pairs that are meant to touch / interpenetrate
    ("sheet", "sheet"), ("sheet", "rivnut"), ("sheet", "standoff"), ("standoff", "plate"), ("sheet", "foot"),
    ("sheet", "panel_in"), ("sheet", "fan"), ("sheet", "panel_screw"), ("panel_screw", "panel_in"),
    ("sheet", "rivet"), ("plate", "part"), ("sheet", "stud"), ("fan", "fan_screw"), ("sheet", "fan_screw"),
    ("plate", "screw_head"), ("screw_head", "standoff"),
}
ALLOWED = {tuple(sorted(p)) for p in ALLOWED}


def items(kind):
    Hb = T + E.H[kind]
    top = Hb
    out = []
    # --- steel: body + lid, from the cut-file model
    for p in (E.body(kind), E.lid(kind)):
        for f in p.fold:
            out.append(Item(f"{p.name}: {f[0]}", "sheet", *f[1:]))
    # --- base plate, standoffs, plate screws, feet
    py0, py1 = T + 5, T + 5 + 2
    out.append(Item("base plate", "plate", -220, 220, py0, py1, -142.5, 142.5))
    for x in (-(W / 2 - 20), 0, W / 2 - 20):
        for z in (-(D / 2 - 20), D / 2 - 20):
            out.append(Item(f"standoff ({x:.0f},{z:.0f})", "standoff", x - 3.5, x + 3.5, T, py0, z - 3.5, z + 3.5))
            out.append(Item(f"plate screw head ({x:.0f},{z:.0f})", "screw_head", x - 3.8, x + 3.8, py1, py1 + 2.2, z - 3.8, z + 3.8))
    for x in (-(W / 2 - 40), W / 2 - 40):
        for z in (-(D / 2 - 40), D / 2 - 40):
            out.append(Item(f"rubber foot ({x:.0f},{z:.0f})", "foot", x - 10, x + 10, -E.foot if hasattr(E, "foot") else -8, 0, z - 10, z + 10))
    # --- rivnut bodies hanging inside the lips (Ø5 x 9 below the flange)
    xr = E.WO / 2 - T - E.RIV_IN
    for s in (-1, 1):
        out.append(Item(f"rivnut, {('left','right')[s>0]} top lip", "rivnut", s * xr - 2.5, s * xr + 2.5, top - T - 9, top, -2.5, 2.5))
        out.append(Item(f"rivnut, {('left','right')[s>0]} back lip", "rivnut", s * xr - 2.5, s * xr + 2.5, T + E.H[kind] / 2 - 2.5, T + E.H[kind] / 2 + 2.5, E.ZB, E.ZB + T + 9))
    out.append(Item("rivnut, front top lip", "rivnut", -2.5, 2.5, top - T - 9, top, E.ZF - T - E.RIV_IN - 2.5, E.ZF - T - E.RIV_IN + 2.5))
    out.append(Item("rivnut, base back lip", "rivnut", -2.5, 2.5, T + E.LIP / 2 - 2.5, T + E.LIP / 2 + 2.5, E.ZB, E.ZB + T + 9))
    # --- tab rivets: dome inside the tab
    for s in (-1, 1):
        for v in (Hb * 0.3, Hb * 0.7):
            out.append(Item("tab rivet head", "rivet", s * 217.5 - 2.8, s * 217.5 + 2.8, v - 2.8, v + 2.8, D / 2 - T - 1.5, D / 2 + T))
    # --- wall-mounted things: depth behind the wall (from the inside face)
    def wall_item(name, wall, u, v, w, h, depth, tag="panel_in"):
        if wall == "left":
            out.append(Item(name, tag, -W / 2, -W / 2 + depth, v - h / 2, v + h / 2, u - w / 2, u + w / 2))
        elif wall == "right":
            out.append(Item(name, tag, W / 2 - depth, W / 2, v - h / 2, v + h / 2, u - w / 2, u + w / 2))
        else:   # front
            out.append(Item(name, tag, u - w / 2, u + w / 2, v - h / 2, v + h / 2, D / 2 - depth, D / 2))
    def panel(wall, key, u, v, name, depth):
        c = E.PANEL[key]
        wall_item(f"{name}: parts behind", wall, u, v, c["cut"][0], c["cut"][1], depth)
        for a in (-1, 1):
            for b in (-1, 1):
                wall_item(f"{name}: screw + nut", wall, u + a * c["screw"][0], v + b * c["screw"][1], 6.5, 6.5, 6.0, "panel_screw")
    if kind == "control":
        panel("front", "gx_rail", -10, T + E.H[kind] / 2, "GX16 rail", 30)
        panel("right", "receiving", D / 2 - 146, E.panel_y(kind, 70), "Receiving panel", 35)
        panel("left", "usb_ant", -D / 2 + 242.5, E.panel_y(kind, 40), "USB/antenna panel", 30)
        fan_v, fan_z = T + E.H[kind] / 2 - 8, -30
    else:
        panel("right", "psu", D / 2 - 160, E.panel_y(kind, 140.4), "PSU panel", 40)
        panel("left", "iec", D / 2 - 175, T + E.H[kind] / 2, "IEC panel", 50)
        fan_v, fan_z = T + 50, D / 2 - 50
        out.append(Item("earth stud + lugs", "stud", -W / 2, -W / 2 + 20, T + 20 - 6, T + 20 + 6, D / 2 - 260 - 6, D / 2 - 260 + 6))
    out.append(Item("fan (80 x 80 x 25)", "fan", -W / 2, -W / 2 + 25, fan_v - 40, fan_v + 40, fan_z - 40, fan_z + 40))
    # --- interior parts (placeholders, soft)
    pt = py1
    if kind == "control":
        for i in range(3):
            z = D / 2 - 60 - i * 77
            out.append(Item(f"driver D{i + 1} (standing)", "part", -W / 2 + 71.75, -W / 2 + 168.25, pt + 3, pt + 3 + 70, z - 28.5, z + 28.5, soft=True))
        out.append(Item("FluidNC board on 10 mm posts", "part", 95 - 62.5, 95 + 62.5, pt, pt + 10 + 1.6 + 15, -40 - 42.5, -40 + 42.5, soft=True))
    else:
        out.append(Item("24 V PSU", "part", -W / 2 + 60, -W / 2 + 175, pt + 3, pt + 33, -D / 2 + 40, -D / 2 + 255, soft=True))
        out.append(Item("12 V PSU", "part", -W / 2 + 185, -W / 2 + 300, pt + 3, pt + 33, -D / 2 + 40, -D / 2 + 255, soft=True))
    return out


def run():
    fails, warns = [], []
    for kind in ("control", "power"):
        it = items(kind)
        for a, b in itertools.combinations(it, 2):
            pair = tuple(sorted((a.tag, b.tag)))
            if pair in ALLOWED or (a.tag == b.tag == "sheet"):
                continue
            g = gap(a, b)
            if g < GAP:
                msg = f"{kind}: {a.name}  ×  {b.name}   gap {g:.1f} mm (need {GAP})"
                (warns if (a.soft or b.soft) else fails).append(msg)
    return fails, warns


if __name__ == "__main__":
    f, w = run()
    print(f"{len(f)} clashes, {len(w)} warnings on placeholder parts")
    for m in f:
        print("  CLASH", m)
    for m in w:
        print("  warn ", m)
    sys.exit(1 if f else 0)
