#!/usr/bin/env python3
"""Route the case harness, find the conflicts, and search for a better layout.

    python3 hardware/wiring.py            # report the current layout
    python3 hardware/wiring.py --search   # try connector orderings, print the best

Every bundle in the lid is modelled as a source, a destination, a conductor
count and a kind. Each is routed as an L -- wires in a box turn square corners,
they do not go as the crow flies -- and the result is scored on four things:

    obstruction   a bundle crossing a component it does not belong to. This is
                  the hard failure: you cannot route through a TB6600.
    crossing      two bundles crossing each other. Each one is a place where
                  something has to lift over something else.
    separation    mains or motor-phase running close to a signal bundle.
    length        total conductor-millimetres, which is both cost and noise.

Geometry comes from case.py, so this cannot drift from the model.
"""

import argparse
import itertools
import pathlib
import sys
from dataclasses import dataclass

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "parts"))

import case  # noqa: E402

# kind -> (is_noisy, weight per conductor-mm)
KINDS = {
    "mains":  (True,  1.0),
    "phase":  (True,  1.0),   # motor phases: chopped current, noisy
    "power":  (False, 1.0),   # DC rails
    "signal": (False, 1.5),   # step/dir/endstop
    "pwm":    (False, 1.5),   # the servo line, single-ended and timing-critical
    "usb":    (False, 1.0),   # differential and short by nature
}

# How long a run of each kind may get before it starts costing. USB is absent
# on purpose: it is differential, so length is not the thing that hurts it, and
# leaving it in here makes the optimiser trade a robust 4-wire bundle against a
# fragile 1-wire one and get the answer backwards.
STRETCH_LIMIT = {"signal": 200.0, "pwm": 150.0}

# Bundles inside the lid. The base is trivially short and is not routed.
# A driver endpoint may name a terminal block: "tb6600_x1:sig" or ":pwr".
# "hinge" is the edge the two bays talk across.
LID_NETS = [
    ("step_x1",   "elecrow_6x", "tb6600_x1:sig",  4, "signal"),
    ("step_x2",   "elecrow_6x", "tb6600_x2:sig",  4, "signal"),
    ("step_y",    "elecrow_6x", "tb6600_y:sig",   4, "signal"),
    ("phase_x1",  "tb6600_x1:pwr",  "gx16_5_x1",  4, "phase"),
    ("phase_x2",  "tb6600_x2:pwr",  "gx16_5_x2",  4, "phase"),
    ("phase_y",   "tb6600_y:pwr",   "gx16_5_y",   4, "phase"),
    ("endstop_x", "gx16_3_endstop_x", "elecrow_6x", 3, "signal"),
    ("endstop_y", "gx16_3_endstop_y", "elecrow_6x", 3, "signal"),
    ("servo_sig", "gx16_4_servo", "elecrow_6x", 1, "pwm"),
    ("servo_pwr", "hinge",      "gx16_4_servo", 2, "power"),
    ("usb",       "usb_c",      "elecrow_6x", 4, "usb"),
    ("vmot_x1",   "hinge",      "tb6600_x1:pwr",  2, "power"),
    ("vmot_x2",   "hinge",      "tb6600_x2:pwr",  2, "power"),
    ("vmot_y",    "hinge",      "tb6600_y:pwr",   2, "power"),
    ("vmot_board", "hinge",     "elecrow_6x", 2, "power"),
    # 24 V is already at the nearest driver; running this back to the hinge
    # would mean crossing the whole driver row for no reason.
    ("fan_pwr",   "tb6600_y:pwr", "fan_exhaust", 2, "power"),
]

