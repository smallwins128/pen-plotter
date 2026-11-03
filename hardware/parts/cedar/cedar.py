"""R09 Cedar: a bench power supply. CAD run 2 (2026-11-03), from lo-fi v7.

An ATX PSU (on its side) sits on four wood strips between two printed end plates with a sloped side profile.
Five DIN rails span the plates, every rail end in the same printed seat:
    top      terminals only (9 x KV121) + a DIN switch for the board's 2-pin socket (Allwin)
    back x2  facing out, free for later
    slope x2 facing out toward the user, for prototypes (2 x KV121 feed each)
A thin printed sleeve follows the side profile over the 63 mm cable bay. It is two prints: the shell, and a flat end
wall at the PSU end. The end wall's window is the PSU outline less a 3 mm lip; two bars across it carry the ATX
breakout board on 15 mm standoffs, facing the bay, so cables leaving anywhere on the PSU's face can pass behind it.
Every rail also screws into a rib on the sleeve (M3 nut channel, any slot), so it is held at both plates and the bay end.

Rail seat (standard, every rail end): a 12 mm deep surface on the plate shaped to the rail (pocket for the web,
shoulders under the flanges) and a clamp with a boss that presses the web; 2 x M3 countersunk into heat-set inserts,
outside the rail, so the rail's slot positions don't matter.

Frame (mm): x along the rails (0 = left plate's inner face, 203 = right plate's inner face), y up (0 = bench),
z toward the user (0 = back edge). Side-profile sketches use (z, y).

Placeholders: KV121 9 x 43 x 52 (Allwin: 8-9 mm thick); HY-Z09 70 x 68 (Allwin) with holes 3.5 in from the corners;
PSU screw holes 6 in from the face corners; DIN switch 18 x 45 x 45.

    python3 hardware/parts/cedar/cedar.py          # checks only (about 1 min)
    python3 hardware/parts/cedar/cedar.py --stl    # also meshes: hardware/out/cedar/*.stl + summary.json
"""
import itertools
import json
import math
import pathlib
import sys

from build123d import Box, Cone, Cylinder, Plane, Pos, Rot, export_stl
from shapely.geometry import Point, Polygon, box as sbox
from shapely.ops import unary_union

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from window_inserts import slab  # noqa: E402

OUT = HERE.parent.parent / "out" / "cedar"

# ------------------------------------------------------------------ bought parts
SPAN = 203.0                                   # rail piece = inner span between plates (measured)
RAIL_W, RAIL_H, RAIL_WEB, RAIL_T = 35.0, 7.5, 27.0, 1.0
PSU = (18.0, 105.0, 11.0, 161.0)               # z0 z1 y0 y1: 87 deep, 150 tall, on its side; x 63..203
PSU_X0 = SPAN - 140.0
STRIP_W, STRIP_T, STRIP_L = 35.0, 6.0, 227.0   # wood, 6 proud of each plate (Allwin)
STRIP_Y = (5.0, 5.0 + STRIP_T + 0.4)           # slot; the strip sits on its bottom and the PSU on the strip
STRIPS = [(20.0, 55.4), (64.0, 99.4), (110.0, 145.4), (158.0, 193.4)]
KV = dict(t=9.0, w=43.0, h=52.0)               # along the rail, across, out from the web
BOARD = dict(w=70.0, h=68.0, t=1.6, hole_in=3.5)
SWITCH = dict(t=18.0, w=45.0, h=45.0)

