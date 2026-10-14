#!/usr/bin/env python3
"""Cut files for the two stacked 1 mm stainless enclosures, with checks.

    python3 hardware/sheet/enclosure.py            # build, check, write hardware/out/sheet/
    python3 hardware/sheet/enclosure.py --report   # checks only

One set of dimensions drives every part: the body and lid of each box (one
folded blank each, 1 mm 304 stainless) and the two base plates (flat, 2 mm).
Each flat pattern is written as DXF R12 in the layer convention of the
earlier SMPS drawings:

    Visible         the cut: outline, holes, cutouts, vents
    Visible Narrow  bend-zone edges, either side of each bend line (not cut)
    Bend Center     bend lines, CENTER2 linetype (not cut)
    Bend Notes      "Up 90° R1" beside every bend line
    Leaders         what each hole is for
    Title           part name, material, quantity, view, bend data

Every flat is drawn from the INSIDE face: every bend goes UP 90°.

The flat lengths assume inner radius R = t and K = 0.44 (bend allowance 2.26,
bend deduction 1.74 per 90° bend). The shop's number wins: give them the
folded drawing too, and if their bend deduction differs, set BD here, re-run,
and re-send. Hole positions are referenced from bend lines, so a different
deduction moves them by half the difference.

Before writing anything it runs every check below and refuses to write if
one fails. The DXFs are then parsed back from disk, independently, and
rendered to SVG, so the preview shows what the shop will actually load.
"""
import argparse
import json
import math
import pathlib
import sys

from shapely.geometry import LineString, Point, Polygon, box as sbox
from shapely.ops import unary_union


HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent / "out" / "sheet"

# ============================================================================
# DIMENSIONS (mm)
# ============================================================================
T = 1.0                    # sheet, 304 stainless
R = 1.0                    # inner bend radius
K = 0.44
BA = math.pi / 2 * (R + K * T)          # bend allowance, 90 deg
S = R + T                               # setback: outer mold line to the start of the bend
BD = 2 * S - BA                         # bend deduction, 90 deg
W, D = 450.0, 295.0                     # inside width, inside depth (front wall to back lips)
H = {"control": 110.0, "power": 170.0}  # inside height (floor to underside of the top lips)
LIP = 15.0                              # lips, measured inside
LIPO = LIP + T                          # lip outer leg, from the outer face of the wall it folds off
CLR = 1.0                               # lid return lips to the body, per side (sliding fit; bends are ±0.5)
FOLD_GAP = 2.5                          # gap between folded flanges that must not touch (rule: ≥ 2, bends are ±0.5)
TAB_GAP = 0.5                           # side walls' front edges + corner tabs stop shy of the front wall; rivets close it
BAND = 20.0                             # no-mount band under the lid's lips
RIV_IN = 8.0                            # rivnut centre from the inside face of its wall
WO = W + 2 * T                          # body outside width
ZF, ZB = D / 2 + T, -D / 2 - T          # body front outer face, back-lip outer face (z = 0 mid-depth)

HOLE = {   # name: (diameter, leader text)
    "rivnut_m3": (5.0, "M3 Rivnut (5mm)"),
    "acc": (5.0, "Ø5 accessory (M3 rivnut or plug)"),
    "rivnut_m4": (6.0, "M4 Rivnut (6mm)"),
    "m3": (3.4, "Ø3.4 M3 screw"),
    "rivet": (3.2, "Ø3.2 solid rivet"),
    "m4": (4.5, "Ø4.5 M4"),
    "fan": (4.4, "Ø4.4 fan screw"),
    "lidclr": (10.0, "Ø10 clears rivnut flange"),
    "peg": (8.0, "Ø8 locating hole"),
    "pegclr": (10.0, "Ø10 peg clearance"),
    "sma": (6.5, "Ø6.5 SMA antenna"),
    "stud": (6.5, "Ø6.5 M6 earth stud"),
    "grid": (6.0, "Ø6 grid (M4 rivnut)"),
}

# Original printed panels (hardware/parts/link_panel.py): cutout, plate, screw offsets.
# Mounted on their sides, so the 152 runs along the wall.
PANEL = {
    "receiving": dict(cut=(152.0, 50.0), plate=(172.0, 70.0), screw=(80.0, 29.0)),
    "psu": dict(cut=(152.0, 120.4), plate=(172.0, 140.4), screw=(80.0, 64.2)),
    # new prints, on M3 rivnuts: rivnut centres 7 out from the cutout (room to set), plate 5 past them
    "iec": dict(cut=(130.0, 65.0), plate=(154.0, 89.0), screw=(72.0, 39.5), rivnut=True),
    "usb_ant": dict(cut=(80.0, 30.0), plate=(104.0, 54.0), screw=(47.0, 22.0), rivnut=True),  # USB-C + antenna + pendant GX16
}


# Stacked boxes line up: both fans in one column on the left walls, both jack panels in one column on the right
FAN_Z = D / 2 - 68                      # fan centre along the left walls (z), both boxes; clear of the front standoffs
JACK_Z = D / 2 - 160                    # receiving panel (control) and PSU panel (power) centre along the right walls
FAN = {"control": (FAN_Z, T + H["control"] / 2 - 8), "power": (FAN_Z, T + 55)}   # left wall: (z, y) centre, 80 x 80 x 25
FAN_DEPTH = 25.0


# Stacking: printed feet under the control box (flange = spacer, peg = locator) drop into the power lid.
FEET_XZ = [(sx * (W / 2 - 40), sz * (D / 2 - 40)) for sx in (-1, 1) for sz in (-1, 1)]     # both boxes' foot holes
STACK = dict(flange_d=24.0, flange_h=6.0, peg_d=7.6, peg_len=6.0,
             lid_fix_h=1.2 + 2.4,          # penny washer + M3 pan head, proud of the power lid
             floor_head_h=2.8,             # M4 standoff screw heads under the control floor
             foot_screw_head_h=2.8)        # M4 screw holding each foot, head inside on the control floor
# power-lid holes under the feet: front-left locates, front-right slot (along x) stops rotation, back two only clear
PEG_HOLES = {(-(W / 2 - 40), D / 2 - 40): "round", (W / 2 - 40, D / 2 - 40): "slot",
             (-(W / 2 - 40), -(D / 2 - 40)): "clear", (W / 2 - 40, -(D / 2 - 40)): "clear"}
PEG_SLOT = (11.0, 8.0)                     # length along x, width
# accessory holes: plain Ø5, take an M3 rivnut (set later, from outside) or a printed plug
ACC_LID = [(sx * (W / 2 - 40), sz * (D / 2 - 40)) for sx in (-1, 1) for sz in (-1, 1)]   # control lid top corners (over the power lid's peg holes)
ACC_FRONT = [(-(W / 2 - 40), 30.0), (0.0, 30.0), (W / 2 - 40, 30.0)]   # power front (x, height)
# windows: three identical rectangles (R5), one on the control front right of the GX plates, two on the power front at
# its edges. A printed bezel is bolted round each into 4 M3 rivnuts (one per side), panels snap onto the bezel with
# magnets. Clearance: the panel (bezel + rim) stays 15 mm from the box edge and from the GX plates; rivnut centres 7 mm
# out from the opening edge (room for the rivnut to set, and its flange)
VENT_ROWS = (145.0, 42.0)                 # power front vent rows (height of slot centre); the middle top row is gone
WIN = dict(w=143.0, h=50.0, r=5.0, band=13.0, rim=1.5, mar=3.0, scr=7.0, edge=15.0,
           cy={"control": 46.5, "power": 93.5})
WIN_X = (53.5, 196.5)                      # opening u range: right window (and the control window); left = mirror
# logo mount, power front centre: keyhole slot for a printed spine (2 dovetail lugs pass the entries from inside,
# then drop 15); a logo plate slides down onto the lugs from above
LOGO = dict(cx=0.0, slot_w=4.2, slot=(62.0, 121.5), entry=13.0, entries=(85.0, 115.0), drop=15.0, plate=(48.0, 79.0), cy=93.5)


# control front: GX16 sockets live in printed plates; the steel only has one plain opening per group (6 mm play round
# each Ø22 rear nut, so sockets can move inside a group with a reprint) and M3 rivnuts the plates screw onto from the front
GX_NUT_R = 11.0
GX_PLAY = 6.0
GX_GROUPS = {"steppers": [(-173.0, 62.0), (-139.0, 62.0), (-156.0, 33.0)],     # X1, X2 top; Y below
             "servo": [(-82.0, 47.0)],                                         # PEN
             "endstops": [(-32.0, 47.0), (2.0, 47.0)]}                         # XLIM, YLIM
GX_RIVNUT_OUT = 6.0                        # rivnut centre outside the opening edge


def gx_openings():
    """{group: (opening rect (x0, y0, x1, y1), [rivnut points])} on the control front, (u, v) = (x, height)."""
    out = {}
    for g, pts in GX_GROUPS.items():
        e = GX_NUT_R + GX_PLAY
        x0, x1 = min(p[0] for p in pts) - e, max(p[0] for p in pts) + e
        y0, y1 = min(p[1] for p in pts) - e, max(p[1] for p in pts) + e
        xm, ym, o = (x0 + x1) / 2, (y0 + y1) / 2, GX_RIVNUT_OUT
        riv = [(x0 - o, ym), (x1 + o, ym), (xm, y1 + o)] if g == "steppers" else [(xm, y1 + o), (xm, y0 - o)]
        out[g] = ((x0, y0, x1, y1), riv)
    return out


