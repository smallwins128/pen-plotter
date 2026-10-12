"""Cable-duct clearance on the base plates: which runs fit, and at what height.

A ring of two ducts round each box, inset from the walls (power/motor outside, signal inside, 12 mm apart),
plus a bridge across the middle: between the two PSUs (power box), between the board and the drivers
(control box). Each run is tested at several duct heights against everything in the whole-assembly model
(assembly_check.items): walls, lips, fans, panels and their screws, GX sockets, rivnuts, plate screw heads,
and the placeholder interior parts. Needs 2 mm clear, like the rest of the assembly.

    python3 hardware/sheet/duct_check.py            # default layout
    python3 hardware/sheet/duct_check.py --inset 30 # ring further in
"""
import argparse
import sys

import assembly_check as A
import enclosure as E

W, D = E.W, E.D
PLATE_TOP = E.PLATE_Y[1]
HEIGHTS = (25.0, 16.0, 15.0, 12.0)
POWER_W, SIGNAL_W, SEP = 25.0, 15.0, 12.0
BRIDGE_X = {"control": None, "power": None}       # filled from the parts below


def bridge_x(kind, items):
    """Centre of the gap the bridge runs through: board / drivers (control), 24 V / 12 V PSU (power)."""
    by = {i.name: i for i in items}
    if kind == "control":
        drv = max(i.b[1] for i in items if i.name.startswith("driver D"))
        brd = by["FluidNC board on 10 mm posts"].b[0]
        return (drv + brd) / 2, brd - drv
    a, b = by["24 V PSU"], by["12 V PSU"]
    return (a.b[1] + b.b[0]) / 2, b.b[0] - a.b[1]


def runs(kind, inset, items):
    """Duct runs as (name, x0, x1, z0, z1) on the plate."""
    xi, zi = W / 2, D / 2                          # inner faces of the walls
    out = []
    for name, w, off in (("power/motor", POWER_W, inset), ("signal", SIGNAL_W, inset + POWER_W + SEP)):
        x0, x1, z0, z1 = -xi + off, xi - off, -zi + off, zi - off
        out += [(f"{name} · front", x0, x1, z1 - w, z1), (f"{name} · back", x0, x1, z0, z0 + w),
                (f"{name} · left", x0, x0 + w, z0, z1), (f"{name} · right", x1 - w, x1, z0, z1)]
    bx, room = bridge_x(kind, items)
    zlo, zhi = -zi + inset + POWER_W, zi - inset - POWER_W
    what = "board / drivers" if kind == "control" else "PSU / PSU"
    out.append((f"bridge between {what} ({room:.0f} mm gap)", bx - SIGNAL_W / 2, bx + SIGNAL_W / 2, zlo, zhi))
    return out


def blockers(kind, run, h, items, soft=True):
    name, x0, x1, z0, z1 = run
    d = A.Item(name, "duct", x0, x1, PLATE_TOP, PLATE_TOP + h, z0, z1)
    hits = []
    for it in items:
        if it.tag in ("plate", "standoff", "foot", "peg") or (it.soft and not soft):
            continue                               # the plate it sits on; things under the plate or outside the box
        if it.b[3] <= PLATE_TOP + 1e-6 or it.b[2] >= PLATE_TOP + h + A.GAP:
            continue
        g = A.gap(d, it)
        if g < A.GAP:
            hits.append((g, it.name.replace("control_body: ", "").replace("power_body: ", "")))
    return sorted(hits)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--inset", type=float, default=27.0, help="outer duct edge from the inside of the walls, mm")
    a = ap.parse_args(argv)
    bad = 0
    for kind in ("control", "power"):
        items = A.items(kind)
        print(f"\n{kind.upper()} BOX  (ring {a.inset:g} mm in from the walls; power/motor {POWER_W:g} wide outside, "
              f"signal {SIGNAL_W:g} wide inside, {SEP:g} apart)")
        for r in runs(kind, a.inset, items):
            hard = [h for h in HEIGHTS if not blockers(kind, r, h, items, soft=False)]
            allp = [h for h in HEIGHTS if not blockers(kind, r, h, items)]
            th, ta = (max(hard) if hard else 0), (max(allp) if allp else 0)
            print(f"  {r[0]:50s} box: {'up to %2.0f mm' % th if th else 'NO FIT':12s}  with today's parts: {'up to %2.0f mm' % ta if ta else 'NO FIT'}")
            if th < 25:
                for g, n in blockers(kind, r, min(h for h in HEIGHTS if h > th), items, soft=False)[:3]:
                    print(f"      box:   {n}  ({g:.1f} mm)")
            if ta < th:
                for g, n in [q for q in blockers(kind, r, min(h for h in HEIGHTS if h > ta), items) if q not in blockers(kind, r, min(h for h in HEIGHTS if h > ta), items, soft=False)][:3]:
                    print(f"      parts: {n}  ({g:.1f} mm)")
            bad += not hard
        # the room left inside the ring for the parts
        xi, zi = W / 2, D / 2; o = a.inset + POWER_W + SEP + SIGNAL_W + 2
        print(f"  room inside the ring for parts: {2 * (xi - o):.0f} x {2 * (zi - o):.0f} mm (x by depth)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