# ------------------------------------------------------------------ printed parts
PT = 6.0                                       # plate thickness
SEAT_B = 12.0                                  # seat depth along the rail
A, B = (120.0, 200.0), (205.0, 25.0)           # slope line, top-front to bottom-front (64 deg)
TOP_Y, FOOT_Z, CORNER_R = 200.0, 216.0, 22.0
M3_CLEAR, CSK_D, INSERT_BORE, INSERT_DEPTH = 3.4, 6.4, 4.2, 4.5
NUT_W, NUT_H, SKIN = 5.9, 2.7, 1.2             # M3 nut channel in the sleeve ribs
SLEEVE_T, SLEEVE_X = 1.6, 63.0
SLEEVE_BACK, SLEEVE_TOP, SLEEVE_BOT, SLEEVE_IN = 17.0, 163.6, 11.0, 13.5
END_T, END_LIP, END_CLEAR, LEDGE = 2.5, 3.0, 0.3, 1.5
STANDOFF = dict(d=7.0, l=15.0)
BED = 256.0
PLA = 1.24

L = math.dist(A, B)
U = ((B[0] - A[0]) / L, (B[1] - A[1]) / L)
N = (-U[1], U[0]) if -U[1] > 0 else (U[1], -U[0])           # outward (front, up)
RAILS = {   # name: (centre on the flange plane (z, y), across-rail dir u, outward n) -- all in (z, y)
    "top": ((61.5, 180.0), (1.0, 0.0), (0.0, 1.0)),
    "back1": ((4.0, 55.0), (0.0, 1.0), (-1.0, 0.0)),
    "back2": ((4.0, 125.0), (0.0, 1.0), (-1.0, 0.0)),
    "slope1": ((A[0] + 0.30 * (B[0] - A[0]), A[1] + 0.30 * (B[1] - A[1])), U, N),
    "slope2": ((A[0] + 0.75 * (B[0] - A[0]), A[1] + 0.75 * (B[1] - A[1])), U, N),
}
# rail-local sections: a across the rail, b along n (0 = flange plane, web underside at -7.5)
HAT = [(-17.5, 0), (-17.5, -1), (-13.5, -1), (-13.5, -7.5), (13.5, -7.5), (13.5, -1), (17.5, -1), (17.5, 0),
       (12.5, 0), (12.5, -6.5), (-12.5, -6.5), (-12.5, 0)]
HAT_SOLID = None   # built in hat_poly()
BASE = [(-25.5, -1), (-13.5, -1), (-13.5, -7.5), (13.5, -7.5), (13.5, -1), (25.5, -1), (25.5, -11.5), (-25.5, -11.5)]
CLAMP = [(-25.5, 0), (-12.2, 0), (-12.2, -6.3), (12.2, -6.3), (12.2, 0), (25.5, 0), (25.5, 4), (-25.5, 4)]
SCREW_A = 21.5


def hat_poly():
    """TS35 section as a closed outline (top-hat, 1 mm sheet)."""
    outer = Polygon([(-17.5, 0), (17.5, 0), (17.5, -1), (13.5, -1), (13.5, -7.5), (-13.5, -7.5), (-13.5, -1), (-17.5, -1)])
    inner = Polygon([(-12.5, 0.01), (12.5, 0.01), (12.5, -6.5), (-12.5, -6.5)])
    return outer.difference(inner)


# ------------------------------------------------------------------ placement helpers
def zy(c, u, n, a, b):
    return (c[0] + a * u[0] + b * n[0], c[1] + a * u[1] + b * n[1])


def rail_plane(name, x_end):
    """Plane whose local (x, y, z) = (a, b, -x) for a rail, with origin at x_end (extrude 0..len goes toward -x)."""
    (cz, cy), u, n = RAILS[name]
    return Plane(origin=(x_end, cy, cz), x_dir=(0, u[1], u[0]), z_dir=(-1, 0, 0))


def along(name, poly, x0, x1):
    """Extrude a rail-local (a, b) shapely polygon along the rail from x0 to x1."""
    return rail_plane(name, x1).location * slab(poly, 0, x1 - x0)


def bx(x0, x1, y0, y1, z0, z1):
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