# The base runs are short and its parts do not move, so these are not searched
# over -- but they are routed and drawn, because a harness you cannot see is a
# harness you cannot check.
BASE_NETS = [
    ("mains_main",  "iec_inlet",     "psu_24v_main",  3, "mains"),
    ("mains_servo", "iec_inlet",     "psu_24v_servo", 3, "mains"),
    ("rail_24v",    "psu_24v_main",  "bus_24v",       2, "power"),
    ("rail_gnd",    "psu_24v_main",  "bus_ground",    2, "power"),
    ("servo_in",    "psu_24v_servo", "buck_servo",    2, "power"),
    ("servo_out",   "buck_servo",    "hinge",         2, "power"),
    ("vmot_up",     "bus_24v",       "hinge",         2, "power"),
    ("gnd_up",      "bus_ground",    "hinge",         2, "power"),
    # The intake fan sits at the far end from the bus; it takes its 24 V from
    # the main supply's own terminals, which are right beside it.
    ("fan_in_pwr",  "psu_24v_main",  "fan_intake",    2, "power"),
]

NETS = [(n, a, b, c, k, "lid") for n, a, b, c, k in LID_NETS] + \
       [(n, a, b, c, k, "base") for n, a, b, c, k in BASE_NETS]

CLEARANCE = 12.0        # mm a noisy bundle should keep from a signal bundle
# Total conductor-mm alone undervalues a thin, noise-sensitive line: the servo
# PWM is a single wire, so an optimiser will happily park it at the far end of
# the box to free a better slot for a four-wire bundle. FINDINGS.md section 7
# is a long argument about the servo being marginal, so length on that line is
# penalised on its own terms rather than by conductor count.


@dataclass(frozen=True)
class Box2:
    name: str
    x: float
    y: float
    w: float
    d: float

    def contains(self, px, py, pad=0.0):
        return (abs(px - self.x) <= self.w / 2 + pad
                and abs(py - self.y) <= self.d / 2 + pad)

    def port(self, toward_x, offset=0.0):
        """Where wires leave: on the edge facing the lane.

        `offset` shifts along that edge, which is how a TB6600's two terminal
        blocks are told apart -- signal leaves one end, motor phases the other.
        Treating them as one point is what made step/dir look like it ran
        alongside its own phases.
        """
        side = self.w / 2 if toward_x > self.x else -self.w / 2
        return (self.x + side, self.y + offset)


# A layout is where the three groups sit across the lid, plus where the board
# sits along it. Everything else follows.
def current_layout():
    board = next(p for p in case.LID_PARTS if p[0] == "elecrow_6x")
    drv = next(p for p in case.LID_PARTS if p[0].startswith("tb6600"))
    return {"board_x": board[2][0], "board_y": board[2][1],
            "driver_x": drv[2][0], "lane_x": case.LANE_X}


def base_geometry():
    """Base-bay obstacles and connection points."""
    boxes = {}
    for name, (w, d, _), (x, y), _, _ in case.BASE_PARTS:
        boxes[name] = Box2(name, x, y, w, d)
    for name, bay, (x, y), _ in case.FANS:
        if bay == "base":
            boxes[name] = Box2(name, x, y, case.FAN_SIZE, case.FAN_THICK)
    return boxes, {}


def geometry(layout=None, panel_order=None):
    """Lid components and connector points, as the router sees them.

    Connector bodies hang into the bay, so they are obstacles as well as
    endpoints -- leaving them out was why the first pass thought a route could
    pass straight through the lane.
    """
    layout = layout or current_layout()
    boxes = {}

    for name, (w, d, _), (x, y), _, _ in case.LID_PARTS:
        if name == "elecrow_6x":
            x, y = layout["board_x"], layout["board_y"]
        elif name.startswith("tb6600"):
            x = layout["driver_x"]
        boxes[name] = Box2(name, x, y, w, d)

    for name, bay, (x, y), _ in case.FANS:
        if bay == "lid":
            boxes[name] = Box2(name, x, y, case.FAN_SIZE, case.FAN_THICK)

    slots = sorted(y for _, _, (_, y), _ in case.PANEL)
    names = list(panel_order) if panel_order else [n for n, _, _, _ in case.PANEL]

    points = {}
    for n, y in zip(names, slots):
        points[n] = (layout["lane_x"], y)
        boxes[n] = Box2(n, layout["lane_x"], y, case.PANEL_BODY, case.PANEL_BODY)

    # The hinge is an edge, not a point: power can cross it anywhere along its
    # length, so it resolves per-net to whatever Y suits the destination.
    points["hinge"] = None
    return boxes, points


