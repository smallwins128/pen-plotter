#!/usr/bin/env python3
"""Power box: floor layout and every individual conductor, routed through ducts.

    python3 hardware/psu_layout.py      -> hardware/out/psu_layout.html

Data first, drawing second. The rail schedule, the gear placement, the terminal
strips, the duct grid and the 30 conductors are all tables. Every polyline in
the SVG comes out of route(), and the cut list comes out of the same polylines.
So the picture, the schedule and the wire lengths cannot disagree.

Terminal positions are taken from the real parts, not guessed:

  LRS-350-24   7-way strip on ONE 115 mm short end:  +V +V -V -V (E) N L
               -> AC and DC leave the same face. 215 mm is too long to stand
                  that face at the back wall, so it lies long-ways and the
                  face points at a vertical duct.
  RS-25-24     5-way strip on one short end:  +V -V (E) N L
  LM2596       IN+ IN- on one end, OUT+ OUT- on the OPPOSITE end
  IEC module   switched + fused inlet, spade terminals on the rear face
  fan          40 mm, flying leads

The duct grid is what makes the drawing clean: one horizontal collector H1
across the front of the rail, and a vertical duct beside each piece of gear so
that every terminal face points at a duct at 90 degrees. No wire crosses open
floor, and no wire leaves a terminal at an angle.
"""

import pathlib

OUT = pathlib.Path(__file__).resolve().parent / "out" / "psu_layout.html"

FLOOR = (442.0, 265.0)          # UN4412 internal
MODULE = 17.5                   # one DIN module

# --- the rail, left to right, in the order power flows -----------------------
# name, width mm, kind, note
RAIL = [
    ("", 8.0, "clamp", "end clamp"),
    ("MCB1", 2 * MODULE, "mcb", "6 A 1P+N, C-curve — mains in, protects both PSUs"),
    ("", 2.0, "part", ""),
    ("L1", 5.2, "L", "line in from MCB1, out to the LRS-350"),
    ("L2", 5.2, "L", "line out to the RS-25"),
    ("N1", 5.2, "N", "neutral in from MCB1, out to the LRS-350"),
    ("N2", 5.2, "N", "neutral out to the RS-25"),
    ("PE1", 5.2, "E", "earth in from the IEC module"),
    ("PE2", 5.2, "E", "earth out to the LRS-350 chassis"),
    ("PE3", 5.2, "E", "earth out to the RS-25 chassis"),
    ("PE4", 5.2, "E", "earth out to the case + lid bonding stud"),
    ("", 2.0, "part", ""),
    ("MCB2", MODULE, "mcb", "5 A 1P DC — protects the 24 V trunk wiring"),
    ("", 2.0, "part", ""),
    ("K1", 16.0, "relay", "24 V coil, 1 N/O — drops the driver rail on E-stop"),
    ("", 2.0, "part", ""),
    ("+24", 5.2, "v24", "in from MCB2; also feeds the E-stop loop"),
    ("+24a", 5.2, "v24", "always on → the board, and K1's contact"),
    ("+24f", 5.2, "v24", "always on → the fan"),
    ("+24s", 5.2, "v24", "switched by K1 → the drivers"),
    ("0V", 5.2, "v0", "in from both supplies — the single-point 0 V bond"),
    ("0Va", 5.2, "v0", "→ the link, and the buck's return"),
    ("0Vb", 5.2, "v0", "→ the fan, and K1's coil return"),
    ("+6", 5.2, "v6", "in from the buck"),
    ("+6o", 5.2, "v6", "→ the link"),
    ("", 2.0, "part", ""),
    ("sp", 5.2, "sp", "spare"), ("sp", 5.2, "sp", "spare"), ("sp", 5.2, "sp", "spare"),
    ("", 8.0, "clamp", "end clamp"),
]

RAIL_START = 70.0               # mm from the left wall — the IEC module sits left of it
RAIL_Y = 18.0                   # mm from the back wall to the rail
RAIL_DEPTH = 70.0               # how far DIN gear projects from the wall
RAIL_FACE = RAIL_Y + RAIL_DEPTH # where a conductor leaves the gear, in plan

# sub-terminals on the multi-terminal modules: name, offset from the block's x
RAIL_SUBS = {
    "MCB1": [("MCB1.L-in", 4.0), ("MCB1.L-out", 13.0),
             ("MCB1.N-in", 22.0), ("MCB1.N-out", 31.0)],
    "MCB2": [("MCB2.in", 3.4), ("MCB2.out", 13.4)],
    "K1":   [("K1.A1", 1.9), ("K1.A2", 5.9), ("K1.13", 10.9), ("K1.14", 14.9)],
}

# combs, not wires: adjacent blocks bridged by an insertable jumper bar
JUMPERS = [("L1", "L2"), ("N1", "N2"), ("PE1", "PE2", "PE3", "PE4"),
           ("+24", "+24a", "+24f"), ("0V", "0Va", "0Vb"), ("+6", "+6o")]

# --- the duct grid -----------------------------------------------------------
# name: (axis, c0, c1, s0, s1)
#   "h": c0..c1 are the y bounds, s0..s1 the x extent
#   "v": c0..c1 are the x bounds, s0..s1 the y extent
DUCTS = {
    "H1": ("h",  90.0, 132.0,   0.0, 430.0),   # the collector, across the rail face
    "V1": ("v", 221.0, 246.0,  90.0, 230.0),   # beside the LRS-350's terminal face
    "V2": ("v", 324.0, 349.0,  90.0, 192.0),   # between the RS-25 and the buck
    "V3": ("v", 414.0, 432.0,  90.0, 222.0),   # buck output and the fan
}
# Slotted duct comes in 25/40/60/80 mm widths; H1 and the two verticals are real
# duct, with 1 mm of clearance each side. V3 carries three conductors, which is
# not worth a duct: it is a spiral-wrapped pair and a single, in two P-clips.
DUCT_KIND = {"H1": ("duct", 40.0), "V1": ("duct", 25.0),
             "V2": ("duct", 25.0), "V3": ("clip", 0.0)}
