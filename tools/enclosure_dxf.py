#!/usr/bin/env python3
"""enclosure_dxf.py - flat patterns for the laser-cut control box.

Emits DXF (R12) flat patterns plus an SVG preview of each part:

    base.dxf      bottom + 4 walls, one folded piece, corner tabs
    lid.dxf       shallow pan that telescopes over the base
    adapters.dxf  small flat plates that bridge awkward hole patterns
                  onto the base grid

    python3 enclosure_dxf.py               write into ./enclosure/
    python3 enclosure_dxf.py --out ~/box   somewhere else
    python3 enclosure_dxf.py --report      print the numbers, write nothing

No dependencies.  Everything you might want to change is in CONFIG below.

READ THIS BEFORE CUTTING METAL
------------------------------
The flat patterns assume a bend deduction this script computes from R, T and
K (see BEND below).  That number belongs to whoever owns the press brake, not
to this file.  Hand the shop the FOLDED dimensions and let them do their own
unfold; use these DXFs as the cutout and hole positions, or as a cross-check.
Every hole in a wall shifts in the flat if their bend deduction differs from
ours.

Three dimensions in CONFIG are marked MEASURE.  They are the ones nobody
should take on trust - a datasheet envelope is not the same as the unit on
your bench, and the connector cutouts vary between vendors selling the same
part number.  The base is a hole grid precisely so that being wrong about a
component's mounting pattern costs you a 3 mm adapter plate, not a box.
"""

import argparse, math, os, sys

# ===========================================================================
# CONFIG
# ===========================================================================

# --- sheet ----------------------------------------------------------------
T = 1.5                 # sheet thickness, mm.  1.5 CR steel or 2.0 5052 ally
R_BEND = 1.5            # inner bend radius, mm.  1 x T is the usual default
K = 0.42                # K-factor.  0.42 suits a 1 x T radius in mild steel

# --- enclosure, interior --------------------------------------------------
LI = 350.0              # length, front wall to... along the front wall
WI = 220.0              # depth, front wall to rear wall
HI = 75.0               # height, floor to top edge

# --- what goes inside -----------------------------------------------------
# Envelopes only.  None of these drives a hole in the base - the grid does.
PSU = (215.0, 115.0, 30.0)      # Mean Well LRS-350-24.  MEASURE: read the
                                # label, the original Ender-3 had variants
BOARD = (68.6, 53.4)            # Arduino Uno R3 outline
BOARD_STACK_H = 50.0            # MEASURE: Uno + shield + A4988 + heatsink,
                                # from the base of the standoffs
DIN_RUN = 90.0                  # TS35 rail length for PE + 2 fuses + 2 blocks

# --- base hole grid -------------------------------------------------------
GRID_PITCH = 25.0       # matches the 25 mm slot pitch of TS35 DIN rail
GRID_DIA = 3.5          # M3 clearance
GRID_MARGIN = 20.0      # keep the grid out of the bend zone

# --- panel cutouts --------------------------------------------------------
# u = along the wall from its left edge (front wall: from the box's left end;
#     end walls: from the front).  v = height above the interior floor.
GX16_DIA = 16.0
GX12_DIA = 12.0
PORT_V = 37.5           # one centreline for every round port

FRONT_PORTS = [         # (u, diameter, label)
    (55.0,  GX16_DIA, "X"),
    (100.0, GX16_DIA, "A"),
    (145.0, GX16_DIA, "Y"),
    (200.0, GX12_DIA, "LIM"),
    (245.0, GX12_DIA, "PEN"),
]
# MEASURE: USB-B panel couplers come as rectangular-with-two-screws and as
# D-hole.  This is the common rectangular one.  Confirm against your part.
USB_U, USB_W, USB_H = 300.0, 27.5, 15.5
USB_SCREW_PITCH, USB_SCREW_DIA = 30.0, 3.4

# MEASURE: snap-in power entry modules vary.  ~47 x 27 is the common size.
IEC_U, IEC_W, IEC_H = 150.0, 47.0, 27.0     # left end wall, u from the front

