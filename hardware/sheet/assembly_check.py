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
from shapely.geometry import box as sbox

GAP = 2.0          # parts to parts
STEEL_GAP = 2.0    # folded flanges that must not touch: bends are ±0.5 each, so 2 mm survives a bad stack
T, W, D = E.T, E.W, E.D

# Steel faces that touch or nearly touch on purpose: (fold A, fold B, designed gap, why). Exact fold names.
# Every other pair of folded flanges (not joined by a bend) must keep STEEL_GAP.
CONTACT = []
for _s in ("left", "right"):
    CONTACT += [
        (f"{_s} top lip", "lid top", 0.0, "lid rests on the body's top lips"),
        (f"{_s} wall", "lid top", 0.0, "lid rests on the body's top edge"),
        (f"{_s} back lip", "lid back", 0.0, "lid back screws to the body's back lips"),
        (f"{_s} wall", "lid back", 0.0, "lid back closes over the side walls' back edges"),
        (f"{_s} wall", f"lid {_s} return", E.CLR, "lid return slides over the body wall"),
        (f"{_s} top lip", f"lid {_s} return", E.CLR, "lid return slides over the body wall"),
        (f"{_s} back lip", f"lid {_s} return", E.CLR, "lid return slides over the body wall"),
        (f"{_s} wall", f"lid back {_s} return", E.CLR, "lid back return slides over the body wall"),
        (f"{_s} back lip", f"lid back {_s} return", E.CLR, "lid back return slides over the body wall"),
        ("base", f"lid back {_s} return", E.CLR, "lid back return slides over the body wall"),
        ("front wall", f"lid {_s} return", E.CLR, "lid return slides over the front wall's edge"),
        (f"{_s} corner tab", "front wall", E.TAB_GAP, "tab riveted to the front wall; rivets close the gap"),
        (f"{_s} wall", "front wall", E.TAB_GAP, "side wall edge meets the front wall; rivets close the gap"),
    ]
CONTACT += [
    ("front top lip", "lid top", 0.0, "lid rests on the body's top lips"),
    ("front wall", "lid top", 0.0, "lid rests on the body's top edge"),
    ("front wall", "lid front return", E.CLR, "lid front return slides over the front wall"),
    ("front top lip", "lid front return", E.CLR, "lid front return slides over the front wall"),
    ("base back lip", "lid back", 0.0, "lid back screws to the base back lip"),
    ("base", "lid back", 0.0, "lid back closes over the base's back edge"),
]
MIN_CLR, MIN_TAB = 1.0, 0.5   # least acceptable sliding clearance (lid over body) and rivet-closed gap (tabs)


def contact(a, b):
    for x, y, g, why in CONTACT:
        if (a, b) in ((x, y), (y, x)):
            return g, why
    return None


class Item:
    def __init__(self, name, tag, x0, x1, y0, y1, z0, z1, soft=False, part=None, foot=None):
        self.name, self.tag, self.soft, self.part = name, tag, soft, part
        self.b = (min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1), min(z0, z1), max(z0, z1))
        self.foot = foot   # optional shapely footprint in x-z (a notched plate)


def gap(a, b):
    """Separation between two items (negative = overlap depth along the least-overlapping axis)."""
    d = [max(a.b[k] - b.b[k + 1], b.b[k] - a.b[k + 1]) for k in (0, 2, 4)]
    if a.foot is not None or b.foot is not None:
        fa = a.foot if a.foot is not None else sbox(a.b[0], a.b[4], a.b[1], a.b[5])
        fb = b.foot if b.foot is not None else sbox(b.b[0], b.b[4], b.b[1], b.b[5])
        dxz = fa.distance(fb)
        return max(d[1], dxz if dxz > 0 else -0.01 - fa.intersection(fb).area ** 0.5)
    return max(d)


ALLOWED = {   # tag pairs that are meant to touch / interpenetrate
    ("sheet", "rivnut"), ("sheet", "standoff"), ("standoff", "plate"), ("sheet", "foot"),
    ("sheet", "panel_in"), ("sheet", "fan"), ("sheet", "panel_screw"), ("panel_screw", "panel_in"),
    ("sheet", "rivet"), ("plate", "part"), ("sheet", "stud"),
    ("plate", "screw_head"), ("screw_head", "standoff"), ("sheet", "foot_screw"), ("foot", "foot_screw"),
}
ALLOWED = {tuple(sorted(p)) for p in ALLOWED}
# what sticks in from each wall item, by the feature name the generator gives it
DEPTH = {"Receiving panel": 35, "USB/antenna panel": 30, "PSU panel": 40, "IEC panel": 50}