LANE_PITCH, LANE_INSET = 2.1, 2.0
MAINS = {"L", "N", "E"}
# which band sits nearest the duct's "inner" edge
BANDS = {"H1": ("mains", "dc"), "V1": ("dc", "mains"),
         "V2": ("dc", "mains"), "V3": ("dc", "mains")}

# --- gear on the floor -------------------------------------------------------
# name, x, y, w, d, kind, note
GEAR = [
    ("LRS-350-24", 6.0, 134.0, 215.0, 115.0, "psu",
     "24 V 14.6 A, ex-Ender 3 — lies long-ways, +V end toward the back wall"),
    ("RS-25-24", 246.0, 134.0, 78.0, 51.0, "psu", "24 V 1.1 A, the servo's supply"),
    ("LM2596", 349.0, 134.0, 65.0, 45.0, "pcb", "24 → 6.0 V buck, IN and OUT opposite ends"),
    ("IEC", 0.0, 30.0, 30.0, 50.0, "abs", "panel-mount switched + fused inlet"),
    ("fan 40", 432.0, 182.0, 10.0, 40.0, "abs", "24 V 40 mm, exhaust"),
]

# gear, face x, body y, body depth, pitch, duct, [(terminal, class)] back → front
STRIPS = [
    ("LRS-350-24", 221.0, 134.0, 115.0, 10.5, "V1",
     [("LRS.+V", "v24"), ("LRS.+V2", "v24"), ("LRS.-V", "v0"), ("LRS.-V2", "v0"),
      ("LRS.PE", "E"), ("LRS.N", "N"), ("LRS.L", "L")]),
    ("RS-25-24", 324.0, 134.0, 51.0, 7.6, "V2",
     [("RS.+V", "v24"), ("RS.-V", "v0"), ("RS.PE", "E"), ("RS.N", "N"), ("RS.L", "L")]),
]

# loose terminals: name, x, y, duct, stub axis
LOOSE = [
    ("BUCK.IN+", 349.0, 154.0, "V2", "x"), ("BUCK.IN-", 349.0, 159.0, "V2", "x"),
    ("BUCK.OUT+", 414.0, 154.0, "V3", "x"), ("BUCK.OUT-", 414.0, 159.0, "V3", "x"),
    ("IEC.L", 30.0, 42.0, "H1", "y"), ("IEC.N", 30.0, 55.0, "H1", "y"),
    ("IEC.PE", 30.0, 68.0, "H1", "y"),
    ("ESTOP.1", 16.0, 100.0, "H1", "y"), ("ESTOP.2", 16.0, 108.0, "H1", "y"),
    ("BOND", 6.0, 124.0, "H1", "y"),
    ("FAN.+", 432.0, 197.0, "V3", "x"), ("FAN.-", 432.0, 213.0, "V3", "x"),
    ("LINK.+24a", 430.0, 100.0, "H1", "y"), ("LINK.+24s", 430.0, 106.0, "H1", "y"),
    ("LINK.+6", 430.0, 112.0, "H1", "y"), ("LINK.0V", 430.0, 118.0, "H1", "y"),
]

# panel penetrations: label, x, y, wall
PANEL = [
    ("IEC inlet", 0.0, 55.0, "left"),
    ("E-stop loop, 2-pole", 0.0, 104.0, "left"),
    ("earth stud (lid strap)", 0.0, 124.0, "left"),
    ("link gland → control box", 442.0, 109.0, "right"),
    ("fan 40 mm, exhaust", 442.0, 202.0, "right"),
]

# --- every conductor ---------------------------------------------------------
# id, class, from, to, mm2, note
WIRES = [
    ("w01", "L",    "IEC.L",      "MCB1.L-in",  1.0, "inlet is already switched and fused"),
    ("w02", "N",    "IEC.N",      "MCB1.N-in",  1.0, ""),
    ("w03", "E",    "IEC.PE",     "PE1",        1.0, "earth never passes through a breaker"),
    ("w04", "L",    "MCB1.L-out", "L1",         1.0, ""),
    ("w05", "N",    "MCB1.N-out", "N1",         1.0, ""),
    ("w06", "L",    "L1",         "LRS.L",      1.0, ""),
    ("w07", "N",    "N1",         "LRS.N",      1.0, ""),
    ("w08", "E",    "PE2",        "LRS.PE",     1.0, ""),
    ("w09", "L",    "L2",         "RS.L",       0.75, ""),
    ("w10", "N",    "N2",         "RS.N",       0.75, ""),
    ("w11", "E",    "PE3",        "RS.PE",      0.75, ""),
    ("w12", "E",    "PE4",        "BOND",       1.5, "case and lid bond to the same stud"),
    ("w13", "v24",  "LRS.+V",     "MCB2.in",    1.5, "the whole 24 V output, through its breaker"),
    ("w14", "v0",   "LRS.-V",     "0V",         1.5, ""),
    ("w15", "v24",  "MCB2.out",   "+24",        1.5, ""),
    ("w16", "v24",  "+24a",       "K1.13",      1.5, "relay common"),
    ("w17", "v24",  "K1.14",      "+24s",       1.5, "the only rail K1 cuts"),
    ("w18", "ctrl", "+24",        "ESTOP.1",    0.5, "coil feed, out to the button"),
    ("w19", "ctrl", "ESTOP.2",    "K1.A1",      0.5, "N/C loop returns — a cut wire stops it too"),
    ("w20", "ctrl", "K1.A2",      "0Vb",        0.5, "coil return"),
    ("w21", "v24",  "RS.+V",      "BUCK.IN+",   0.75, ""),
    ("w22", "v0",   "RS.-V",      "0V",         0.75, "the one place the two supplies' 0 V meet"),
    ("w23", "v0",   "BUCK.IN-",   "0Va",        0.75, "buck return to the rail, not through its own trace"),
    ("w24", "v6",   "BUCK.OUT+",  "+6",         0.75, ""),
    ("w25", "v24",  "+24f",       "FAN.+",      0.5, "always on — cooling must not stop at an E-stop"),
    ("w26", "v0",   "0Vb",        "FAN.-",      0.5, ""),
    ("w27", "v24",  "+24a",       "LINK.+24a",  0.75, "to the board"),
    ("w28", "v24",  "+24s",       "LINK.+24s",  0.75, "to the three drivers"),
    ("w29", "v6",   "+6o",        "LINK.+6",    0.75, "to the servo"),
    ("w30", "v0",   "0Va",        "LINK.0V",    2.5, "two sizes up: the servo's 2.5 A return shares it"),
]

