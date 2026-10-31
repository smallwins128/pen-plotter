"""Fume extractor: three printed parts that stack front to back around an 80 mm fan (Allwin, 2026-10-31).

v2: the stack screws run through the fan's own corner holes (71.5 square), so the body only wraps the fan (90 wide).
v3: one set of screws from the front, into heat-set inserts at the back; magnets on the screw heads hold the face.
v4 (Allwin): the spacer goes, the jack and switch move into the fan layer's chin, and the fan, rear filter and back
grille are one print. Only M3 x 50 countersunk are on hand, so the inserts sit where 50 mm screws reach them.

    P1 face    grille, flush and screwless; a lip in the pad pocket + 4 magnets that snap onto 4 magnets in P2
    P2 filter  front carbon pad on a rib grid, 3.5 mm plenum behind it; the 6 screw heads, hidden under P1
               (the 4 fan screws sit 2.1 deep with a magnet on each)
    grilles    v5: the face and the body's back have one plain Ø74 hole each; the grille is a swappable insert (a plate in the
               pocket behind the hole, a boss that fills the hole flush). The stack pins it: no glue, no clips.
    v6 (Allwin): the body is a base: back panel, the rear pad between solid corner tabs that stop at the top of the
               pad, then just the outer wall round the fan, which sits on the tab tops. The 2 chin screws get short
               tabs too, and 2 printed spacer tubes span the fan zone. Solid corners also end the stray voids.
    v7 (Allwin): the jack and switch move to the back panel (the switch body runs 15 mm into the chin); the sides
               carry 2 x M5 heat-set inserts each, for mounting (2020 / 2040 T-nuts are M5).
    v8 (Allwin): the chin tabs run the full height of the base (no spacers; the 2 chin inserts sit in its front
               face). The face holds by its lip and 3 magnet pairs in the chin: bottom centre and one low on each
               side. The 4 front screws sit flush.
    P3 body    rear pad zone, fan zone and back panel in one; DC jack + switch in the chin; 2 x M3 inserts on top
               for a 5-hole Meccano strip handle; 6 M3 inserts: 4 on bosses under the fan corners, 2 at the chin face

Air: grille -> front pad -> plenum -> fan -> rear pad -> grille. Layers are walls with a hollow where there is room,
closed by the two grille plates. The chin under the fan carries the wiring.

Frame: x across the face, y up (0 = bench), z into the body (0 = front face). Each layer is modelled at its own z = 0
(its front face) and exported in its print orientation.

    python3 hardware/parts/fume/fume.py        # checks only, in seconds
    python3 hardware/parts/fume/fume.py --stl  # full build: hardware/out/fume/*.stl (about 10 min: the two grilles)
"""
import json
import math
import pathlib
import sys

from build123d import Box, Cone, Cylinder, Pos, Rot, export_stl
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from window_inserts import slab  # noqa: E402

OUT = HERE.parent.parent / "out" / "fume"

# --- body (the reference sketch: portrait, fan high, a chin below) ---
W, R = 90.0, 8.0                      # width and corner radius (R 8 keeps 2.4 of wall at the fan's square corners)
WALL, INNER = 2.4, 1.6                # outer wall, wall around each layer's air opening
CY = 80.0                             # fan centre height: chin below, as in the sketch

# --- bought parts (unverified until measured: see NEED below) ---
FAN, FAN_T, FAN_GAP = 80.0, 25.0, 0.2           # 80 x 80 x 25, same as the enclosure fans (71.5 hole square measured)
FAN_HOLE = 71.5
PAD, PAD_T, PAD_CLIP = 80.0, 10.0, 16.0         # pad cut 80 square, 16 snipped off each corner; pocket 10 (pad 9 measured)
JACK_D, SWITCH_D = 12.0, 6.0                    # panel DC jack and switch holes (Allwin, 2026-10-31); fan is 12 V
MECCANO = 12.7                                  # Meccano hole pitch
HANDLE_PITCH = 4 * MECCANO                      # 5-hole strip: its end holes, three holes between them (2026-10-31)
TOP_INSERT_BORE, TOP_INSERT_DEPTH = 4.2, 4.5    # handle: M3 inserts too (only M3 in this build), M3 standoffs
TOP_WALL = TOP_INSERT_DEPTH + 1.5               # above the fan pocket: the insert plus a floor
H = CY + FAN / 2 + FAN_GAP + TOP_WALL           # 126.2
MAGNET_D, MAGNET_T = 6.0, 2.0                   # 4 discs in the face pull on the steel L5 screw heads

