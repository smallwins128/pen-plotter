#!/usr/bin/env python3
"""Over-plates: a stainless saddle over the control box and a bumper band round the power box's front.

    python3 hardware/sheet/overplates.py      # checks + a summary (enclosure.py builds and writes them)

Both stand off the boxes on M3 standoffs. They never cover a port: every port gets a window with
KEEP mm of air round its printed plate, and the fans get slotted grilles. Corners are bump-bent,
BUMP_N bends of BUMP_DEG each, BUMP_A mm apart, so they read as a smooth curve.

Frame (the stack): x across (+ right), y up from the power box's base underside, z toward the front.
f = ZF - z is the distance back from the bodies' front outer face; side-plate outlines are drawn in (f, y).

Flats are drawn from the INSIDE face (the face toward the boxes): every bend goes UP.
"""
import functools
import math
import sys

from shapely.geometry import LineString, Point, Polygon, box as sbox
from shapely.ops import unary_union

import enclosure as E

# ============================================================================
# DIMENSIONS (mm)
# ============================================================================
HB = {k: E.T + E.H[k] for k in E.H}                                   # body height, base underside to top lips
Y0 = {"power": 0.0, "control": HB["power"] + E.T + E.STACK["flange_h"]}   # base underside of each box, stack frame
LIDTOP = {k: Y0[k] + HB[k] + E.T for k in Y0}                         # lid top surface
XO, ZF = E.WO / 2, E.ZF                                               # body wall outer face, front outer face
F_BACK = E.ZF - (E.ZB - E.T)                                          # lid back outer face, as f

KEEP = 10.0          # air round every port's printed plate
EDGE_R = 5.0         # every outline corner
MIN_WEB = 12.0       # narrowest steel left between windows and edges (a web touching the corner counts the corner)
BUMP_N, BUMP_DEG, BUMP_A = 6, 15.0, 5.0     # corners: 6 bends of 15 deg, 5 mm flat between bends
RIVNUT_FLANGE = 1.0  # M3 rivnut flange thickness, proud of the wall
WASHER_T = 1.2       # the lid fixings' penny washers

SAD = dict(t=1.5, R=1.5, mat="1.5 mm 304 stainless, brushed, film on, deburred + edge-rounded",
           side_gap=16.0,               # wall outer face to the plate's inner face: M3 x 15 standoff on the rivnut flange
           top_standoff=15.0,           # M3 x 15 male-female standoff replaces each lid-top screw
           f_nose=-40.0, f_tail=292.0,  # visor overhang in front, back edge 6 mm short of the lid back
           flange=10.0)                 # visor + back flanges, measured down from the top's outer face
SAD["top_gap"] = WASHER_T + SAD["top_standoff"]
BND = dict(t=1.0, R=1.0, mat="1.0 mm 304 stainless, brushed, film on, deburred + edge-rounded",
           gap=16.0, y0=6.0, y1=72.0,
           left_to=82.0, right_to=54.0, slant=12.0)   # side flanges: how far back (f) at the bottom; top edge ends `slant` shorter
LAPTOP_N, LEAN_N = 20.0, 100.0         # 2 kg laptop; 10 kg leaning hand
E_STEEL, NU, SIGMA_Y = 193000.0, 0.29, 205.0
TOP_RIVNUT_F = (40.0, 256.0)           # extra lid-top fixings on the control box's side lips (front, back), as f


def ba(deg, R, t):
    return math.radians(deg) * (R + E.K * t)


def corner(R, t, n=BUMP_N, deg=BUMP_DEG, a=BUMP_A, samples=4):
    """Inner surface of a bump-bent 90 deg corner: from the tangent on the first flat, heading outward (+u),
    turning down (-v). Returns the sampled polyline, its extents (du, dv), its developed length, and each
    bend's centre as developed distance from the start."""
    u = v = phi = 0.0
    pts = [(0.0, 0.0)]
    centres, s = [], 0.0
    b = ba(deg, R, t)
    for i in range(n):
        p0, p1 = phi, phi + math.radians(deg)
        cu, cv = u - R * math.sin(p0), v - R * math.cos(p0)
        for k in range(1, samples + 1):
            q = p0 + (p1 - p0) * k / samples
            pts.append((cu + R * math.sin(q), cv + R * math.cos(q)))
        u, v = pts[-1]; phi = p1
        centres.append(s + b / 2); s += b
        if i < n - 1:
            u += a * math.cos(phi); v -= a * math.sin(phi); pts.append((u, v)); s += a
    return dict(pts=pts, du=u, dv=-v, dev=s, centres=centres, ba=b)