TERMINAL_SPLIT = 0.25    # of the driver's depth, either side of centre


def _centre(name, boxes, points):
    base = name.split(":")[0]
    if base == "hinge":
        return (case.CASE_INT[0] / 2, 0.0)
    if base in points:
        return points[base]
    b = boxes[base]
    return (b.x, b.y)


def _endpoint(name, boxes, points, toward, other=None):
    """Where a bundle leaves a component.

    `toward` is the other end of the bundle, not a fixed lane: a part should
    present its terminals to whatever it is wired to. Pointing everything at
    the lid's lane made base parts route out of their far side and straight
    back through their neighbours.
    """
    base, _, block = name.partition(":")
    if base == "hinge":
        y = other[1] if other else 0.0
        limit = case.CASE_INT[1] / 2
        return (case.CASE_INT[0] / 2, max(-limit, min(limit, y)))
    if base in points:
        return points[base]
    box = boxes[base]
    offset = 0.0
    if block == "sig":
        offset = -box.d * TERMINAL_SPLIT
    elif block == "pwr":
        offset = box.d * TERMINAL_SPLIT
    return box.port(toward, offset)


DETOURS = (0.0, 25.0, -25.0, 50.0, -50.0, 80.0, -80.0)


def _candidates(a, b):
    """Every rectilinear path worth trying between two points.

    Two Ls, plus Z-shaped detours offset to either side. Without the detours a
    bundle whose ends share a coordinate has exactly one possible path, and if
    something sits on it the router can only report the collision -- it cannot
    route around, which is what a person would obviously do.
    """
    out = [[(a, (a[0], b[1])), ((a[0], b[1]), b)],
           [(a, (b[0], a[1])), ((b[0], a[1]), b)]]

    for off in DETOURS[1:]:
        y = a[1] + off
        out.append([(a, (a[0], y)), ((a[0], y), (b[0], y)), ((b[0], y), b)])
        x = a[0] + off
        out.append([(a, (x, a[1])), ((x, a[1]), (x, b[1])), ((x, b[1]), b)])
    return out


def _hits(seg, box, pad=0.0):
    """Does a rectilinear segment pass through this box?"""
    (x0, y0), (x1, y1) = seg
    lo_x, hi_x = min(x0, x1), max(x0, x1)
    lo_y, hi_y = min(y0, y1), max(y0, y1)
    return (hi_x >= box.x - box.w / 2 - pad and lo_x <= box.x + box.w / 2 + pad
            and hi_y >= box.y - box.d / 2 - pad and lo_y <= box.y + box.d / 2 + pad)


def _cross(s1, s2):
    """Do two axis-aligned segments cross? (shared endpoints do not count)"""
    (a, b), (c, d) = s1, s2
    a_vert, c_vert = a[0] == b[0], c[0] == d[0]
    if a_vert == c_vert:
        return False
    if not a_vert:
        a, b, c, d = c, d, a, b
    x = a[0]
    lo_y, hi_y = sorted((a[1], b[1]))
    y = c[1]
    lo_x, hi_x = sorted((c[0], d[0]))
    return lo_x < x < hi_x and lo_y < y < hi_y


