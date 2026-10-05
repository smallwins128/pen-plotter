#!/usr/bin/env python3
"""The engine behind the two box layout drawings.

A layout module supplies tables -- the DIN rail schedule, the duct grid, where
the gear sits, which terminal is where on each part, and every conductor -- and
this module turns them into lanes, paths, checks, SVG and HTML. Nothing here
knows anything about either box.

The routing model, in one paragraph: every terminal declares which duct it
feeds and whether its stub runs in x or y. A wire's path is its start terminal,
a chain of ducts, and its end terminal; inside each duct it sits in a lane, so
parallel runs lie side by side instead of on top of each other. Lanes come from
a left-edge assignment over the spans, banded so that power and logic never
interleave within a duct. In a vertical duct whose terminals all exit the same
way that also comes out crossing-free, because the left-edge order is depth
order. Crossings inside a duct are not faults -- they are under the lid and
invisible -- but a wire through a part, an overfull duct, or three conductors
on a two-screw block are, and build() refuses to write any of them.
"""

LANE_PITCH, LANE_INSET = 2.1, 2.0


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# --- schedule and terminals --------------------------------------------------

def rail_schedule(S):
    out, x = [], S.RAIL_START
    for name, w, kind, note in S.RAIL:
        out.append((name, x, w, kind, note))
        x += w
    return out, x - S.RAIL_START


def rail_face(S):
    return S.RAIL_Y + S.RAIL_DEPTH


def build_terminals(S):
    """name -> (x, y, duct, stub axis). Fans a two-wire rail block apart."""
    t = {}
    sched, _ = rail_schedule(S)
    users = {}
    for _, _, frm, to, _, _ in S.WIRES:
        for n in (frm, to):
            users[n] = users.get(n, 0) + 1

    for name, x, w, kind, _note in sched:
        if kind in ("part", "clamp"):
            continue
        if name in S.RAIL_SUBS:
            for sub, off in S.RAIL_SUBS[name]:
                t[sub] = (x + off, rail_face(S), S.RAIL_DUCT, "y")
            continue
        n = users.get(name, 0)
        if n <= 1:
            t[name] = (x + w / 2, rail_face(S), S.RAIL_DUCT, "y")
        else:
            t[name] = (x + w / 2 - 1.3, rail_face(S), S.RAIL_DUCT, "y")
            t[name + "#2"] = (x + w / 2 + 1.3, rail_face(S), S.RAIL_DUCT, "y")

    for _gear, axis, fixed, c0, clen, pitch, duct, strip in S.STRIPS:
        span = pitch * (len(strip) - 1)
        start = c0 + clen / 2 - span / 2
        for i, (name, _cls) in enumerate(strip):
            # "v": a face on the left or right of a part -- terminals run down it
            # in y and their stubs leave in x. "h": a face on its back or front.
            t[name] = ((fixed, start + i * pitch, duct, "x") if axis == "v"
                       else (start + i * pitch, fixed, duct, "y"))

    for name, x, y, duct, axis in S.LOOSE:
        t[name] = (x, y, duct, axis)
    return t


# --- routing -----------------------------------------------------------------

def _dmid(S, d):
    _axis, c0, c1, _s0, _s1 = S.DUCTS[d]
    return (c0 + c1) / 2


def duct_rect(S, d):
    axis, c0, c1, s0, s1 = S.DUCTS[d]
    return (s0, c0, s1 - s0, c1 - c0) if axis == "h" else (c0, s0, c1 - c0, s1 - s0)


def adjacency(S):
    """Two ducts are connected where they physically overlap. Nothing else is.

    This is the rule that stops a wire taking a shortcut between two parallel
    ducts -- which, before it existed, drove six conductors straight through a
    stepper driver because both ends happened to sit on a horizontal run.
    """
    rects = {d: duct_rect(S, d) for d in S.DUCTS}
    adj = {d: set() for d in S.DUCTS}
    for a, (ax, ay, aw, ah) in rects.items():
        for b, (bx, by, bw, bh) in rects.items():
            if a != b and ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah:
                adj[a].add(b)
    return adj