def local_cyl(name, a, b0, b1, x, r):
    """Cylinder along n (rail-local b) at (a, x)."""
    (cz, cy), u, n = RAILS[name]
    z0, y0 = zy((cz, cy), u, n, a, b0)
    h = b1 - b0
    c = Cylinder(r, h)                                     # along +Z, centred
    pl = Plane(origin=(x, y0 + n[1] * h / 2, z0 + n[0] * h / 2), x_dir=(1, 0, 0), z_dir=(0, n[1], n[0]))
    return pl.location * c


def local_cone(name, a, b0, b1, x, r0, r1):
    (cz, cy), u, n = RAILS[name]
    z0, y0 = zy((cz, cy), u, n, a, b0)
    h = b1 - b0
    pl = Plane(origin=(x, y0 + n[1] * h / 2, z0 + n[0] * h / 2), x_dir=(1, 0, 0), z_dir=(0, n[1], n[0]))
    return pl.location * Cone(r0, r1, h)


def plate_slab(outline, x0):
    """Extrude a (z, y) outline across x from x0 to x0 + PT. Local u = -z, v = y, w = x."""
    flip = Polygon([(-z, y) for z, y in outline.exterior.coords], [[(-z, y) for z, y in r.coords] for r in outline.interiors])
    pl = Plane(origin=(x0, 0, 0), x_dir=(0, 0, -1), z_dir=(1, 0, 0))
    return pl.location * slab(flip, 0, PT)


def hexagon(c, r):
    return Polygon([(c[0] + r * math.cos(math.radians(60 * k + 30)), c[1] + r * math.sin(math.radians(60 * k + 30))) for k in range(6)])


def hex_fill(zone, keep_out, r=8.0, web=2.6):
    dx, dy = r * math.sqrt(3) + web, 1.5 * r + web * 0.87
    minx, miny, maxx, maxy = zone.bounds
    out, row, y = [], 0, miny
    while y < maxy:
        x = minx + (dx / 2 if row % 2 else 0)
        while x < maxx:
            h = hexagon((x, y), r)
            if zone.contains(h) and not keep_out.intersects(h):
                out.append(h)
            x += dx
        y += dy
        row += 1
    return out


# ------------------------------------------------------------------ outlines (z, y)
def slope_z(y, inset=0.0):
    a = (A[0] - inset * N[0], A[1] - inset * N[1])
    b = (B[0] - inset * N[0], B[1] - inset * N[1])
    t = (y - a[1]) / (b[1] - a[1])
    return a[0] + t * (b[0] - a[0])


def plate_outline():
    """Side profile: back, flat top, R22 into the slope, foot. Other convex corners R6."""
    core = Polygon([(0, 0), (0, TOP_Y), (A[0], TOP_Y), B, (212, 22), (FOOT_Z, 14), (FOOT_Z, 0)])
    p = core.buffer(-6, join_style=1).buffer(6, join_style=1)
    cy = TOP_Y - CORNER_R
    c = (slope_z(cy, CORNER_R), cy)                                       # fillet centre, R from both edges
    t1, t2 = (c[0], TOP_Y), (c[0] + CORNER_R * N[0], c[1] + CORNER_R * N[1])
    cut = Polygon([t1, (A[0] + 1, TOP_Y + 1), t2]).buffer(0.01).difference(Point(c).buffer(CORNER_R, 64))
    return p.difference(cut)


def sleeve_outline():
    return Polygon([(SLEEVE_BACK, SLEEVE_BOT), (SLEEVE_BACK, SLEEVE_TOP), (slope_z(SLEEVE_TOP, SLEEVE_IN), SLEEVE_TOP),
                    (slope_z(SLEEVE_BOT, SLEEVE_IN), SLEEVE_BOT)]).buffer(-6, join_style=1).buffer(6, join_style=1)


def seat_zy(name, pts):
    c, u, n = RAILS[name]
    return Polygon([zy(c, u, n, a, b) for a, b in pts])