def route(layout=None, panel_order=None):
    """Route every net, choosing the L that clears the most obstacles."""
    boxes, points = geometry(layout, panel_order)
    routed = []

    base_boxes, base_points = base_geometry()

    for name, src, dst, n, kind, bay in NETS:
        bx, pts = (boxes, points) if bay == "lid" else (base_boxes, base_points)
        ca, cb = _centre(src, bx, pts), _centre(dst, bx, pts)
        if src == "hinge":
            b = _endpoint(dst, bx, pts, toward=ca[0])
            a = _endpoint(src, bx, pts, toward=cb[0], other=b)
        else:
            a = _endpoint(src, bx, pts, toward=cb[0])
            b = _endpoint(dst, bx, pts, toward=ca[0], other=a)
        own = {src.split(":")[0], dst.split(":")[0]}

        best = None
        for segs in _candidates(a, b):
            if any(abs(s[0][0] - s[1][0]) + abs(s[0][1] - s[1][1]) < 1e-9 for s in segs):
                segs = [s for s in segs if abs(s[0][0] - s[1][0]) + abs(s[0][1] - s[1][1]) > 1e-9]
            if not segs:
                continue
            blocked = sum(1 for s in segs for ob in bx.values()
                          if ob.name not in own and _hits(s, ob))
            length = sum(abs(s[1][0] - s[0][0]) + abs(s[1][1] - s[0][1]) for s in segs)
            cand = (blocked, length, segs)
            if best is None or cand[:2] < best[:2]:
                best = cand
        if best is None:
            best = (0, 0.0, [])

        blocked, length, segs = best
        routed.append({"name": name, "kind": kind, "n": n, "segs": segs,
                       "len": length, "blocked": blocked, "bay": bay,
                       "src": src, "dst": dst})
    return routed, boxes


def analyse(layout=None, panel_order=None):
    routed, _ = route(layout, panel_order)

    obstruction = sum(r["blocked"] for r in routed)
    total = sum(r["len"] * r["n"] for r in routed)

    crossings, near = [], []
    for i, r1 in enumerate(routed):
        for r2 in routed[i + 1:]:
            if r1["bay"] != r2["bay"]:
                continue
            if any(_cross(s1, s2) for s1 in r1["segs"] for s2 in r2["segs"]):
                crossings.append((r1["name"], r2["name"]))
            noisy1, noisy2 = KINDS[r1["kind"]][0], KINDS[r2["kind"]][0]
            quiet = {"signal", "pwm", "usb"}
            if (noisy1 and r2["kind"] in quiet) or (noisy2 and r1["kind"] in quiet):
                for s1 in r1["segs"]:
                    for s2 in r2["segs"]:
                        if _parallel_close(s1, s2, CLEARANCE):
                            near.append((r1["name"], r2["name"]))
                            break
                    else:
                        continue
                    break

    stretched = [(r["name"], r["len"], STRETCH_LIMIT[r["kind"]]) for r in routed
                 if r["kind"] in STRETCH_LIMIT and r["len"] > STRETCH_LIMIT[r["kind"]]]
    stretch_cost = sum(l - lim for _, l, lim in stretched) * 3.0

    score = (obstruction * 10000 + len(crossings) * 500 + len(near) * 250
             + stretch_cost + total / 100.0)
    return {"routed": routed, "obstruction": obstruction, "crossings": crossings,
            "near": near, "total": total, "stretched": stretched, "score": score}


def _parallel_close(s1, s2, gap):
    """Two parallel segments running alongside each other within `gap`."""
    (a, b), (c, d) = s1, s2
    v1, v2 = a[0] == b[0], c[0] == d[0]
    if v1 != v2:
        return False
    if v1:
        if abs(a[0] - c[0]) > gap:
            return False
        lo1, hi1 = sorted((a[1], b[1]))
        lo2, hi2 = sorted((c[1], d[1]))
    else:
        if abs(a[1] - c[1]) > gap:
            return False
        lo1, hi1 = sorted((a[0], b[0]))
        lo2, hi2 = sorted((c[0], d[0]))
    return min(hi1, hi2) - max(lo1, lo2) > gap