# --- fit (from fit_kit.py where tested) ---
M3_CLEAR, INSERT_BORE, INSERT_DEPTH = 3.4, 4.2, 4.5   # M3 heat-set inserts are 4 long (measured)
CSK_D = 6.4
BOSS_R = 4.0
LIP_H, LIP_W, LIP_GAP = 3.0, 1.6, 0.15          # face-plate lip into the front pad pocket
OPENING_D = 74.0                                # the hole in the face and in the back panel
INSERT_BOSS_D = OPENING_D - 0.2                 # grille insert boss: snug in the hole, flush with the outside
INSERT_PLATE_F, INSERT_PLATE_B = 1.6, 1.0       # insert plate behind the face (in the lip) / behind the back (under the pad)
MAGNETS = True

# --- layer depths ---
T6 = 3.0                       # face: magnet pockets 2.1 deep leave 0.9 of face
PLENUM = 3.5                   # P2: rib grid that carries the pad, and the air gap in front of the fan
T5 = LIP_H + PAD_T + PLENUM    # the face lip fills the front 3 mm of the pocket
FT = FAN_T + FAN_GAP           # P3: fan pocket depth
GRILLE_T = 2.4                 # back grille: 1.2 skin + 1.2 ribs
T3 = FT + PAD_T + GRILLE_T     # P3: fan pocket, rear pad pocket, grille
SCREW_L = 50.0                 # the only M3 countersunk length on hand
SWITCH_BODY = 15.0             # the switch runs this far into the chin behind the back panel (Allwin)
MOUNT_BORE, MOUNT_DEPTH = 6.4, 8.0             # M5 heat-set inserts in the sides (unmeasured: typical OD 7, length 8)
MOUNT_Y, MOUNT_ZS = 26.0, (9.0, 27.0)          # 2 per side in the chin, a row front to back, 18 apart
LAYERS = [("P1_face", T6), ("P2_filter", T5), ("P3_body", T3)]

# --- fixings ---
FAN_SCREWS = [(sx * FAN_HOLE / 2, CY + sy * FAN_HOLE / 2) for sx in (-1, 1) for sy in (-1, 1)]
CHIN_SCREWS = [(-36.0, 9.0), (36.0, 9.0)]
SCREWS = FAN_SCREWS + CHIN_SCREWS
MAGNET_XY = [(0.0, 5.0), (-40.0, 28.0), (40.0, 28.0)]   # face <-> filter: bottom centre, one low on each side
MAG_BLOCK = 4.6                                 # solid block round each magnet in the filter part's chin
JACK_XY, SWITCH_XY = (-14.0, 22.0), (14.0, 22.0)   # in the back panel's chin, seen from the front