def items(kind):
    Hb = T + E.H[kind]
    top = Hb
    body, lid, plate = E.body(kind), E.lid(kind), E.base_plate(kind)
    out = []
    # --- steel: body + lid, from the cut-file model
    for p in (body, lid):
        for f in p.fold:
            out.append(Item(f"{p.name}: {f[0]}", "sheet", *f[1:], part=p))
    # --- base plate (its real, notched outline), standoffs, plate screws, feet
    py0, py1 = E.PLATE_Y
    pb = plate.outline().bounds
    out.append(Item("base plate", "plate", pb[0], pb[2], py0, py1, pb[1], pb[3], foot=plate.outline()))
    for h in body.holes:
        if h["note"] == "Ø4.5 standoff":
            x, z = h["uv"]
            out.append(Item(f"standoff ({x:.0f},{z:.0f})", "standoff", x - 3.5, x + 3.5, T, py0, z - 3.5, z + 3.5))
            out.append(Item(f"plate screw head ({x:.0f},{z:.0f})", "screw_head", x - 3.8, x + 3.8, py1, py1 + 2.2, z - 3.8, z + 3.8))
        elif h["note"] == "Ø4.5 rubber foot":
            x, z = h["uv"]
            out.append(Item(f"rubber foot ({x:.0f},{z:.0f})", "foot", x - 10, x + 10, -8, 0, z - 10, z + 10))
        elif h["note"] == "Ø4.5 locating foot":     # printed flange under the floor; its M4 screw head sits inside
            x, z = h["uv"]
            S_ = E.STACK; r = S_["flange_d"] / 2
            out.append(Item(f"locating foot ({x:.0f},{z:.0f})", "foot", x - r, x + r, -S_["flange_h"], 0, z - r, z + r))
            out.append(Item(f"foot screw head ({x:.0f},{z:.0f})", "foot_screw", x - 3.5, x + 3.5, T, T + S_["foot_screw_head_h"], z - 3.5, z + 3.5))
    # --- rivnut bodies inside the lips (Ø5 x 9 behind the flange), from the generator's rivnut holes
    for h in body.holes:
        if h.get("type") != "rivnut_m3":
            continue
        u, v, face = h["folded"]
        if face == "top":   # (x, z) on a top lip
            out.append(Item(f"rivnut, {h['face']}", "rivnut", u - 2.5, u + 2.5, top - T - 9, top, v - 2.5, v + 2.5))
        else:               # (x, y) on a back lip
            out.append(Item(f"rivnut, {h['face']}", "rivnut", u - 2.5, u + 2.5, v - 2.5, v + 2.5, E.ZB, E.ZB + T + 9))
    # --- window bezel screw tails under the control lid top (M3 + nut, 6 mm)
    for h in lid.holes:
        if "win_screw" in h:
            x, z = h["win_screw"]
            out.append(Item(f"lid window screw ({x:.0f},{z:.0f})", "panel_screw", x - 3.25, x + 3.25, top - 6, top, z - 3.25, z + 3.25))
    # --- accessory rivnuts under the control lid top
    for h in lid.holes:
        if h.get("type") == "acc":
            x, z = h["acc_at"]
            out.append(Item(f"accessory rivnut, lid top ({x:.0f},{z:.0f})", "rivnut", x - 2.5, x + 2.5, top - 10, top, z - 2.5, z + 2.5))
    # --- tab rivets: dome inside the tab
    for s in (-1, 1):
        for v in (Hb * 0.3, Hb * 0.7):
            x = s * (E.WO / 2 - T - (E.LIPO - T) / 2)
            out.append(Item("tab rivet head", "rivet", x - 2.8, x + 2.8, v - 2.8, v + 2.8, D / 2 - E.TAB_GAP - T - 1.5, D / 2 + T))
    # --- wall-mounted things, from the generator's feature list (plate outline on the wall + depth behind it)
    def wall_item(name, wall, u0, u1, v0, v1, depth, tag):
        if wall == "left":
            out.append(Item(name, tag, -W / 2, -W / 2 + depth, v0, v1, u0, u1))
        elif wall == "right":
            out.append(Item(name, tag, W / 2 - depth, W / 2, v0, v1, u0, u1))
        else:
            out.append(Item(name, tag, u0, u1, v0, v1, D / 2 - depth, D / 2))
    for wall, u0, u1, v0, v1, name in body.feat:
        if name in DEPTH:
            c = next(E.PANEL[k] for k in E.PANEL if abs(E.PANEL[k]["plate"][0] - (u1 - u0)) < 1e-6 and abs(E.PANEL[k]["plate"][1] - (v1 - v0)) < 1e-6)
            uc, vc = (u0 + u1) / 2, (v0 + v1) / 2
            wall_item(f"{name}: parts behind", wall, uc - c["cut"][0] / 2, uc + c["cut"][0] / 2, vc - c["cut"][1] / 2, vc + c["cut"][1] / 2, DEPTH[name], "panel_in")
            for a in (-1, 1):
                for b in (-1, 1):
                    su, sv = uc + a * c["screw"][0], vc + b * c["screw"][1]
                    wall_item(f"{name}: screw + nut", wall, su - 3.25, su + 3.25, sv - 3.25, sv + 3.25, 6.0, "panel_screw")
        elif name.startswith("fan"):
            wall_item("fan (80 x 80 x 25)", wall, u0, u1, v0, v1, E.FAN_DEPTH, "fan")
        elif name == "earth stud":
            wall_item("earth stud + lugs", wall, u0, u1, v0, v1, 20, "stud")
        elif name == "front vents":
            pass
        elif name.startswith("GX16 "):                   # sockets in a printed plate: Ø22 rear nut + body + cable, 30 deep
            g = name.split(" ", 1)[1]
            for su, sv in E.GX_GROUPS[g]:
                wall_item(f"GX16 socket ({su:.0f},{sv:.0f})", wall, su - 11, su + 11, sv - 11, sv + 11, 30.0, "panel_in")
            for su, sv in E.gx_openings()[g][1]:
                wall_item(f"GX plate rivnut ({su:.0f},{sv:.0f})", wall, su - 2.5, su + 2.5, sv - 2.5, sv + 2.5, 10.0, "rivnut")
        elif name == "window bezels":                    # bezel + acrylic are outside; inside: the M3 screw tails, nothing else
            for _, scr in E.window_panes():
                for su, sv in scr:
                    wall_item(f"window bezel screw ({su:.0f},{sv:.0f})", wall, su - 3.25, su + 3.25, sv - 3.25, sv + 3.25, 6.0, "panel_screw")
        elif name == "accessory rivnut":                 # M3 rivnut body (Ø5 x 9) + 1 mm, set later from outside
            wall_item(f"{name} ({(u0 + u1) / 2:.0f},{(v0 + v1) / 2:.0f})", wall, u0 + 1.5, u1 - 1.5, v0 + 1.5, v1 - 1.5, 10.0, "rivnut")
        elif name == "ETCH mark":                        # the black print's plate, inside the front wall
            wall_item(f"{name}: printed backing", wall, u0, u1, v0, v1, 2.5, "panel_in")
        else:
            raise SystemExit(f"assembly_check: no rule for wall feature {name!r}")
    # --- interior parts (placeholders, soft)
    pt = py1
    if kind == "power":   # pegs of the control box's feet reaching through the power lid
        S_ = E.STACK; r = S_["peg_d"] / 2
        for x, z in E.FEET_XZ:
            out.append(Item(f"stacking peg ({x:.0f},{z:.0f})", "peg", x - r, x + r, Hb + T - S_["peg_len"], Hb + T + 0.01, z - r, z + r))
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
    fails, warns, fits = [], [], []
    if E.CLR < MIN_CLR:
        fails.append(f"lid clearance {E.CLR} mm per side is under {MIN_CLR}: bends are ±0.5, the lid may not go on")
    if E.TAB_GAP < MIN_TAB:
        fails.append(f"corner-tab gap {E.TAB_GAP} mm is under {MIN_TAB}: a long side wall would push the front wall out")
    for kind in ("control", "power"):
        it = items(kind)
        for a, b in itertools.combinations(it, 2):
            g = gap(a, b)
            if {a.tag, b.tag} == {"peg", "sheet"} and ("lid top" in a.name or "lid top" in b.name):
                continue                             # the peg passes through its hole in the lid top
            if a.tag == b.tag == "sheet":
                if a.part is b.part and frozenset((a.name.split(": ", 1)[1], b.name.split(": ", 1)[1])) in a.part.connect:
                    continue
                c = contact(a.name.split(": ", 1)[1], b.name.split(": ", 1)[1])
                if c:
                    want, why = c
                    if g < want - 1e-6:
                        fails.append(f"{kind}: {a.name}  ×  {b.name}   gap {g:.2f} mm, designed {want} ({why})")
                    else:
                        fits.append(f"{kind}: {a.name.split(': ',1)[1]} / {b.name.split(': ',1)[1]}: {g:.1f} mm ({why})")
                elif g < STEEL_GAP - 1e-6:
                    fails.append(f"{kind}: {a.name}  ×  {b.name}   gap {g:.2f} mm (steel needs {STEEL_GAP})")
                continue
            if tuple(sorted((a.tag, b.tag))) in ALLOWED:
                continue
            if g < GAP:
                msg = f"{kind}: {a.name}  ×  {b.name}   gap {g:.1f} mm (need {GAP})"
                (warns if (a.soft or b.soft) else fails).append(msg)
    return fails, warns, fits


if __name__ == "__main__":
    f, w, fits = run()
    if "-v" in sys.argv:
        for m in sorted(set(fits)):
            print("  fit  ", m)
    print(f"{len(f)} clashes, {len(w)} warnings on placeholder parts")
    for m in f:
        print("  CLASH", m)
    for m in w:
        print("  warn ", m)
    sys.exit(1 if f else 0)