def psu_window():
    z0, z1, y0, y1 = PSU
    lip, pad = 5.0, 13.0
    win = sbox(z0 + lip, y0 + lip, z1 - lip, y1 - lip)
    for cz, cy in itertools.product((z0, z1 - pad), (y0, y1 - pad)):
        win = win.difference(sbox(cz, cy, cz + pad, cy + pad))
    return win


def psu_holes():
    z0, z1, y0, y1 = PSU
    return [(z, y) for z in (z0 + 6, z1 - 6) for y in (y0 + 6, y1 - 6)]


def slots():
    return [sbox(z0, STRIP_Y[0], z1, STRIP_Y[1]) for z0, z1 in STRIPS]


# ------------------------------------------------------------------ printed: plates
def plate(side):
    out = plate_outline()
    keep = unary_union([seat_zy(k, BASE).buffer(3) for k in RAILS] + [s.buffer(4) for s in slots()])
    for s in slots():
        out = out.difference(s)
    if side < 0:
        zone = sleeve_outline().buffer(-5)
    else:
        z0, z1, y0, y1 = PSU
        out = out.difference(psu_window())
        for h in psu_holes():
            out = out.difference(Point(h).buffer(1.8, 24))
        zone = out.buffer(-7).difference(sbox(z0 - 8, 0, z1 + 8, y1 + 8))
    hexes = hex_fill(zone, keep)
    for h in hexes:
        out = out.difference(h)
    p = plate_slab(out, -PT if side < 0 else SPAN)
    x0, x1 = (0.0, SEAT_B) if side < 0 else (SPAN - SEAT_B, SPAN)
    for k in RAILS:
        p = p + along(k, Polygon(BASE), x0, x1)
        for a in (-SCREW_A, SCREW_A):
            p = p - local_cyl(k, a, -1 - INSERT_DEPTH, -0.9, (x0 + x1) / 2, INSERT_BORE / 2)
    return p, len(hexes)


def clamp_part(name, side):
    x0, x1 = (0.0, SEAT_B) if side < 0 else (SPAN - SEAT_B, SPAN)
    c = along(name, Polygon(CLAMP), x0, x1)
    h = (CSK_D - M3_CLEAR) / 2
    for a in (-SCREW_A, SCREW_A):
        c = c - local_cyl(name, a, -0.1, 4.1, (x0 + x1) / 2, M3_CLEAR / 2)
        c = c - local_cone(name, a, 4.0 - h, 4.01, (x0 + x1) / 2, M3_CLEAR / 2, CSK_D / 2 + 0.01)
    return c


# ------------------------------------------------------------------ printed: sleeve
def rib_depth(name):
    (cz, cy), u, n = RAILS[name]
    if name == "top":
        return cy - SLEEVE_TOP
    if name.startswith("back"):
        return SLEEVE_BACK - cz
    return SLEEVE_IN