def rrect(w, h, r, cx=0.0, cy=0.0):
    return box(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2).buffer(-r, join_style=1).buffer(r, join_style=1) \
        if r > 0 else box(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


OUTLINE = rrect(W, H, R, 0, H / 2)
FAN_POCKET = box(-(FAN / 2 + FAN_GAP), CY - (FAN / 2 + FAN_GAP), FAN / 2 + FAN_GAP, CY + FAN / 2 + FAN_GAP)


def pad_poly(size, clip):
    h = size / 2
    return Polygon([(-h + clip, -h), (h - clip, -h), (h, -h + clip), (h, h - clip), (h - clip, h), (-h + clip, h),
                    (-h, h - clip), (-h, -h + clip)])


PAD_POCKET = pad_poly(PAD + 1.0, PAD_CLIP).buffer(0)
PAD_POCKET = Polygon([(x, y + CY) for x, y in PAD_POCKET.exterior.coords])


def bosses(r=BOSS_R, extra=()):
    return unary_union([Point(x, y).buffer(r, quad_segs=16) for x, y in list(SCREWS) + list(extra)])


def opening():
    return Point(0, CY).buffer(OPENING_D / 2, quad_segs=64)


# --- grille patterns, in the insert's own frame (centre 0, 0) ---------------------------------------------------------

def _region():
    return Point(0, 0).buffer(INSERT_BOSS_D / 2 - 0.8, quad_segs=64)


def pat_hslots(w=1.8, pitch=3.4):
    reg, out = _region(), []
    n = int(OPENING_D / pitch) + 2
    for k in range(-n, n + 1):
        seg = LineString([(-60, k * pitch), (60, k * pitch)]).intersection(reg.buffer(-w / 2))
        if not seg.is_empty and seg.length > 2:
            out.append(seg.buffer(w / 2, cap_style=1, quad_segs=8))
    return unary_union(out)


def pat_rings(w=2.0, pitch=4.0, spoke=2.0):
    c, out, r = Point(0, 0), [], 2.0 + w / 2
    while r + w / 2 <= INSERT_BOSS_D / 2 - 0.8:
        out.append(c.buffer(r + w / 2, quad_segs=64).difference(c.buffer(r - w / 2, quad_segs=64)))
        r += pitch
    from shapely import affinity
    sp = unary_union([affinity.rotate(box(-spoke / 2, 0, spoke / 2, 40), a, origin=(0, 0)) for a in (45, 135, 225, 315)])
    return unary_union(out).difference(sp)


def pat_hex(af=6.0, wall=1.2):
    reg, out = _region(), []
    p, r = af + wall, af / math.sqrt(3)
    n = int(OPENING_D / p) + 2
    for j in range(-n, n + 1):
        for i in range(-n, n + 1):
            x, y = (i + (j % 2) * 0.5) * p, j * p * math.sqrt(3) / 2
            h = Polygon([(x + r * math.cos(math.radians(30 + 60 * k)), y + r * math.sin(math.radians(30 + 60 * k)))
                         for k in range(6)])
            if reg.contains(h):
                out.append(h)
    return unary_union(out)


def pat_holes(d=3.0, pitch=3.8):
    reg, out = _region().buffer(-d / 2), []
    dy = pitch * math.sqrt(3) / 2
    n = int(OPENING_D / dy) + 2
    for j in range(-n, n + 1):
        for i in range(-n, n + 1):
            x, y = (i + (j % 2) * 0.5) * pitch, j * dy
            if reg.contains(Point(x, y)):
                out.append(Point(x, y).buffer(d / 2, quad_segs=4))
    return unary_union(out)


PATTERNS = dict(hslots=pat_hslots, rings=pat_rings, hex=pat_hex, holes=pat_holes)


def insert_plate(side):
    """The plate follows the pocket it sits in (front: inside the face lip; back: the rear pad pocket), less 0.2: the
    octagon keeps slots from turning."""
    from shapely import affinity
    shape = (PAD_POCKET.buffer(-LIP_GAP, join_style=2).buffer(-LIP_W, join_style=2) if side == "front"
             else PAD_POCKET).buffer(-0.2, join_style=2)
    return affinity.translate(shape, 0, -CY)


def grille_insert(pattern, side):
    """Boss (z 0..boss, outside face first) + plate. Prints boss down; the slot spine in the plate layer bridges 1.8."""
    boss_l, plate_t = (T6, INSERT_PLATE_F) if side == "front" else (GRILLE_T, INSERT_PLATE_B)
    holes = PATTERNS[pattern]()
    plate = insert_plate(side).difference(holes)
    if pattern == "hslots":                                    # hidden spine: stiffens the long bars
        plate = plate.union(box(-0.6, -OPENING_D / 2, 0.6, OPENING_D / 2).intersection(insert_plate(side)))
    boss = Point(0, 0).buffer(INSERT_BOSS_D / 2, quad_segs=64).difference(holes)
    return slab(boss, 0, boss_l) + slab(plate, boss_l - 0.01, boss_l + plate_t), holes


def csk(part, x, y, face_z, depth_dir):
    """Ø3.4 through the layer + 90 deg countersink opening on the face at face_z (depth_dir +1: into +z)."""
    h = (CSK_D - M3_CLEAR) / 2
    zc = face_z + depth_dir * h / 2
    big, small = (CSK_D / 2 + 0.01, M3_CLEAR / 2) if depth_dir > 0 else (M3_CLEAR / 2, CSK_D / 2 + 0.01)
    return part - Pos(x, y, zc) * Cone(big, small, h + 0.02)


def through(part, x, y, t, d=M3_CLEAR):
    return part - Pos(x, y, t / 2) * Cylinder(d / 2, t + 2)


def teardrop(axis, x, y, z, d, length, up):
    """Horizontal hole that prints without support: circle plus a 45 deg point toward `up` (+1/-1 along z)."""
    r = d / 2       # the point: a square of side r turned 45 deg, centred r/sqrt(2) off the axis, corner at r*sqrt(2)
    if axis == "x":
        cyl, tip = Rot(0, 90, 0) * Cylinder(r, length), Rot(45, 0, 0) * Box(length, r, r)
    else:
        cyl, tip = Rot(90, 0, 0) * Cylinder(r, length), Rot(0, 45, 0) * Box(r, length, r)
    return Pos(x, y, z) * cyl + Pos(x, y, z + up * r / math.sqrt(2)) * tip


# --- the layers -------------------------------------------------------------------------------------------------------

def ribbed_plate(holes, total, skin, skin_front, extra=None):
    """A grille plate: a thin skin over the whole outline, ribs behind it only where needed (rim, grille disc, bosses,
    a 14 mm grid), so the flat face stays flat and the plate stays light. skin_front: the skin is at z = 0."""
    cut = unary_union(holes)
    g, pitch = [], 14.0
    for k in range(-8, 9):
        g.append(box(k * pitch - 0.6, 0, k * pitch + 0.6, H))
        g.append(box(-W / 2, CY + k * pitch - 0.6, W / 2, CY + k * pitch + 0.6))
    ribs = unary_union([OUTLINE.difference(OUTLINE.buffer(-WALL, join_style=2)),
                        Point(0, CY).buffer(OPENING_D / 2 + 2.0, quad_segs=64), bosses(BOSS_R + 1.0)] + g
                       + ([extra] if extra is not None else []))
    ribs = ribs.intersection(OUTLINE).difference(cut)
    s0, s1 = (0, skin) if skin_front else (total - skin, total)
    r0, r1 = (skin - 0.01, total) if skin_front else (0, total - skin + 0.01)
    return slab(OUTLINE.difference(cut), s0, s1) + slab(ribs, r0, r1)


def p1_face():
    holes = [opening()]
    mags = unary_union([Point(x, y).buffer(5.0) for x, y in MAGNET_XY]) if MAGNETS else None
    p = ribbed_plate(holes, T6, 1.6, True, mags)
    lip_cut = unary_union([Point(x, y).buffer(BOSS_R + 0.3) for x, y in FAN_SCREWS])
    lip_out = PAD_POCKET.buffer(-LIP_GAP, join_style=2)
    p += slab(lip_out.difference(lip_out.buffer(-LIP_W, join_style=2)).difference(lip_cut), T6 - 0.01, T6 + LIP_H)
    if MAGNETS:
        for x, y in MAGNET_XY:
            p -= Pos(x, y, T6 - (MAGNET_T + 0.1) / 2 + 0.01) * Cylinder(MAGNET_D / 2 + 0.05, MAGNET_T + 0.1)
    return p


CHIN_BLOCK = 15.0                                   # chin tabs: corner blocks round the 2 chin screws


def chin_blocks():
    return unary_union([box(sx * (abs(x) - 5.5), 0, sx * W / 2, CHIN_BLOCK) if sx > 0 else
                        box(-W / 2, 0, -(abs(x) - 5.5), CHIN_BLOCK) for (x, _), sx in zip(CHIN_SCREWS, (-1, 1))])


def chin_cavity():
    """The hollow chin under the pad: inside the outer wall, under a 1.6 rib that carries the pad's bottom edge."""
    top = PAD_POCKET.bounds[1] - INNER
    return OUTLINE.buffer(-WALL, join_style=2).intersection(box(-W, -1, W, top)).difference(chin_blocks())


def pad_zone():
    """Section of a pad layer: solid round the pad (the corner tabs are the solid corners), the chin hollow."""
    return OUTLINE.difference(PAD_POCKET).difference(chin_cavity())


def mag_blocks():
    return unary_union([box(x - MAG_BLOCK, y - MAG_BLOCK, x + MAG_BLOCK, y + MAG_BLOCK) for x, y in MAGNET_XY]) \
        .intersection(OUTLINE)


def p2_filter():
    """Front pad pocket with a rib grid behind the pad (the plenum). All 6 screw heads countersunk flush; 3 magnets in
    the front face (chin blocks). Prints back down: the ribs land on the bed, the magnet pockets face up."""
    p = slab(pad_zone().union(mag_blocks()), 0, T5)
    g, pitch, rib = [], 13.0, 1.2
    for k in range(-3, 4):
        g.append(box(k * pitch - rib / 2, 0, k * pitch + rib / 2, H))
        g.append(box(-W / 2, CY + k * pitch - rib / 2, W / 2, CY + k * pitch + rib / 2))
    p += slab(unary_union(g).intersection(PAD_POCKET.buffer(0.5)), LIP_H + PAD_T, T5)
    for x, y in SCREWS:
        p = csk(through(p, x, y, T5), x, y, 0, +1)
    for x, y in MAGNET_XY:
        p -= Pos(x, y, (MAGNET_T + 0.1) / 2 - 0.01) * Cylinder(MAGNET_D / 2 + 0.05, MAGNET_T + 0.1)
    return p


def p3_body():
    """The base. Fan zone (0..FT): the outer wall only, the fan held by its screws and sitting on the tab tops. Rear
    pad zone (FT..FT+PAD_T): solid corner tabs, the chin tabs, inserts in all six tab tops. Then the back panel.
    Prints back down (panel on the bed); "up" in the print is -z here."""
    hx = HANDLE_PITCH / 2
    handle_cols = unary_union([box(sx * hx - TOP_INSERT_BORE / 2 - 2.0, CY + FAN / 2 + FAN_GAP,
                                   sx * hx + TOP_INSERT_BORE / 2 + 2.0, H) for sx in (-1, 1)])
    ring = OUTLINE.difference(OUTLINE.buffer(-WALL, join_style=2)).union(handle_cols.intersection(OUTLINE)) \
        .union(chin_blocks())                                        # chin tabs run the full height
    p = slab(ring, 0, FT)
    p += slab(pad_zone(), FT - 0.01, FT + PAD_T)
    pads = unary_union([Point(*JACK_XY).buffer(JACK_D / 2 + 3), Point(*SWITCH_XY).buffer(SWITCH_D / 2 + 3)])
    p += Pos(0, 0, FT + PAD_T - 0.01) * ribbed_plate([opening()], GRILLE_T, 1.2, False, pads)
    blind = T3 - 1.2                                                 # screw holes stop short of the back face
    for x, y in FAN_SCREWS:                                          # inserts in the four corner tab tops
        p -= Pos(x, y, (FT + blind) / 2) * Cylinder(M3_CLEAR / 2, blind - FT + 0.02)
        p -= Pos(x, y, FT + INSERT_DEPTH / 2 - 0.01) * Cylinder(INSERT_BORE / 2, INSERT_DEPTH)
    for x, y in CHIN_SCREWS:                                         # inserts in the chin tabs' front face
        p -= Pos(x, y, blind / 2) * Cylinder(M3_CLEAR / 2, blind + 0.02)
        p -= Pos(x, y, INSERT_DEPTH / 2 - 0.01) * Cylinder(INSERT_BORE / 2, INSERT_DEPTH)
    for (x, y), d in ((JACK_XY, JACK_D), (SWITCH_XY, SWITCH_D)):     # back panel, in the chin: round holes
        p -= Pos(x, y, (FT + PAD_T + T3) / 2) * Cylinder(d / 2 + 0.1, T3 - FT - PAD_T + 2)
    p += mount_blocks()
    for sx in (-1, 1):                                               # M5 inserts in from the sides
        for z in MOUNT_ZS:
            p -= teardrop("x", sx * (W / 2 - MOUNT_DEPTH / 2 + 0.01), MOUNT_Y, z, MOUNT_BORE, MOUNT_DEPTH, -1)
    zc = FT / 2                                                      # handle: M3 inserts down into the top
    for sx in (-1, 1):
        p -= teardrop("y", sx * hx, H - TOP_INSERT_DEPTH / 2 + 0.01, zc, TOP_INSERT_BORE, TOP_INSERT_DEPTH, -1)
    return p


def mount_block_poly(sx):
    """Side-insert block in the chin, as an x-y section: from the outer wall inward, round the insert row."""
    r = MOUNT_BORE / 2 + 2.5
    x_out, x_in = sx * W / 2, sx * (W / 2 - MOUNT_DEPTH - 1.5)
    return box(min(x_out, x_in), MOUNT_Y - r, max(x_out, x_in), MOUNT_Y + r).intersection(OUTLINE)


def mount_blocks():
    """Solid blocks round the side inserts, run back to the back panel so they print without support."""
    r = MOUNT_BORE / 2 + 2.5
    z0 = min(MOUNT_ZS) - r
    return slab(mount_block_poly(-1), z0, FT + PAD_T) + slab(mount_block_poly(1), z0, FT + PAD_T)


# --- checks -----------------------------------------------------------------------------------------------------------

def checks():
    out = []

    def add(name, value, ok, unit="mm"):
        out.append(dict(check=name, value=round(value, 2), unit=unit, ok=bool(ok)))

    inner = OUTLINE.buffer(-WALL + 0.01, join_style=2)
    for i, (x, y) in enumerate(SCREWS):
        c = Point(x, y)
        d = OUTLINE.exterior.distance(c) - INSERT_BORE / 2
        add(f"screw {i + 1}: insert bore to outside", d, d >= 1.5)
        d = PAD_POCKET.distance(c) - INSERT_BORE / 2
        add(f"screw {i + 1}: bore to pad pocket", d, d >= 1.5)
    for i, (x, y) in enumerate(FAN_SCREWS):
        d = pad_zone().boundary.distance(Point(x, y)) - INSERT_BORE / 2
        add(f"fan screw {i + 1}: insert bore inside its corner tab", d, pad_zone().contains(Point(x, y)) and d >= 1.2)
    for i, (x, y) in enumerate(CHIN_SCREWS):
        d = chin_blocks().boundary.distance(Point(x, y)) - INSERT_BORE / 2
        add(f"chin screw {i + 1}: insert inside its full-height tab", d, chin_blocks().contains(Point(x, y)) and d >= 1.2)
    for x, y in MAGNET_XY:
        c = Point(x, y).buffer(MAGNET_D / 2 + 0.05)
        d = OUTLINE.exterior.distance(c)
        add(f"magnet ({x:.0f}, {y:.0f}): wall to the outside", d, d >= 1.2)
        d = mag_blocks().boundary.distance(Point(x, y)) - MAGNET_D / 2
        add(f"magnet ({x:.0f}, {y:.0f}): inside its block", d, d >= 1.2 or OUTLINE.exterior.distance(c) < 4)
        d = min(Point(sx, sy).distance(Point(x, y)) for sx, sy in SCREWS) - MAGNET_D / 2 - CSK_D / 2
        add(f"magnet ({x:.0f}, {y:.0f}): clear of screw heads", d, d >= 1.5)
        add(f"magnet ({x:.0f}, {y:.0f}): below the pad shelf", PAD_POCKET.bounds[1] - INNER - (y + MAG_BLOCK),
            PAD_POCKET.bounds[1] - INNER - (y + MAG_BLOCK) >= 0)
    add("fan fits inside the outer wall", 1.0, inner.contains(FAN_POCKET), "")
    stray = [g for g in (pad_zone().geoms if hasattr(pad_zone(), "geoms") else [pad_zone()])]
    holes = sum(len(g.interiors) for g in stray)
    add("pad layers: no stray voids (pad pocket + chin only)", holes, holes <= 2, "")
    add("pad pocket inside the wall", 1.0, inner.contains(PAD_POCKET), "")
    add("pad still covers the fan disc", PAD_POCKET.distance(Point(0, CY)) * 0 + 1.0,
        PAD_POCKET.buffer(-0.5).contains(opening()), "")
    from shapely import affinity
    for side in ("front", "back"):
        pl = affinity.translate(insert_plate(side), 0, CY)
        ledge = pl.exterior.distance(Point(0, CY)) - OPENING_D / 2
        add(f"{side} insert: plate overlaps the panel round the hole", ledge, ledge >= 1.2)
    lip_in = PAD_POCKET.buffer(-LIP_GAP, join_style=2).buffer(-LIP_W, join_style=2)
    add("front insert plate inside the face lip", 1.0, lip_in.contains(affinity.translate(insert_plate("front"), 0, CY)), "")
    add("front insert plate within the lip height", LIP_H - INSERT_PLATE_F, LIP_H - INSERT_PLATE_F >= 0)
    add("back insert plate + 9 mm pad fill the rear pocket", PAD_T - INSERT_PLATE_B - 9.0, PAD_T - INSERT_PLATE_B - 9.0 >= 0)
    hx = HANDLE_PITCH / 2
    add("top inserts on the flat top", W / 2 - R - (hx + TOP_INSERT_BORE / 2), W / 2 - R - (hx + TOP_INSERT_BORE / 2) >= 2)
    add("floor under the top inserts", TOP_WALL - TOP_INSERT_DEPTH, TOP_WALL - TOP_INSERT_DEPTH >= 1.2)
    chin = chin_cavity()
    for name, (x, y), d in (("jack", JACK_XY, JACK_D), ("switch", SWITCH_XY, SWITCH_D)):
        c = Point(x, y).buffer(d / 2 + 1.5)
        add(f"{name} hole inside the chin, clear of the tabs", chin.boundary.distance(Point(x, y)) - d / 2,
            chin.contains(c))
    gap = Point(*JACK_XY).distance(Point(*SWITCH_XY)) - JACK_D / 2 - SWITCH_D / 2
    add("web between jack and switch holes", gap, gap >= 4)
    add("switch body fits in the chin depth", FT + PAD_T - SWITCH_BODY, FT + PAD_T - SWITCH_BODY >= 3)
    r = MOUNT_BORE / 2 + 2.5
    add("side inserts below the fan", (CY - FAN / 2 - FAN_GAP) - (MOUNT_Y + r), (CY - FAN / 2 - FAN_GAP) - (MOUNT_Y + r) >= 1)
    add("side inserts above the chin tabs", MOUNT_Y - r - CHIN_BLOCK, MOUNT_Y - r - CHIN_BLOCK >= -0.01)
    add("side inserts inside the base depth", min(MOUNT_ZS) - MOUNT_BORE / 2, min(MOUNT_ZS) - MOUNT_BORE / 2 >= 3)
    inner_x = W / 2 - MOUNT_DEPTH - 1.5
    add("side blocks clear the jack and switch", inner_x - (abs(SWITCH_XY[0]) + JACK_D / 2),
        inner_x - (abs(SWITCH_XY[0]) + JACK_D / 2) >= 5)
    blind = T3 - 1.2
    fan_in = chin_in = SCREW_L - T5                # all heads flush: screw length past P2, into P3
    add("chin screws: bite in the insert at the base's front", min(chin_in, INSERT_DEPTH), chin_in >= INSERT_DEPTH)
    add("fan screws: bite in the insert under the fan", min(fan_in - FT, INSERT_DEPTH), fan_in - FT >= INSERT_DEPTH)
    add("fan screws: tip short of the back face", blind - fan_in, blind - fan_in >= 0.5)
    add("chin screws: tip short of the back face", blind - chin_in, blind - chin_in >= 0.5)
    return out, fan_in, chin_in


def main():
    if "--stl" not in sys.argv:            # checks only (seconds); the grilles make a full build ~10 min
        res, fan_in, chin_in = checks()
        for c in res:
            print(("ok  " if c["ok"] else "FAIL"), c["check"], c["value"], c["unit"])
        print(f"body {W:.0f} x {H:.1f} x {T6 + T5 + T3:.1f}; {sum(c['ok'] for c in res)}/{len(res)} checks pass")
        print("not exported: run with --stl once the design is final")
        if not all(c["ok"] for c in res):
            raise SystemExit("checks failed")
        return
    OUT.mkdir(parents=True, exist_ok=True)
    parts = dict(P1_face=p1_face(), P2_filter=p2_filter(), P3_body=p3_body())
    flip = {"P2_filter", "P3_body"}       # print with the back face on the bed
    z, meta = 0.0, []
    for name, t in LAYERS:
        part = parts[name]
        vol = part.volume / 1000.0
        export_stl(part, str(OUT / f"{name}.stl"))
        printed = Rot(180, 0, 0) * part if name in flip else part
        export_stl(printed, str(OUT / f"{name}_print.stl"))
        meta.append(dict(name=name, z=round(z, 2), t=round(t, 2), cm3=round(vol, 1), g_petg=round(vol * 1.27, 0)))
        z += t
    grilles = []
    pats = next((a.split("=", 1)[1].split(",") for a in sys.argv if a.startswith("--grilles=")), ["hslots"])
    for pat in pats:
        for side in ("front", "back"):
            g, holes = grille_insert(pat, side)
            name = f"G_{pat}_{side}"
            export_stl(g, str(OUT / f"{name}_print.stl"))           # boss down
            export_stl(g, str(OUT / f"{name}.stl"))
            grilles.append(dict(name=name, pattern=pat, side=side, open_pct=round(100 * holes.area / (math.pi * OPENING_D ** 2 / 4)),
                                openings=len(holes.geoms) if hasattr(holes, "geoms") else 1, cm3=round(g.volume / 1000, 1)))
    res, fan_in, chin_in = checks()
    summary = dict(
        body=dict(w=W, h=H, cy=CY, depth=round(z, 1), r=R, opening=OPENING_D), grilles=grilles,
        layers=meta, total_cm3=round(sum(m["cm3"] for m in meta), 1),
        total_g_petg=round(sum(m["g_petg"] for m in meta)),
        screws=dict(stack=f"6 x M3 x {SCREW_L:.0f} CSK",
                    fan_fit=f"{fan_in:.1f} into the body, tip {T3 - 1.2 - fan_in:.1f} short of the back",
                    chin_fit=f"{chin_in:.1f} into the body, tip {T3 - 1.2 - chin_in:.1f} short of the back",
                    inserts="6 x M3 heat-set in the body (4 under the fan corners, 2 at the chin)",
                    magnets="6 x Ø6 x 2: 3 in the filter part's chin (bottom centre, each side low), 3 in the face",
                    handle=f"2 x M3 heat-set in the top, {HANDLE_PITCH:.1f} apart (5-hole Meccano strip on M3 standoffs)"),
        checks=res, failed=[c for c in res if not c["ok"]])
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1))
    for m in meta:
        print(f"{m['name']:16s} z {m['z']:5.1f}  t {m['t']:5.1f}  {m['cm3']:6.1f} cm3  ~{m['g_petg']:.0f} g PETG")
    print(f"body {W:.0f} x {H:.0f} x {z:.1f}, {summary['total_cm3']} cm3, ~{summary['total_g_petg']} g solid PETG")
    print(summary["screws"])
    for c in res:
        if not c["ok"]:
            print("FAIL", c)
    if summary["failed"]:
        raise SystemExit("checks failed")
    print(f"{len(res)} checks pass")


if __name__ == "__main__":
    main()