FAN_U = 60.0            # right end wall, u from the front
FAN_HOLE_DIA = 57.0
FAN_SCREW_PITCH, FAN_SCREW_DIA = 50.0, 4.5

VENT_DIA = 5.0          # rear wall perf field.  5 mm keeps fingers out
VENT_PITCH = 10.0
VENT_MARGIN = 18.0

EARTH_STUD_DIA = 6.5    # M6 earth stud in the base, its own hole, shared
                        # with nothing
FOOT_DIA = 4.5
FOOT_INSET = 32.5      # GRID_MARGIN + half a pitch: clears the grid

# --- lid ------------------------------------------------------------------
LID_SKIRT = 15.0        # telescopes over the base walls
LID_GAP = 0.4           # clearance per side
LID_SCREW_DIA = 3.4
LID_SCREW_V = 7.5       # up from the bottom edge of the skirt
LID_SCREWS_LONG = 2     # per long side
LID_SCREWS_END = 1      # per end

# --- corner tabs ----------------------------------------------------------
TAB_LEN = 20.0          # laps inside the adjacent wall
TAB_INSET = 5.0         # from the top edge of the wall
TAB_HOLE_DIA = 3.4
RELIEF_R = None         # None -> use T

# --- Arduino Uno R3 mounting holes ---------------------------------------
# MEASURE: the four holes are not on a grid and none of the spacings is
# round.  These are the published R3 figures; trace them off your board
# before you rely on them.  Origin at the board's lower-left corner.
UNO_HOLES = [(13.97, 2.54), (15.24, 50.80), (66.04, 35.56), (66.04, 7.62)]
UNO_HOLE_DIA = 3.4
ADAPTER_PAD = 12.0      # material around the board outline on the adapter

# ===========================================================================


def bend_deduction(t=T, r=R_BEND, k=K, angle=90.0):
    """Outside bend deduction for one bend, mm.

    BA = pi/180 * angle * (r + k*t)      arc length at the neutral axis
    BD = 2*(r + t) - BA                  for a 90 degree bend
    """
    ba = math.radians(angle) * (r + k * t)
    ossb = (r + t) * math.tan(math.radians(angle) / 2.0)
    return 2.0 * ossb - ba


BD = bend_deduction()
RELIEF = RELIEF_R if RELIEF_R is not None else T


# ---------------------------------------------------------------------------
# geometry primitives, collected per part as (layer, kind, args)
# ---------------------------------------------------------------------------

class Part:
    def __init__(self, name):
        self.name = name
        self.ents = []
        self.reliefs = []       # corner reliefs; they straddle a bend on purpose

    def line(self, x1, y1, x2, y2, layer="CUT"):
        self.ents.append((layer, "LINE", (x1, y1, x2, y2)))

    def circle(self, cx, cy, d, layer="CUT"):
        self.ents.append((layer, "CIRCLE", (cx, cy, d / 2.0)))

    def arc(self, cx, cy, r, a0, a1, layer="CUT"):
        self.ents.append((layer, "ARC", (cx, cy, r, a0, a1)))

    def rect(self, x, y, w, h, layer="CUT"):
        self.line(x, y, x + w, y, layer)
        self.line(x + w, y, x + w, y + h, layer)
        self.line(x + w, y + h, x, y + h, layer)
        self.line(x, y + h, x, y, layer)

    def rect_centred(self, cx, cy, w, h, layer="CUT"):
        self.rect(cx - w / 2.0, cy - h / 2.0, w, h, layer)

    def text(self, x, y, s, h=4.0, layer="ETCH"):
        self.ents.append((layer, "TEXT", (x, y, h, s)))

    def extents(self):
        xs, ys = [], []
        for _, kind, a in self.ents:
            if kind == "LINE":
                xs += [a[0], a[2]]; ys += [a[1], a[3]]
            elif kind == "CIRCLE":
                xs += [a[0] - a[2], a[0] + a[2]]; ys += [a[1] - a[2], a[1] + a[2]]
            elif kind == "ARC":
                xs += [a[0] - a[2], a[0] + a[2]]; ys += [a[1] - a[2], a[1] + a[2]]
        return min(xs), min(ys), max(xs), max(ys)


