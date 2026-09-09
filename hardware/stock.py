#!/usr/bin/env python3
"""What to buy, and how to cut it.

    python3 hardware/stock.py            # every profile
    python3 hardware/stock.py 20x20      # just one

Collects the cut lists from every part, groups them by profile, then packs the
pieces onto stock bars first-fit-decreasing so you can see how many to order and
what comes off each one.

Saw kerf is taken off for every cut, which is the difference between a plan that
works and one where the last piece on a bar is 3 mm short.
"""

import sys
import pathlib
from collections import defaultdict

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "parts"))

KERF = 3.0                       # typical mitre-saw blade in aluminium
STOCK_LENGTHS = (1000.0, 2000.0)


def gather():
    """profile -> [(length, label), ...] for every linear piece in the design."""
    import make

    pieces = defaultdict(list)
    for name, module in make._parts().items():
        if name == "assembly":          # would double-count its children
            continue
        cut_list = getattr(module, "cut_list", None)
        if cut_list is None:
            continue
        for row in cut_list():
            qty, length, label = row[0], row[1], row[2]
            profile = row[3] if len(row) > 3 else "?"
            if profile == "sheet":       # not bar stock
                continue
            for _ in range(qty):
                pieces[profile].append((length, label))
    return pieces


def pack(lengths, stock):
    """First-fit-decreasing onto bars of `stock`, allowing a kerf per cut.

    Not optimal in general, but for a handful of pieces it lands on the same
    answer as the optimum and is easy to check by eye.
    """
    bars = []
    for length in sorted(lengths, reverse=True):
        if length > stock:
            raise ValueError(f"{length:g} mm piece does not fit {stock:g} mm stock")
        for bar in bars:
            need = length + (KERF if bar else 0)
            if sum(bar) + KERF * len(bar) + length <= stock:
                bar.append(length)
                break
        else:
            bars.append([length])
    return bars


def report(only=None):
    pieces = gather()
    out = []

    for profile in sorted(pieces):
        if only and profile != only:
            continue
        rows = pieces[profile]
        total = sum(l for l, _ in rows)

        out.append(f"{profile} extrusion -- {len(rows)} pieces, {total:.0f} mm ({total/1000:.2f} m)")

        counts = defaultdict(list)
        for length, label in rows:
            counts[length].append(label)
        for length in sorted(counts, reverse=True):
            labels = sorted(set(counts[length]))
            out.append(f"    {len(counts[length])} x {length:7.1f} mm   {', '.join(labels)}")

        out.append("")
        for stock in STOCK_LENGTHS:
            bars = pack([l for l, _ in rows], stock)
            waste = len(bars) * stock - total
            out.append(f"  buy {len(bars)} x {stock/1000:.0f} m  "
                       f"({waste:.0f} mm offcut, {waste/(len(bars)*stock)*100:.0f}%)")
            for i, bar in enumerate(bars, 1):
                used = sum(bar) + KERF * (len(bar) - 1)
                cuts = " + ".join(f"{l:g}" for l in bar)
                out.append(f"      bar {i}:  {cuts}   ({stock - used:.0f} mm left)")
            out.append("")
    return out


if __name__ == "__main__":
    only = sys.argv[1] if len(sys.argv) > 1 else None
    for line in report(only):
        print(line)