def sleeve_shell():
    outer = sleeve_outline()
    inner = outer.buffer(-SLEEVE_T, join_style=1)
    def flip(p):
        return Polygon([(-z, y) for z, y in p.exterior.coords], [[(-z, y) for z, y in r.coords] for r in p.interiors])
    ring = outer.difference(inner)
    lring = inner.difference(inner.buffer(-LEDGE, join_style=1))
    shell = slab(flip(ring), 0, SLEEVE_X)
    ledge = slab(flip(lring), SLEEVE_X - END_T - LEDGE, SLEEVE_X - END_T)
    pl = Plane(origin=(0, 0, 0), x_dir=(0, 0, -1), z_dir=(1, 0, 0))    # local (u, v, w) = (-z, y, x)
    s = pl.location * (shell + ledge)
    # ribs under every rail, after the seat, with an M3 nut channel open at the PSU end
    for k in RAILS:
        d = rib_depth(k)
        rib = Polygon([(-6, -7.5), (6, -7.5), (6, -d - SLEEVE_T), (-6, -d - SLEEVE_T)])
        s = s + along(k, rib, SEAT_B, SLEEVE_X)
        ch = Polygon([(-NUT_W / 2, -7.5 - SKIN - NUT_H), (NUT_W / 2, -7.5 - SKIN - NUT_H), (NUT_W / 2, -7.5 - SKIN), (-NUT_W / 2, -7.5 - SKIN)])
        sl = Polygon([(-M3_CLEAR / 2, -7.5 - SKIN - 0.1), (M3_CLEAR / 2, -7.5 - SKIN - 0.1), (M3_CLEAR / 2, -7.4), (-M3_CLEAR / 2, -7.4)])
        s = s - along(k, ch, SEAT_B + 6, SLEEVE_X + 0.1) - along(k, sl, SEAT_B + 6, SLEEVE_X + 0.1)
    # wire slot in the top, behind the top rib: board wires up to the terminals
    s = s - bx(20, 55, SLEEVE_TOP - 3, SLEEVE_TOP + 1, 26, 48)
    # honeycomb on the back face (between the back ribs) and on the slope face (between the slope ribs)
    n_hex = 0
    for face in ("back", "slope"):
        for hx in face_hexes(face):
            s = s - hx
            n_hex += 1
    return s, n_hex


def face_hexes(face, r=6.0, web=2.4):
    """Hex prisms through one flat face of the sleeve, kept clear of its ribs, edges and the end ledge."""
    out = []
    if face == "back":
        y0, y1 = SLEEVE_BOT + 10, SLEEVE_TOP - 10
        ribs = [RAILS[k][0][1] for k in ("back1", "back2")]
        pts = []
        dx, dy = r * math.sqrt(3) + web, 1.5 * r + web * 0.87
        row, y = 0, y0 + r
        while y < y1 - r:
            x = 6 + r + (dx / 2 if row % 2 else 0)
            while x < SLEEVE_X - END_T - LEDGE - r - 3:
                if all(abs(y - yr) > 6 + r + 2 for yr in ribs):
                    pts.append((x, y))
                x += dx
            y += dy
            row += 1
        for x, y in pts:
            pl = Plane(origin=(x, y, SLEEVE_BACK), x_dir=(1, 0, 0), z_dir=(0, 0, 1))
            out.append(pl.location * slab(hexagon((0, 0), r), -3, 3))
    else:
        top = (slope_z(SLEEVE_TOP, SLEEVE_IN), SLEEVE_TOP)
        bot = (slope_z(SLEEVE_BOT, SLEEVE_IN), SLEEVE_BOT)
        length = math.dist(top, bot)
        # rail centres projected on the face, in s from the top point
        rib_s = []
        for k in ("slope1", "slope2"):
            (cz, cy), u, n = RAILS[k]
            rib_s.append((cz - top[0]) * U[0] + (cy - top[1]) * U[1])
        dx, dy = r * math.sqrt(3) + web, 1.5 * r + web * 0.87
        row, sv = 0, 12 + r
        while sv < length - 12 - r:
            x = 6 + r + (dx / 2 if row % 2 else 0)
            while x < SLEEVE_X - END_T - LEDGE - r - 3:
                if all(abs(sv - rs) > 6 + r + 2 for rs in rib_s):
                    z, y = top[0] + sv * U[0], top[1] + sv * U[1]
                    pl = Plane(origin=(x, y, z), x_dir=(1, 0, 0), z_dir=(0, N[1], N[0]))
                    out.append(pl.location * slab(hexagon((0, 0), r), -3, 3))
                x += dx
            sv += dy
            row += 1
    return out