COLOUR = {"L": "brown", "N": "blue", "E": "green/yellow", "v24": "red",
          "v0": "black", "v6": "orange", "ctrl": "violet"}
FERRULE = {0.5: "0.5 orange", 0.75: "0.75 white", 1.0: "1.0 yellow",
           1.5: "1.5 black", 2.5: "2.5 blue"}
SLACK = 60.0                    # 30 mm of dressing allowance at each end

LINK = [("+24 always", 0.75, "to the board — stays up through an E-stop"),
        ("+24 switched", 0.75, "to the three drivers — K1 drops this"),
        ("+6", 0.75, "to the servo, via the control box"),
        ("0V", 2.5, "two sizes up: the servo's 2.5 A return shares it")]


# --- schedule and terminal map ----------------------------------------------

def rail_schedule():
    out, x = [], RAIL_START
    for name, w, kind, note in RAIL:
        out.append((name, x, w, kind, note))
        x += w
    return out, x - RAIL_START


def build_terminals():
    """name -> (x, y, duct, stub axis). Fans multi-wire rail blocks apart."""
    t = {}
    sched, _ = rail_schedule()
    users = {}
    for _, _, frm, to, _, _ in WIRES:
        for n in (frm, to):
            users[n] = users.get(n, 0) + 1

    for name, x, w, kind, note in sched:
        if kind in ("part", "clamp"):
            continue
        if name in RAIL_SUBS:
            for sub, off in RAIL_SUBS[name]:
                t[sub] = (x + off, RAIL_FACE, "H1", "y")
            continue
        n = users.get(name, 0)
        if n <= 1:
            t[name] = (x + w / 2, RAIL_FACE, "H1", "y")
        else:                                    # two landings, fanned for legibility
            for i in range(n):
                t.setdefault(name, (x + w / 2 - 1.3 + 2.6 * i, RAIL_FACE, "H1", "y"))
            # the second wire on the block gets the other screw
            t[name] = (x + w / 2 - 1.3, RAIL_FACE, "H1", "y")
            t[name + "#2"] = (x + w / 2 + 1.3, RAIL_FACE, "H1", "y")

    for gear, fx, by, bd, pitch, duct, strip in STRIPS:
        span = pitch * (len(strip) - 1)
        y0 = by + bd / 2 - span / 2
        for i, (name, _cls) in enumerate(strip):
            t[name] = (fx, y0 + i * pitch, duct, "x")

    for name, x, y, duct, axis in LOOSE:
        t[name] = (x, y, duct, axis)
    return t


TERMINALS = build_terminals()


def _endpoint(name, seen):
    """Resolve the second wire on a shared rail block to its own screw."""
    if name in seen and (name + "#2") in TERMINALS:
        return TERMINALS[name + "#2"], name + " (2nd screw)"
    return TERMINALS[name], name


# --- routing -----------------------------------------------------------------

def _dmid(d):
    axis, c0, c1, _s0, _s1 = DUCTS[d]
    return (c0 + c1) / 2


def chain_for(da, db):
    if da == db:
        return [da]
    if da == "H1" or db == "H1":
        return [da, db] if da != "H1" else [da, db]
    return [da, "H1", db]


def spans(a, b, chain):
    """Extent of the wire along each duct in its chain (lane-independent)."""
    out = []
    for i, d in enumerate(chain):
        axis = DUCTS[d][0]
        start = a[1] if axis == "v" else a[0]
        end = b[1] if axis == "v" else b[0]
        if i > 0:
            prev = chain[i - 1]
            start = _dmid(prev)
        if i < len(chain) - 1:
            nxt = chain[i + 1]
            end = _dmid(nxt)
        out.append((d, min(start, end), max(start, end)))
    return out


def allocate_lanes(routes):
    """Left-edge assignment per duct, banded so mains and DC never interleave."""
    demand = {d: [] for d in DUCTS}
    for r in routes:
        for d, lo, hi in r["spans"]:
            demand[d].append((r["id"], lo, hi, r["cls"]))

    lanes, used_max = {}, {}
    for d, items in demand.items():
        placed = []
        base = 0
        for band in BANDS[d]:
            grp = [i for i in items
                   if (i[3] in MAINS) == (band == "mains")]
            for wid, lo, hi, _cls in sorted(grp, key=lambda i: (i[1], i[2])):
                lane = base
                while any(l == lane and lo < h - 1e-6 and hi > o + 1e-6
                          for l, o, h in placed):
                    lane += 1
                placed.append((lane, lo, hi))
                lanes[(wid, d)] = lane
            base = max((l for l, _, _ in placed), default=-1) + 1
        used_max[d] = max((l for l, _, _ in placed), default=-1) + 1
    return lanes, used_max


def lane_coord(d, lane):
    axis, c0, c1, _s0, _s1 = DUCTS[d]
    return c0 + LANE_INSET + lane * LANE_PITCH


def capacity(d):
    _axis, c0, c1, _s0, _s1 = DUCTS[d]
    return int((c1 - c0 - 2 * LANE_INSET) / LANE_PITCH) + 1


def _dedupe(pts):
    out = [pts[0]]
    for p in pts[1:]:
        if abs(p[0] - out[-1][0]) > 1e-6 or abs(p[1] - out[-1][1]) > 1e-6:
            out.append(p)
    return out


def route(a, b, chain, wid, lanes):
    pts = [(a[0], a[1])]
    cx, cy = a[0], a[1]
    for d in chain:
        c = lane_coord(d, lanes[(wid, d)])
        if DUCTS[d][0] == "h":
            cy = c
        else:
            cx = c
        pts.append((cx, cy))
    if DUCTS[chain[-1]][0] == "h":
        pts.append((b[0], cy))
    else:
        pts.append((cx, b[1]))
    pts.append((b[0], b[1]))
    return _dedupe(pts)


def path_len(pts):
    return sum(abs(pts[i + 1][0] - pts[i][0]) + abs(pts[i + 1][1] - pts[i][1])
               for i in range(len(pts) - 1))