def section(inner, t):
    """Closed cross-section of a sheet whose inner surface is `inner` (outer side = left of travel)."""
    outer = []
    for i, (x, y) in enumerate(inner):
        a = inner[max(i - 1, 0)]; b = inner[min(i + 1, len(inner) - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy)
        outer.append((x - dy / L * t, y + dx / L * t))
    return inner + outer[::-1]


def bez(p0, p1, p2, p3, n=24):
    return [tuple((1 - s) ** 3 * a + 3 * (1 - s) ** 2 * s * b + 3 * (1 - s) * s ** 2 * c + s ** 3 * d
                  for a, b, c, d in zip(p0, p1, p2, p3)) for s in (i / n for i in range(n + 1))]


def rounded(p, r):
    return p.buffer(-r, join_style=1).buffer(2 * r, join_style=1).buffer(-r, join_style=1)


# ============================================================================
# WHAT IS ON THE WALLS (from the cut-file model, before any over-plate holes)
# ============================================================================
@functools.lru_cache(maxsize=None)
def wall_features():
    """Per side wall ('left'/'right') and the power front: (name, f0, f1, y0, y1) in the stack frame."""
    out = {"left": [], "right": [], "front": []}
    for kind in ("control", "power"):
        b = E.body(kind, overplates=False)
        for wall, u0, u1, v0, v1, name in b.feat:
            y0, y1 = Y0[kind] + v0, Y0[kind] + v1
            if wall == "front":
                out["front"].append((f"{kind} {name}", u0, u1, y0, y1))
            else:
                out[wall].append((f"{kind} {name}", ZF - u1, ZF - u0, y0, y1))
    return out


def keepouts(side):
    """Windows: every port on that side; fans are not windows (they get grilles)."""
    return [(n, sbox(f0, y0, f1, y1).buffer(KEEP, 32)) for n, f0, f1, y0, y1 in wall_features()[side] if "fan" not in n]


def fans(side):
    return [(n, ((f0 + f1) / 2, (y0 + y1) / 2)) for n, f0, f1, y0, y1 in wall_features()[side] if "fan" in n]


# ============================================================================
# SADDLE GEOMETRY
# ============================================================================
C_SAD = corner(SAD["R"], SAD["t"])
XS = XO + SAD["side_gap"]                       # side plates' inner face
YT = LIDTOP["control"] + SAD["top_gap"]         # top's inner (under) face
X_TOP = XS - C_SAD["du"]                        # top flat ends (tangent of the first corner bend)
ST = YT - C_SAD["dv"]                           # side flats start (tangent of the last corner bend)


def leg_tip_y(side):
    """The leg ends above every port below the control box on that side."""
    tops = [k.bounds[3] for n, k in keepouts(side) if n.startswith("power")]
    tops += [y1 for n, (f, y) in fans(side) if n.startswith("power") for y1 in [y + 40]]
    return max(tops) + 4.0


def side_outline(side):
    """The 7: a band under the top, a nose over the front, a leg sweeping down and back. Square along the bend (y = ST)."""
    fn, ft, tip = SAD["f_nose"], SAD["f_tail"], leg_tip_y(side)
    pts = [(fn, ST), (ft, ST)]
    pts += bez((ft, ST), (ft - 14, ST - 26), (222, ST - 36), (200, ST - 62))[1:]
    pts += bez((200, ST - 62), (222, ST - 92), (246, tip + 30), (262, tip))[1:]
    pts += bez((262, tip), (232, tip - 4), (95, ST - 92), (2, ST - 20))[1:]
    pts += bez((2, ST - 20), (-14, ST - 10), (fn + 10, ST - 1), (fn, ST))[1:]
    return Polygon(pts)


@functools.lru_cache(maxsize=None)
def side_plate(side):
    """Side flat with windows, every corner rounded except along the bend line."""
    above = sbox(SAD["f_nose"], ST, SAD["f_tail"], ST + 40)
    p = unary_union([side_outline(side), above])
    for _, k in keepouts(side):                   # windows: KEEP mm of air all round, so their corners are R KEEP
        p = p.difference(k)
    p = p.buffer(-EDGE_R, join_style=1).buffer(EDGE_R, join_style=1)   # round every outside corner (removes steel only)
    return p.intersection(sbox(-1e3, -1e3, 1e3, ST))


# ============================================================================
# BAND GEOMETRY
# ============================================================================
C_BND = corner(BND["R"], BND["t"])
XB = XO + BND["gap"]                            # side flanges' inner face
ZBF = ZF + BND["gap"]                           # front plate's inner face
X_FRONT = XB - C_BND["du"]                      # front flat ends
F_SIDE0 = ZF - (ZBF - C_BND["dv"])              # side flats start, as f


def band_side(side):
    to = BND["left_to"] if side == "left" else BND["right_to"]
    y0, y1 = BND["y0"], BND["y1"]
    p = Polygon([(F_SIDE0 - 40, y0), (to, y0), (to - BND["slant"], y1), (F_SIDE0 - 40, y1)])
    p = rounded(p, EDGE_R).intersection(sbox(F_SIDE0, -1e3, 1e3, 1e3))
    return p


# ============================================================================
# STANDOFFS (rivnuts in the bodies)
# ============================================================================
def _free(side, f, y, kind):
    """A wall rivnut at (f, y) in `kind`'s side wall: inside the wall's usable area, clear of every feature."""
    top = Y0[kind] + HB[kind]
    if not (Y0[kind] + E.PLATE_Y[1] + 7 <= y <= top - E.BAND - 4.5):   # body clear of the base plate; flange clear of the lid band
        return False
    if not (12.0 <= f <= F_BACK - E.BAND - 4.5):              # clear of the corner tab and the lid's back returns
        return False
    for n, f0, f1, y0, y1 in wall_features()[side]:
        if sbox(f0, y0, f1, y1).distance(Point(f, y)) < 4.0 + 4.0:   # flange Ø8 + 4 mm
            return False
    return True


@functools.lru_cache(maxsize=None)
def _side_standoffs(side):
    return _pick_standoffs(side, side_plate(side))


def side_standoffs(side, plate=None):
    return _side_standoffs(side)


def _pick_standoffs(side, plate):
    """Two per side, on the control box's wall, inside the plate with margin, as far apart as they can be."""
    ok_area = plate.buffer(-6.0)
    cand = []
    y = Y0["control"]
    while y <= LIDTOP["control"]:
        f = 0.0
        while f <= F_BACK:
            if _free(side, f, y, "control") and ok_area.contains(Point(f, y)):
                cand.append((f, y))
            f += 3.0
        y += 3.0
    best, bd = None, -1
    for i in range(len(cand)):
        for j in range(i + 1, len(cand)):
            d = math.dist(cand[i], cand[j])
            if d > bd:
                best, bd = (cand[i], cand[j]), d
    return list(best) if best else []


def top_fixings():
    """(x, f) of every lid-top fixing on the control box: the 3 it already has + 4 on the side lips."""
    x = XO - E.T - E.RIV_IN
    return [(-x, ZF), (x, ZF), (0.0, E.T + E.RIV_IN)] + [(s * x, f) for s in (-1, 1) for f in TOP_RIVNUT_F]


def band_front_standoffs():
    return [(-150.0, 40.0), (0.0, 40.0), (150.0, 40.0)]       # (x, y) on the power front


def band_side_standoffs():
    return {"left": [], "right": [(30.0, 40.0)]}               # (f, y); the left flange sits over the fan


def body_rivnuts(kind):
    """Rivnuts the over-plates need in this body, for enclosure.body(): (face, u, v)."""
    out = []
    if kind == "control":
        for s in ("left", "right"):
            for f, y in side_standoffs(s, side_plate(s)):
                out.append((s, ZF - f, y - Y0[kind]))
    else:
        for x, y in band_front_standoffs():
            out.append(("front", x, y - Y0[kind]))
        for s, lst in band_side_standoffs().items():
            for f, y in lst:
                out.append((s, ZF - f, y - Y0[kind]))
    return out


def lid_top_rivnuts(kind):
    """Extra rivnuts in the body's side top lips (x, z), with a clearance hole in the lid over each."""
    if kind != "control":
        return []
    x = XO - E.T - E.RIV_IN
    return [(s * x, ZF - f) for s in (-1, 1) for f in TOP_RIVNUT_F]


# ============================================================================
# FLAT PATTERNS
# ============================================================================
def _slots(plate, centre, r=36.0, pitch=8.0, w=4.0):
    """Horizontal grille slots over a fan, clipped to the plate (4 mm in from every edge)."""
    cf, cy = centre
    room = plate.buffer(-4.0 - w / 2)
    out, y = [], cy - r + pitch / 2
    while y < cy + r:
        h = math.sqrt(max(r * r - (y - cy) ** 2, 0.0))
        seg = LineString([(cf - h, y), (cf + h, y)]).intersection(room)
        for g in getattr(seg, "geoms", [seg]):
            if not g.is_empty and g.length >= 6:
                out.append(list(g.coords))
        y += pitch
    return out


def _slot_hole(p0, p1, w, note, face):
    return dict(kind="slot", p0=p0, p1=p1, r=w / 2, note=note, face=face, type="vent",
                geom=LineString([p0, p1]).buffer(w / 2, 24))


def _circle(c, d, note, face):
    return dict(kind="circle", c=c, r=d / 2, note=note, face=face, type="m3", geom=Point(c).buffer(d / 2, 48))


def saddle():
    t, R = SAD["t"], SAD["R"]
    p = E.Part("saddle", "SADDLE (over the control box)", SAD["mat"])
    c = C_SAD
    b90 = ba(90, R, t)
    fn, ft, fl = SAD["f_nose"], SAD["f_tail"], SAD["flange"]
    # top: X = x, Y = -f; flanges fold down at the visor (front) and the back
    yf_tan, yb_tan = -(fn + t + R), -(ft - t - R)              # top flat's tangents, front and back
    top = sbox(-X_TOP, yb_tan, X_TOP, yf_tan)
    p.solid.append(top); p.faces["top"] = top
    leg = fl - t - R                                           # flange leg beyond its bend zone
    for name, y_tan, sgn in (("visor", yf_tan, 1), ("back", yb_tan, -1)):
        z = sbox(-X_TOP + 1, min(y_tan, y_tan + sgn * b90), X_TOP - 1, max(y_tan, y_tan + sgn * b90))
        g = sbox(-X_TOP + 1, min(y_tan + sgn * b90, y_tan + sgn * (b90 + leg)), X_TOP - 1, max(y_tan + sgn * b90, y_tan + sgn * (b90 + leg)))
        p.solid += [z, g]
        yl = y_tan + sgn * b90 / 2
        p.bends.append(dict(line=((-X_TOP + 1, yl), (X_TOP - 1, yl)), note=f"Up 90° R{R:g}", zone=z, ba=b90))
        for sx in (-1, 1):                                     # relief where the flange meets the corner's first bend
            x0, x1 = sorted((sx * (X_TOP - 1), sx * X_TOP))
            p.relief.append(sbox(x0, min(y_tan - sgn * 1.0, y_tan + sgn * (b90 + leg) + sgn), x1,
                                 max(y_tan - sgn * 1.0, y_tan + sgn * (b90 + leg) + sgn)))
    # corners + sides: X = sgn * (X_TOP + s) where s is developed distance from the top's tangent
    Yn, Yt = -fn, -ft
    for side, sgn in (("left", -1), ("right", 1)):
        x0, x1 = sorted((sgn * X_TOP, sgn * (X_TOP + c["dev"])))
        p.solid.append(sbox(x0, Yt, x1, Yn))
        for cc in c["centres"]:
            xl = sgn * (X_TOP + cc)
            zx0, zx1 = sorted((sgn * (X_TOP + cc - c["ba"] / 2), sgn * (X_TOP + cc + c["ba"] / 2)))
            p.bends.append(dict(line=((xl, Yt), (xl, Yn)), note=f"Up {BUMP_DEG:g}° R{R:g}", zone=sbox(zx0, Yt, zx1, Yn), ba=c["ba"]))
        sp = side_plate(side)
        def m(f, y, sgn=sgn): return (sgn * (X_TOP + c["dev"] + (ST - y)), -f)
        flat = unary_union([Polygon([m(f, y) for f, y in g.exterior.coords], [[m(f, y) for f, y in r.coords] for r in g.interiors])
                            for g in getattr(sp, "geoms", [sp])])           # a split plate fails "one piece" in the checks
        p.solid.append(flat); p.faces[side] = flat
        for _, centre in fans(side):
            for seg in _slots(sp, centre):
                p.holes.append(_slot_hole(m(*seg[0]), m(*seg[-1]), 4.0, "fan grille", side))
        for f, y in side_standoffs(side, sp):
            p.holes.append(_circle(m(f, y), 3.4, "Ø3.4 standoff (M3)", side)); p.holes[-1]["at"] = (side, f, y)
    for x, f in top_fixings():
        p.holes.append(_circle((x, -f), 3.4, "Ø3.4 standoff (M3)", "top")); p.holes[-1]["at"] = ("top", x, f)
    p.title_lines = [p.title, f"Material: {p.material}   Qty: 1   Units: mm",
                     f"Drawn from the INSIDE face (toward the box). Corners: {BUMP_N} bends of {BUMP_DEG:g}° each, "
                     f"{BUMP_A:g} mm flat between bends, R{R:g}. Visor + back: Up 90° R{R:g}.",
                     f"Flat assumes K {E.K}: {BUMP_DEG:g}° allowance {c['ba']:.3f}, 90° allowance {b90:.3f}. Shop's values win: re-run if different.",
                     "All cut edges deburred and edge-rounded (it is handled)."]
    p.notes = [f"Folded: top {2 * XS + 2 * t:.0f} wide over the sides, {ft - fn:.0f} deep; visor {-fn:.0f} mm past the front"]
    return p


def band():
    t, R = BND["t"], BND["R"]
    p = E.Part("band", "BUMPER BAND (round the power box's front)", BND["mat"])
    c = C_BND
    y0, y1 = BND["y0"], BND["y1"]
    # front: X = -x (drawn from inside, looking forward), Y = y
    front = sbox(-X_FRONT, y0, X_FRONT, y1)
    p.solid.append(front); p.faces["front"] = front
    for side, sx in (("left", -1), ("right", 1)):
        X = lambda s, sx=sx: -sx * (X_FRONT + s)
        x0, x1 = sorted((X(0), X(c["dev"])))
        p.solid.append(sbox(x0, y0, x1, y1))
        for cc in c["centres"]:
            zx0, zx1 = sorted((X(cc - c["ba"] / 2), X(cc + c["ba"] / 2)))
            p.bends.append(dict(line=((X(cc), y0), (X(cc), y1)), note=f"Up {BUMP_DEG:g}° R{R:g}", zone=sbox(zx0, y0, zx1, y1), ba=c["ba"]))
        sp = band_side(side)
        def m(f, y, X=X): return (X(c["dev"] + (f - F_SIDE0)), y)
        flat = Polygon([m(f, y) for f, y in sp.exterior.coords])
        p.solid.append(flat); p.faces[side] = flat
        for _, centre in fans(side):
            if not sp.intersects(Point(centre).buffer(40)):
                continue
            for seg in _slots(sp, centre):
                p.holes.append(_slot_hole(m(*seg[0]), m(*seg[-1]), 4.0, "fan grille", side))
        for f, y in band_side_standoffs()[side]:
            p.holes.append(_circle(m(f, y), 3.4, "Ø3.4 standoff (M3)", side)); p.holes[-1]["at"] = (side, f, y)
    for x, y in band_front_standoffs():
        p.holes.append(_circle((-x, y), 3.4, "Ø3.4 standoff (M3)", "front")); p.holes[-1]["at"] = ("front", x, y)
    p.title_lines = [p.title, f"Material: {p.material}   Qty: 1   Units: mm",
                     f"Drawn from the INSIDE face. Corners: {BUMP_N} bends of {BUMP_DEG:g}° each, {BUMP_A:g} mm flat between bends, R{R:g}.",
                     f"Flat assumes K {E.K}: {BUMP_DEG:g}° allowance {c['ba']:.3f}. Shop's value wins: re-run if different.",
                     "Long flange (slotted) = the power box's LEFT side (fan side). All cut edges deburred and edge-rounded."]
    p.notes = [f"Folded: {2 * XB + 2 * t:.0f} wide, {y1 - y0:.0f} tall, {BND['gap']:g} mm off the front"]
    return p


def parts():
    return [saddle(), band()]


# ============================================================================
# CHECKS
# ============================================================================
def laptop_check():
    """Hand estimates for the saddle's top (not FE): a plate on four supported edges (side rows of standoffs,
    visor + back flanges), plus the flanges' own sag as beams between the side plates."""
    t = SAD["t"]
    a = SAD["f_tail"] - SAD["f_nose"]                 # between the flanges
    b = 2 * X_TOP                                     # between the side rows
    a, b = min(a, b), max(a, b)
    Dp = E_STEEL * t ** 3 / (12 * (1 - NU ** 2))
    r = b / a
    alpha = 0.01160 + (0.01484 - 0.01160) * min(max((r - 1.0) / 0.4, 0), 1)   # Timoshenko, central load, SS edges
    plate = lambda P: alpha * P * a * a / Dp
    # flange as an L beam: the flange leg + 25 t of top
    h, w = SAD["flange"], 25 * t
    A1, A2 = w * t, (h - t) * t
    yc = (A1 * (h - t / 2) + A2 * (h - t) / 2) / (A1 + A2)
    I = w * t ** 3 / 12 + A1 * (h - t / 2 - yc) ** 2 + t * (h - t) ** 3 / 12 + A2 * ((h - t) / 2 - yc) ** 2
    beam = lambda P: (P / 4) * (2 * X_TOP) ** 3 / (48 * E_STEEL * I)   # a quarter of the load reaches each flange's midspan
    c_ = 25.0                                          # hand contact radius
    sigma = 3 * LEAN_N / (2 * math.pi * t ** 2) * ((1 + NU) * math.log(2 * a / (math.pi * c_)) + 1)
    return dict(lean=plate(LEAN_N) + beam(LEAN_N), laptop=plate(LAPTOP_N) + beam(LAPTOP_N), sigma=sigma)


def checks(ps=None):
    out = []
    def ok(c, part, text): out.append((bool(c), part, text))
    ps = ps or parts()
    by = {p.name: p for p in ps}
    # --- every flat: one piece, holes inside with margin and clear of bend zones, bend zones the right width
    for p in ps:
        g = p.outline()
        ok(g.geom_type == "Polygon", p.name, f"outline is one piece ({g.geom_type})")
        for h in p.holes:
            ok(g.buffer(-3.0).contains(h["geom"]), p.name, f"{h['note']} ≥3 mm inside the outline")
            dz = min(h["geom"].distance(b["zone"]) for b in p.bends)
            ok(dz >= 3.0, p.name, f"{h['note']} {dz:.1f} mm from a bend zone (min 3)")
        for b in p.bends:
            zb = b["zone"].bounds
            wdt = min(zb[2] - zb[0], zb[3] - zb[1])
            ok(abs(wdt - b["ba"]) < 1e-6, p.name, f"bend zone = allowance ({b['ba']:.3f})")
        hs = [h["geom"] for h in p.holes]
        worst = min((hs[i].distance(hs[j]) for i in range(len(hs)) for j in range(i + 1, len(hs))), default=99)
        ok(worst >= 3.0, p.name, f"narrowest web between holes {worst:.1f} mm (min 3)")
    # --- ports: no plate within KEEP of any port's printed plate (straight from the walls, not from the window list)
    ports = {s: [(n, sbox(f0, y0, f1, y1).buffer(KEEP - 0.05, 32)) for n, f0, f1, y0, y1 in wall_features()[s] if "fan" not in n]
             for s in ("left", "right")}
    for side in ("left", "right"):
        sp = side_plate(side)
        for n, k in ports[side]:
            a = sp.intersection(k).area
            ok(a < 0.5, "saddle", f"{side} side clear of {n} by {KEEP:g} mm")
        bs = band_side(side)
        for n, k in ports[side]:
            ok(bs.intersection(k).area < 0.5, "band", f"{side} flange clear of {n} by {KEEP:g} mm")
        # webs: the side plate plus the corner above it must have no web under MIN_WEB
        with_corner = unary_union([sp, sbox(SAD["f_nose"], ST, SAD["f_tail"], ST + 18)])
        ok(with_corner.buffer(-MIN_WEB / 2 + 0.01).geom_type == "Polygon", "saddle", f"{side} side: every web ≥ {MIN_WEB:g} mm")
        # rounded corners: opening by the edge radius changes nothing below the bend line
        op = sp.buffer(-(EDGE_R - 0.5), join_style=1).buffer(EDGE_R - 0.5, join_style=1)
        ok(sp.difference(op).difference(sbox(-1e3, ST - 2 * EDGE_R, 1e3, ST + 1)).area < 1.0, "saddle", f"{side} side: every corner R ≥ {EDGE_R - 0.5:g}")
        # fans: under a plate they get a grille with real open area
        for n, (cf, cy) in fans(side):
            disc = Point(cf, cy).buffer(36)
            for nm, plate in (("saddle", sp), ("band", band_side(side))):
                cov = plate.intersection(disc).area
                if cov < 1:
                    continue
                part = by[nm]
                op_ = sum(h["geom"].area for h in part.holes if h["note"] == "fan grille" and h["face"] == side)
                ok(op_ / cov >= 0.35, nm, f"{side}: {n} grille open {100 * op_ / cov:.0f}% of the steel over it (min 35)")
    # --- clearances in the stack
    lid_out = XO + E.CLR + E.T
    ok(XS - lid_out >= 8.0, "saddle", f"sides {XS - lid_out:.1f} mm outside the lid returns (min 8)")
    ok(XS - (XO + 3.0) >= 10.0, "saddle", f"sides {XS - XO - 3:.1f} mm outside the printed panels (min 10)")
    ok(SAD["top_gap"] - E.STACK["lid_fix_h"] >= 2.0, "saddle", f"top {SAD['top_gap'] - E.STACK['lid_fix_h']:.1f} mm above the lid fixings (min 2)")
    back_bottom = YT + SAD["t"] - SAD["flange"]
    ok(back_bottom - LIDTOP["control"] >= 2.0, "saddle", f"back flange ends {back_bottom - LIDTOP['control']:.1f} mm above the lid (min 2)")
    inner = [(X_TOP + u, YT + v) for u, v in C_SAD["pts"]]
    dl = LineString(inner).distance(Point(lid_out, LIDTOP["control"]))
    ok(dl >= 2.0, "saddle", f"corner {dl:.1f} mm from the lid's top edge (min 2)")
    ok(SAD["f_tail"] <= F_BACK, "saddle", f"back edge inside the lid back ({F_BACK - SAD['f_tail']:.1f} mm)")
    for side in ("left", "right"):
        tip = side_plate(side).bounds[1]
        under = max(k.bounds[3] for n, k in keepouts(side) if n.startswith("power"))
        ok(tip >= under, "saddle", f"{side} leg ends at y {tip:.0f}, above the power box's side panel ({under:.0f} with air)")
    # top fixings: on the top flat, clear of the corner bends, the flanges, and each other
    for x, f in top_fixings():
        head = X_TOP - (abs(x) + 2.85)                         # M3 button head Ø5.7
        ok(head >= 2.0, "saddle", f"top fixing ({x:.0f}, f {f:.0f}): screw head {head:.1f} mm inside the corner's first bend (min 2)")
        ok(SAD["f_nose"] + SAD["t"] + SAD["R"] + 6 <= f <= SAD["f_tail"] - SAD["t"] - SAD["R"] - 6, "saddle", f"top fixing f {f:.0f} on the top flat")
    # side standoffs: two per side, all inside the plate
    for side in ("left", "right"):
        so = side_standoffs(side, side_plate(side))
        ok(len(so) == 2, "saddle", f"{side}: 2 standoffs to the control wall ({len(so)})")
        if len(so) == 2:
            ok(math.dist(*so) >= 60, "saddle", f"{side}: standoffs {math.dist(*so):.0f} mm apart (min 60)")
    # band: clear of the power front's features and below them
    for n, x0, x1, fy0, fy1 in wall_features()["front"]:
        if n.startswith("power"):
            ok(fy0 - BND["y1"] >= 10, "band", f"band top {fy0 - BND['y1']:.0f} mm below the {n.split(' ', 1)[1]}")
    # --- laptop
    L = laptop_check()
    ok(L["laptop"] <= 1.0, "saddle", f"laptop (2 kg): ~{L['laptop']:.1f} mm sag (max 1, hand estimate)")
    ok(L["lean"] <= 5.0, "saddle", f"10 kg lean, mid-top: ~{L['lean']:.1f} mm sag (max 5, hand estimate)")
    ok(L["sigma"] <= 0.6 * SIGMA_Y, "saddle", f"10 kg lean: ~{L['sigma']:.0f} MPa (max {0.6 * SIGMA_Y:.0f}: no dent)")
    return out


def refold(p, ents):
    """Rebuild the folded widths from the bend lines as written in the DXF."""
    f = lambda e, c: float(e[c][0])
    bl = [e for e in ents if e["type"] == "LINE" and e["8"][0] == "Bend Center"]
    vx = sorted({round(f(e, "10"), 4) for e in bl if abs(f(e, "10") - f(e, "11")) < 1e-6})
    c = C_SAD if p.name == "saddle" else C_BND
    res = []
    for half in (vx[:BUMP_N], vx[-BUMP_N:]):
        steps = [abs(b - a) for a, b in zip(half, half[1:])]
        res.append((all(abs(s - (c["ba"] + BUMP_A)) < 0.01 for s in steps), f"refold {p.name}: corner bends {BUMP_A:g} mm + allowance apart"))
    flat_half = (vx[-BUMP_N] - vx[BUMP_N - 1]) / 2 - c["ba"] / 2
    want = X_TOP if p.name == "saddle" else X_FRONT
    got = flat_half + c["du"]
    res.append((abs(flat_half - want) < 0.01, f"refold {p.name}: folded inside width {2 * got:.2f} (design {2 * (XS if p.name == 'saddle' else XB):.2f})"))
    return res


def inspector_data():
    """Folded geometry for the 3D inspector (stack frame; z = ZF - f)."""
    r = lambda v: round(v, 2)
    zf = lambda f: r(ZF - f)
    def slot_polys(plate, side):
        out = []
        for _, centre in fans(side):
            if plate.intersects(Point(centre).buffer(40)):
                for seg in _slots(plate, centre):
                    g = LineString(seg).buffer(2.0, 6)
                    out.append([[zf(f), r(y)] for f, y in g.exterior.coords[:-1]])
        return out
    def ring(c): return [[zf(f), r(y)] for f, y in list(c)[:-1]]
    sad_inner = [(X_TOP + u, YT + v) for u, v in C_SAD["pts"]]
    bnd_inner = [(X_FRONT + u, ZBF + v) for u, v in C_BND["pts"]]
    sides = {}
    for s in ("left", "right"):
        sp = side_plate(s)
        g = sp if sp.geom_type == "Polygon" else max(sp.geoms, key=lambda q: q.area)
        sides[s] = dict(ext=ring(g.exterior.coords), holes=[ring(i.coords) for i in g.interiors] + slot_polys(sp, s),
                        standoffs=[[zf(f), r(y)] for f, y in side_standoffs(s)])
    bsides = {}
    for s in ("left", "right"):
        bp = band_side(s)
        bsides[s] = dict(ext=ring(bp.exterior.coords), holes=slot_polys(bp, s),
                         standoffs=[[zf(f), r(y)] for f, y in band_side_standoffs()[s]])
    return dict(
        saddle=dict(t=SAD["t"], yT=r(YT), xTop=r(X_TOP), xs=r(XS), zNose=zf(SAD["f_nose"]), zTail=zf(SAD["f_tail"]),
                    flange=SAD["flange"], lidTop=r(LIDTOP["control"]), washer=WASHER_T, xo=XO,
                    section=[[r(x), r(y)] for x, y in section(sad_inner, SAD["t"])],
                    topHoles=[[r(x), zf(f)] for x, f in top_fixings()], sides=sides,
                    info=f"{SAD['mat']}. {BUMP_N} x {BUMP_DEG:g}° bump-bent corners. On {len(top_fixings())} standoffs over the lid "
                         f"and 2 per side; windows keep {KEEP:g} mm of air round every port."),
        band=dict(t=BND["t"], y0=BND["y0"], y1=BND["y1"], xFront=r(X_FRONT), xb=r(XB), zIn=r(ZBF), zf=ZF, xo=XO,
                  section=[[r(x), r(z)] for x, z in section(bnd_inner, BND["t"])],
                  frontStandoffs=[[r(x), r(y)] for x, y in band_front_standoffs()], sides=bsides,
                  info=f"{BND['mat']}. {BND['gap']:g} mm off the power box's front; slotted over the fan."))


if __name__ == "__main__":
    res = checks()
    bad = [r for r in res if not r[0]]
    for okk, part, txt in res:
        print(f"  {'ok  ' if okk else 'FAIL'} {part:7s} {txt}")
    L = laptop_check()
    print(f"{len(res)} checks, {len(bad)} failed.  corner du {C_SAD['du']:.1f} dv {C_SAD['dv']:.1f}; laptop {L}")
    sys.exit(1 if bad else 0)