def end_wall():
    """Flat print at the PSU end of the sleeve: closes the bay, window over the PSU face, board on 2 bars."""
    outline = sleeve_outline().buffer(-SLEEVE_T - END_CLEAR, join_style=1)
    z0, z1, y0, y1 = PSU
    win = sbox(z0 + END_LIP, y0 + END_LIP, z1 - END_LIP, y1 - END_LIP)
    bz0, bz1, by0, by1 = board_rect()
    holes = board_holes()
    bars = unary_union([sbox(z0 + END_LIP - 0.5, y - 4, z1 - END_LIP + 0.5, y + 4) for y in sorted({h[1] for h in holes})])
    face = outline.difference(win).union(bars)
    pl = Plane(origin=(SLEEVE_X, 0, 0), x_dir=(0, 0, 1), z_dir=(-1, 0, 0))   # local (u, v, w) = (z, y, -x)
    w = pl.location * slab(face, 0, END_T)
    for hz, hy in holes:
        so = Pos(SLEEVE_X - END_T - STANDOFF["l"] / 2 + 0.01, hy, hz) * (Rot(0, 90, 0) * Cylinder(STANDOFF["d"] / 2, STANDOFF["l"]))
        w = w + so
        w = w - Pos(SLEEVE_X - END_T - STANDOFF["l"] + INSERT_DEPTH / 2 - 0.05, hy, hz) * (Rot(0, 90, 0) * Cylinder(INSERT_BORE / 2, INSERT_DEPTH + 0.1))
    return w, win.area - bars.intersection(win).area


def board_rect():
    zc = (PSU[0] + PSU[1]) / 2
    return (zc - BOARD["w"] / 2, zc + BOARD["w"] / 2, 88.0, 88.0 + BOARD["h"])


def board_holes():
    z0, z1, y0, y1 = board_rect()
    i = BOARD["hole_in"]
    return [(z, y) for z in (z0 + i, z1 - i) for y in (y0 + i, y1 - i)]


# ------------------------------------------------------------------ bought stand-ins
def rail(name):
    return along(name, hat_poly(), 0.0, SPAN)


def kv121(name, x0):
    foot = Polygon([(-12.0, -6.4), (12.0, -6.4), (12.0, 0.05), (-12.0, 0.05)])
    body = Polygon([(-KV["w"] / 2, 0.05), (KV["w"] / 2, 0.05), (KV["w"] / 2, KV["h"] - 7.5), (-KV["w"] / 2, KV["h"] - 7.5)])
    return along(name, foot, x0 + 0.15, x0 + KV["t"] - 0.15) + along(name, body, x0 + 0.15, x0 + KV["t"] - 0.15)


def din_switch(name, x0):
    foot = Polygon([(-12.0, -6.4), (12.0, -6.4), (12.0, 0.05), (-12.0, 0.05)])
    body = Polygon([(-SWITCH["w"] / 2, 0.05), (SWITCH["w"] / 2, 0.05), (SWITCH["w"] / 2, SWITCH["h"]), (-SWITCH["w"] / 2, SWITCH["h"])])
    return along(name, foot, x0 + 0.2, x0 + SWITCH["t"] - 0.2) + along(name, body, x0 + 0.2, x0 + SWITCH["t"] - 0.2)


def psu():
    z0, z1, y0, y1 = PSU
    return bx(PSU_X0, SPAN, y0, y1, z0, z1)


def board():
    z0, z1, y0, y1 = board_rect()
    xb = SLEEVE_X - END_T - STANDOFF["l"]                    # board's back face on the standoff tips
    b = bx(xb - BOARD["t"], xb, y0, y1, z0, z1)
    b += bx(xb - BOARD["t"] - 13, xb - BOARD["t"], y0 + 4, y0 + 16, z0 + 8, z0 + 60)       # 24-pin socket, plug from the bay
    b += bx(xb - BOARD["t"] - 12, xb - BOARD["t"], y1 - 12, y1 - 2, z0 + 6, z0 + 64)       # screw terminal
    return b


def strip(z0, z1):
    return bx(-PT - 6.0, SPAN + PT + 6.0, STRIP_Y[0], STRIP_Y[0] + STRIP_T, z0 + 0.3, z1 - 0.3)