def gx_plate(rect, g):
    """The inspector's plate (chamfered, after Allwin's sketch): opening + 10 (5 sideways for the two small groups)."""
    mx = 10.0 if g == "steppers" else 5.0
    b = sbox(rect[0] - mx, rect[1] - 10, rect[2] + mx, rect[3] + 10)
    c = 7.0 if g == "steppers" else 5.0
    return b.buffer(-c, join_style=2).buffer(c, join_style=3)


def _rect_window(x0, x1, cy):
    """Rounded rectangular opening and its 4 rivnut points (one per side, WIN["scr"] out from the edge)."""
    w = WIN
    y0, y1 = cy - w["h"] / 2, cy + w["h"] / 2
    poly = sbox(x0, y0, x1, y1).buffer(-w["r"], join_style=1, quad_segs=8).buffer(w["r"], join_style=1, quad_segs=8)
    xm, s_ = (x0 + x1) / 2, w["scr"]
    return poly, [(xm, y0 - s_), (x1 + s_, cy), (xm, y1 + s_), (x0 - s_, cy)]


def ctrl_window():
    return _rect_window(WIN_X[0], WIN_X[1], WIN["cy"]["control"])


def window_panes():
    """The two window openings on the power front, (u, v) = (x, height). Returns [(rounded polygon, rivnut points)]."""
    cy = WIN["cy"]["power"]
    return [_rect_window(-WIN_X[1], -WIN_X[0], cy), _rect_window(WIN_X[0], WIN_X[1], cy)]


def logo_slot():
    """Keyhole slot for the logo spine, (u, v) on the power front."""
    L = LOGO
    parts = [sbox(L["cx"] - L["slot_w"] / 2, L["slot"][0], L["cx"] + L["slot_w"] / 2, L["slot"][1])]
    parts += [sbox(L["cx"] - L["entry"] / 2, v - L["entry"] / 2, L["cx"] + L["entry"] / 2, v + L["entry"] / 2) for v in L["entries"]]
    u = unary_union(parts)
    return u.buffer(-1.5, join_style=1, quad_segs=8).buffer(1.5, join_style=1, quad_segs=8)


def panel_y(kind, ht):
    """Panel centre height above the base underside: as high as the lid band allows."""
    top = T + H[kind]
    return min(T + H[kind] / 2, top - BAND - 2 - ht / 2)


# ============================================================================
# PRIMITIVES (flat coordinates)
# ============================================================================
class Part:
    def __init__(self, name, title, material, qty=1):
        self.name, self.title, self.material, self.qty = name, title, material, qty
        self.solid = []        # shapely polygons unioned into the outline
        self.relief = []       # shapely polygons cut from the outline
        self.holes = []        # dicts: kind circle|arc_slot|slot|rect, geometry, note, face
        self.bends = []        # dicts: line ((x0,y0),(x1,y1)), note, zone polygon
        self.faces = {}        # face name -> shapely polygon (flat face, between bend zones)
        self.notes = []        # extra title lines
        self.fold = []         # folded 3D boxes for the collision check: (name, xmin..zmax)
        self.connect = set()   # pairs of fold boxes joined by a bend (they share material, not a clash)

    def outline(self):
        g = unary_union(self.solid)
        if self.relief:
            g = g.difference(unary_union(self.relief))
        return g


class Map:
    """Affine map from a face's folded (u, v) to flat (X, Y): X = ox + a*u + b*v, Y = oy + c*u + d*v."""
    def __init__(self, a, b, c, d, ox, oy):
        self.m = (a, b, c, d); self.o = (ox, oy)

    def __call__(self, u, v):
        a, b, c, d = self.m
        return self.o[0] + a * u + b * v, self.o[1] + c * u + d * v

    @property
    def det(self):
        a, b, c, d = self.m
        return a * d - b * c

    def vec(self, du, dv):
        a, b, c, d = self.m
        return a * du + b * dv, c * du + d * dv


def add_circle(p, face, mp, u, v, kind, note=None):
    d, txt = HOLE[kind]
    x, y = mp(u, v)
    p.holes.append(dict(kind="circle", c=(x, y), r=d / 2, note=note or txt, face=face, type=kind,
                        geom=Point(x, y).buffer(d / 2, 48), uv=(u, v)))


def add_rect(p, face, mp, u, v, w, h, note):
    x, y = mp(u, v)
    dx, dy = mp.vec(w, h)
    w2, h2 = abs(dx), abs(dy)
    p.holes.append(dict(kind="rect", c=(x, y), w=w2, h=h2, note=note, face=face, type="cutout",
                        geom=sbox(x - w2 / 2, y - h2 / 2, x + w2 / 2, y + h2 / 2), uv=(u, v), uvwh=(w, h)))


def add_poly(p, face, mp, pts, note, kind="poly"):
    """Closed polygon hole from (u, v) points on a face."""
    xy = [mp(u, v) for u, v in pts]
    g = Polygon(xy)
    p.holes.append(dict(kind="poly", pts=xy, c=tuple(g.representative_point().coords[0]), r=2.0, note=note, face=face, type=kind,
                        geom=g, uvpts=[tuple(q) for q in pts]))


def add_slot(p, face, mp, u, v, length, width, ang, note):
    """Stadium slot. `ang` in the face's (u, v) frame."""
    x, y = mp(u, v)
    dx, dy = mp.vec(math.cos(ang), math.sin(ang))
    a = math.atan2(dy, dx)
    h = max(0.0, length / 2 - width / 2)
    p0 = (x - h * math.cos(a), y - h * math.sin(a)); p1 = (x + h * math.cos(a), y + h * math.sin(a))
    p.holes.append(dict(kind="slot", p0=p0, p1=p1, r=width / 2, note=note, face=face, type="vent",
                        geom=LineString([p0, p1]).buffer(width / 2, 24), uv=(u, v), uvslot=(length, width, ang)))


def add_arc_slot(p, face, mp, u, v, r, w, a0, a1, note):
    """Curved slot of centre radius r and width w from angle a0 to a1 (face frame, CCW), round ends."""
    x, y = mp(u, v)
    def ang(t):
        dx, dy = mp.vec(math.cos(t), math.sin(t)); return math.atan2(dy, dx)
    b0, b1 = ang(a0), ang(a1)
    if mp.det < 0:
        b0, b1 = b1, b0
    while b1 <= b0:
        b1 += 2 * math.pi
    pts = [(x + r * math.cos(b0 + (b1 - b0) * i / 40), y + r * math.sin(b0 + (b1 - b0) * i / 40)) for i in range(41)]
    p.holes.append(dict(kind="arc_slot", c=(x, y), r=r, w=w, a0=b0, a1=b1, note=note, face=face, type="vent",
                        geom=LineString(pts).buffer(w / 2, 24)))


def add_bend(p, a, b, note, zone):
    p.bends.append(dict(line=(a, b), note=note, zone=zone))


def relief_notch(p, at, along, inward, outward):
    """Bend relief at the end of a partial-length flange: a 1 mm slot cut across the bend zone.
    `at` = point on the bend's face-side edge where the flange ends; `along` = unit vector along the bend
    pointing away from the flange; `inward` = unit vector into the face; `outward` = into the flange."""
    (ax, ay), (lx, ly), (ix, iy), (ox, oy) = at, along, inward, outward
    depth_in, depth_out = S + 0.5, BA + 0.5
    w = 1.0
    pts = []
    for s0, s1 in ((0, w),):
        q = [(ax + lx * s0 + ix * depth_in, ay + ly * s0 + iy * depth_in),
             (ax + lx * s1 + ix * depth_in, ay + ly * s1 + iy * depth_in),
             (ax + lx * s1 + ox * depth_out, ay + ly * s1 + oy * depth_out),
             (ax + lx * s0 + ox * depth_out, ay + ly * s0 + oy * depth_out)]
        pts.append(Polygon(q))
    p.relief += pts


def corner_relief(p, x0, x1, y0, y1):
    """Square relief where two bend zones cross."""
    p.relief.append(sbox(x0 - 0.5, y0 - 0.5, x1 + 0.5, y1 + 0.5))


def mirror_x(p):
    """Mirror a part's flat left-right. The body is built in the design frame (x right, seen from outside); the
    shop reads the drawing from the INSIDE face and folds UP, which mirrors it. Flipping the flat makes the folded
    body come out as designed (fold.py checks this from the DXF)."""
    from shapely.affinity import scale
    fx = lambda q: (-q[0], q[1])
    m = lambda g: scale(g, -1, 1, origin=(0, 0))
    p.solid = [m(g) for g in p.solid]; p.relief = [m(g) for g in p.relief]
    p.faces = {k: m(g) for k, g in p.faces.items()}
    for b in p.bends:
        b["line"] = tuple(fx(q) for q in b["line"]); b["zone"] = m(b["zone"])
    for h in p.holes:
        h["geom"] = m(h["geom"])
        for k in ("c", "p0", "p1"):
            if k in h:
                h[k] = fx(h[k])
        if "pts" in h:
            h["pts"] = [fx(q) for q in h["pts"]]
        if h["kind"] == "arc_slot":                      # angle a -> pi - a, and the CCW sweep runs the other way
            h["a0"], h["a1"] = math.pi - h["a1"], math.pi - h["a0"]
    return p


