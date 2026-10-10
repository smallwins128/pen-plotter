#!/usr/bin/env python3
"""Bill of materials, counted from the model rather than remembered.

    python3 hardware/bom.py           # the table
    python3 hardware/bom.py --csv     # same thing, for a spreadsheet

Quantities that the model knows -- extrusion lengths, sheet size, connector
counts, terminal ways, wire length by gauge, ferrules by size -- are computed.
Quantities it cannot know are declared in BOUGHT below and marked so, because a
guessed number that looks computed is worse than one that admits it.
"""

import argparse
import csv
import io
import pathlib
import sys
from collections import defaultdict

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "parts"))

import case                     # noqa: E402
import panel                    # noqa: E402
import ctrl_layout              # noqa: E402
import psu_layout               # noqa: E402
import deck as deck_mod         # noqa: E402
import stock                    # noqa: E402
from params import DECK_T, DECK_X, DECK_Y  # noqa: E402

# Conductor gauge per bundle kind, and the ferrule that goes on its ends.
GAUGE = {"mains": 1.0, "power": 1.0, "phase": 0.5, "signal": 0.25, "pwm": 0.25, "usb": 0.25}

# Routed length is the ideal. Real wire needs slack for the service loop at the
# hinge, dressing round corners, and the bit you cut off after mis-stripping.
SLACK = 1.4

# Things the model cannot count. Kept explicit so nothing here reads as though
# it were derived.
BOUGHT = [
    ("Motion", "NEMA 17 stepper, Ender-3 42-34", 3, "ea", "2 on X, 1 on Y, all ride the gantry"),
    ("Motion", "OpenBuilds gantry plate, 65.5 mm", 2, "ea", "3-wheel; needs V-slot rail"),
    ("Motion", "GT2 pulley, 20 T", 3, "ea", "bore to suit the motor shaft"),
    ("Motion", "GT2 belt, 6 mm", 4, "m", "estimate -- belt path not modelled"),
    ("Motion", "GT2 idler, smooth bore", 4, "ea", "estimate -- ends not modelled"),
    ("Motion", "Limit switch, NC", 2, "ea", "X and Y"),
    ("Motion", "Drag chain + end brackets", 2, "set", "already owned"),
    ("Electronics", "Mean Well LRS-350-24", 1, "ea", "already owned, ex-Ender 3"),
    ("Electronics", "Mean Well RS-25-24", 1, "ea", "servo supply"),
    ("Electronics", "Elecrow 6-axis CNC board", 1, "ea", "125 x 85 mm"),
    ("Electronics", "TB6600 stepper driver", 3, "ea", "96.5 x 67.7 x 57 mm"),
    ("Electronics", "LM2596 buck, adjustable", 1, "ea", "set to 6.0 V for the MG996R"),
    ("Electronics", "TowerPro MG996R servo", 1, "ea", "already owned"),
    ("Enclosure", "UN4412 hard carry case", 2, "ea", "442 x 265 x 124 internal; power box + control box"),
    ("Enclosure", "IEC C14 inlet, fused + switched", 1, "ea", "power box"),
    ("Consumable", "Heatshrink, assorted", 1, "pack", ""),
    ("Consumable", "Cable ties + adhesive mounts", 1, "pack", ""),
    ("Consumable", "Cable gland / grommet", 2, "ea", "every hole the harness passes through"),
    ("Tool", "Ferrule crimper, 4-indent, 0.25-6 mm^2", 1, "ea", "NOT a flat-jaw lug crimper"),
]


def extrusion():
    for profile, pieces in sorted(stock.gather().items()):
        counts = defaultdict(int)
        for length, _ in pieces:
            counts[length] += 1
        for length in sorted(counts, reverse=True):
            yield ("Structure", f"{profile} extrusion, {length:.0f} mm", counts[length], "ea", "")
        bars = stock.pack([l for l, _ in pieces], 1000.0)
        yield ("Structure", f"{profile} stock to buy", len(bars), "x 1 m", "first-fit, kerf allowed")