def proto_ghost(name):
    return along(name, Polygon([(-30, 0.5), (30, 0.5), (30, 28), (-30, 28)]), 40.0, 150.0)


TERMINALS = ["12V", "GND", "5V", "GND", "3V3", "GND", "12V", "5V", "GND"]
TOP_X0 = SEAT_B + 2.0
SWITCH_X0 = TOP_X0 + len(TERMINALS) * KV["t"] + 6.0
FEEDS_X0 = SEAT_B + 2.0


def assembly():
    printed, bought = {}, {}
    pl, nl = plate(-1)
    pr, nr = plate(1)
    printed["plate_left"], printed["plate_right"] = pl, pr
    for k in RAILS:
        printed[f"clamp_{k}_left"] = clamp_part(k, -1)
        printed[f"clamp_{k}_right"] = clamp_part(k, 1)
    shell, nsh = sleeve_shell()
    printed["sleeve_shell"] = shell
    ew, open_area = end_wall()
    printed["sleeve_end_wall"] = ew
    bought["psu"] = psu()
    for k in RAILS:
        bought[f"rail_{k}"] = rail(k)
    for i, (z0, z1) in enumerate(STRIPS):
        bought[f"strip_{i + 1}"] = strip(z0, z1)
    for i, lab in enumerate(TERMINALS):
        bought[f"kv_top_{i}_{lab}"] = kv121("top", TOP_X0 + i * KV["t"])
    bought["din_switch"] = din_switch("top", SWITCH_X0)
    for k in ("slope1", "slope2"):
        bought[f"kv_{k}_0_pos"] = kv121(k, FEEDS_X0)
        bought[f"kv_{k}_1_neg"] = kv121(k, FEEDS_X0 + KV["t"])
    bought["board"] = board()
    ghosts = {f"ghost_{k}": proto_ghost(k) for k in ("slope1", "slope2")}
    info = dict(hex_left=nl, hex_right=nr, hex_sleeve=nsh, open_area=open_area)
    return printed, bought, ghosts, info