# ============================================================================
# BODY: base + front + two sides, top lips, back lips, base back lip, corner tabs
# ============================================================================
def body(kind):
    Hb = T + H[kind]                       # outer mold height (base underside to top of the top lips)
    p = Part(f"{kind}_body", f"{kind.upper()} BOX · BODY", "1.0 mm 304 stainless, brushed, film on")
    xe = WO / 2 - S                         # base face half-width in the flat
    yb0, yb1 = ZB + S, ZF - S               # base face, flat Y (= folded z)
    base = sbox(-xe, yb0, xe, yb1)
    p.solid.append(base); p.faces["base"] = base
    # --- walls
    # left wall: (u=z, v=y) -> X = -xe - BA - (v - S), Y = u
    ML = Map(0, -1, 1, 0, -xe - BA + S, 0)
    MR = Map(0, 1, 1, 0, xe + BA - S, 0)
    zfi = D / 2                              # front-wall inner face
    zs = zfi - TAB_GAP                       # side walls' front mold line = corner tab outer face
    for side, M_, sgn in (("left", ML, -1), ("right", MR, 1)):
        x_in, x_top = M_(0, S)[0], M_(0, Hb - S)[0]         # wall face X at its bottom and top bend lines
        face = sbox(min(x_in, x_top), yb0, max(x_in, x_top), zs - S)
        p.solid.append(face); p.faces[side] = face
        zone = sbox(min(sgn * xe, sgn * (xe + BA)), yb0, max(sgn * xe, sgn * (xe + BA)), zs - S)   # base→wall
        p.solid.append(zone)
        add_bend(p, (sgn * (xe + BA / 2), yb0), (sgn * (xe + BA / 2), zs - S), "Up 90° R1", zone)
        # top lip: full wall length
        xt0, xt1 = x_top, x_top + sgn * BA
        ztop = sbox(min(xt0, xt1), yb0, max(xt0, xt1), zs - S)
        lip = sbox(min(xt1, xt1 + sgn * (LIPO - S)), yb0, max(xt1, xt1 + sgn * (LIPO - S)), zs - S)
        p.solid += [ztop, lip]
        add_bend(p, ((xt0 + xt1) / 2, yb0), ((xt0 + xt1) / 2, zs - S), "Up 90° R1", ztop)
        p.fold.append((f"{side} top lip", *sorted((sgn * (WO / 2), sgn * (WO / 2 - LIPO))), Hb - T, Hb, ZB + 0.0 + S, zs - S))
        # back lip: y from 16.5 to Hb-3
        vb0, vb1 = LIPO + FOLD_GAP, Hb - 3.0          # clear of the base back lip
        xa, xb = M_(0, vb0)[0], M_(0, vb1)[0]
        zb_zone = sbox(min(xa, xb), yb0 - BA, max(xa, xb), yb0)
        blip = sbox(min(xa, xb), yb0 - BA - (LIPO - S), max(xa, xb), yb0 - BA)
        p.solid += [zb_zone, blip]
        add_bend(p, (xa, yb0 - BA / 2), (xb, yb0 - BA / 2), "Up 90° R1", zb_zone)
        for xe_, away in ((xa, -sgn), (xb, sgn)):
            relief_notch(p, (xe_, yb0), (away, 0), (0, 1), (0, -1))
        p.fold.append((f"{side} back lip", *sorted((sgn * (WO / 2), sgn * (WO / 2 - LIPO))), vb0, vb1, ZB, ZB + T))
        # corner tab at the front edge: y from 8 to Hb-3
        tv0, tv1 = 8.0, Hb - 3.0
        xa, xb = M_(0, tv0)[0], M_(0, tv1)[0]
        tz = sbox(min(xa, xb), zs - S, max(xa, xb), zs - S + BA)
        tab = sbox(min(xa, xb), zs - S + BA, max(xa, xb), zs - S + BA + (LIPO - S))
        p.solid += [tz, tab]
        add_bend(p, (xa, zs - S + BA / 2), (xb, zs - S + BA / 2), "Up 90° R1", tz)
        for xe_, away in ((xa, -sgn), (xb, sgn)):
            relief_notch(p, (xe_, zs - S), (away, 0), (0, -1), (0, 1))
        p.fold.append((f"{side} corner tab", *sorted((sgn * (WO / 2 - T), sgn * (WO / 2 - LIPO))), tv0, tv1, zs - T, zs))
        # tab rivet holes (tab frame: u = distance in from the wall's outer face, v = y)
        MT = Map(0, -sgn, 1, 0, 0, 0)       # placeholder: holes placed directly below
        for v in (Hb * 0.3, Hb * 0.7):
            xh = M_(0, v)[0]; yh = zs - S + BA + (LIPO / 2 + T / 2 - S)
            p.holes.append(dict(kind="circle", c=(xh, yh), r=HOLE["rivet"][0] / 2, note=HOLE["rivet"][1], face=f"{side} tab",
                                type="rivet", geom=Point(xh, yh).buffer(HOLE["rivet"][0] / 2, 48)))
        # top-lip rivnut (lip frame: distance in from the wall's outer face = T + RIV_IN)
        xr = xt1 + sgn * (T + RIV_IN - S); yr = 0.0
        p.holes.append(dict(kind="circle", c=(xr, yr), r=HOLE["rivnut_m3"][0] / 2, note=HOLE["rivnut_m3"][1], face=f"{side} top lip",
                            type="rivnut_m3", geom=Point(xr, yr).buffer(HOLE["rivnut_m3"][0] / 2, 48), folded=(sgn * (WO / 2 - T - RIV_IN), 0.0, "top")))
        # back-lip rivnut at mid height
        vm = T + H[kind] / 2
        xr2 = M_(0, vm)[0]; yr2 = yb0 - BA - (T + RIV_IN - S)
        p.holes.append(dict(kind="circle", c=(xr2, yr2), r=HOLE["rivnut_m3"][0] / 2, note=HOLE["rivnut_m3"][1], face=f"{side} back lip",
                            type="rivnut_m3", geom=Point(xr2, yr2).buffer(HOLE["rivnut_m3"][0] / 2, 48), folded=(sgn * (WO / 2 - T - RIV_IN), vm, "back")))
        # corner reliefs: base corners
        x0, x1 = sorted((sgn * xe, sgn * (xe + BA)))
        corner_relief(p, x0, x1, yb0 - BA, yb0)
        corner_relief(p, x0, x1, zs - S, yb1 + BA)      # from the wall bend's front end (it stops short for the tab) to past the front bend
        p.fold.append((f"{side} wall", *sorted((sgn * WO / 2, sgn * (WO / 2 - T))), 0, Hb, ZB, zs))
    # --- front wall: (u=x, v=y) -> X = u, Y = yb1 + BA + (v - S)
    MF = Map(1, 0, 0, 1, 0, yb1 + BA - S)
    fz = sbox(-xe, yb1, xe, yb1 + BA)
    front = sbox(-WO / 2, yb1 + BA, WO / 2, MF(0, Hb - S)[1])
    p.solid += [fz, front]; p.faces["front"] = front
    add_bend(p, (-xe, yb1 + BA / 2), (xe, yb1 + BA / 2), "Up 90° R1", fz)
    yt = MF(0, Hb - S)[1]
    flx = WO / 2 - LIPO - FOLD_GAP          # front top lip ends clear of the side top lips
    ftz = sbox(-flx, yt, flx, yt + BA)
    flip = sbox(-flx, yt + BA, flx, yt + BA + (LIPO - S))
    p.solid += [ftz, flip]
    add_bend(p, (-flx, yt + BA / 2), (flx, yt + BA / 2), "Up 90° R1", ftz)
    for xe_, away in ((-flx, -1), (flx, 1)):
        relief_notch(p, (xe_, yt), (away, 0), (0, -1), (0, 1))
    p.fold.append(("front top lip", -flx, flx, Hb - T, Hb, ZF - LIPO, ZF))
    p.fold.append(("front wall", -WO / 2, WO / 2, 0, Hb, ZF - T, ZF))
    xr = 0.0; yr = yt + BA + (T + RIV_IN - S)
    p.holes.append(dict(kind="circle", c=(xr, yr), r=2.5, note=HOLE["rivnut_m3"][1], face="front top lip", type="rivnut_m3",
                        geom=Point(xr, yr).buffer(2.5, 48), folded=(0.0, ZF - T - RIV_IN, "top")))
    # front-wall rivet holes matching the tabs
    for sgn in (-1, 1):
        for v in (Hb * 0.3, Hb * 0.7):
            x, y = MF(sgn * (WO / 2 - T - (LIPO - T) / 2), v)
            p.holes.append(dict(kind="circle", c=(x, y), r=1.6, note=HOLE["rivet"][1], face="front", type="rivet",
                                geom=Point(x, y).buffer(1.6, 48)))
    # --- base back lip
    bx = W / 2 - FOLD_GAP                    # ends clear of the side walls
    bz = sbox(-bx, yb0 - BA, bx, yb0)
    blip = sbox(-bx, yb0 - BA - (LIPO - S), bx, yb0 - BA)
    p.solid += [bz, blip]
    add_bend(p, (-bx, yb0 - BA / 2), (bx, yb0 - BA / 2), "Up 90° R1", bz)
    for xe_, away in ((-bx, -1), (bx, 1)):
        relief_notch(p, (xe_, yb0), (away, 0), (0, 1), (0, -1))
    p.fold.append(("base back lip", -bx, bx, 0, LIPO, ZB, ZB + T))
    p.fold.append(("base", -WO / 2, WO / 2, 0, T, ZB, ZF))
    xr, yr = 0.0, yb0 - BA - (T + LIP / 2 - S)
    p.holes.append(dict(kind="circle", c=(xr, yr), r=2.5, note=HOLE["rivnut_m3"][1], face="base back lip", type="rivnut_m3",
                        geom=Point(xr, yr).buffer(2.5, 48), folded=(0.0, T + LIP / 2, "back")))
    # --- base holes: standoffs, feet (base frame: X = x, Y = z)
    MB = Map(1, 0, 0, 1, 0, 0)
    for x in (-(W / 2 - 20), 0.0, W / 2 - 20):
        for z in (-(D / 2 - 20), D / 2 - 20):
            add_circle(p, "base", MB, x, z, "m4", "Ø4.5 standoff")
    for x, z in FEET_XZ:
        add_circle(p, "base", MB, x, z, "m4", "Ø4.5 locating foot" if kind == "control" else "Ø4.5 rubber foot")
    # --- wall features
    feat = []                                  # (wall, u0, u1, v0, v1, name) in folded wall coords, for the band check
    panels = []                                # printed panels: where they sit, for the inspector
    def panel(wall, mp, uc, vc, key, name):
        c = PANEL[key]
        add_rect(p, wall, mp, uc, vc, c["cut"][0], c["cut"][1], f"{name} cutout {c['cut'][0]:g} x {c['cut'][1]:g}")
        for a in (-1, 1):
            for b in (-1, 1):
                if c.get("rivnut"):
                    add_circle(p, wall, mp, uc + a * c["screw"][0], vc + b * c["screw"][1], "rivnut_m3", f"M3 rivnut (5mm), {name}")
                else:
                    add_circle(p, wall, mp, uc + a * c["screw"][0], vc + b * c["screw"][1], "m3", f"{name} screw")
        feat.append((wall, uc - c["plate"][0] / 2, uc + c["plate"][0] / 2, vc - c["plate"][1] / 2, vc + c["plate"][1] / 2, name))
        panels.append(dict(wall=wall, key=key, name=name, u=uc, v=vc, cut=list(c["cut"]), plate=list(c["plate"]), screw=list(c["screw"])))
    def fan(wall, mp, uc, vc):
        for k, rr in enumerate((12, 20, 28, 36)):
            for i in range(4):
                br, off = 7 / rr, k * 0.4
                add_arc_slot(p, wall, mp, uc, vc, rr, 4.0, off + i * math.pi / 2 + br, off + (i + 1) * math.pi / 2 - br, "fan grille")
        for a in (-1, 1):
            for b in (-1, 1):
                add_circle(p, wall, mp, uc + a * 35.75, vc + b * 35.75, "fan")
        feat.append((wall, uc - 40, uc + 40, vc - 40, vc + 40, "fan + screws"))
    if kind == "control":
        for g, (rect, riv) in gx_openings().items():
            poly = sbox(*rect).buffer(-3, join_style=1, quad_segs=4).buffer(3, join_style=1, quad_segs=4)
            add_poly(p, "front", MF, list(poly.exterior.coords)[:-1], f"GX16 {g} opening (printed plate over it)", kind="cutout")
            for u, v in riv:
                add_circle(p, "front", MF, u, v, "acc", "M3 rivnut (5mm), GX plate")
            feat.append(("front", rect[0], rect[2], rect[1], rect[3], f"GX16 {g}"))
        poly, scr = ctrl_window()
        add_poly(p, "front", MF, list(poly.exterior.coords)[:-1], "window (printed bezel + snap-on panel)", kind="window")
        for u, v in scr:
            add_circle(p, "front", MF, u, v, "rivnut_m3", "M3 rivnut (5mm), window bezel")
        bb = poly.buffer(WIN["band"] + WIN["rim"], join_style=1, quad_segs=4).bounds
        feat.append(("front", bb[0], bb[2], bb[1], bb[3], "window bezels"))
        fan("left", ML, *FAN[kind])
        panel("left", ML, -45.0, panel_y(kind, PANEL["usb_ant"]["plate"][1]), "usb_ant", "USB/antenna panel")
        panel("right", MR, JACK_Z, panel_y(kind, PANEL["receiving"]["plate"][1]), "receiving", "Receiving panel")
    else:
        top = T + H[kind]
        n, xv = 12, W / 2 - 40                    # full-width rows of 12, centred, pitch ~33.6
        for vr in VENT_ROWS:
            for i in range(n):
                add_slot(p, "front", MF, xv - i * 2 * xv / (n - 1), vr, 28, 3.5, 0.0, "vent")
        for vr in VENT_ROWS:
            feat.append(("front", -xv - 14, xv + 14, vr - 3.75, vr + 3.75, "front vents"))
        for poly, scr in window_panes():
            add_poly(p, "front", MF, list(poly.exterior.coords)[:-1], "window (printed bezel + snap-on panel)", kind="window")
            for u, v in scr:
                add_circle(p, "front", MF, u, v, "rivnut_m3", "M3 rivnut (5mm), window bezel")
            bb = poly.buffer(WIN["band"] + WIN["rim"], join_style=1, quad_segs=4).bounds
            feat.append(("front", bb[0], bb[2], bb[1], bb[3], "window bezels"))
        ls = logo_slot()
        add_poly(p, "front", MF, list(ls.exterior.coords)[:-1], "logo keyhole slot (printed spine)", kind="cutout")
        pw, ph = LOGO["plate"]
        feat.append(("front", LOGO["cx"] - pw / 2, LOGO["cx"] + pw / 2, LOGO["cy"] - ph / 2, LOGO["cy"] + ph / 2, "logo"))
        for u, v in ACC_FRONT:
            add_circle(p, "front", MF, u, v, "acc")
            feat.append(("front", u - 4, u + 4, v - 4, v + 4, "accessory rivnut"))
        fan("left", ML, *FAN[kind])
        panel("left", ML, D / 2 - 188.5, T + H[kind] / 2, "iec", "IEC panel")
        add_circle(p, "left", ML, D / 2 - 260, T + 20, "stud")
        feat.append(("left", D / 2 - 266, D / 2 - 254, T + 14, T + 26, "earth stud"))
        panel("right", MR, JACK_Z, panel_y(kind, PANEL["psu"]["plate"][1]), "psu", "PSU panel")
    p.feat, p.Hb, p.panels = feat, Hb, panels
    for side in ("left", "right"):
        for f in ("top lip", "back lip", "corner tab"):
            p.connect.add(frozenset((f"{side} wall", f"{side} {f}")))
        p.connect.add(frozenset((f"{side} wall", "base")))
    p.connect |= {frozenset(("front wall", "base")), frozenset(("front wall", "front top lip")), frozenset(("base", "base back lip"))}
    p.notes = [f"Folded outside: {WO:.0f} W x {ZF - ZB:.0f} D x {Hb:.0f} H (body, lips in)",
               f"Inside: {W:.0f} x {D:.0f} x {H[kind]:.0f}"]
    return mirror_x(p)