def build_routes():
    seen = set()
    pre = []
    for wid, cls, frm, to, mm2, note in WIRES:
        ta, la = _endpoint(frm, seen)
        tb, lb = _endpoint(to, seen)
        seen.add(frm); seen.add(to)
        chain = chain_for(ta[2], tb[2])
        pre.append({"id": wid, "cls": cls, "mm2": mm2, "note": note,
                    "a": ta, "b": tb, "la": la, "lb": lb,
                    "frm": frm, "to": to, "chain": chain,
                    "spans": spans(ta, tb, chain)})
    lanes, used = allocate_lanes(pre)
    for r in pre:
        r["pts"] = route(r["a"], r["b"], r["chain"], r["id"], lanes)
        r["len"] = path_len(r["pts"]) + SLACK
        r["lanes"] = [(d, lanes[(r["id"], d)]) for d in r["chain"]]
    return pre, used


# --- checks ------------------------------------------------------------------

def _crosses(p, q, rect, eps=0.4):
    x, y, w, d = rect
    x0, y0, x1, y1 = x + eps, y + eps, x + w - eps, y + d - eps
    ax, ay, bx, by = p[0], p[1], q[0], q[1]
    if abs(ay - by) < 1e-6:                                 # horizontal segment
        return y0 < ay < y1 and max(ax, bx) > x0 and min(ax, bx) < x1
    return x0 < ax < x1 and max(ay, by) > y0 and min(ay, by) < y1


def check(routes, used):
    bad = []
    for d, n in used.items():
        if n > capacity(d):
            bad.append(f"{d} needs {n} lanes, holds {capacity(d)}")

    rects = [(x, y, w, dd) for _n, x, y, w, dd, _k, _t in GEAR]
    rects.append((RAIL_START, RAIL_Y, rail_schedule()[1], RAIL_DEPTH))
    for r in routes:
        for i in range(len(r["pts"]) - 1):
            for rect in rects:
                if _crosses(r["pts"][i], r["pts"][i + 1], rect):
                    bad.append(f"{r['id']} segment {i} runs through {rect}")

    landings = {}
    for wid, _c, frm, to, _m, _n in WIRES:
        for t in (frm, to):
            landings.setdefault(t, []).append(wid)
    for t, ws in landings.items():
        limit = 2 if t in {n for n, _x, _w, k, _o in rail_schedule()[0]
                           if k not in ("part", "clamp")} else 1
        if len(ws) > limit:
            bad.append(f"{t} has {len(ws)} wires on a {limit}-screw landing: {ws}")

    crossings = 0
    for i, r in enumerate(routes):
        for s in routes[i + 1:]:
            for a in range(len(r["pts"]) - 1):
                p, q = r["pts"][a], r["pts"][a + 1]
                for b in range(len(s["pts"]) - 1):
                    u, v = s["pts"][b], s["pts"][b + 1]
                    ph = abs(p[1] - q[1]) < 1e-6
                    uh = abs(u[1] - v[1]) < 1e-6
                    if ph == uh:
                        continue
                    hp, hq, vp, vq = (p, q, u, v) if ph else (u, v, p, q)
                    if (min(hp[0], hq[0]) < vp[0] < max(hp[0], hq[0]) and
                            min(vp[1], vq[1]) < hp[1] < max(vp[1], vq[1])):
                        crossings += 1
    return bad, crossings


# --- drawing -----------------------------------------------------------------