# ------------------------------------------------------------------ checks
def checks(printed, bought, info):
    res = []

    def add(name, ok, detail):
        res.append(dict(name=name, ok=bool(ok), detail=detail))

    allp = {**printed, **bought}
    hits = []
    for (a, sa), (b, sb) in itertools.combinations(allp.items(), 2):
        if (a.startswith("kv_") or a == "din_switch") and (b.startswith("kv_") or b == "din_switch"):
            continue
        ba, bb = sa.bounding_box(), sb.bounding_box()
        if (ba.min.X > bb.max.X or bb.min.X > ba.max.X or ba.min.Y > bb.max.Y or bb.min.Y > ba.max.Y
                or ba.min.Z > bb.max.Z or bb.min.Z > ba.max.Z):
            continue
        v = (sa & sb).volume
        if v > 0.05:
            hits.append(f"{a} x {b}: {v:.1f} mm3")
    add("No two parts overlap", not hits, "; ".join(hits) or "every pair clear or face to face")

    for n in ("plate_left", "plate_right", "sleeve_shell", "sleeve_end_wall", "clamp_top_left"):
        bb = printed[n].bounding_box()
        d = sorted([bb.size.X, bb.size.Y, bb.size.Z])
        add(f"{n} fits the A1 bed", d[1] <= BED and d[2] <= BED, f"{bb.size.X:.0f} x {bb.size.Y:.0f} x {bb.size.Z:.0f} mm")

    add("PSU sits on the wood strips", abs(PSU[2] - (STRIP_Y[0] + STRIP_T)) < 0.01,
        f"PSU bottom {PSU[2]:.1f}, strip top {STRIP_Y[0] + STRIP_T:.1f}; strips 2 and 1 run its full length")
    webs = [STRIPS[i + 1][0] - STRIPS[i][1] for i in range(len(STRIPS) - 1)]
    add("Plate between strip slots", min(webs) >= 8, f"{min(webs):.1f} mm minimum")

    # wire entry through the end wall
    add("Cables can leave the PSU anywhere on its face", info["open_area"] >= 0.8 * (PSU[1] - PSU[0] - 6) * (PSU[3] - PSU[2] - 6),
        f"window {(PSU[1] - PSU[0] - 2 * END_LIP):.0f} x {(PSU[3] - PSU[2] - 2 * END_LIP):.0f}, "
        f"{info['open_area'] / 100:.0f} cm2 open after the 2 board bars")
    add("Room for a cable bundle behind the board", STANDOFF["l"] >= 12, f"{STANDOFF['l']:.0f} mm between the end wall and the board")
    bz0, bz1, by0, by1 = board_rect()
    below = by0 - (PSU[2] + END_LIP)
    add("Open band under the board for the main bundle", below >= 50, f"{below:.0f} mm tall, full window width")

    for k in RAILS:
        d = rib_depth(k) - 7.5
        add(f"Rib under the {k} rail holds a nut channel", d >= SKIN + NUT_H + 0.8, f"{d:.1f} mm rib (needs {SKIN + NUT_H + 0.8:.1f})")
    end_top = SWITCH_X0 + SWITCH["t"]
    add("Top rail: 9 terminals + switch fit between the seats", end_top <= SPAN - SEAT_B,
        f"ends at {end_top:.0f}; {SPAN - SEAT_B - end_top:.0f} mm free")
    add("Clamp screws land in the seat shoulders", SCREW_A - CSK_D / 2 >= 17.5 and SCREW_A + INSERT_BORE / 2 <= 25.5 - 1.2,
        f"screws at ±{SCREW_A}: clear of the flanges (17.5), 1.8 mm wall outside each insert")
    add("End wall drops into the shell", END_CLEAR >= 0.2, f"{END_CLEAR} mm clearance all round, stopped by a {LEDGE} mm ledge")
    return res


def main():
    stl = "--stl" in sys.argv
    printed, bought, ghosts, info = assembly()
    res = checks(printed, bought, info)
    for r in res:
        print(("PASS " if r["ok"] else "FAIL ") + r["name"] + ": " + r["detail"])
    failed = [r["name"] for r in res if not r["ok"]]
    parts = []
    for n, s in printed.items():
        bb = s.bounding_box()
        parts.append(dict(name=n, kind="printed", cm3=round(s.volume / 1000, 1), g_pla=round(s.volume / 1000 * PLA),
                          size=[round(bb.size.X), round(bb.size.Y), round(bb.size.Z)]))
    for n in bought:
        parts.append(dict(name=n, kind="bought"))
    for n in ghosts:
        parts.append(dict(name=n, kind="ghost"))
    total = sum(p.get("g_pla", 0) for p in parts)
    print(f"printed: {total} g PLA (solid estimate); hexes L {info['hex_left']} R {info['hex_right']} sleeve {info['hex_sleeve']}; {len(failed)} failing")
    if stl:
        OUT.mkdir(parents=True, exist_ok=True)
        for f in OUT.glob("*.stl"):
            f.unlink()
        for n, s in {**printed, **bought, **ghosts}.items():
            export_stl(s, str(OUT / f"{n}.stl"), tolerance=0.05, angular_tolerance=0.3)
        rails = {k: dict(c=RAILS[k][0], u=RAILS[k][1], n=RAILS[k][2]) for k in RAILS}
        summary = dict(size=[round(SPAN + 2 * PT), TOP_Y, FOOT_Z], strip_len=STRIP_L, parts=parts, checks=res, failed=failed,
                       total_g_pla=total, rails=rails, span=SPAN, pt=PT, sleeve_x=SLEEVE_X, info=info,
                       terminals=TERMINALS, kv=KV)
        (OUT / "summary.json").write_text(json.dumps(summary, indent=1))
        print("wrote", OUT)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