# ============================================================================
# LID: top + back, side/front return lips on the top, side return lips on the back
# ============================================================================
def lid(kind):
    Hb = T + H[kind]
    L = WO / 2 + CLR + T                     # lid half-width, outer
    zl0, zl1 = ZB - T, ZF + CLR + T          # lid back outer face, lid front-return outer face
    Hl = Hb + T - 1.0                        # lid back, from the top's outer face to its bottom edge
    p = Part(f"{kind}_lid", f"{kind.upper()} BOX · LID", "1.0 mm 304 stainless, brushed, film on")
    xe = L - S
    y0, y1 = zl0 + S, zl1 - S
    top = sbox(-xe, y0, xe, y1); p.solid.append(top); p.faces["top"] = top
    # side returns, full length
    G = FOLD_GAP - (S - T)                   # side returns stop short of the front return and the back
    for sgn in (-1, 1):
        x0, x1 = sorted((sgn * xe, sgn * (xe + BA)))
        lx0, lx1 = sorted((sgn * (xe + BA), sgn * (xe + BA + LIPO - S)))
        z = sbox(x0, y0 + G, x1, y1 - G)
        lip = sbox(lx0, y0 + G, lx1, y1 - G)
        p.solid += [z, lip]
        add_bend(p, (sgn * (xe + BA / 2), y0 + G), (sgn * (xe + BA / 2), y1 - G), "Up 90° R1", z)
        relief_notch(p, (sgn * xe, y0 + G), (0, -1), (-sgn, 0), (sgn, 0))
        relief_notch(p, (sgn * xe, y1 - G), (0, 1), (-sgn, 0), (sgn, 0))
        p.fold.append((f"lid {('left','right')[sgn > 0]} return", *sorted((sgn * L, sgn * (L - T))), Hb + T - LIPO, Hb + T, zl0 + S + G, zl1 - S - G))
    # front return
    fz = sbox(-xe, y1, xe, y1 + BA); flip = sbox(-xe, y1 + BA, xe, y1 + BA + LIPO - S)
    p.solid += [fz, flip]
    add_bend(p, (-xe, y1 + BA / 2), (xe, y1 + BA / 2), "Up 90° R1", fz)
    p.fold.append(("lid front return", -xe, xe, Hb + T - LIPO, Hb + T, zl1 - T, zl1))
    # back: (u = x, v = y above base underside) -> X = u, Y = y0 - BA - ((Hb + T - v) - S)
    MBk = Map(1, 0, 0, 1, 0, y0 - BA - (Hb + T) + S)
    bz = sbox(-xe, y0 - BA, xe, y0)
    back = sbox(-xe, MBk(0, Hb + T - Hl)[1], xe, y0 - BA)
    p.solid += [bz, back]; p.faces["back"] = back
    add_bend(p, (-xe, y0 - BA / 2), (xe, y0 - BA / 2), "Up 90° R1", bz)
    p.fold.append(("lid top", -L, L, Hb, Hb + T, zl0, zl1))
    p.fold.append(("lid back", -L, L, Hb + T - Hl, Hb + T, zl0, zl0 + T))
    # back side returns: from 16.5 below the top's outer face to the bottom edge
    h0 = LIPO + FOLD_GAP                     # clear of the top's side returns
    ya, yb = MBk(0, Hb + T - h0)[1], MBk(0, Hb + T - Hl)[1]
    for sgn in (-1, 1):
        x0, x1 = sorted((sgn * xe, sgn * (xe + BA)))
        z = sbox(x0, yb, x1, ya)
        lx0, lx1 = sorted((sgn * (xe + BA), sgn * (xe + BA + LIPO - S)))
        lip = sbox(lx0, yb, lx1, ya)
        p.solid += [z, lip]
        add_bend(p, (sgn * (xe + BA / 2), yb), (sgn * (xe + BA / 2), ya), "Up 90° R1", z)
        relief_notch(p, (sgn * xe, ya), (0, 1), (-sgn, 0), (sgn, 0))
        corner_relief(p, x0, x1, y0 - BA, y0)
        p.fold.append((f"lid back {('left','right')[sgn > 0]} return", *sorted((sgn * L, sgn * (L - T))), Hb + T - Hl, Hb + T - h0, zl0, zl0 + LIPO))
    corner_relief(p, -xe - BA, -xe, y1, y1 + BA)
    corner_relief(p, xe, xe + BA, y1, y1 + BA)
    # clearance holes over the body's rivnuts
    MT = Map(1, 0, 0, 1, 0, 0)
    for sgn in (-1, 1):
        add_circle(p, "top", MT, sgn * (WO / 2 - T - RIV_IN), 0.0, "lidclr")
        p.holes[-1]["folded"] = (sgn * (WO / 2 - T - RIV_IN), 0.0, "top")
        add_circle(p, "back", MBk, sgn * (WO / 2 - T - RIV_IN), T + H[kind] / 2, "lidclr")
        p.holes[-1]["folded"] = (sgn * (WO / 2 - T - RIV_IN), T + H[kind] / 2, "back")
    add_circle(p, "top", MT, 0.0, ZF - T - RIV_IN, "lidclr"); p.holes[-1]["folded"] = (0.0, ZF - T - RIV_IN, "top")
    add_circle(p, "back", MBk, 0.0, T + LIP / 2, "lidclr"); p.holes[-1]["folded"] = (0.0, T + LIP / 2, "back")
    if kind == "control":                    # accessory holes on the top of the stack
        for x, z in ACC_LID:
            add_circle(p, "top", MT, x, z, "acc")
            p.holes[-1]["acc_at"] = (x, z)
    if kind == "power":                      # locating holes for the control box's feet
        for (x, z), how in PEG_HOLES.items():
            if how == "slot":
                add_slot(p, "top", MT, x, z, PEG_SLOT[0], PEG_SLOT[1], 0.0, f"{PEG_SLOT[1]:g} x {PEG_SLOT[0]:g} locating slot")
            else:
                add_circle(p, "top", MT, x, z, "peg" if how == "round" else "pegclr")
            p.holes[-1]["peg"] = (x, z)
    # flow-field vents on the back, clear of the holes
    keep = [Point(h["c"]).buffer(14) for h in p.holes if h["face"] == "back"]
    seed = 2.1 if kind == "control" else 0.0
    u = -W / 2 + 40
    while u <= W / 2 - 40:
        v = T + LIPO + 25
        while v <= Hb - 30:
            a = 0.9 * math.sin(u / 55 + seed) + 0.7 * math.cos(v / 22 + u / 140)
            x, y = MBk(u, v)
            if not any(k.contains(Point(x, y)) for k in keep):
                add_slot(p, "back", MBk, u, v, 11, 3.0, a, "vent")
            v += 15
        u += 17
    for side in ("left", "right"):
        p.connect |= {frozenset(("lid top", f"lid {side} return")), frozenset(("lid back", f"lid back {side} return"))}
    p.connect |= {frozenset(("lid top", "lid front return")), frozenset(("lid top", "lid back"))}
    p.notes = [f"Folded outside: {2 * L:.0f} W x {zl1 - zl0:.1f} D x {Hl + 0:.0f} H at the back",
               f"Fits over the body with {CLR} mm per side inside the return lips"]
    return p