def din_hardware():
    """Rail, blocks, combs and duct for BOTH boxes, counted off their layouts.

    The control box used to carry lever distribution blocks because a DIN block
    looked unwirable in a 62 mm bay. That was wrong -- the case's 124 mm is base
    plus lid, so a block on the floor has the whole cavity. Both boxes are on
    rail now and the counts come from the two rail schedules.
    """
    boxes = [("power box", psu_layout), ("control box", ctrl_layout)]
    kinds, rail_mm, combs = defaultdict(int), 0.0, defaultdict(int)
    duct, clips = defaultdict(lambda: [0.0, []]), []
    for label, mod in boxes:
        sched, used = panel.rail_schedule(mod)
        rail_mm += used
        for name, _x, _w, kind, _note in sched:
            kinds[kind] += 1
        for grp in mod.JUMPERS:
            combs[len(grp)] += 1
        for d, (_axis, _c0, _c1, s0, s1) in sorted(mod.DUCTS.items()):
            kind, nom = mod.DUCT_KIND[d]
            if kind == "duct":
                duct[nom][0] += (s1 - s0) / 1000.0
                duct[nom][1].append(f"{label[:5]} {d}")
            else:
                clips.append(f"{label[:5]} {d}")

    yield ("Electronics", "DIN rail TS35, 35 x 7.5 mm", 1, "x 1 m",
           f"{rail_mm:.0f} mm used across both boxes -- cut "
           f"{panel.rail_schedule(psu_layout)[1]:.0f} and "
           f"{panel.rail_schedule(ctrl_layout)[1]:.0f} from one length")
    yield ("Electronics", "DIN end clamp", kinds["clamp"], "ea", "two per rail")
    yield ("Electronics", "MCB, 6 A 1P+N C-curve", 1, "ea", "mains in; protects both supplies")
    yield ("Electronics", "Fuse terminal block, 5 x 20 mm, same family as the blocks",
           kinds["fuse"], "ea",
           "protects the 24 V trunk wiring, not the supply -- the LRS limits itself")
    yield ("Consumable", "Fuse, 5 A 5 x 20 mm, time-lag (T)", 5, "ea", "F1, plus spares")
    yield ("Consumable", "Fuse, 2 A 5 x 20 mm, time-lag (T)", 5, "ea",
           "the IEC inlet's own fuse -- the box draws ~0.2 A at 230 V")
    yield ("Electronics", "Relay, 24 V coil 1 N/O, + DIN socket", 1, "ea",
           "K1; drops only the driver rail on E-stop")
    plain = kinds["L"] + kinds["N"] + kinds["v24"] + kinds["v0"] + kinds["v6"] \
        + kinds["v5"] + kinds["es"] + kinds["pwm"] + kinds["sp"]
    yield ("Electronics", "Feed-through terminal, 2.5 mm^2 screw", plain, "ea",
           f"both boxes; {kinds['sp']} left spare")
    yield ("Electronics", "Earth terminal, 2.5 mm^2 (green/yellow, rail-bonding)",
           kinds["E"], "ea",
           "power box only; commoned by the rail they clamp, not by a comb")
    ways_total = sum(n * w for w, n in combs.items())
    yield ("Electronics", "Insertable jumper comb, 10-way, matching the blocks", 3, "ea",
           f"cut to length: {', '.join(f'{n}x {w}-way' for w, n in sorted(combs.items()))} "
           f"= {ways_total} ways needed")
    yield ("Electronics", "E-stop button, 22 mm, N/C", 1, "ea",
           "lives on the machine, not on a box; the box carries the loop connector")
    for nom in sorted(duct):
        run, names = duct[nom]
        yield ("Electronics", f"Slotted wiring duct + lid, {nom:.0f} mm wide",
               f"{run:.2f}", "m", ", ".join(names))
    if clips:
        yield ("Consumable", "P-clip, 6 mm, adhesive", 2 * len(clips), "ea",
               ", ".join(clips) + " -- too few conductors to be worth a duct")