def corners(S, a, b, chain, coord):
    """The polyline for a chain, given a function duct -> its lane coordinate."""
    pts = [(a[0], a[1])]
    cx, cy = a[0], a[1]
    for d in chain:
        if S.DUCTS[d][0] == "h":
            cy = coord(d)
        else:
            cx = coord(d)
        pts.append((cx, cy))
    if S.DUCTS[chain[-1]][0] == "h":
        pts.append((b[0], cy))
    else:
        pts.append((cx, b[1]))
    pts.append((b[0], b[1]))
    return _dedupe(pts)


def chain_for(S, a, b):
    """Shortest duct path from a's duct to b's, scored by the length it gives."""
    da, db = a[2], b[2]
    if da == db:
        return [da]
    adj = S._ADJ
    best = None
    path = [da]

    def walk(cur):
        nonlocal best
        if cur == db:
            score = path_len(corners(S, a, b, path, lambda d: _dmid(S, d)))
            if best is None or score < best[0]:
                best = (score, list(path))
            return
        if len(path) >= 4:
            return
        for n in sorted(adj[cur]):
            if n not in path:
                path.append(n)
                walk(n)
                path.pop()

    walk(da)
    if best is None:
        raise ValueError(f"no duct path from {da} to {db} — they do not meet")
    return best[1]


def spans(S, a, b, chain):
    out = []
    for i, d in enumerate(chain):
        axis = S.DUCTS[d][0]
        start = a[1] if axis == "v" else a[0]
        end = b[1] if axis == "v" else b[0]
        if i > 0:
            start = _dmid(S, chain[i - 1])
        if i < len(chain) - 1:
            end = _dmid(S, chain[i + 1])
        out.append((d, min(start, end), max(start, end)))
    return out


def band_of(S, cls):
    return "a" if cls in S.BAND_A else "b"


def allocate_lanes(S, routes):
    demand = {d: [] for d in S.DUCTS}
    for r in routes:
        for d, lo, hi in r["spans"]:
            demand[d].append((r["id"], lo, hi, band_of(S, r["cls"])))

    lanes, used = {}, {}
    for d, items in demand.items():
        placed, base = [], 0
        for band in S.BANDS[d]:
            grp = [i for i in items if i[3] == band]
            for wid, lo, hi, _b in sorted(grp, key=lambda i: (i[1], i[2])):
                lane = base
                while any(l == lane and lo < h - 1e-6 and hi > o + 1e-6
                          for l, o, h in placed):
                    lane += 1
                placed.append((lane, lo, hi))
                lanes[(wid, d)] = lane
            base = max((l for l, _, _ in placed), default=-1) + 1
        used[d] = max((l for l, _, _ in placed), default=-1) + 1
    return lanes, used


def lane_coord(S, d, lane):
    _axis, c0, _c1, _s0, _s1 = S.DUCTS[d]
    return c0 + LANE_INSET + lane * LANE_PITCH


def capacity(S, d):
    _axis, c0, c1, _s0, _s1 = S.DUCTS[d]
    return int((c1 - c0 - 2 * LANE_INSET) / LANE_PITCH) + 1


def _dedupe(pts):
    out = [pts[0]]
    for p in pts[1:]:
        if abs(p[0] - out[-1][0]) > 1e-6 or abs(p[1] - out[-1][1]) > 1e-6:
            out.append(p)
    return out


def route(S, a, b, chain, wid, lanes):
    return corners(S, a, b, chain, lambda d: lane_coord(S, d, lanes[(wid, d)]))


def path_len(pts):
    return sum(abs(pts[i + 1][0] - pts[i][0]) + abs(pts[i + 1][1] - pts[i][1])
               for i in range(len(pts) - 1))