# ============================================================================
# BASE PLATE (flat, no bends)
# ============================================================================
PLATE_Y = (T + 5.0, T + 7.0)              # base plate underside / top, above the base underside


def plate_notches(kind):
    """Cut the plate clear (by FOLD_GAP) of what hangs low: the fan if it reaches below the plate's top + screw heads,
    and the base back lip's rivnut body (Ø5 x 9 inward)."""
    out = []
    fz, fy = FAN[kind]
    if fy - 40 < PLATE_Y[1] + 2.2 + FOLD_GAP:
        out.append(sbox(-W, fz - 40 - FOLD_GAP, -W / 2 + FAN_DEPTH + FOLD_GAP, fz + 40 + FOLD_GAP))
    out.append(sbox(-2.5 - FOLD_GAP - 1, -D, 2.5 + FOLD_GAP + 1, -D / 2 + 9 + FOLD_GAP))
    return out


def base_plate(kind):
    p = Part(f"{kind}_base_plate", f"{kind.upper()} BOX · BASE PLATE", "2.0 mm aluminium 5052 (or 1.5 mm 304)")
    pw, pd = 440.0, 285.0
    plate = sbox(-pw / 2, -pd / 2, pw / 2, pd / 2)
    plate = plate.difference(unary_union(plate_notches(kind)))
    p.solid.append(plate); p.faces["plate"] = plate
    M0 = Map(1, 0, 0, 1, 0, 0)
    so = [(x, z) for x in (-(W / 2 - 20), 0.0, W / 2 - 20) for z in (-(D / 2 - 20), D / 2 - 20)]
    for x, z in so:
        add_circle(p, "plate", M0, x, z, "m4", "Ø4.5 standoff")
    r, z = 0, -pd / 2 + 20
    while z <= pd / 2 - 15:
        x = -pw / 2 + 20 + (20 if r % 2 else 0)
        while x <= pw / 2 - 15:
            if all(math.hypot(x - sx, z - sz) >= 14 for sx, sz in so) and plate.buffer(-6).contains(Point(x, z)):
                add_circle(p, "plate", M0, x, z, "grid")
            x += 40
        z += 40; r += 1
    p.notes = ["Flat, no bends. Sits on 6 x M4 standoffs, 5 mm.", "Grid: 40 mm rows, every other row shifted 20 mm"]
    return p