def report(layout=None, panel_order=None):
    r = analyse(layout, panel_order)
    lines = [f"{len(r['routed'])} bundles, {sum(x['n'] for x in r['routed'])} conductors",
             f"  obstructions   {r['obstruction']}",
             f"  crossings      {len(r['crossings'])}",
             f"  noisy-adjacent {len(r['near'])}",
             f"  conductor-mm   {r['total']:.0f}",
             f"  score          {r['score']:.1f}   (lower is better)", ""]
    for x in sorted(r["routed"], key=lambda v: -v["len"]):
        flag = "  <-- BLOCKED" if x["blocked"] else ""
        lines.append(f"   {x['name']:12s} {x['kind']:6s} {x['n']}w  {x['len']:5.0f} mm{flag}")
    if r["crossings"]:
        lines += ["", "  crossings:"] + [f"    {a} x {b}" for a, b in r["crossings"]]
    if r["near"]:
        lines += ["", "  noisy running alongside signal:"] + [f"    {a} || {b}" for a, b in r["near"]]
    if r["stretched"]:
        lines += ["", "  runs past their length budget:"] + [
            f"    {n} at {l:.0f} mm (limit {lim:.0f})" for n, l, lim in r["stretched"]]
    return lines


BOARD_XS = (-94.0,)
BOARD_YS = (-150.0, -120.0, -60.0, 0.0, 60.0, 95.0, 130.0)


def search():
    """Best board position and connector ordering, by score."""
    names = [n for n, _, _, _ in case.PANEL]
    base = current_layout()
    best = None
    for bx in BOARD_XS:
        for by in BOARD_YS:
            layout = dict(base, board_x=bx, board_y=by)
            for order in itertools.permutations(names):
                s = analyse(layout, order)["score"]
                if best is None or s < best[0]:
                    best = (s, layout, order)
    return best


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--search", action="store_true")
    args = ap.parse_args()

    print("CURRENT LAYOUT")
    for line in report():
        print(" ", line)

    if args.search:
        score, layout, order = search()
        print(f"\nBEST FOUND  score {score:.1f}")
        print(f"   board at ({layout['board_x']:+.0f}, {layout['board_y']:+.0f})")
        slots = sorted(y for _, _, (_, y), _ in case.PANEL)
        for n, y in zip(order, slots):
            print(f"   {n:18s} at y {y:+.0f}")
        print()
        for line in report(layout, order):
            print(" ", line)


# Height the harness runs at in each bay: tucked near the shell, clear of the
# components, dropping to a terminal only at its ends.
LID_RUN_Z = case.LID_CEILING - 14.0
BASE_RUN_Z = case.CAVITY_Z0 + 12.0
HINGE_Z = case.SPLIT_Z


def _terminal_z(name, bay):
    """Height of the terminal a bundle lands on."""
    base = name.split(":")[0]
    if base == "hinge":
        return HINGE_Z

    for n, b, _, _ in case.FANS:
        if n == base:
            z0 = case.CAVITY_Z0 if b == "base" else case.SPLIT_Z
            return z0 + case.FAN_SIZE / 2

    for n, _, _, _ in case.PANEL:
        if n == base:
            return case.LID_CEILING - case.PANEL_DEPTH

    for n, (_, _, h), _, _, _ in case.BASE_PARTS:
        if n == base:
            return case.CAVITY_Z0 + h / 2
    for n, (_, _, h), _, _, _ in case.LID_PARTS:
        if n == base:
            return case.LID_CEILING - h / 2
    return LID_RUN_Z if bay == "lid" else BASE_RUN_Z


def polylines_3d(layout=None, panel_order=None):
    """Every bundle as a 3D polyline, for the viewer.

    The run height is constant within a bay -- the router has already proved
    nothing is in the way there -- with a vertical drop onto each terminal.
    """
    routed, _ = route(layout, panel_order)
    out = []

    for r in routed:
        if not r["segs"]:
            continue
        run_z = LID_RUN_Z if r["bay"] == "lid" else BASE_RUN_Z

        flat = [r["segs"][0][0]] + [s[1] for s in r["segs"]]
        pts = [[flat[0][0], flat[0][1], _terminal_z(r["src"], r["bay"])]]
        pts += [[x, y, run_z] for x, y in flat]
        pts.append([flat[-1][0], flat[-1][1], _terminal_z(r["dst"], r["bay"])])

        out.append({"name": r["name"], "kind": r["kind"], "n": r["n"],
                    "bay": r["bay"], "len": round(r["len"], 1), "pts": pts})
    return out