def harness():
    """Wire and ferrules, counted from both routed layouts.

    Both boxes are routed now, so these lengths are real and SLACK is already in
    them. What is still open is the cable between the boxes and out to the
    machine, because that depends on where the two cases end up on the table.
    """
    by_gauge, ends = defaultdict(float), defaultdict(int)
    for mod in (psu_layout, ctrl_layout):
        routes, _used = panel.build_routes(mod)
        for r in routes:
            by_gauge[r["mm2"]] += r["len"]
            ends[r["mm2"]] += 2
    for g in sorted(by_gauge, reverse=True):
        yield ("Consumable", f"Wire, {g:g} mm^2 stranded 300/500 V", f"{by_gauge[g]/1000:.2f}",
               "m", f"inside the boxes, routed; {ends[g]} ends")
    for g in sorted(ends, reverse=True):
        colour = (psu_layout.FERRULE.get(g) or ctrl_layout.FERRULE[g]).split()[1]
        yield ("Consumable", f"Bootlace ferrule, {g:g} mm^2 ({colour})", ends[g], "ea",
               "never tin a stranded end with solder -- it creeps and loosens")

    for g, why in ((0.75, "24 V and 6 V between the boxes"),
                   (2.5,  "ground between the boxes -- two sizes up on purpose"),
                   (0.5,  "motor phases, box to machine"),
                   (0.25, "endstops and the servo signal, box to machine")):
        yield ("Consumable", f"Cable, {g:g} mm^2 (box to box, box to machine)", "TBD", "m",
               f"{why}; needs the cases placed on the table")


def connectors():
    """Panel cutouts, counted per box off case.BOXES."""
    from collections import Counter
    kinds = Counter()
    for box, spec in case.BOXES.items():
        for name, note in spec["panel"]:
            if name.startswith("gx16"):
                kinds["GX16-" + name.split("_")[1] + " aviator, panel mount"] += 1
            elif name.startswith("usb"):
                kinds["USB-C panel mount"] += 1
            elif name.startswith("link"):
                kinds["GX16-6 aviator (inter-box link, 2 ways spare)"] += 1
            elif name.startswith("spare"):
                kinds["-- spare panel position, left free"] += 1
            elif name.startswith("mains_switch"):
                kinds["Rocker switch, panel mount"] += 1
    for key in sorted(kinds):
        if key.startswith("--"):
            yield ("Enclosure", key, kinds[key], "ea", "for a display or control later")
        else:
            yield ("Enclosure", key, kinds[key], "ea", "")
    yield ("Enclosure", "Fan, 24 V axial", len(case.BOXES), "ea",
           "insurance, not cooling -- 11 W total. The model still says 60 mm; the one in hand is 40 mm")
    yield ("Enclosure", "Fan guard + filter", len(case.BOXES), "ea",
           "size follows the fan")


def sheet():
    yield ("Structure", f"Steel sheet {DECK_X:.0f} x {DECK_Y:.0f} x {DECK_T:g} mm", 1, "ea",
           f"{deck_mod.mass():.1f} kg; ferritic (430) if you want magnets -- 304 is not magnetic")
    yield ("Structure", "M5 x 12 screw + drop-in T-nut", len(deck_mod.hole_positions()), "ea",
           "deck to frame; see README on head clearance")


def rows():
    out = list(extrusion()) + list(sheet()) + list(BOUGHT) + list(connectors()) \
        + list(din_hardware()) + list(harness())
    order = ["Structure", "Motion", "Electronics", "Enclosure", "Consumable", "Tool"]
    return sorted(out, key=lambda r: (order.index(r[0]), r[1]))


def main(as_csv=False):
    data = rows()
    if as_csv:
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["category", "item", "qty", "unit", "note"])
        w.writerows(data)
        print(buf.getvalue(), end="")
        return 0

    group = None
    for cat, item, qty, unit, note in data:
        if cat != group:
            print(f"\n{cat.upper()}")
            group = cat
        q = f"{qty:g}" if isinstance(qty, (int, float)) else str(qty)
        print(f"  {q:>5} {unit:<7} {item}" + (f"   -- {note}" if note else ""))
    print(f"\n{len(data)} line items")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", action="store_true")
    raise SystemExit(main(ap.parse_args().csv))