# ============================================================================
# CHECKS
# ============================================================================
def checks(parts):
    out = []          # (ok, part, text)
    def ok(cond, part, text): out.append((bool(cond), part, text))
    for p in parts:
        g = p.outline()
        ok(g.geom_type == "Polygon", p.name, f"outline is one piece ({g.geom_type})")
        bend_lines = [LineString(b["line"]) for b in p.bends]
        for h in p.holes:
            hg = h["geom"]
            ok(g.buffer(-1.0).contains(hg), p.name, f"{h['note']} @({h.get('c', h.get('p0'))[0]:.1f},{h.get('c', h.get('p0'))[1]:.1f}) ≥1 mm inside the outline")
            for b in bend_lines:
                dmin = hg.distance(b)
                if dmin < 5.0 - 1e-6:
                    ok(False, p.name, f"{h['note']} is {dmin:.2f} mm from a bend line (min 5)")
        # webs between holes
        hs = [h["geom"] for h in p.holes]
        worst = 99.0
        for i in range(len(hs)):
            for j in range(i + 1, len(hs)):
                if hs[i].bounds[0] - 10 > hs[j].bounds[2] or hs[j].bounds[0] - 10 > hs[i].bounds[2]:
                    continue
                d = hs[i].distance(hs[j]); worst = min(worst, d)
        ok(worst >= 1.5, p.name, f"narrowest web between holes {worst:.2f} mm (min 1.5)")
        # every bend ends in free air (a relief or the part edge) for R + T either side: material past a bend's end tears or bulges
        for b in p.bends:
            (ax, ay), (cx, cy) = b["line"]; L_ = math.hypot(cx - ax, cy - ay)
            dx, dy = (cx - ax) / L_, (cy - ay) / L_; nx, ny = -dy, dx
            for ex, ey, sx in ((ax, ay, -1), (cx, cy, 1)):
                k_ = BA / 2 + 0.25  # across the zone and R + T into the faces either side
                q = Polygon([(ex + nx * k_, ey + ny * k_), (ex - nx * k_, ey - ny * k_),
                             (ex - nx * k_ + sx * dx * 0.5, ey - ny * k_ + sx * dy * 0.5),
                             (ex + nx * k_ + sx * dx * 0.5, ey + ny * k_ + sx * dy * 0.5)])
                ok(g.intersection(q).area < 1e-3, p.name, f"bend relieved at its end ({ex:.1f}, {ey:.1f})")
        # bend lines lie on the part and inside their zone
        for b in p.bends:
            ln = LineString(b["line"])
            ok(b["zone"].buffer(1e-6).contains(ln), p.name, f"bend line inside its zone")
            ok(abs(b["zone"].bounds[2] - b["zone"].bounds[0] - BA) < 1e-6 or abs(b["zone"].bounds[3] - b["zone"].bounds[1] - BA) < 1e-6,
               p.name, "bend zone width = bend allowance")
        # folded collisions
        boxes = p.fold
        clashes = 0
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                a, b = boxes[i], boxes[j]
                if frozenset((a[0], b[0])) in p.connect:
                    continue
                ov = [min(a[k + 1], b[k + 1]) - max(a[k], b[k]) for k in (1, 3, 5)]
                if all(o > 1e-6 for o in ov):
                    clashes += 1
                    ok(False, p.name, f"folded clash: {a[0]} / {b[0]} ({ov[0]:.2f} x {ov[1]:.2f} x {ov[2]:.2f})")
        if boxes:
            ok(clashes == 0, p.name, f"folded: {len(boxes)} panels, no two overlap except along their own bends")
    # cross-part: rivnut holes in the body sit under the lid's clearance holes
    by = {p.name: p for p in parts}
    for kind in ("control", "power"):
        # the lid, folded, sits on the body without touching it except face to face
        hits = []
        for a in by[f"{kind}_lid"].fold:
            for b in by[f"{kind}_body"].fold:
                ov = [min(a[k + 1], b[k + 1]) - max(a[k], b[k]) for k in (1, 3, 5)]
                if all(o > 1e-6 for o in ov):
                    hits.append(f"{a[0]} / {b[0]}")
        ok(not hits, kind, "lid on body: no overlap " + ("" if not hits else str(hits)))
        bh = [h["folded"] for h in by[f"{kind}_body"].holes if "folded" in h]
        lh = [h["folded"] for h in by[f"{kind}_lid"].holes if "folded" in h]
        ok(len(bh) == len(lh) == 6, kind, f"6 lid fixings on body ({len(bh)}) and lid ({len(lh)})")
        for f in bh:
            m = [l for l in lh if l[2] == f[2] and math.hypot(l[0] - f[0], l[1] - f[1]) < 0.01]
            ok(len(m) == 1, kind, f"lid clearance hole over rivnut at {f[2]} ({f[0]:.1f}, {f[1]:.1f})")
        # rivnut flange (Ø8) inside the lid's Ø9 hole
        ok((HOLE["lidclr"][0] - 8.0) / 2 >= CLR, kind, f"lid hole clears the rivnut flange by the lid play (Ø{HOLE['lidclr'][0]:g} over Ø8, ±{CLR})")
        # band check
        b = by[f"{kind}_body"]
        top = b.Hb
        for wall, u0, u1, v0, v1, name in b.feat:
            clash_top = v1 > top - BAND
            clash_back = wall != "front" and u0 < ZB + BAND
            ok(not (clash_top or clash_back), kind, f"lid band: {name} clear ({top - v1:.1f} mm below the band line)")
        # outside the wall: panel plates, fan screws and the stud keep 3 mm from each other
        for i, f1 in enumerate(b.feat):
            for f2 in b.feat[i + 1:]:
                if f1[0] == f2[0]:
                    g = max(f2[1] - f1[2], f1[1] - f2[2], f2[3] - f1[4], f1[3] - f2[4])
                    ok(g >= 3.0, kind, f"{f1[0]} wall: {f1[5]} / {f2[5]} {g:.1f} mm apart outside (need 3)")
        # base plate standoff holes over the floor's
        fl = sorted(h["uv"] for h in b.holes if h["note"] == "Ø4.5 standoff")
        pl = sorted(h.get("uv", h["c"]) for h in by[f"{kind}_base_plate"].holes if h["note"] == "Ø4.5 standoff")
        ok(fl == pl, kind, "base plate standoff holes line up with the floor's")
    # panel cutouts against the original printed panels in link_panel.py
    lp = _link_panel()
    if lp:
        for key, kind_ in (("receiving", "ctrl"), ("psu", "psu")):
            w, h = lp[kind_]
            cw, ch = PANEL[key]["cut"]
            ok(abs(max(w, h) - cw) < 0.01 and abs(min(w, h) - ch) < 0.01, "panels", f"{key} cutout {cw} x {ch} = printed panel's {max(w,h):.1f} x {min(w,h):.1f}")
            ex, ey = max(w, h) / 2 + 10 - 6, min(w, h) / 2 + 10 - 6
            ok(abs(ex - PANEL[key]["screw"][0]) < 0.01 and abs(ey - PANEL[key]["screw"][1]) < 0.01, "panels",
               f"{key} screw pattern ±{ex:.1f} x ±{ey:.1f} matches the print")
    # stacked boxes: fans in one column, jack panels in one column
    ok(FAN["control"][0] == FAN["power"][0], "stack", f"fans line up along the left walls (z {FAN['control'][0]:g})")
    jz = [q["u"] for b in (by["control_body"], by["power_body"]) for q in b.panels if q["key"] in ("receiving", "psu")]
    ok(len(jz) == 2 and jz[0] == jz[1], "stack", f"jack panels line up along the right walls (z {jz[0]:g})")
    # stacking: power-lid peg holes sit under the control box's foot holes, and the feet clear what lies between
    feet = sorted(h["uv"] for h in by["control_body"].holes if h["note"] == "Ø4.5 locating foot")
    pegs = sorted(h["peg"] for h in by["power_lid"].holes if "peg" in h)
    ok(feet == pegs and len(feet) == 4, "stack", "power-lid locating holes line up with the control box's 4 feet")
    ok(HOLE["peg"][0] - STACK["peg_d"] >= 0.3 and PEG_SLOT[1] - STACK["peg_d"] >= 0.3 and HOLE["pegclr"][0] - STACK["peg_d"] >= 2.0,
       "stack", f"peg Ø{STACK['peg_d']} in Ø{HOLE['peg'][0]:g} / {PEG_SLOT[1]:g} slot / Ø{HOLE['pegclr'][0]:g}")
    ok(PEG_SLOT[0] - STACK["peg_d"] >= 2 * 1.0 + 0.4, "stack", f"slot allows ±1 mm of width error ({PEG_SLOT[0]:g} long)")
    ok(STACK["flange_h"] - max(STACK["lid_fix_h"], STACK["floor_head_h"]) >= 2.0, "stack",
       f"{STACK['flange_h']:g} mm flange clears the lid fixings ({STACK['lid_fix_h']:.1f}) and the floor screw heads ({STACK['floor_head_h']:g}) by 2")
    ok(max(HOLE["peg"][0], PEG_SLOT[1], HOLE["pegclr"][0]) < 12.0, "stack", "stacking holes under 12 mm (finger probe)")
    # the lid's return lips must end inside the no-mount band, with margin
    ok(LIPO - T + 2.0 <= BAND, "fit", f"lid return lips reach {LIPO - T:.0f} mm down the walls; band is {BAND:.0f} (needs 2 mm margin)")
    # lid fits: inside of the lid's returns vs the body's outside
    ok(abs((2 * (WO / 2 + CLR + T) - 2 * T) - (WO + 2 * CLR)) < 1e-9, "fit", f"lid inside width {WO + 2 * CLR:.1f} = body {WO:.0f} + 2 x {CLR}")
    return out


def _link_panel():
    """Cutout sizes of the original printed panels, read from link_panel.py without build123d."""
    src = HERE.parent / "parts" / "link_panel.py"
    try:
        s = src.read_text()
        s = s.split("from build123d")[0] + s.split("extrude)", 1)[1]
        ns = {"__name__": "x", "__file__": str(src)}
        exec(s, ns)
        return {k: ns["_layout"](k)[:2] for k in ("psu", "ctrl")}
    except Exception as e:
        print("  (could not read link_panel.py:", e, ")")
        return None


# ============================================================================
# DXF R12 OUT
# ============================================================================
LAYERS = [("Visible", 7, "CONTINUOUS"), ("Visible Narrow", 8, "CONTINUOUS"), ("Bend Center", 1, "CENTER2"),
          ("Bend Notes", 3, "CONTINUOUS"), ("Leaders", 5, "CONTINUOUS"), ("Title", 7, "CONTINUOUS")]