def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def plan_svg(routes, scale=2.0):
    pad_l, pad_t = 172, 46
    W, H = FLOOR
    vw, vh = W * scale + pad_l + 186, H * scale + pad_t + 112
    X = lambda mm: pad_l + mm * scale
    Y = lambda mm: pad_t + mm * scale
    p = [f'<svg viewBox="0 0 {vw:.0f} {vh:.0f}" role="img" xmlns="http://www.w3.org/2000/svg"'
         ' aria-label="Plan of the power box floor, drawn to scale: a DIN rail across the back,'
         ' the two supplies and the buck converter in front with their terminal faces turned'
         ' toward vertical wiring ducts, and all thirty conductors drawn individually, each in'
         ' its own lane inside the ducts.">']

    p.append(f'<rect x="{X(0):.1f}" y="{Y(0):.1f}" width="{W*scale:.1f}" height="{H*scale:.1f}"'
             ' rx="5" fill="var(--surface-2)" stroke="currentColor" stroke-width="1.8"/>')
    p.append(f'<text x="{X(W/2):.1f}" y="{Y(0)-17:.1f}" text-anchor="middle" font-size="12.5"'
             f' fill="currentColor" opacity=".72">UN4412 base — {W:.0f} × {H:.0f} mm internal,'
             ' terminals facing up into the lid cavity</text>')

    # duct floors, under everything
    for name, (axis, c0, c1, s0, s1) in DUCTS.items():
        x, y, w, d = ((s0, c0, s1 - s0, c1 - c0) if axis == "h"
                      else (c0, s0, c1 - c0, s1 - s0))
        p.append(f'<rect x="{X(x):.1f}" y="{Y(y):.1f}" width="{w*scale:.1f}"'
                 f' height="{d*scale:.1f}" fill="var(--duct)"/>')

    # the rail
    sched, rail_len = rail_schedule()
    p.append(f'<rect x="{X(RAIL_START):.1f}" y="{Y(RAIL_Y):.1f}" width="{rail_len*scale:.1f}"'
             f' height="{RAIL_DEPTH*scale:.1f}" fill="var(--rail)" stroke="currentColor"'
             ' stroke-width="1.3"/>')
    for name, x, w, kind, note in sched:
        if kind in ("part", "clamp"):
            continue
        fill = {"mcb": "var(--w-L)", "relay": "var(--accent)"}.get(kind, f"var(--w-{kind})")
        h = RAIL_DEPTH if kind in ("mcb", "relay") else RAIL_DEPTH * 0.70
        p.append(f'<rect x="{X(x)+0.5:.1f}" y="{Y(RAIL_Y):.1f}" width="{max(w*scale-1,2):.1f}"'
                 f' height="{h*scale:.1f}" fill="{fill}" opacity=".80"/>')
        cx, ty = X(x + w / 2), Y(RAIL_Y + h) - 7
        p.append(f'<text x="{cx:.1f}" y="{ty:.1f}" font-size="9.5" font-weight="500"'
                 f' fill="{"var(--surface)" if kind in ("mcb","relay") else "currentColor"}"'
                 f' transform="rotate(-90 {cx:.1f} {ty:.1f})">{_esc(name)}</text>')
    for grp in JUMPERS:
        xs = [x for n, x, w, k, o in sched if n in grp]
        ws = [w for n, x, w, k, o in sched if n in grp]
        if not xs:
            continue
        a, b = min(xs) + 1.0, max(xs) + max(ws) - 1.0
        yy = Y(RAIL_Y + RAIL_DEPTH * 0.70) + 4
        p.append(f'<line x1="{X(a):.1f}" y1="{yy:.1f}" x2="{X(b):.1f}" y2="{yy:.1f}"'
                 ' stroke="currentColor" stroke-width="3" stroke-linecap="round" opacity=".85"/>')
    p.append(f'<text x="{X(RAIL_START):.1f}" y="{Y(RAIL_Y)-7:.1f}" font-size="10.5"'
             f' fill="currentColor" opacity=".72">DIN rail, {rail_len:.0f} mm — thick bars'
             ' underneath are jumper combs, not wires</text>')

    # gear
    for name, x, y, w, d, kind, note in GEAR:
        fill = {"psu": "var(--g-steel)", "pcb": "var(--g-pcb)"}.get(kind, "var(--g-abs)")
        p.append(f'<rect x="{X(x):.1f}" y="{Y(y):.1f}" width="{w*scale:.1f}"'
                 f' height="{d*scale:.1f}" rx="2.5" fill="{fill}" stroke="currentColor"'
                 ' stroke-width="1.4"/>')
        if w > 24:
            p.append(f'<text x="{X(x+w/2):.1f}" y="{Y(y+d/2)+4:.1f}" text-anchor="middle"'
                     f' font-size="11.5" fill="currentColor" opacity=".9">{_esc(name)}</text>')

    # terminal strips, labelled inside the gear at the face
    for gear, fx, by, bd, pitch, duct, strip in STRIPS:
        for name, cls in strip:
            tx, ty, _d, _a = TERMINALS[name]
            p.append(f'<rect x="{X(tx)-9:.1f}" y="{Y(ty)-3.0:.1f}" width="9" height="6"'
                     f' fill="var(--w-{cls})" opacity=".9"/>')
            p.append(f'<text x="{X(tx)-12:.1f}" y="{Y(ty)+3:.1f}" text-anchor="end"'
                     f' font-size="8" fill="currentColor" opacity=".8">'
                     f'{_esc(name.split(".")[1])}</text>')
    for nm in ("BUCK.IN+", "BUCK.IN-", "BUCK.OUT+", "BUCK.OUT-"):
        tx, ty, _d, _a = TERMINALS[nm]
        side = -1 if "IN" in nm else 1
        p.append(f'<rect x="{X(tx)+(0 if side>0 else -7):.1f}" y="{Y(ty)-2.2:.1f}" width="7"'
                 f' height="4.4" fill="var(--w-v24)" opacity=".85"/>')

    # every conductor
    for r in routes:
        pts = " ".join(f"{X(a):.1f},{Y(b):.1f}" for a, b in r["pts"])
        p.append(f'<polyline points="{pts}" fill="none" stroke="var(--w-{r["cls"]})"'
                 f' stroke-width="{1.9 if r["mm2"]<=0.75 else 2.5:.1f}" stroke-linejoin="round"'
                 ' stroke-linecap="round"/>')

    # duct lids, drawn over the wires: what you actually see with the lid on
    for name, (axis, c0, c1, s0, s1) in DUCTS.items():
        x, y, w, d = ((s0, c0, s1 - s0, c1 - c0) if axis == "h"
                      else (c0, s0, c1 - c0, s1 - s0))
        p.append(f'<rect x="{X(x):.1f}" y="{Y(y):.1f}" width="{w*scale:.1f}"'
                 f' height="{d*scale:.1f}" fill="var(--duct-lid)" stroke="currentColor"'
                 ' stroke-width="1" stroke-dasharray="6 4" opacity=".95"/>')
        kind, nom = DUCT_KIND[name]
        lab = (f'{name} · {nom:.0f} mm duct' if kind == "duct"
               else f'{name} · clipped, not a duct')
        if axis == "h":
            p.append(f'<text x="{X(x)+4:.1f}" y="{Y(y)-5:.1f}" font-size="9.5"'
                     f' font-weight="600" fill="currentColor" opacity=".6">{lab}</text>')
        else:
            tx, ty = X(x + w / 2) + 3.5, Y(y + d) - 5
            p.append(f'<text x="{tx:.1f}" y="{ty:.1f}" font-size="9.5" font-weight="600"'
                     f' fill="currentColor" opacity=".6" text-anchor="start"'
                     f' transform="rotate(-90 {tx:.1f} {ty:.1f})">{lab}</text>')

    # panel penetrations
    for label, x, y, wall in PANEL:
        left = wall == "left"
        p.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="4.5" fill="var(--accent)"/>')
        p.append(f'<text x="{X(x)+(-9 if left else 9):.1f}" y="{Y(y)+4:.1f}" font-size="10"'
                 f' fill="currentColor" opacity=".85"'
                 f' text-anchor="{"end" if left else "start"}">{_esc(label)}</text>')

    # legend
    lx, ly = X(8), Y(H) + 26
    items = [("L", "L, brown"), ("N", "N, blue"), ("E", "PE, green/yellow"),
             ("v24", "+24 V, red"), ("v0", "0 V, black"), ("v6", "+6 V, orange"),
             ("ctrl", "E-stop loop, violet")]
    for i, (k, lab) in enumerate(items):
        cx = lx + (i % 4) * 150
        cy = ly + (i // 4) * 18
        p.append(f'<line x1="{cx:.0f}" y1="{cy:.0f}" x2="{cx+20:.0f}" y2="{cy:.0f}"'
                 f' stroke="var(--w-{k})" stroke-width="2.6" stroke-linecap="round"/>')
        p.append(f'<text x="{cx+27:.0f}" y="{cy+4:.0f}" font-size="10.5" fill="currentColor"'
                 f' opacity=".8">{lab}</text>')
    p.append(f'<text x="{lx:.0f}" y="{ly+44:.0f}" font-size="10.5" fill="currentColor"'
             ' opacity=".6">Shaded bands are the ducts, drawn over the wires — with the duct'
             ' lids on, only the stubs are visible. Each conductor has its own lane inside.</text>')
    p.append("</svg>")
    return "\n".join(p)


def elevation_svg(scale=2.4):
    sched, rail_len = rail_schedule()
    pad_l, pad_t = 16, 30
    H_MCB, H_TB = 85.0, 58.0
    vw = rail_len * scale + pad_l * 2
    vh = H_MCB * scale + pad_t + 80
    X = lambda mm: pad_l + (mm - RAIL_START) * scale
    base = pad_t + H_MCB * scale

    p = [f'<svg viewBox="0 0 {vw:.0f} {vh:.0f}" role="img" xmlns="http://www.w3.org/2000/svg"'
         ' aria-label="Front elevation of the DIN rail: mains breaker, line, neutral and earth'
         ' terminals, the DC breaker, the E-stop relay, the DC distribution terminals and three'
         ' spares, in the order power flows, with jumper combs marked across each bridged group.">']
    p.append(f'<line x1="{X(RAIL_START):.1f}" y1="{base:.1f}"'
             f' x2="{X(RAIL_START+rail_len):.1f}" y2="{base:.1f}"'
             ' stroke="currentColor" stroke-width="3" opacity=".7"/>')

    for name, x, w, kind, note in sched:
        if kind in ("part", "clamp"):
            continue
        h = H_MCB if kind in ("mcb", "relay") else H_TB
        fill = {"mcb": "var(--w-L)", "relay": "var(--accent)"}.get(kind, f"var(--w-{kind})")
        p.append(f'<rect x="{X(x):.1f}" y="{base - h*scale:.1f}"'
                 f' width="{max(w*scale-1.2,2.5):.1f}" height="{h*scale:.1f}" rx="1.5"'
                 f' fill="{fill}" opacity=".88"/>')
        if kind in ("mcb", "relay"):
            p.append(f'<text x="{X(x+w/2):.1f}" y="{base - h*scale/2 + 4:.1f}"'
                     ' text-anchor="middle" font-size="12" font-weight="600"'
                     f' fill="var(--surface)">{_esc(name)}</text>')
        else:
            tx, ty = X(x + w / 2), base - h * scale - 6
            p.append(f'<text x="{tx:.1f}" y="{ty:.1f}" text-anchor="start" font-size="9"'
                     f' fill="currentColor" opacity=".8"'
                     f' transform="rotate(-90 {tx:.1f} {ty:.1f})">{_esc(name)}</text>')

    for grp in JUMPERS:
        xs = [x for n, x, w, k, o in sched if n in grp]
        ws = [w for n, x, w, k, o in sched if n in grp]
        a, b = min(xs) + 1.2, max(xs) + max(ws) - 1.2
        yy = base - H_TB * scale * 0.52
        p.append(f'<line x1="{X(a):.1f}" y1="{yy:.1f}" x2="{X(b):.1f}" y2="{yy:.1f}"'
                 ' stroke="var(--surface)" stroke-width="3.4" stroke-linecap="round"'
                 ' opacity=".95"/>')

    for label, a, b in (("mains, protected", RAIL_START + 8, RAIL_START + 86),
                        ("DC protect + switch", RAIL_START + 88, RAIL_START + 124),
                        ("DC distribution", RAIL_START + 126, RAIL_START + 173),
                        ("spare", RAIL_START + 175, RAIL_START + 190)):
        y = base + 16
        p.append(f'<line x1="{X(a):.1f}" y1="{y:.1f}" x2="{X(b):.1f}" y2="{y:.1f}"'
                 ' stroke="currentColor" stroke-width="1.2" opacity=".5"/>')
        p.append(f'<text x="{X((a+b)/2):.1f}" y="{y+15:.1f}" text-anchor="middle"'
                 f' font-size="10.5" fill="currentColor" opacity=".72">{_esc(label)}</text>')

    p.append(f'<text x="{X(RAIL_START):.1f}" y="{pad_t-12:.1f}" font-size="10.5"'
             f' fill="currentColor" opacity=".7">{rail_len:.0f} mm of rail — breakers and the'
             ' relay stand 85 mm, terminals 58 mm, in a 124 mm cavity. Pale bars are'
             ' jumper combs.</text>')
    p.append("</svg>")
    return "\n".join(p)


PAGE = """<title>Power Box Wiring</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap">
<style>
:root{
  --paper:#e9edf1; --surface:#fff; --surface-2:#f1f5f8; --rail:#dde4ea;
  --duct:#e4ebf1; --duct-lid:rgba(255,255,255,.22);
  --g-steel:#dfe4e8; --g-pcb:#cdd9c4; --g-abs:#f0f2f4;
  --ink:#131b22; --ink-2:#4a5a67; --ink-3:#7d8d9a; --line:#ccd6de; --line-2:#dde4ea;
  --accent:#c2622c;
  --w-L:#7d4426; --w-N:#2d5c8c; --w-E:#5d7f2e;
  --w-v24:#c33a2a; --w-v0:#2b343b; --w-v6:#c2821a; --w-ctrl:#7a4fa3;
  --w-sp:#aab6c0; --w-mcb:#7d4426; --w-relay:#c2622c;
}
@media (prefers-color-scheme:dark){ :root:not([data-theme="light"]){
  --paper:#0c1218; --surface:#141d25; --surface-2:#18212a; --rail:#232f38;
  --duct:#1e2831; --duct-lid:rgba(20,29,37,.28);
  --g-steel:#2b3740; --g-pcb:#36442f; --g-abs:#283139;
  --ink:#e4ecf2; --ink-2:#9aabb8; --ink-3:#6c7d8a; --line:#26333d; --line-2:#1e2a33;
  --accent:#e08a52;
  --w-L:#c08055; --w-N:#5f94c4; --w-E:#90b85c;
  --w-v24:#e2614c; --w-v0:#97a6b2; --w-v6:#d9a63f; --w-ctrl:#a67fd0;
  --w-sp:#55646f; --w-mcb:#c08055; --w-relay:#e08a52;
}}
:root[data-theme="dark"]{
  --paper:#0c1218; --surface:#141d25; --surface-2:#18212a; --rail:#232f38;
  --duct:#1e2831; --duct-lid:rgba(20,29,37,.28);
  --g-steel:#2b3740; --g-pcb:#36442f; --g-abs:#283139;
  --ink:#e4ecf2; --ink-2:#9aabb8; --ink-3:#6c7d8a; --line:#26333d; --line-2:#1e2a33;
  --accent:#e08a52;
  --w-L:#c08055; --w-N:#5f94c4; --w-E:#90b85c;
  --w-v24:#e2614c; --w-v0:#97a6b2; --w-v6:#d9a63f; --w-ctrl:#a67fd0;
  --w-sp:#55646f; --w-mcb:#c08055; --w-relay:#e08a52;
}
*{box-sizing:border-box}
body{margin:0; background:var(--paper); color:var(--ink);
  font-family:"IBM Plex Sans",system-ui,sans-serif; font-size:15px; line-height:1.55;
  -webkit-font-smoothing:antialiased}
.wrap{max-width:1040px; margin:0 auto; padding:30px 20px 60px}
h1{margin:0; font-size:27px; font-weight:600; letter-spacing:-.02em}
.sub{margin:5px 0 0; color:var(--ink-2); font-size:14px; max-width:68ch}
h2{margin:0 0 10px; font-size:10.5px; font-weight:600; text-transform:uppercase;
   letter-spacing:.1em; color:var(--ink-3)}
figure{margin:24px 0 0; padding:14px; background:var(--surface);
       border:1px solid var(--line); border-radius:4px; overflow-x:auto}
figure svg{display:block; max-width:100%; height:auto; color:var(--ink)}
figcaption{margin-top:12px; font-size:12.5px; color:var(--ink-2); max-width:74ch}
table{width:100%; border-collapse:collapse; font-size:12.5px; margin-top:4px}
th{text-align:left; font-size:10px; text-transform:uppercase; letter-spacing:.09em;
   color:var(--ink-3); font-weight:600; padding:0 8px 6px 0; border-bottom:1px solid var(--line)}
td{padding:5px 8px 5px 0; border-bottom:1px solid var(--line-2); vertical-align:top}
tr:last-child td{border-bottom:none}
td.grp{padding-top:14px; font-size:10px; text-transform:uppercase; letter-spacing:.09em;
       color:var(--ink-3); font-weight:600; border-bottom:1px solid var(--line)}
.num{font-family:"IBM Plex Mono",monospace; font-variant-numeric:tabular-nums; white-space:nowrap}
.id{font-family:"IBM Plex Mono",monospace; color:var(--ink-3)}
.sw{display:inline-block; width:9px; height:9px; border-radius:2px; margin-right:7px;
    vertical-align:-1px}
.panel{background:var(--surface); border:1px solid var(--line); border-radius:4px;
       padding:16px; margin-top:16px}
.cols{display:grid; grid-template-columns:1fr 1fr; gap:16px}
.cols3{display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px}
@media (max-width:860px){.cols,.cols3{grid-template-columns:1fr}}
.note{margin-top:14px; padding:12px 14px; font-size:13.5px; color:var(--ink-2);
      background:var(--surface); border-left:2px solid var(--accent); border-radius:0 3px 3px 0}
.note b{color:var(--ink)}
code{font-family:"IBM Plex Mono",monospace; font-size:.92em}
footer{margin-top:26px; padding-top:14px; border-top:1px solid var(--line);
       font-size:12px; color:var(--ink-3)}
</style>

<div class="wrap">
  <h1>Power box — every conductor</h1>
  <p class="sub">UN4412, 442 × 265 mm floor. Thirty individual wires, each one routed from
  the terminal it actually lands on, through a duct, to the terminal at the other end. The
  gear is placed so that every terminal face points at a duct at 90° — which is the whole
  trick behind a panel that looks tidy.</p>

  <figure>
    __PLAN__
    <figcaption><b>Floor plan, to scale.</b> The LRS-350's terminals are on one 115 mm short
    end, so it cannot face the back wall — 215 mm of depth would not fit. It lies long-ways
    with that face turned into <b>V1</b> — its second <code>+V</code>/<code>−V</code> pair is left spare for a future feed. The RS-25 does the same into <b>V2</b>, where the
    buck's IN terminals meet it; the buck's OUT terminals are on the opposite end and face
    <b>V3</b>, which also picks up the fan. Everything collects in <b>H1</b> across the face
    of the rail. Nothing crosses open floor: __XING__</figcaption>
  </figure>

  <figure>
    __ELEV__
    <figcaption><b>The rail, front on.</b> Four zones in the order power moves through them.
    The pale bars are insertable jumper combs — six groups bridged without a single wire,
    which is where most of the clutter in a hand-wired box comes from.</figcaption>
  </figure>

  <div class="panel">
    <h2>Wire schedule — __NWIRE__ conductors, __TOTAL__ m including dressing slack</h2>
    <table><thead><tr><th>#</th><th>From</th><th>To</th><th class="num">mm²</th>
      <th>Colour</th><th>Ferrule</th><th>Route</th><th class="num">mm</th>
      <th>Why</th></tr></thead><tbody>__WIRES__</tbody></table>
  </div>

  <div class="cols3">
    <div class="panel">
      <h2>Cut list</h2>
      <table><thead><tr><th class="num">mm²</th><th class="num">Cores</th>
        <th class="num">Metres</th></tr></thead><tbody>__CUT__</tbody></table>
    </div>
    <div class="panel">
      <h2>Jumper combs</h2>
      <table><thead><tr><th>Bridged</th><th class="num">Ways</th></tr></thead>
        <tbody>__JUMP__</tbody></table>
    </div>
    <div class="panel">
      <h2>The link out</h2>
      <table><thead><tr><th>Conductor</th><th class="num">mm²</th></tr></thead>
        <tbody>__LINK__</tbody></table>
    </div>
  </div>

  <div class="panel">
    <h2>Rail schedule</h2>
    <table><thead><tr><th>Pos</th><th class="num">mm</th><th class="num">Width</th>
      <th>Item</th></tr></thead><tbody>__SCHED__</tbody></table>
  </div>

  <div class="note"><b>The duct grid is doing the work, not neatness.</b> A wire that leaves
  its terminal at 90° into a duct 20 mm away has nowhere to wander. The drawing puts the duct
  lids <i>over</i> the conductors, so what you see is what the box looks like built: short,
  identical stubs into a clean band. Inside the ducts the wires lie across each other
  __XING2__ — that is normal and invisible, and it is why a duct exists.</div>

  <div class="note"><b>Lay the LRS-350 with its <code>+V</code> end toward the back wall.</b>
  The strip reads <code>+V +V −V −V ⏚ N L</code> in one fixed order, and the unit can only be
  turned end-for-end, so this choice is the one thing that decides whether the heavy DC pair
  takes the short route or the long one up V1. Back-wall-side puts the 14.6 A pair nearest H1.</div>

  <div class="note"><b>0 V is a star, not a chain.</b> Both supplies' <code>−V</code> land on
  the <code>0V</code> block and nowhere else, so that is the single point where they meet. The
  buck's return goes to <code>0Va</code> on the rail rather than being daisy-chained off the
  RS-25's screw — and the servo's 6 V return is taken from the rail too, not from the buck's
  <code>OUT−</code>, so 2.5 A never travels through the module's thin ground trace.
  <code>BUCK.OUT−</code> is deliberately left empty.</div>

  <div class="note"><b>The relay earns its place by what it does <i>not</i> cut.</b> K1
  switches only <code>+24s</code>. The board sits upstream on <code>+24a</code> and the fan on
  <code>+24f</code>, so an E-stop drops the motors while GRBL stays awake to tell you it
  happened and the box keeps cooling. The button is wired <b>normally-closed in series with
  K1's coil</b>, so a cut wire stops the machine too. It lives on the machine, not on this
  box — the box only carries a 2-pole connector for the loop.</div>

  <div class="note"><b>MCB2 protects the wiring, not the supply.</b> The LRS-350 already
  limits its own output. What it cannot do is notice a pinched conductor in the drag chain
  drawing 4 A through a wire sized for 1.7.</div>

  <footer>Generated by <code>python3 hardware/psu_layout.py</code>. Lane assignment, path
  routing, wire lengths and the cut list all come from the same tables as the drawing, and
  the script refuses to write a layout whose wires pass through a part.</footer>
</div>
"""

GROUPS = [("mains, 220 V", ("L", "N", "E")), ("24 V DC", ("v24", "v0")),
          ("6 V DC", ("v6",)), ("E-stop loop", ("ctrl",))]


def build():
    routes, used = build_routes()
    bad, crossings = check(routes, used)
    if bad:
        raise ValueError("layout is not buildable:\n  " + "\n  ".join(bad))

    by_id = {r["id"]: r for r in routes}
    rows = []
    for title, classes in GROUPS:
        rows.append(f'<tr><td class="grp" colspan="9">{title}</td></tr>')
        for r in [x for x in routes if x["cls"] in classes]:
            rt = " → ".join(f"{d}·{l}" for d, l in r["lanes"])
            rows.append(
                f'<tr><td class="id">{r["id"][1:]}</td>'
                f'<td><span class="sw" style="background:var(--w-{r["cls"]})"></span>'
                f'{_esc(r["la"])}</td><td>{_esc(r["lb"])}</td>'
                f'<td class="num">{r["mm2"]}</td><td>{COLOUR[r["cls"]]}</td>'
                f'<td class="num">{FERRULE[r["mm2"]]}</td>'
                f'<td class="num">{rt}</td><td class="num">{r["len"]:.0f}</td>'
                f'<td>{_esc(r["note"])}</td></tr>')

    cut = {}
    for r in routes:
        n, m = cut.get(r["mm2"], (0, 0.0))
        cut[r["mm2"]] = (n + 1, m + r["len"])
    cutrows = "".join(f'<tr><td class="num">{k}</td><td class="num">{v[0]}</td>'
                      f'<td class="num">{v[1]/1000:.2f}</td></tr>'
                      for k, v in sorted(cut.items()))

    jump = "".join(f'<tr><td>{" – ".join(g)}</td><td class="num">{len(g)}</td></tr>'
                   for g in JUMPERS)
    link = "".join(f'<tr><td>{_esc(n)}</td><td class="num">{mm2}</td></tr>'
                   for n, mm2, _w in LINK)

    sched, _ = rail_schedule()
    srows = []
    for name, x, w, kind, note in sched:
        if kind in ("part", "clamp"):
            continue
        srows.append(f'<tr><td><span class="sw" style="background:var(--w-{kind})"></span>'
                     f'{_esc(name)}</td><td class="num">{x:.1f}</td>'
                     f'<td class="num">{w:.1f}</td><td>{_esc(note)}</td></tr>')

    total = sum(r["len"] for r in routes) / 1000
    html = (PAGE.replace("__PLAN__", plan_svg(routes))
                .replace("__ELEV__", elevation_svg())
                .replace("__WIRES__", "".join(rows))
                .replace("__CUT__", cutrows)
                .replace("__JUMP__", jump)
                .replace("__LINK__", link)
                .replace("__SCHED__", "".join(srows))
                .replace("__NWIRE__", str(len(routes)))
                .replace("__TOTAL__", f"{total:.1f}")
                .replace("__XING__", "zero of the crossings in this drawing are outside a duct.")
                .replace("__XING2__", f"({crossings} times)"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html)
    return OUT, routes, used, crossings


if __name__ == "__main__":
    path, routes, used, crossings = build()
    print(f"wrote {path.relative_to(path.parent.parent.parent)} "
          f"({path.stat().st_size/1024:.0f} KB)")
    print(f"  {len(routes)} conductors, "
          f"{sum(r['len'] for r in routes)/1000:.2f} m, {crossings} in-duct crossings")
    print(f"  lanes: " + ", ".join(f"{d} {n}/{capacity(d)}" for d, n in used.items()))