# ---------------------------------------------------------------------------
# the pan: floor + four walls from one blank
# ---------------------------------------------------------------------------

def pan(name, li, wi, h, tabs=True):
    """A pan folded up from a flat blank.

    Returns (part, frame) where frame carries the bend-line positions and a
    helper that maps wall-local (u, v) coordinates into the flat.
    """
    p = Part(name)
    lo, wo, ho = li + 2 * T, wi + 2 * T, h + T
    bx1 = ho - BD / 2.0
    bx2 = bx1 + (lo - BD)
    by1 = ho - BD / 2.0
    by2 = by1 + (wo - BD)
    fl, fw = bx2 + bx1, by2 + by1

    tab = TAB_LEN if tabs else 0.0

    def corner(sx, sy, xin, yin, xout, yout):
        """One corner of the blank.

        (xin, yin) is where the two bend lines cross; (xout, yout) is the
        outer corner of the blank.  sx and sy are the direction from inner to
        outer, +-1 each.  The tab hangs off the end wall (the one that folds
        about x = xin) and laps inside the front or rear wall.

        Walking the retained edge, for the front-left corner as an example:
            (xout, yin) -> (t_a, yin)     leaves the end wall
            (t_a, yin)  -> (t_a, t_far)   down the tab's free edge
            (t_a, t_far)-> (xin, t_far)   along the tab's end
            (xin, t_far)-> (xin, yout)    separates tab from the front wall
        """
        if not tabs:
            p.line(xout, yin, xin, yin)
            p.line(xin, yin, xin, yout)
            p.circle(xin, yin, 2 * RELIEF)
            p.reliefs.append((xin, yin))
            return

        t_far = yin + sy * tab              # the tab's free edge
        t_a = xout - sx * TAB_INSET         # inset from the wall's top edge

        p.line(xout, yin, t_a, yin)
        p.line(t_a, yin, t_a, t_far)
        p.line(t_a, t_far, xin, t_far)
        p.line(xin, t_far, xin, yout)

        # the tab folds about the same line the front/rear wall folds about
        p.line(t_a, yin, xin, yin, "BEND")

        # relief where the two bends meet - without it the corner tears
        p.circle(xin, yin, 2 * RELIEF)
        p.reliefs.append((xin, yin))

        # tab holes.  Drill the mating holes through the wall at assembly,
        # with the corner clamped square - that way a bend deduction that
        # differs from ours cannot put them out of line.
        for frac in (0.25, 0.75):
            hx = t_a + (xin - t_a) * frac
            p.circle(hx, yin + sy * tab / 2.0, TAB_HOLE_DIA)

    # --- blank outline: four wall edges, four corners ----------------------
    p.line(bx1, 0, bx2, 0)        # front wall outer edge
    p.line(bx1, fw, bx2, fw)      # rear wall outer edge
    p.line(0, by1, 0, by2)        # left wall outer edge
    p.line(fl, by1, fl, by2)      # right wall outer edge

    corner(-1, -1, bx1, by1, 0.0, 0.0)     # front-left
    corner(+1, -1, bx2, by1, fl, 0.0)      # front-right
    corner(-1, +1, bx1, by2, 0.0, fw)      # rear-left
    corner(+1, +1, bx2, by2, fl, fw)       # rear-right

    # --- bend lines --------------------------------------------------------
    p.line(bx1, by1, bx1, by2, "BEND")
    p.line(bx2, by1, bx2, by2, "BEND")
    p.line(bx1, by1, bx2, by1, "BEND")
    p.line(bx1, by2, bx2, by2, "BEND")

    frame = {
        "bx1": bx1, "bx2": bx2, "by1": by1, "by2": by2,
        "fl": fl, "fw": fw, "lo": lo, "wo": wo, "ho": ho,
        "li": li, "wi": wi, "h": h,
    }

    def wall(which, u, v):
        """Map wall-local (u, v) to flat coordinates.

        u runs along the wall from its left end as you face it from outside;
        v is height above the interior floor.
        """
        if which == "front":
            return (bx1 + u, by1 - (v + T) + BD / 2.0)
        if which == "rear":
            return (bx2 - u, by2 + (v + T) - BD / 2.0)
        if which == "left":
            return (bx1 - (v + T) + BD / 2.0, by1 + u)
        if which == "right":
            return (bx2 + (v + T) - BD / 2.0, by2 - u)
        raise ValueError(which)

    frame["wall"] = wall
    return p, frame