def write_dxf(p, path):
    L = []
    def g(code, val): L.append(f"{code:>3}"); L.append(str(val))
    def line(a, b, layer):
        g(0, "LINE"); g(8, layer); g(10, f"{a[0]:.4f}"); g(20, f"{a[1]:.4f}"); g(30, 0.0); g(11, f"{b[0]:.4f}"); g(21, f"{b[1]:.4f}"); g(31, 0.0)
    def circle(c, r, layer):
        g(0, "CIRCLE"); g(8, layer); g(10, f"{c[0]:.4f}"); g(20, f"{c[1]:.4f}"); g(30, 0.0); g(40, f"{r:.4f}")
    def arc(c, r, a0, a1, layer):   # degrees, CCW
        g(0, "ARC"); g(8, layer); g(10, f"{c[0]:.4f}"); g(20, f"{c[1]:.4f}"); g(30, 0.0); g(40, f"{r:.4f}")
        g(50, f"{math.degrees(a0) % 360:.4f}"); g(51, f"{math.degrees(a1) % 360:.4f}")
    def text(x, y, h, s, layer, rot=0.0):
        s = s.replace("°", "%%D").replace("Ø", "%%c").replace("·", "-").replace("→", "->").replace("×", "x")
        s = s.encode("ascii", "replace").decode()
        g(0, "TEXT"); g(8, layer); g(10, f"{x:.4f}"); g(20, f"{y:.4f}"); g(30, 0.0); g(40, f"{h:.3f}"); g(1, s)
        if rot: g(50, f"{rot:.2f}")
    # header + tables
    g(0, "SECTION"); g(2, "HEADER"); g(9, "$ACADVER"); g(1, "AC1009"); g(9, "$INSUNITS"); g(70, 4); g(0, "ENDSEC")
    g(0, "SECTION"); g(2, "TABLES")
    g(0, "TABLE"); g(2, "LTYPE"); g(70, 2)
    g(0, "LTYPE"); g(2, "CONTINUOUS"); g(70, 0); g(3, "Solid line"); g(72, 65); g(73, 0); g(40, 0.0)
    g(0, "LTYPE"); g(2, "CENTER2"); g(70, 0); g(3, "Center (.5x) ___ _ ___ _"); g(72, 65); g(73, 4); g(40, 28.575)
    for d in (19.05, -3.175, 3.175, -3.175):
        g(49, d)
    g(0, "ENDTAB")
    g(0, "TABLE"); g(2, "LAYER"); g(70, len(LAYERS))
    for name, col, lt in LAYERS:
        g(0, "LAYER"); g(2, name); g(70, 0); g(62, col); g(6, lt)
    g(0, "ENDTAB"); g(0, "ENDSEC")
    g(0, "SECTION"); g(2, "ENTITIES")
    # outline
    o = p.outline()
    rings = [o.exterior] + list(o.interiors)
    for ring in rings:
        cs = list(ring.coords)
        for a, b in zip(cs, cs[1:]):
            if math.dist(a, b) > 1e-6:
                line(a, b, "Visible")
    # holes
    for h in p.holes:
        k = h["kind"]
        if k == "circle":
            circle(h["c"], h["r"], "Visible")
        elif k == "rect":
            x, y, w, hh = *h["c"], h["w"], h["h"]
            pts = [(x - w / 2, y - hh / 2), (x + w / 2, y - hh / 2), (x + w / 2, y + hh / 2), (x - w / 2, y + hh / 2), (x - w / 2, y - hh / 2)]
            for a, b in zip(pts, pts[1:]):
                line(a, b, "Visible")
        elif k == "poly":
            pts = list(h["pts"]) + [h["pts"][0]]
            for a, b in zip(pts, pts[1:]):
                if math.dist(a, b) > 1e-6:
                    line(a, b, "Visible")
        elif k == "slot":
            (x0, y0), (x1, y1), r = h["p0"], h["p1"], h["r"]
            a = math.atan2(y1 - y0, x1 - x0); nx, ny = -math.sin(a) * r, math.cos(a) * r
            line((x0 + nx, y0 + ny), (x1 + nx, y1 + ny), "Visible"); line((x0 - nx, y0 - ny), (x1 - nx, y1 - ny), "Visible")
            arc((x1, y1), r, a - math.pi / 2, a + math.pi / 2, "Visible"); arc((x0, y0), r, a + math.pi / 2, a + 3 * math.pi / 2, "Visible")
        elif k == "arc_slot":
            (x, y), r, w, a0, a1 = h["c"], h["r"], h["w"], h["a0"], h["a1"]
            arc((x, y), r + w / 2, a0, a1, "Visible"); arc((x, y), r - w / 2, a0, a1, "Visible")
            for aa, s0, s1 in ((a1, a1, a1 + math.pi), (a0, a0 + math.pi, a0 + 2 * math.pi)):
                arc((x + r * math.cos(aa), y + r * math.sin(aa)), w / 2, s0, s1, "Visible")
    # bends
    for b in p.bends:
        (a, c) = b["line"]
        line(a, c, "Bend Center")
        z = b["zone"].bounds
        if abs(a[0] - c[0]) < 1e-9:      # vertical bend
            line((z[0], z[1]), (z[0], z[3]), "Visible Narrow"); line((z[2], z[1]), (z[2], z[3]), "Visible Narrow")
            text(a[0] + 2.5, (a[1] + c[1]) / 2, 3.5, b["note"], "Bend Notes", 90)
        else:
            line((z[0], z[1]), (z[2], z[1]), "Visible Narrow"); line((z[0], z[3]), (z[2], z[3]), "Visible Narrow")
            text((a[0] + c[0]) / 2 - 12, a[1] + 2.5, 3.5, b["note"], "Bend Notes")
    # leaders: one note per hole type per face, beside one hole of that type
    seen = set()
    for h in p.holes:
        key = (h["face"], h["note"])
        if key in seen or h["type"] == "vent" and h["note"] == "vent" and (h["face"], "vent") in seen:
            continue
        seen.add(key)
        x, y = h.get("c", h.get("p0"))
        rr = h.get("r", 2) if h["kind"] != "rect" else h["h"] / 2
        text(x + rr + 1.5, y - 1.2, 2.5, h["note"], "Leaders")
    # title block
    minx, miny, maxx, maxy = o.bounds
    ty = miny - 12
    lines = [p.title, f"Material: {p.material}   Qty: {p.qty}   Units: mm",
             "Drawn from the INSIDE face. All bends: UP 90°, inner radius R1." if p.bends else "Flat part, no bends.",
             f"Flat assumes K {K}, bend allowance {BA:.2f}, deduction {BD:.2f} per bend. Shop's value wins: re-run if different." if p.bends else "",
             *p.notes, f"Flat size: {maxx - minx:.1f} x {maxy - miny:.1f}"]
    for i, s in enumerate([l for l in lines if l]):
        text(minx, ty - i * 6.5, 4.0 if i == 0 else 3.0, s, "Title")
    g(0, "ENDSEC"); g(0, "EOF")
    path.write_text("\n".join(L) + "\n", encoding="ascii")


# ============================================================================
# INDEPENDENT READ-BACK + SVG PREVIEW
# ============================================================================
def read_dxf(path):
    lines = path.read_text().splitlines()
    pairs = [(lines[i].strip(), lines[i + 1]) for i in range(0, len(lines) - 1, 2)]
    i = next(k for k, (c, v) in enumerate(pairs) if c == "2" and v == "ENTITIES")
    ents, cur = [], None
    for c, v in pairs[i + 1:]:
        if c == "0":
            if v == "ENDSEC":
                break
            cur = {"type": v}; ents.append(cur)
        else:
            cur.setdefault(c, []).append(v)
    return ents


def verify_and_preview(path, svg_path):
    ents = read_dxf(path)
    f = lambda e, c, i=0: float(e[c][i])
    by = {}
    for e in ents:
        by.setdefault((e["type"], e["8"][0]), []).append(e)
    # outline closure: every Visible line endpoint is shared by exactly two endpoints
    pts = {}
    for e in by.get(("LINE", "Visible"), []):
        for a in (((f(e, "10"), f(e, "20"))), ((f(e, "11"), f(e, "21")))):
            k = (round(a[0], 3), round(a[1], 3)); pts[k] = pts.get(k, 0) + 1
    for e in by.get(("ARC", "Visible"), []):
        cx, cy, r = f(e, "10"), f(e, "20"), f(e, "40")
        for ang in (f(e, "50"), f(e, "51")):
            a = (cx + r * math.cos(math.radians(ang)), cy + r * math.sin(math.radians(ang)))
            k = (round(a[0], 3), round(a[1], 3)); pts[k] = pts.get(k, 0) + 1
    # tolerate 1e-3 rounding: merge keys that differ by one unit in the last place
    merged = {}
    for k, v in pts.items():
        hit = next((m for m in merged if abs(m[0] - k[0]) <= 0.002 and abs(m[1] - k[1]) <= 0.002), None)
        merged[hit or k] = merged.get(hit or k, 0) + v
    pts = merged
    odd = sum(1 for v in pts.values() if v % 2)
    xs = [k[0] for k in pts] or [0]; ys = [k[1] for k in pts] or [0]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    # svg
    pad, sc = 20, 1.0
    W_, H_ = (maxx - minx) * sc + 2 * pad, (maxy - miny) * sc + 2 * pad + 90
    X = lambda x: pad + (x - minx) * sc
    Y = lambda y: pad + (maxy - y) * sc
    col = {"Visible": "#111", "Visible Narrow": "#9aa", "Bend Center": "#d22", "Bend Notes": "#2a7", "Leaders": "#25a", "Title": "#111"}
    o = []
    for e in ents:
        lay = e.get("8", ["?"])[0]; c = col.get(lay, "#f0f")
        dash = ' stroke-dasharray="8 2 2 2"' if lay == "Bend Center" else ""
        if e["type"] == "LINE":
            o.append(f'<line x1="{X(f(e,"10")):.2f}" y1="{Y(f(e,"20")):.2f}" x2="{X(f(e,"11")):.2f}" y2="{Y(f(e,"21")):.2f}" stroke="{c}" stroke-width="0.35"{dash}/>')
        elif e["type"] == "CIRCLE":
            o.append(f'<circle cx="{X(f(e,"10")):.2f}" cy="{Y(f(e,"20")):.2f}" r="{f(e,"40")*sc:.2f}" fill="none" stroke="{c}" stroke-width="0.35"/>')
        elif e["type"] == "ARC":
            cx, cy, r, a0, a1 = f(e, "10"), f(e, "20"), f(e, "40"), math.radians(f(e, "50")), math.radians(f(e, "51"))
            sweep = (a1 - a0) % (2 * math.pi)
            x0, y0 = X(cx + r * math.cos(a0)), Y(cy + r * math.sin(a0)); x1, y1 = X(cx + r * math.cos(a1)), Y(cy + r * math.sin(a1))
            o.append(f'<path d="M{x0:.2f},{y0:.2f} A{r*sc:.2f},{r*sc:.2f} 0 {1 if sweep > math.pi else 0} 0 {x1:.2f},{y1:.2f}" fill="none" stroke="{c}" stroke-width="0.35"/>')
        elif e["type"] == "TEXT":
            x, y, h = X(f(e, "10")), Y(f(e, "20")), f(e, "40") * sc
            rot = -float(e["50"][0]) if "50" in e else 0
            s = e["1"][0].replace("%%D", "°").replace("%%c", "Ø").replace("&", "&amp;").replace("<", "&lt;")
            o.append(f'<text x="{x:.2f}" y="{y:.2f}" font-size="{h:.2f}" fill="{c}" font-family="Helvetica, Arial" transform="rotate({rot} {x:.2f} {y:.2f})">{s}</text>')
    # include text extents
    ty = [Y(f(e, "20")) for e in by.get(("TEXT", "Title"), [])]
    H_ = max(H_, (max(ty) + 30) if ty else H_)
    svg_path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W_:.0f}mm" height="{H_:.0f}mm" viewBox="0 0 {W_:.1f} {H_:.1f}">'
                        f'<rect width="100%" height="100%" fill="#fff"/>{"".join(o)}</svg>')
    counts = {f"{t}/{l}": len(v) for (t, l), v in sorted(by.items())}
    return dict(open_ends=odd, size=(maxx - minx, maxy - miny), counts=counts)