def build_routes(S):
    S._ADJ = adjacency(S)
    T = S.TERMINALS
    seen, pre = set(), []
    for wid, cls, frm, to, mm2, note in S.WIRES:
        ta = T[frm + "#2"] if (frm in seen and frm + "#2" in T) else T[frm]
        tb = T[to + "#2"] if (to in seen and to + "#2" in T) else T[to]
        la = frm + " (2nd screw)" if (frm in seen and frm + "#2" in T) else frm
        lb = to + " (2nd screw)" if (to in seen and to + "#2" in T) else to
        seen.add(frm); seen.add(to)
        chain = chain_for(S, ta, tb)
        pre.append({"id": wid, "cls": cls, "mm2": mm2, "note": note,
                    "a": ta, "b": tb, "la": la, "lb": lb, "frm": frm, "to": to,
                    "chain": chain, "spans": spans(S, ta, tb, chain)})
    lanes, used = allocate_lanes(S, pre)
    for r in pre:
        r["pts"] = route(S, r["a"], r["b"], r["chain"], r["id"], lanes)
        r["len"] = path_len(r["pts"]) + S.SLACK
        r["lanes"] = [(d, lanes[(r["id"], d)]) for d in r["chain"]]
    return pre, used


# --- checks ------------------------------------------------------------------

def _crosses(p, q, rect, eps=0.4):
    x, y, w, d = rect
    x0, y0, x1, y1 = x + eps, y + eps, x + w - eps, y + d - eps
    if abs(p[1] - q[1]) < 1e-6:
        return y0 < p[1] < y1 and max(p[0], q[0]) > x0 and min(p[0], q[0]) < x1
    return x0 < p[0] < x1 and max(p[1], q[1]) > y0 and min(p[1], q[1]) < y1


def _in_duct(S, pt):
    for d, (axis, c0, c1, s0, s1) in S.DUCTS.items():
        if axis == "h" and c0 - .1 <= pt[1] <= c1 + .1 and s0 - .1 <= pt[0] <= s1 + .1:
            return d
        if axis == "v" and c0 - .1 <= pt[0] <= c1 + .1 and s0 - .1 <= pt[1] <= s1 + .1:
            return d
    return None


def check(S, routes, used):
    bad = []
    for d, n in used.items():
        if n > capacity(S, d):
            bad.append(f"{d} needs {n} lanes, holds {capacity(S, d)}")

    rects = [(x, y, w, dd) for _n, x, y, w, dd, _k, _t in S.GEAR]
    rects.append((S.RAIL_START, S.RAIL_Y, rail_schedule(S)[1], S.RAIL_DEPTH))
    def _owns(rect, pt):
        x, y, w, d = rect
        return x - .5 <= pt[0] <= x + w + .5 and y - .5 <= pt[1] <= y + d + .5

    for r in routes:
        # a wire may sit inside the part it lands on -- a fan's flying leads
        # start inside the fan -- so skip the rects its own ends belong to
        mine = [rect for rect in rects
                if _owns(rect, r["pts"][0]) or _owns(rect, r["pts"][-1])]
        for i in range(len(r["pts"]) - 1):
            for rect in rects:
                if rect in mine:
                    continue
                if _crosses(r["pts"][i], r["pts"][i + 1], rect):
                    bad.append(f"{r['id']} segment {i} runs through {rect}")

    rail_names = {n for n, _x, _w, k, _o in rail_schedule(S)[0]
                  if k not in ("part", "clamp")}
    landings = {}
    for wid, _c, frm, to, _m, _n in S.WIRES:
        for t in (frm, to):
            landings.setdefault(t, []).append(wid)
    for t, ws in landings.items():
        limit = 2 if t in rail_names else 1
        if len(ws) > limit:
            bad.append(f"{t} has {len(ws)} wires on a {limit}-screw landing: {ws}")

    inn = out = 0
    for i, r in enumerate(routes):
        for s in routes[i + 1:]:
            for a in range(len(r["pts"]) - 1):
                p, q = r["pts"][a], r["pts"][a + 1]
                for b in range(len(s["pts"]) - 1):
                    u, v = s["pts"][b], s["pts"][b + 1]
                    ph, uh = abs(p[1] - q[1]) < 1e-6, abs(u[1] - v[1]) < 1e-6
                    if ph == uh:
                        continue
                    hp, hq, vp, vq = (p, q, u, v) if ph else (u, v, p, q)
                    if (min(hp[0], hq[0]) < vp[0] < max(hp[0], hq[0]) and
                            min(vp[1], vq[1]) < hp[1] < max(vp[1], vq[1])):
                        if _in_duct(S, (vp[0], hp[1])):
                            inn += 1
                        else:
                            out += 1
                            bad.append(f"{r['id']} crosses {s['id']} on open floor "
                                       f"at ({vp[0]:.0f}, {hp[1]:.0f})")
    return bad, inn, out