# ---------------------------------------------------------------------------
# the parts
# ---------------------------------------------------------------------------

def build_base():
    p, f = pan("base", LI, WI, HI, tabs=True)
    w = f["wall"]

    # --- front wall: the machine ports ------------------------------------
    for u, dia, label in FRONT_PORTS:
        x, y = w("front", u, PORT_V)
        p.circle(x, y, dia)
        tx, ty = w("front", u, PORT_V + dia / 2.0 + 6.0)
        p.text(tx - 4, ty, label, 4.0)

    x, y = w("front", USB_U, PORT_V)
    p.rect_centred(x, y, USB_W, USB_H)
    for s in (-1, 1):
        sx, sy = w("front", USB_U + s * USB_SCREW_PITCH / 2.0, PORT_V)
        p.circle(sx, sy, USB_SCREW_DIA)

    # --- left end wall: mains inlet ---------------------------------------
    x, y = w("left", IEC_U, PORT_V)
    p.rect_centred(x, y, IEC_H, IEC_W)      # rotated: u runs along +y here
    p.text(*w("left", IEC_U - 10, PORT_V + 30), "MAINS", 4.0)

    # --- right end wall: fan ----------------------------------------------
    x, y = w("right", FAN_U, PORT_V)
    p.circle(x, y, FAN_HOLE_DIA)
    for du in (-1, 1):
        for dv in (-1, 1):
            fx, fy = w("right", FAN_U + du * FAN_SCREW_PITCH / 2.0,
                       PORT_V + dv * FAN_SCREW_PITCH / 2.0)
            p.circle(fx, fy, FAN_SCREW_DIA)

    # --- rear wall: vent field over the PSU -------------------------------
    # the rear wall runs the length of the box, not its depth
    n_u = int((LI - 2 * VENT_MARGIN) // VENT_PITCH) + 1
    n_v = int((HI - 2 * VENT_MARGIN) // VENT_PITCH) + 1
    u0 = (LI - (n_u - 1) * VENT_PITCH) / 2.0
    v0 = (HI - (n_v - 1) * VENT_PITCH) / 2.0
    vents = 0
    for i in range(n_u):
        for j in range(n_v):
            u = u0 + i * VENT_PITCH + (VENT_PITCH / 2.0 if j % 2 else 0.0)
            if u > LI - VENT_MARGIN / 2.0:
                continue
            x, y = w("rear", u, v0 + j * VENT_PITCH)
            p.circle(x, y, VENT_DIA)
            vents += 1

    # --- lid fixings: clearance holes for self-clinch nuts in the walls ----
    lid_pts = _lid_screw_positions()
    for which, u in lid_pts:
        x, y = w(which, u, HI - LID_SCREW_V)
        p.circle(x, y, LID_SCREW_DIA)

    # --- floor: the grid, the earth stud, the feet -------------------------
    grid = 0
    x = f["bx1"] + GRID_MARGIN
    while x <= f["bx2"] - GRID_MARGIN + 1e-6:
        y = f["by1"] + GRID_MARGIN
        while y <= f["by2"] - GRID_MARGIN + 1e-6:
            p.circle(x, y, GRID_DIA)
            grid += 1
            y += GRID_PITCH
        x += GRID_PITCH

    p.circle(f["bx1"] + 32.5, f["by1"] + WI - 57.5, EARTH_STUD_DIA)
    p.text(f["bx1"] + 40, f["by1"] + WI - 59, "PE", 4.0)

    for dx in (FOOT_INSET, LI - FOOT_INSET):
        for dy in (FOOT_INSET, WI - FOOT_INSET):
            p.circle(f["bx1"] + dx, f["by1"] + dy, FOOT_DIA)

    return p, f, {"grid": grid, "vents": vents}


def _lid_screw_positions():
    out = []
    for i in range(LID_SCREWS_LONG):
        u = LI * (i + 1) / (LID_SCREWS_LONG + 1)
        out.append(("front", u))
        out.append(("rear", u))
    for i in range(LID_SCREWS_END):
        u = WI * (i + 1) / (LID_SCREWS_END + 1)
        out.append(("left", u))
        out.append(("right", u))
    return out


def build_lid():
    # the lid's interior must clear the base's exterior
    li = LI + 2 * T + 2 * LID_GAP
    wi = WI + 2 * T + 2 * LID_GAP
    # open butt corners: a tab would foul the base wall inside the skirt
    p, f = pan("lid", li, wi, LID_SKIRT, tabs=False)
    w = f["wall"]
    for which, u in _lid_screw_positions():
        # lid u is measured on the lid's own wall, which is longer than the
        # base's by the clearance; centre the run so the screws still line up
        span = li if which in ("front", "rear") else wi
        base_span = LI if which in ("front", "rear") else WI
        x, y = w(which, u + (span - base_span) / 2.0, LID_SCREW_V)
        p.circle(x, y, LID_SCREW_DIA)
    return p, f


def build_adapters():
    """Flat plates that bridge an awkward hole pattern onto the base grid.

    The Uno's four holes are not on any grid, so it gets a plate.  A blank
    plate is included for whatever the PSU turns out to need.
    """
    p = Part("adapters")
    ox = 0.0

    # --- Uno plate ---------------------------------------------------------
    bw, bh = BOARD
    pw = bw + 2 * ADAPTER_PAD
    ph = bh + 2 * ADAPTER_PAD
    p.rect(ox, 0, pw, ph)
    for hx, hy in UNO_HOLES:
        p.circle(ox + ADAPTER_PAD + hx, ADAPTER_PAD + hy, UNO_HOLE_DIA)
    # four grid holes on a whole number of pitches, centred on the plate
    gw = GRID_PITCH * max(1, int((pw - 12.0) // GRID_PITCH))
    gh = GRID_PITCH * max(1, int((ph - 12.0) // GRID_PITCH))
    for dx in (-gw / 2.0, gw / 2.0):
        for dy in (-gh / 2.0, gh / 2.0):
            p.circle(ox + pw / 2.0 + dx, ph / 2.0 + dy, GRID_DIA)
    p.text(ox + 4, ph + 5, "UNO ADAPTER - VERIFY HOLES", 4.0)
    ox += pw + 20

    # --- blank plate -------------------------------------------------------
    bwid, bhei = 140.0, 110.0
    p.rect(ox, 0, bwid, bhei)
    i = GRID_PITCH
    while i < bwid:
        j = GRID_PITCH
        while j < bhei:
            p.circle(ox + i, j, GRID_DIA)
            j += GRID_PITCH
        i += GRID_PITCH
    p.text(ox + 4, bhei + 5, "BLANK - DRILL TO SUIT", 4.0)

    return p



# ---------------------------------------------------------------------------
# self-check: run after every edit to CONFIG
# ---------------------------------------------------------------------------

MIN_WEB = 1.5           # metal left between two holes, mm
MIN_BEND_CLEAR = 3.0    # hole edge to bend line, mm


def _seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    l2 = dx * dx + dy * dy
    t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / l2))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def check(part):
    """Holes too close to each other, or sitting in a bend zone.

    A hole in a bend zone deforms when the wall folds; two holes with less
    than MIN_WEB between them leave a web that tears.  Corner reliefs are
    exempt - straddling the bend is their whole job.
    """
    warn = []
    cut = [a for l, k, a in part.ents if k == "CIRCLE" and l == "CUT"]
    bends = [a for l, k, a in part.ents if k == "LINE" and l == "BEND"]
    exempt = set((round(x, 3), round(y, 3)) for x, y in part.reliefs)

    for i in range(len(cut)):
        for j in range(i + 1, len(cut)):
            a, b = cut[i], cut[j]
            gap = math.hypot(a[0] - b[0], a[1] - b[1]) - a[2] - b[2]
            if gap < MIN_WEB:
                warn.append("%s: %.2f mm web between holes at (%.1f, %.1f) "
                            "and (%.1f, %.1f)"
                            % (part.name, gap, a[0], a[1], b[0], b[1]))
    for c in cut:
        if (round(c[0], 3), round(c[1], 3)) in exempt:
            continue
        for bl in bends:
            g = _seg_dist(c[0], c[1], *bl) - c[2]
            if g < MIN_BEND_CLEAR:
                warn.append("%s: hole at (%.1f, %.1f) is %.2f mm from a bend"
                            % (part.name, c[0], c[1], g))
                break
    return warn


# ---------------------------------------------------------------------------
# writers
# ---------------------------------------------------------------------------

LAYER_COLOUR = {"CUT": 7, "BEND": 5, "ETCH": 3}


def write_dxf(part, path):
    o = []
    def g(code, val):
        o.append(str(code)); o.append(str(val))

    g(0, "SECTION"); g(2, "TABLES")
    g(0, "TABLE"); g(2, "LAYER"); g(70, len(LAYER_COLOUR))
    for name, colour in LAYER_COLOUR.items():
        g(0, "LAYER"); g(2, name); g(70, 0); g(62, colour); g(6, "CONTINUOUS")
    g(0, "ENDTAB"); g(0, "ENDSEC")

    g(0, "SECTION"); g(2, "ENTITIES")
    for layer, kind, a in part.ents:
        if kind == "LINE":
            g(0, "LINE"); g(8, layer)
            g(10, a[0]); g(20, a[1]); g(30, 0.0)
            g(11, a[2]); g(21, a[3]); g(31, 0.0)
        elif kind == "CIRCLE":
            g(0, "CIRCLE"); g(8, layer)
            g(10, a[0]); g(20, a[1]); g(30, 0.0); g(40, a[2])
        elif kind == "ARC":
            g(0, "ARC"); g(8, layer)
            g(10, a[0]); g(20, a[1]); g(30, 0.0); g(40, a[2])
            g(50, a[3]); g(51, a[4])
        elif kind == "TEXT":
            g(0, "TEXT"); g(8, layer)
            g(10, a[0]); g(20, a[1]); g(30, 0.0); g(40, a[2]); g(1, a[3])
    g(0, "ENDSEC"); g(0, "EOF")

    with open(path, "w") as fh:
        fh.write("\n".join(o) + "\n")


SVG_STYLE = {"CUT": "#111", "BEND": "#39f", "ETCH": "#c33"}


def write_svg(part, path, pad=10.0):
    x0, y0, x1, y1 = part.extents()
    w, h = (x1 - x0) + 2 * pad, (y1 - y0) + 2 * pad
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%.1fmm" '
           'height="%.1fmm" viewBox="0 0 %.2f %.2f">' % (w, h, w, h),
           '<g transform="translate(%.3f,%.3f) scale(1,-1)">'
           % (pad - x0, h - pad + y0)]
    for layer, kind, a in part.ents:
        c = SVG_STYLE.get(layer, "#111")
        dash = ' stroke-dasharray="4 3"' if layer == "BEND" else ""
        if kind == "LINE":
            out.append('<line x1="%.3f" y1="%.3f" x2="%.3f" y2="%.3f" '
                       'stroke="%s" stroke-width="0.4" fill="none"%s/>'
                       % (a[0], a[1], a[2], a[3], c, dash))
        elif kind == "CIRCLE":
            out.append('<circle cx="%.3f" cy="%.3f" r="%.3f" stroke="%s" '
                       'stroke-width="0.4" fill="none"/>' % (a[0], a[1], a[2], c))
        elif kind == "ARC":
            a0, a1_ = math.radians(a[3]), math.radians(a[4])
            sx, sy = a[0] + a[2] * math.cos(a0), a[1] + a[2] * math.sin(a0)
            ex, ey = a[0] + a[2] * math.cos(a1_), a[1] + a[2] * math.sin(a1_)
            large = 1 if (a[4] - a[3]) % 360 > 180 else 0
            out.append('<path d="M %.3f %.3f A %.3f %.3f 0 %d 1 %.3f %.3f" '
                       'stroke="%s" stroke-width="0.4" fill="none"/>'
                       % (sx, sy, a[2], a[2], large, ex, ey, c))
        elif kind == "TEXT":
            out.append('<g transform="translate(%.3f,%.3f) scale(1,-1)">'
                       '<text x="0" y="0" font-size="%.2f" fill="%s" '
                       'font-family="monospace">%s</text></g>'
                       % (a[0], a[1], a[2], c, a[3]))
    out += ["</g>", "</svg>"]
    with open(path, "w") as fh:
        fh.write("\n".join(out) + "\n")


# ---------------------------------------------------------------------------

def report(fbase, flid, counts):
    lo, wo = LI + 2 * T, WI + 2 * T
    print("Control box flat patterns")
    print("=" * 58)
    print("sheet          %.1f mm, inner bend radius %.1f, K %.2f" % (T, R_BEND, K))
    print("bend deduction %.3f mm per 90 deg bend  <- SHOP'S NUMBER WINS" % BD)
    print()
    print("folded, interior   %.0f x %.0f x %.0f mm" % (LI, WI, HI))
    print("folded, exterior   %.1f x %.1f x %.1f mm" % (lo, wo, HI + T))
    print("base blank         %.2f x %.2f mm" % (fbase["fl"], fbase["fw"]))
    print("lid blank          %.2f x %.2f mm" % (flid["fl"], flid["fw"]))
    print()
    print("base grid          %d holes, dia %.1f on %.0f mm pitch"
          % (counts["grid"], GRID_DIA, GRID_PITCH))
    print("rear vents         %d holes, dia %.1f  (%.0f mm2 free area)"
          % (counts["vents"], VENT_DIA,
             counts["vents"] * math.pi * (VENT_DIA / 2) ** 2))
    print()
    print("fits, with clearance to the walls:")
    print("  PSU   %.0f x %.0f x %.0f" % PSU + "   MEASURE - read the label")
    print("  board %.1f x %.1f, stack %.0f high   MEASURE the stack" % (BOARD + (BOARD_STACK_H,)))
    print("  DIN   %.0f mm run" % DIN_RUN)
    used = PSU[0] + DIN_RUN
    print("  length used %.0f of %.0f mm along the back" % (used, LI))
    print("  depth  used %.0f of %.0f mm (PSU + board, front to back)"
          % (PSU[1] + BOARD[1], WI))
    print()
    print("MEASURE before cutting: PSU envelope, the Uno's four hole")
    print("positions, and the IEC and USB panel cutouts for the exact")
    print("parts you bought.  The base grid means being wrong costs an")
    print("adapter plate, not a box.")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="enclosure", help="output directory")
    ap.add_argument("--report", action="store_true", help="print numbers only")
    args = ap.parse_args()

    base, fbase, counts = build_base()
    lid, flid = build_lid()
    adapters = build_adapters()

    report(fbase, flid, counts)

    warn = []
    for part in (base, lid, adapters):
        warn += check(part)
    print()
    if warn:
        print("CHECK FAILED - %d issue(s):" % len(warn))
        for w in warn:
            print("  " + w)
    else:
        print("check: no hole clashes, nothing sitting in a bend zone.")

    if args.report:
        return 0

    os.makedirs(args.out, exist_ok=True)
    for part in (base, lid, adapters):
        write_dxf(part, os.path.join(args.out, part.name + ".dxf"))
        write_svg(part, os.path.join(args.out, part.name + ".svg"))
    print()
    print("wrote %s/{base,lid,adapters}.{dxf,svg}" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
