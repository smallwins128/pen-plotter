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


def terminals():
    """Lever distribution blocks, one set in the control box.

    Not DIN: a DIN block on its rail stands 58 mm and its screw is near the
    top, which leaves 4 mm of access in the UN4412's 62 mm bay. At 1.7 A the
    lever blocks are more than adequate and they fit.
    """
    for name, (w, d, h), _, _, note in case.check("control"):
        if name.startswith("dist_"):
            yield ("Enclosure", f"Lever distribution block ({note.split(':')[0]})", 1, "ea", note)
    yield ("Enclosure", "3-in/6-out lever splitter", 1, "ea",
           "mains L/N/E in the power box; label it, the colours are not mains code")


def harness():
    """Wire and ferrules cannot be counted until the layout is real.

    The router that produced these numbers is parked (see wiring.py). Rather
    than carry forward figures from a layout that no longer exists, the rows
    say what they depend on.
    """
    for g, why in ((0.75, "24 V and 6 V between the boxes"),
                   (2.5,  "ground between the boxes -- two sizes up on purpose"),
                   (0.5,  "motor phases"),
                   (0.25, "step/dir, endstops, servo signal")):
        yield ("Consumable", f"Wire, {g:g} mm^2 stranded", "TBD", "m",
               f"{why}; length needs the real layout")
    yield ("Consumable", "Ferrule kit, insulated, 0.25-6 mm^2", 1, "kit",
           "assorted; ~100 ends expected across both boxes")


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
                kinds["GX16-4 aviator (inter-box link)"] += 1
            elif name.startswith("spare"):
                kinds["-- spare panel position, left free"] += 1
            elif name.startswith("mains_switch"):
                kinds["Rocker switch, panel mount"] += 1
    for key in sorted(kinds):
        if key.startswith("--"):
            yield ("Enclosure", key, kinds[key], "ea", "for a display or control later")
        else:
            yield ("Enclosure", key, kinds[key], "ea", "")
    yield ("Enclosure", "Fan, 60 mm 24 V axial", len(case.BOXES), "ea",
           "in the lid face; 11 W total means this is insurance, not cooling")
    yield ("Enclosure", "Fan guard + filter, 60 mm", len(case.BOXES), "ea", "")


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
        q = f"{qty:g}" if isinstance(qty, (int, float)) else str(qty)
        print(f"  {q:>5} {unit:<7} {item}" + (f"   -- {note}" if note else ""))
    print(f"\n{len(data)} line items")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", action="store_true")
    raise SystemExit(main(ap.parse_args().csv))