# --- drawing -----------------------------------------------------------------

GEAR_FILL = {"psu": "var(--g-steel)", "pcb": "var(--g-pcb)", "abs": "var(--g-abs)",
             "heatsink": "var(--g-heat)"}
RAIL_FILL = {"mcb": "var(--w-L)", "relay": "var(--accent)"}


def plan_svg(S, routes, scale=2.0, pad_l=172, pad_r=186):
    pad_t = 46
    W, H = S.FLOOR
    vw, vh = W * scale + pad_l + pad_r, H * scale + pad_t + 112
    X = lambda mm: pad_l + mm * scale
    Y = lambda mm: pad_t + mm * scale
    p = [f'<svg viewBox="0 0 {vw:.0f} {vh:.0f}" role="img"'
         f' xmlns="http://www.w3.org/2000/svg" aria-label="{esc(S.PLAN_ALT)}">']

    p.append(f'<rect x="{X(0):.1f}" y="{Y(0):.1f}" width="{W*scale:.1f}"'
             f' height="{H*scale:.1f}" rx="5" fill="var(--surface-2)"'
             ' stroke="currentColor" stroke-width="1.8"/>')
    p.append(f'<text x="{X(W/2):.1f}" y="{Y(0)-17:.1f}" text-anchor="middle"'
             f' font-size="12.5" fill="currentColor" opacity=".72">{esc(S.FLOOR_LABEL)}</text>')

    for name, (axis, c0, c1, s0, s1) in S.DUCTS.items():
        x, y, w, d = ((s0, c0, s1 - s0, c1 - c0) if axis == "h"
                      else (c0, s0, c1 - c0, s1 - s0))
        p.append(f'<rect x="{X(x):.1f}" y="{Y(y):.1f}" width="{w*scale:.1f}"'
                 f' height="{d*scale:.1f}" fill="var(--duct)"/>')

    sched, rail_len = rail_schedule(S)
    p.append(f'<rect x="{X(S.RAIL_START):.1f}" y="{Y(S.RAIL_Y):.1f}"'
             f' width="{rail_len*scale:.1f}" height="{S.RAIL_DEPTH*scale:.1f}"'
             ' fill="var(--rail)" stroke="currentColor" stroke-width="1.3"/>')
    for name, x, w, kind, _note in sched:
        if kind in ("part", "clamp"):
            continue
        tall = kind in ("mcb", "relay")
        fill = RAIL_FILL.get(kind, f"var(--w-{kind})")
        h = S.RAIL_DEPTH if tall else S.RAIL_DEPTH * 0.70
        p.append(f'<rect x="{X(x)+0.5:.1f}" y="{Y(S.RAIL_Y):.1f}"'
                 f' width="{max(w*scale-1,2):.1f}" height="{h*scale:.1f}"'
                 f' fill="{fill}" opacity=".80"/>')
        cx, ty = X(x + w / 2), Y(S.RAIL_Y + h) - 7
        col = "var(--surface)" if tall else "currentColor"
        p.append(f'<text x="{cx:.1f}" y="{ty:.1f}" font-size="9.5" font-weight="500"'
                 f' fill="{col}" transform="rotate(-90 {cx:.1f} {ty:.1f})">{esc(name)}</text>')
    for grp in S.JUMPERS:
        xs = [x for n, x, _w, _k, _o in sched if n in grp]
        ws = [w for n, _x, w, _k, _o in sched if n in grp]
        if not xs:
            continue
        a, b = min(xs) + 1.0, max(xs) + max(ws) - 1.0
        yy = Y(S.RAIL_Y + S.RAIL_DEPTH * 0.70) + 4
        p.append(f'<line x1="{X(a):.1f}" y1="{yy:.1f}" x2="{X(b):.1f}" y2="{yy:.1f}"'
                 ' stroke="currentColor" stroke-width="3" stroke-linecap="round"'
                 ' opacity=".85"/>')
    p.append(f'<text x="{X(S.RAIL_START+rail_len)+10:.1f}"'
             f' y="{Y(S.RAIL_Y+S.RAIL_DEPTH/2)+4:.1f}" font-size="10.5" fill="currentColor"'
             f' opacity=".72">DIN rail, {rail_len:.0f} mm — the thick bars are jumper'
             ' combs, not wires</text>')

    for name, x, y, w, d, kind, _note in S.GEAR:
        p.append(f'<rect x="{X(x):.1f}" y="{Y(y):.1f}" width="{w*scale:.1f}"'
                 f' height="{d*scale:.1f}" rx="2.5" fill="{GEAR_FILL.get(kind, "var(--g-abs)")}"'
                 ' stroke="currentColor" stroke-width="1.4"/>')
        if w > 24 and d > 24:
            p.append(f'<text x="{X(x+w/2):.1f}" y="{Y(y+d/2)+4:.1f}" text-anchor="middle"'
                     f' font-size="11.5" fill="currentColor" opacity=".9">{esc(name)}</text>')

    for gear, axis, _fixed, _c0, _clen, _pitch, _duct, strip in S.STRIPS:
        for name, cls in strip:
            tx, ty, _d, _a = S.TERMINALS[name]
            side = S.STRIP_SIDE.get(gear, -1)
            lab = esc(name.split(".")[-1])
            if axis == "v":
                p.append(f'<rect x="{X(tx)+(0 if side>0 else -9):.1f}"'
                         f' y="{Y(ty)-3.0:.1f}" width="9" height="6"'
                         f' fill="var(--w-{cls})" opacity=".9"/>')
                p.append(f'<text x="{X(tx)+(13 if side>0 else -12):.1f}"'
                         f' y="{Y(ty)+3:.1f}" text-anchor="{"start" if side>0 else "end"}"'
                         f' font-size="8" fill="currentColor" opacity=".8">{lab}</text>')
            else:
                p.append(f'<rect x="{X(tx)-3.0:.1f}" y="{Y(ty)+(0 if side>0 else -9):.1f}"'
                         f' width="6" height="9" fill="var(--w-{cls})" opacity=".9"/>')
                ly = Y(ty) + (16 if side > 0 else -12)
                p.append(f'<text x="{X(tx):.1f}" y="{ly:.1f}" font-size="7.5"'
                         f' fill="currentColor" opacity=".8" text-anchor="start"'
                         f' transform="rotate(-90 {X(tx):.1f} {ly:.1f})">{lab}</text>')

    for name, cls, side in getattr(S, "MARKS", []):
        tx, ty, _d, _a = S.TERMINALS[name]
        p.append(f'<rect x="{X(tx)+(0 if side>0 else -8):.1f}" y="{Y(ty)-2.4:.1f}"'
                 f' width="8" height="4.8" fill="var(--w-{cls})" opacity=".88"/>')

    for r in routes:
        pts = " ".join(f"{X(a):.1f},{Y(b):.1f}" for a, b in r["pts"])
        p.append(f'<polyline points="{pts}" fill="none" stroke="var(--w-{r["cls"]})"'
                 f' stroke-width="{1.9 if r["mm2"]<=0.5 else 2.5:.1f}"'
                 ' stroke-linejoin="round" stroke-linecap="round"/>')

    for name, (axis, c0, c1, s0, s1) in S.DUCTS.items():
        x, y, w, d = ((s0, c0, s1 - s0, c1 - c0) if axis == "h"
                      else (c0, s0, c1 - c0, s1 - s0))
        p.append(f'<rect x="{X(x):.1f}" y="{Y(y):.1f}" width="{w*scale:.1f}"'
                 f' height="{d*scale:.1f}" fill="var(--duct-lid)" stroke="currentColor"'
                 ' stroke-width="1" stroke-dasharray="6 4" opacity=".95"/>')
        kind, nom = S.DUCT_KIND[name]
        lab = f'{name} · {nom:.0f} mm duct' if kind == "duct" else f'{name} · clipped, not a duct'
        if axis == "h":
            p.append(f'<text x="{X(x+w)-4:.1f}" y="{Y(y)-5:.1f}" font-size="9.5"'
                     f' font-weight="600" fill="currentColor" opacity=".6"'
                     f' text-anchor="end">{lab}</text>')
        else:
            tx, ty = X(x + w / 2) + 3.5, Y(y + d) - 5
            p.append(f'<text x="{tx:.1f}" y="{ty:.1f}" font-size="9.5" font-weight="600"'
                     f' fill="currentColor" opacity=".6"'
                     f' transform="rotate(-90 {tx:.1f} {ty:.1f})">{lab}</text>')

    for label, x, y, wall in S.PANEL:
        p.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="4.5" fill="var(--accent)"/>')
        if wall == "front":
            p.append(f'<text x="{X(x):.1f}" y="{Y(y)+17:.1f}" font-size="10"'
                     f' fill="currentColor" opacity=".85" text-anchor="middle">{esc(label)}</text>')
        else:
            left = wall == "left"
            p.append(f'<text x="{X(x)+(-9 if left else 9):.1f}" y="{Y(y)+4:.1f}"'
                     f' font-size="10" fill="currentColor" opacity=".85"'
                     f' text-anchor="{"end" if left else "start"}">{esc(label)}</text>')

    lx, ly = X(8), Y(H) + 26
    for i, (k, lab) in enumerate(S.LEGEND):
        cx, cy = lx + (i % 4) * 160, ly + (i // 4) * 18
        p.append(f'<line x1="{cx:.0f}" y1="{cy:.0f}" x2="{cx+20:.0f}" y2="{cy:.0f}"'
                 f' stroke="var(--w-{k})" stroke-width="2.6" stroke-linecap="round"/>')
        p.append(f'<text x="{cx+27:.0f}" y="{cy+4:.0f}" font-size="10.5" fill="currentColor"'
                 f' opacity=".8">{esc(lab)}</text>')
    p.append(f'<text x="{lx:.0f}" y="{ly + 18*((len(S.LEGEND)+3)//4) + 22:.0f}" font-size="10.5"'
             ' fill="currentColor" opacity=".6">Shaded bands are the ducts, drawn over the'
             ' conductors — with the lids on, only the stubs show. Each conductor has its'
             ' own lane inside.</text>')
    p.append("</svg>")
    return "\n".join(p)


def elevation_svg(S, scale=2.4, h_tall=85.0, h_block=58.0):
    sched, rail_len = rail_schedule(S)
    # A rail with no breakers on it is only as tall as a terminal block; drawing
    # it in an 85 mm frame leaves a third of the figure empty and magnifies the
    # whole thing, because the page stretches any SVG to its column.
    if not any(k in ("mcb", "relay") for _n, _x, _w, k, _o in sched):
        h_tall = h_block
    # Block names are drawn rotated above each block. Where the frame is as tall
    # as the blocks there is no headroom for them, so make some.
    label_room = 0 if h_tall > h_block else 52
    pad_l, pad_t = 16, 30 + label_room
    vw, vh = rail_len * scale + pad_l * 2, h_tall * scale + pad_t + 80
    X = lambda mm: pad_l + (mm - S.RAIL_START) * scale
    base = pad_t + h_tall * scale

    p = [f'<svg viewBox="0 0 {vw:.0f} {vh:.0f}" role="img"'
         f' style="max-width:{vw*1.7:.0f}px" xmlns="http://www.w3.org/2000/svg"'
         f' aria-label="{esc(S.ELEV_ALT)}">']
    p.append(f'<line x1="{X(S.RAIL_START):.1f}" y1="{base:.1f}"'
             f' x2="{X(S.RAIL_START+rail_len):.1f}" y2="{base:.1f}"'
             ' stroke="currentColor" stroke-width="3" opacity=".7"/>')
    for name, x, w, kind, _note in sched:
        if kind in ("part", "clamp"):
            continue
        tall = kind in ("mcb", "relay")
        h = h_tall if tall else h_block
        fill = RAIL_FILL.get(kind, f"var(--w-{kind})")
        p.append(f'<rect x="{X(x):.1f}" y="{base - h*scale:.1f}"'
                 f' width="{max(w*scale-1.2,2.5):.1f}" height="{h*scale:.1f}" rx="1.5"'
                 f' fill="{fill}" opacity=".88"/>')
        if tall:
            p.append(f'<text x="{X(x+w/2):.1f}" y="{base - h*scale/2 + 4:.1f}"'
                     ' text-anchor="middle" font-size="12" font-weight="600"'
                     f' fill="var(--surface)">{esc(name)}</text>')
        else:
            tx, ty = X(x + w / 2), base - h * scale - 6
            p.append(f'<text x="{tx:.1f}" y="{ty:.1f}" text-anchor="start" font-size="9"'
                     f' fill="currentColor" opacity=".8"'
                     f' transform="rotate(-90 {tx:.1f} {ty:.1f})">{esc(name)}</text>')
    for grp in S.JUMPERS:
        xs = [x for n, x, _w, _k, _o in sched if n in grp]
        ws = [w for n, _x, w, _k, _o in sched if n in grp]
        if not xs:
            continue
        a, b = min(xs) + 1.2, max(xs) + max(ws) - 1.2
        yy = base - h_block * scale * 0.52
        p.append(f'<line x1="{X(a):.1f}" y1="{yy:.1f}" x2="{X(b):.1f}" y2="{yy:.1f}"'
                 ' stroke="var(--surface)" stroke-width="3.4" stroke-linecap="round"'
                 ' opacity=".95"/>')
    for label, a, b in S.ELEV_ZONES:
        y = base + 16
        p.append(f'<line x1="{X(a):.1f}" y1="{y:.1f}" x2="{X(b):.1f}" y2="{y:.1f}"'
                 ' stroke="currentColor" stroke-width="1.2" opacity=".5"/>')
        p.append(f'<text x="{X((a+b)/2):.1f}" y="{y+15:.1f}" text-anchor="middle"'
                 f' font-size="10.5" fill="currentColor" opacity=".72">{esc(label)}</text>')
    p.append(f'<text x="{X(S.RAIL_START):.1f}" y="{pad_t-label_room-12:.1f}"'
             f' font-size="10.5"'
             f' fill="currentColor" opacity=".7">{esc(S.ELEV_NOTE.format(rail=rail_len))}</text>')
    p.append("</svg>")
    return "\n".join(p)


# --- page --------------------------------------------------------------------

_TOKENS_LIGHT = """
  --paper:#e9edf1; --surface:#fff; --surface-2:#f1f5f8; --rail:#dde4ea;
  --duct:#e4ebf1; --duct-lid:rgba(255,255,255,.22);
  --g-steel:#dfe4e8; --g-pcb:#cdd9c4; --g-abs:#f0f2f4; --g-heat:#d7dde2;
  --ink:#131b22; --ink-2:#4a5a67; --ink-3:#7d8d9a; --line:#ccd6de; --line-2:#dde4ea;
  --accent:#c2622c;
  --w-L:#7d4426; --w-N:#2d5c8c; --w-E:#5d7f2e;
  --w-v24:#c33a2a; --w-v0:#2b343b; --w-v6:#c2821a; --w-v5:#9c8418;
  --w-motA:#3f7a46; --w-motB:#2f6a9c; --w-sig:#7a4fa3; --w-es:#2a7f86; --w-pwm:#a8457f;
  --w-ctrl:#7a4fa3; --w-sp:#aab6c0;
"""
_TOKENS_DARK = """
  --paper:#0c1218; --surface:#141d25; --surface-2:#18212a; --rail:#232f38;
  --duct:#1e2831; --duct-lid:rgba(20,29,37,.28);
  --g-steel:#2b3740; --g-pcb:#36442f; --g-abs:#283139; --g-heat:#303c45;
  --ink:#e4ecf2; --ink-2:#9aabb8; --ink-3:#6c7d8a; --line:#26333d; --line-2:#1e2a33;
  --accent:#e08a52;
  --w-L:#c08055; --w-N:#5f94c4; --w-E:#90b85c;
  --w-v24:#e2614c; --w-v0:#97a6b2; --w-v6:#d9a63f; --w-v5:#cbb43c;
  --w-motA:#6fb878; --w-motB:#5fa0d4; --w-sig:#a67fd0; --w-es:#4fb5bd; --w-pwm:#d87ab0;
  --w-ctrl:#a67fd0; --w-sp:#55646f;
"""

HEAD = """<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap">
<style>
:root{__L__}
@media (prefers-color-scheme:dark){ :root:not([data-theme="light"]){__D__}}
:root[data-theme="dark"]{__D__}
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
""".replace("__L__", _TOKENS_LIGHT).replace("__D__", _TOKENS_DARK)


def wire_rows(S, routes):
    rows = []
    for title, classes in S.GROUPS:
        rows.append(f'<tr><td class="grp" colspan="9">{esc(title)}</td></tr>')
        for r in [x for x in routes if x["cls"] in classes]:
            rt = " → ".join(f"{d}·{l}" for d, l in r["lanes"])
            rows.append(
                f'<tr><td class="id">{r["id"][1:]}</td>'
                f'<td><span class="sw" style="background:var(--w-{r["cls"]})"></span>'
                f'{esc(r["la"])}</td><td>{esc(r["lb"])}</td>'
                f'<td class="num">{r["mm2"]}</td><td>{esc(S.COLOUR[r["cls"]])}</td>'
                f'<td class="num">{esc(S.FERRULE[r["mm2"]])}</td>'
                f'<td class="num">{rt}</td><td class="num">{r["len"]:.0f}</td>'
                f'<td>{esc(r["note"])}</td></tr>')
    return "".join(rows)


def cut_rows(routes):
    cut = {}
    for r in routes:
        n, m = cut.get(r["mm2"], (0, 0.0))
        cut[r["mm2"]] = (n + 1, m + r["len"])
    return "".join(f'<tr><td class="num">{k}</td><td class="num">{v[0]}</td>'
                   f'<td class="num">{v[1]/1000:.2f}</td></tr>'
                   for k, v in sorted(cut.items()))


def jumper_rows(S):
    return "".join(f'<tr><td>{" – ".join(g)}</td><td class="num">{len(g)}</td></tr>'
                   for g in S.JUMPERS)


def sched_rows(S):
    out = []
    for name, x, w, kind, note in rail_schedule(S)[0]:
        if kind in ("part", "clamp"):
            continue
        out.append(f'<tr><td><span class="sw" style="background:var(--w-{kind})"></span>'
                   f'{esc(name)}</td><td class="num">{x:.1f}</td>'
                   f'<td class="num">{w:.1f}</td><td>{esc(note)}</td></tr>')
    return "".join(out)


def render(S):
    """Route, check, and return the finished HTML. Raises if it is not buildable."""
    routes, used = build_routes(S)
    bad, inn, out = check(S, routes, used)
    if bad:
        raise ValueError("layout is not buildable:\n  " + "\n  ".join(bad))
    total = sum(r["len"] for r in routes) / 1000
    html = (S.PAGE
            .replace("__HEAD__", HEAD)
            .replace("__PLAN__", plan_svg(S, routes))
            .replace("__ELEV__", elevation_svg(S))
            .replace("__WIRES__", wire_rows(S, routes))
            .replace("__CUT__", cut_rows(routes))
            .replace("__JUMP__", jumper_rows(S))
            .replace("__SCHED__", sched_rows(S))
            .replace("__NWIRE__", str(len(routes)))
            .replace("__TOTAL__", f"{total:.1f}")
            .replace("__RAIL__", f"{rail_schedule(S)[1]:.0f}")
            .replace("__XING__", str(inn)))
    for key, value in getattr(S, "EXTRA_SUBS", {}).items():
        html = html.replace(key, value)
    return html, routes, used, inn


def write(S):
    html, routes, used, inn = render(S)
    S.OUT.parent.mkdir(parents=True, exist_ok=True)
    S.OUT.write_text(html)
    print(f"wrote {S.OUT.relative_to(S.OUT.parent.parent.parent)} "
          f"({S.OUT.stat().st_size/1024:.0f} KB)")
    print(f"  {len(routes)} conductors, {sum(r['len'] for r in routes)/1000:.2f} m, "
          f"{inn} in-duct crossings, 0 on open floor")
    print("  lanes: " + ", ".join(f"{d} {n}/{capacity(S, d)}" for d, n in used.items()))
    return S.OUT