def refold_check(kind, part, ents):
    """Rebuild the folded box from the bend lines as written in the DXF, and compare with the design."""
    f = lambda e, c: float(e[c][0])
    bl = [e for e in ents if e["type"] == "LINE" and e["8"][0] == "Bend Center"]
    vx = sorted({round(f(e, "10"), 4) for e in bl if abs(f(e, "10") - f(e, "11")) < 1e-6})
    # horizontal bend lines that run across the middle (x = 0): base back, base front, front top lip / lid back, lid front
    hy = sorted({round(f(e, "20"), 4) for e in bl if abs(f(e, "20") - f(e, "21")) < 1e-6 and min(f(e, "10"), f(e, "11")) < 0 < max(f(e, "10"), f(e, "11"))})
    span = lambda a, b: abs(b - a) - BA + 2 * S          # folded outer length between two bend lines
    Hb = T + H[kind]
    res = []
    if part.endswith("body"):
        # vertical bends, left to right: left top lip, left base bend, right base bend, right top lip (+ back-lip/tab lines are horizontal)
        xl_top, xl, xr, xr_top = vx[0], vx[1], vx[-2], vx[-1]
        res += [("body width", span(xl, xr), WO), ("left wall height", span(xl_top, xl), Hb), ("right wall height", span(xr, xr_top), Hb)]
        # horizontal bends, bottom to top: back lips (side + base share one line), base back, base front + tabs, front wall top lip
        assert len(hy) == 3, hy
        yb, yf, ytop = hy
        res += [("body depth (base)", span(yb, yf), ZF - ZB), ("front wall height", span(yf, ytop), Hb)]
    else:
        xl, xr = vx[0], vx[-1]
        assert len(hy) == 2, hy
        yback, yfront = hy
        res += [("lid width", span(xl, xr), WO + 2 * (CLR + T)), ("lid depth", span(yback, yfront), (ZF + CLR + T) - (ZB - T))]
    return [(abs(got - want) < 0.01, f"refold {name}: {got:.2f} (design {want:.2f})") for name, got, want in res]


# ============================================================================
def build():
    parts = []
    for kind in ("control", "power"):
        parts += [body(kind), lid(kind), base_plate(kind)]
    return parts


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true", help="run the checks, write nothing")
    a = ap.parse_args(argv)
    parts = build()
    res = checks(parts)
    bad = [r for r in res if not r[0]]
    print(f"{len(res)} checks, {len(bad)} failed")
    for okk, part, txt in res:
        if not okk:
            print(f"  FAIL  {part:16s} {txt}")
    import assembly_check                        # whole assembly: steel gaps, fits, every part inside
    afail, awarn, _ = assembly_check.run()
    print(f"assembly: {len(afail)} clashes, {len(awarn)} warnings on placeholder parts")
    for m in afail:
        print("  CLASH", m)
        res.append((False, "assembly", m))
    for m in awarn:
        print("  warn ", m)
    res.append((not afail, "assembly", f"whole assembly: no clashes; folded flanges ≥ {assembly_check.STEEL_GAP} mm apart, "
                                        f"lid {CLR} mm per side, tabs {TAB_GAP} mm"))
    bad = [r for r in res if not r[0]]
    if bad:
        print("Nothing written.")
        return 1
    if a.report:
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    summary = []
    for p in parts:
        dxf = OUT / f"{p.name}.dxf"
        write_dxf(p, dxf)
        v = verify_and_preview(dxf, OUT / f"{p.name}.svg")
        status = "closed" if v["open_ends"] == 0 else f"{v['open_ends']} OPEN ENDS"
        if p.bends:
            kind = p.name.split("_")[0]
            for okk, txt in refold_check(kind, p.name, read_dxf(dxf)):
                print(f"      {'ok  ' if okk else 'FAIL'} {txt}")
                res.append((okk, p.name, txt))
                if not okk:
                    return 1
        print(f"  {dxf.name:28s} {v['size'][0]:7.1f} x {v['size'][1]:6.1f}  outline {status}  {v['counts']}")
        if v["open_ends"]:
            return 1
        summary.append(dict(part=p.name, title=p.title, material=p.material, qty=p.qty, flat=[round(v["size"][0], 1), round(v["size"][1], 1)],
                            bends=len(p.bends), holes=len(p.holes), notes=p.notes))
    (OUT / "summary.json").write_text(json.dumps(dict(parts=summary, checks=[[r[0], r[1], r[2]] for r in res],
                                                      bend=dict(T=T, R=R, K=K, BA=round(BA, 3), BD=round(BD, 3))), indent=1))
    print(f"wrote {OUT}")
    sync_inspector(parts)
    try:                                         # fold the DXFs as the shop will and compare with the design
        import fold
    except ImportError as ex:
        print(f"fold check skipped ({ex.name} missing: pip install trimesh manifold3d mapbox_earcut scipy)")
        return 0
    print("fold check (from the DXFs):")
    return fold.main()


INSPECTOR = HERE.parent / "web" / "enclosure_inspector.html"


def sync_inspector(parts):
    """Write the generator's numbers into the 3D inspector, so the preview is the cut files, not a copy of them."""
    by = {p.name: p for p in parts}
    gen = dict(clr=CLR, tabGap=TAB_GAP, foldGap=FOLD_GAP, lidHole=HOLE["lidclr"][0], lidReturnInset=FOLD_GAP - (S - T),
               frontLipHalf=WO / 2 - LIPO - FOLD_GAP, baseLipHalf=W / 2 - FOLD_GAP, backLipFrom=LIPO + FOLD_GAP,
               fan={k: list(v) for k, v in FAN.items()}, plate={}, accLid=[list(q) for q in ACC_LID], accD=HOLE["acc"][0],
               gx=[dict(group=g, open=[[round(a, 2), round(b, 2)] for a, b in list(sbox(*rect).buffer(-3, join_style=1, quad_segs=4).buffer(3, join_style=1, quad_segs=4).exterior.coords)[:-1]],
                        plate=[[round(a, 2), round(b, 2)] for a, b in list(gx_plate(rect, g).exterior.coords)[:-1]],
                        sockets=[list(q) for q in GX_GROUPS[g]], rivnuts=[list(q) for q in riv]) for g, (rect, riv) in gx_openings().items()],
               windows={k_: [dict(open=[[round(a, 2), round(b, 2)] for a, b in list(pl.exterior.coords)[:-1]],
                             bezel=[[round(a, 2), round(b, 2)] for a, b in list(pl.buffer(WIN["band"], join_style=1, quad_segs=8).exterior.coords)[:-1]],
                             acrylic=[[round(a, 2), round(b, 2)] for a, b in list(pl.buffer(WIN["mar"], join_style=1, quad_segs=4).exterior.coords)[:-1]],
                             screws=[[round(a, 2), round(b, 2)] for a, b in sc]) for pl, sc in panes] for k_, panes in (("power", window_panes()), ("control", [ctrl_window()]))},
               stack=dict(**STACK, slot=list(PEG_SLOT), peg_hole=HOLE["peg"][0], peg_clear=HOLE["pegclr"][0],
                          holes=[[x, z, how] for (x, z), how in PEG_HOLES.items()]))
    gen["walls"], gen["panels"] = {}, {}
    for kind in ("control", "power"):
        b = by[f"{kind}_body"]
        gen["panels"][kind] = b.panels
        walls = gen["walls"][kind] = {"front": [], "left": [], "right": []}
        for h in b.holes:
            if h["face"] not in walls or ("uv" not in h and "uvpts" not in h) or "fan" in h["note"]:
                continue                       # fan grille + screws: the inspector draws them from gen["fan"]
            u, v = (round(q, 3) for q in h.get("uv", (0, 0)))
            if h["kind"] == "rect":
                walls[h["face"]].append(["rect", u, v, *h["uvwh"]])
            elif h["kind"] == "poly":
                walls[h["face"]].append(["poly", [[round(a, 2), round(b, 2)] for a, b in h["uvpts"]]])
            elif h["kind"] == "slot":
                walls[h["face"]].append(["slot", u, v, *h["uvslot"]])
            else:
                walls[h["face"]].append(["circle", u, v, h["r"]])
    for kind in ("control", "power"):
        pl = by[f"{kind}_base_plate"]
        gen["plate"][kind] = dict(outline=[[round(x, 2), round(z, 2)] for x, z in pl.outline().exterior.coords[:-1]],
                                  holes=[[round(h["c"][0], 2), round(h["c"][1], 2), h["r"]] for h in pl.holes])
    src = INSPECTOR.read_text()
    a, b = src.index("// GEN:BEGIN"), src.index("// GEN:END")
    INSPECTOR.write_text(src[:a] + "// GEN:BEGIN (written by hardware/sheet/enclosure.py, do not edit)\nconst GEN = "
                         + json.dumps(gen, separators=(",", ":")) + ";\n" + src[b:])
    print("synced", INSPECTOR.name)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
