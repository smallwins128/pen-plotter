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
import deck as deck_mod         # noqa: E402
import stock                    # noqa: E402
import wiring                   # noqa: E402
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
    ("Enclosure", "UN4020 hard carry case", 1, "ea", "413 x 352 x 206 mm"),
    ("Enclosure", "IEC C14 inlet, fused + switched", 1, "ea", "panel mount"),
    ("Enclosure", "3-in/6-out lever splitter", 1, "ea", "L/N/E; label it, the colours are not mains code"),
    ("Enclosure", "DIN rail, 35 mm", 0.3, "m", "cut to suit both strips"),
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


def terminals():
    total_blocks = 0
    for name, (pos, neg) in case.DIST_WAYS.items():
        total_blocks += pos + neg
        yield ("Enclosure", f"DIN terminal block 2.5 mm^2 ({name})", pos + neg, "ea",
               f"{pos}x 24 V + {neg}x 0 V")
    yield ("Enclosure", "DIN end clamp", 2 * len(case.DIST_WAYS), "ea", "one each end of each strip")
    yield ("Enclosure", "Jumper comb, 2/4/10 way", 1, "set",
           f"what turns {total_blocks} blocks into buses")


def harness():
    """Wire by gauge and ferrules by size, both counted off the routed harness."""
    wire = defaultdict(float)
    ferrules = defaultdict(int)

    for name, src, dst, n, kind, bay in wiring.NETS:
        g = GAUGE[kind]
        routed = [r for r in wiring.route()[0] if r["name"] == name]
        length = routed[0]["len"] if routed else 0.0
        wire[g] += length * n * SLACK / 1000.0

        screw_ends = sum(
            0 if (e.split(":")[0] == "hinge" or e.split(":")[0].startswith("gx16")
                  or e.split(":")[0] == "usb_c") else 1
            for e in (src, dst))
        ferrules[g] += n * screw_ends

    for g in sorted(wire, reverse=True):
        yield ("Consumable", f"Wire, {g:g} mm^2 stranded", round(wire[g] + 0.5), "m",
               f"routed length x {SLACK} for slack; case only, not the machine harness")
    yield ("Consumable", "Wire, 1.5 mm^2 stranded", 2, "m", "24 V trunk, 9 A -- sized by load not by route")
    for g in sorted(ferrules, reverse=True):
        need = ferrules[g]
        yield ("Consumable", f"Ferrule, insulated, {g:g} mm^2", int(need * 1.6 // 50 + 1) * 50, "ea",
               f"{need} ends counted, bought in 50s with spares")


def connectors():
    kinds = defaultdict(int)
    for name, _, _, note in case.PANEL:
        key = ("USB-C panel mount" if name.startswith("usb")
               else "GX16-" + name.split("_")[1] + " aviator, panel mount")
        kinds[key] += 1
    for key in sorted(kinds):
        yield ("Enclosure", key, kinds[key], "ea", "")
    for name, bay, _, note in case.FANS:
        yield ("Enclosure", f"Fan, 80 mm 24 V axial ({bay})", 1, "ea", note)
    yield ("Enclosure", "Fan guard + filter, 80 mm", len(case.FANS), "ea", "filter on the intake at least")


def sheet():
    yield ("Structure", f"Steel sheet {DECK_X:.0f} x {DECK_Y:.0f} x {DECK_T:g} mm", 1, "ea",
           f"{deck_mod.mass():.1f} kg; ferritic (430) if you want magnets -- 304 is not magnetic")
    yield ("Structure", "M5 x 12 screw + drop-in T-nut", len(deck_mod.hole_positions()), "ea",
           "deck to frame; see README on head clearance")


def rows():
    out = list(extrusion()) + list(sheet()) + list(BOUGHT) + list(connectors()) \
        + list(terminals()) + list(harness())
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
        q = f"{qty:g}"
        print(f"  {q:>5} {unit:<7} {item}" + (f"   -- {note}" if note else ""))
    print(f"\n{len(data)} line items")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", action="store_true")
    raise SystemExit(main(ap.parse_args().csv))
