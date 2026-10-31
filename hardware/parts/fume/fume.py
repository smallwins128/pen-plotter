"""Fume extractor: six printed layers that stack front to back around an 80 mm fan (Allwin, 2026-10-31).

    L6 face    grille, flush and screwless; holds by a friction lip (and 4 optional magnets) so it pops off for the filter
    L5 filter  front carbon pad; 6 countersunk M3 from its front (hidden under L6) run through L5 + L4 into L3
    L4 spacer  plenum in front of the fan, grid that carries the front pad, DC jack + switch in its right side
    L3 fan     80 x 80 x 25 fan in a pocket, heat-set inserts on both faces, the handle on top
    L2 filter  rear carbon pad
    L1 back    exhaust grille; 6 countersunk M3 from the back run through L1 + L2 into L3

Air: grille -> front pad -> plenum -> fan -> rear pad -> grille. Every layer is an outer wall and an inner wall with a
hollow between them (filament), closed by the two grille plates. The chin under the fan carries the wiring.

Frame: x across the face, y up (0 = bench), z into the body (0 = front face). Each layer is modelled at its own z = 0
(its front face) and exported in its print orientation.

    python3 hardware/parts/fume/fume.py        # writes hardware/out/fume/*.stl and prints the checks
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
W, H, R = 108.0, 150.0, 14.0          # outline and corner radius
WALL, INNER = 2.4, 1.6                # outer wall, wall around each layer's air opening
CY = H - W / 2                        # fan centre height: the fan square sits in the top W x W

# --- bought parts (unverified until measured: see NEED below) ---
FAN, FAN_T, FAN_GAP = 80.0, 25.0, 0.2           # 80 x 80 x 25, same as the enclosure fans (71.5 hole square measured)
PAD, PAD_T, PAD_CLIP = 88.0, 10.0, 9.5          # carbon pad cut 88 square, corners clipped 9.5 at 45 deg
JACK_D, SWITCH_D = 8.0, 6.0                     # panel DC jack (M8 thread type), mini toggle (MTS-102)
HANDLE_PITCH, HANDLE_SCREW = 64.0, 4.0          # cabinet pull: hole centres, thread
MAGNET_D, MAGNET_T = 6.0, 2.0                   # optional: 8 discs hold the face plate

# --- fit (from fit_kit.py where tested) ---
M3_CLEAR, INSERT_BORE, INSERT_DEPTH = 3.4, 4.2, 6.0
CSK_D = 6.4
BOSS_R = 4.0
LIP_H, LIP_W, LIP_GAP = 3.0, 1.6, 0.15          # face-plate lip into the front pad pocket
GRILLE_D, HOLE_D, HOLE_PITCH = 76.0, 3.0, 3.8   # round holes on a hex grid: about 56 % open
OPEN_D = 78.0                                   # plenum / fan ring opening
MAGNETS = True

# --- layer depths ---
T6 = 3.0                       # face: magnet pockets 2.1 deep leave 0.9 of face
T5 = PAD_T + LIP_H             # the lip fills the front 3 mm of the pocket
T4 = 14.0                      # jack + nut
SKIN3 = 1.2
T3 = FAN_T + FAN_GAP + SKIN3   # fan pocket + back ring that holds the fan
T2 = PAD_T
T1 = 2.4
LAYERS = [("L6_face", T6), ("L5_filter_front", T5), ("L4_spacer", T4), ("L3_fan", T3), ("L2_filter_back", T2),
          ("L1_back", T1)]

# --- fixings ---
SCREWS = [(sx * 46.0, CY + sy * 46.0) for sx in (-1, 1) for sy in (-1, 1)] + [(-46.0, 10.0), (46.0, 10.0)]
MAGNET_XY = [(-25.0, CY + 49.2), (25.0, CY + 49.2), (-30.0, 24.0), (30.0, 24.0)]
JACK_Y, SWITCH_Y = 20.0, 36.0


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
OPEN = Point(0, CY).buffer(OPEN_D / 2, quad_segs=32)


def bosses(r=BOSS_R, extra=()):
    return unary_union([Point(x, y).buffer(r, quad_segs=16) for x, y in list(SCREWS) + list(extra)])


def framed(opening, extra_solid=None):
    """Outline minus the air opening minus the hollow between the outer and inner walls (bosses stay solid)."""
    hollow = OUTLINE.buffer(-WALL, join_style=2).difference(opening.buffer(INNER, join_style=2))
    keep = bosses()
    if extra_solid is not None:
        keep = keep.union(extra_solid)
    hollow = hollow.difference(keep)
    return OUTLINE.difference(opening).difference(hollow)


def grille_holes():
    out, rr = [], GRILLE_D / 2 - HOLE_D / 2
    dy = HOLE_PITCH * math.sqrt(3) / 2
    n = int(GRILLE_D / dy) + 2
    for j in range(-n, n + 1):
        for i in range(-n, n + 1):
            x, y = (i + (j % 2) * 0.5) * HOLE_PITCH, j * dy
            if x * x + y * y <= rr * rr:
                out.append(Point(x, y + CY).buffer(HOLE_D / 2, quad_segs=4))   # 16-gon
    return out


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
                        Point(0, CY).buffer(GRILLE_D / 2 + 1.6, quad_segs=32), bosses(BOSS_R + 1.0)] + g
                       + ([extra] if extra is not None else []))
    ribs = ribs.intersection(OUTLINE).difference(cut)
    s0, s1 = (0, skin) if skin_front else (total - skin, total)
    r0, r1 = (skin - 0.01, total) if skin_front else (0, total - skin + 0.01)
    return slab(OUTLINE.difference(cut), s0, s1) + slab(ribs, r0, r1)


def l6_face():
    holes = grille_holes()
    mags = unary_union([Point(x, y).buffer(5.0) for x, y in MAGNET_XY]) if MAGNETS else None
    p = ribbed_plate(holes, T6, 1.6, True, mags)
    lip_out = PAD_POCKET.buffer(-LIP_GAP, join_style=2)
    p += slab(lip_out.difference(lip_out.buffer(-LIP_W, join_style=2)), T6 - 0.01, T6 + LIP_H)
    if MAGNETS:
        for x, y in MAGNET_XY:
            p -= Pos(x, y, T6 - (MAGNET_T + 0.1) / 2 + 0.01) * Cylinder(MAGNET_D / 2 + 0.05, MAGNET_T + 0.1)
    return p, len(holes)


def l5_filter_front():
    extra = unary_union([Point(x, y).buffer(5.0) for x, y in MAGNET_XY]) if MAGNETS else None
    p = slab(framed(PAD_POCKET, extra), 0, T5)
    for x, y in SCREWS:
        p = csk(through(p, x, y, T5), x, y, 0, +1)
    if MAGNETS:
        for x, y in MAGNET_XY:
            p -= Pos(x, y, (MAGNET_T + 0.1) / 2 - 0.01) * Cylinder(MAGNET_D / 2 + 0.05, MAGNET_T + 0.1)
    return p


def diag_ribs(r_from, w=2.4):
    """Ribs from the opening ring out to the four fan-corner bosses (carry the fan and pad corners)."""
    ribs = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            a = Point(sx * r_from / math.sqrt(2), CY + sy * r_from / math.sqrt(2))
            b = Point(sx * 46.0, CY + sy * 46.0)
            ribs.append(LineString([a, b]).buffer(w / 2, cap_style=2))
    return unary_union(ribs)


def l4_spacer():
    p = slab(framed(OPEN, diag_ribs(OPEN_D / 2)), 0, T4)
    # grid that carries the front pad across the opening, 2 mm deep at the front face (prints on the bed)
    g, pitch, rib = [], 13.0, 1.2
    for k in range(-3, 4):
        g.append(box(k * pitch - rib / 2, CY - OPEN_D / 2, k * pitch + rib / 2, CY + OPEN_D / 2))
        g.append(box(-OPEN_D / 2, CY + k * pitch - rib / 2, OPEN_D / 2, CY + k * pitch + rib / 2))
    p += slab(unary_union(g).intersection(OPEN.buffer(0.5)), 0, 2.0)
    for x, y in SCREWS:
        p = through(p, x, y, T4)
    # right side, in the chin: DC jack and switch (print: front face down, so the points face +z)
    for y, d in ((JACK_Y, JACK_D), (SWITCH_Y, SWITCH_D)):
        p -= teardrop("x", W / 2 - WALL / 2, y, T4 / 2, d + 0.2, WALL + 2, +1)
    return p


def l3_fan():
    hx = HANDLE_PITCH / 2
    handle_cols = unary_union([box(sx * hx - 6, CY + FAN / 2 + FAN_GAP, sx * hx + 6, H) for sx in (-1, 1)])
    wire = box(26, CY - FAN / 2 - FAN_GAP - INNER - 0.5, 34, CY - FAN / 2)       # fan lead into the chin
    shape = framed(FAN_POCKET, handle_cols.intersection(OUTLINE)).difference(wire)
    p = slab(shape, 0, FAN_T + FAN_GAP)
    ring = shape.union(FAN_POCKET.difference(OPEN))                            # back ring: the fan sits on it
    p += slab(ring, FAN_T + FAN_GAP - 0.01, T3)
    for x, y in SCREWS:
        p = through(p, x, y, T3)
        p -= Pos(x, y, INSERT_DEPTH / 2 - 0.01) * Cylinder(INSERT_BORE / 2, INSERT_DEPTH)
        p -= Pos(x, y, T3 - INSERT_DEPTH / 2 + 0.01) * Cylinder(INSERT_BORE / 2, INSERT_DEPTH)
    # handle: M4 from inside the fan pocket (fan out), head in a counterbore, up into the pull
    zc = (FAN_T + FAN_GAP) / 2
    y0 = CY + FAN / 2 + FAN_GAP
    for sx in (-1, 1):
        x = sx * hx
        # print orientation: L3 is flipped (back ring on the bed), so "up" in the print is -z here
        p -= teardrop("y", x, (y0 + H) / 2, zc, HANDLE_SCREW + 0.5, H - y0 + 2, -1)
        p -= Pos(x, y0 + 1.5, zc) * (Rot(90, 0, 0) * Cylinder(4.4, 3.0 + 0.02))
    return p


def l2_filter_back():
    p = slab(framed(PAD_POCKET), 0, T2)
    for x, y in SCREWS:
        p = through(p, x, y, T2)
    return p


def l1_back():
    holes = grille_holes()
    p = ribbed_plate(holes, T1, 1.2, False)
    for x, y in SCREWS:
        p = csk(through(p, x, y, T1), x, y, T1, -1)
    return p


# --- checks -----------------------------------------------------------------------------------------------------------

def checks():
    out = []

    def add(name, value, ok, unit="mm"):
        out.append(dict(check=name, value=round(value, 2), unit=unit, ok=bool(ok)))

    inner = OUTLINE.buffer(-WALL, join_style=2)
    for i, (x, y) in enumerate(SCREWS):
        c = Point(x, y)
        add(f"screw {i + 1}: insert bore to outside", OUTLINE.exterior.distance(c) - INSERT_BORE / 2,
            OUTLINE.exterior.distance(c) - INSERT_BORE / 2 >= 1.5)
        for name, hole in (("fan pocket", FAN_POCKET), ("pad pocket", PAD_POCKET), ("opening", OPEN)):
            d = hole.distance(c) - INSERT_BORE / 2
            add(f"screw {i + 1}: bore to {name}", d, d >= 1.5)
    add("pad pocket inside the wall", inner.buffer(-INNER).contains(PAD_POCKET) * 1.0, inner.contains(PAD_POCKET), "")
    add("fan pocket inside the wall", 1.0, inner.contains(FAN_POCKET), "")
    if MAGNETS:
        for x, y in MAGNET_XY:
            c = Point(x, y).buffer(MAGNET_D / 2 + 0.05)
            d = min(OUTLINE.exterior.distance(c), PAD_POCKET.distance(c))
            add(f"magnet ({x:.0f}, {y:.0f}) wall", d, d >= 1.2)
    hx = HANDLE_PITCH / 2
    add("handle feet inside the flat top", W / 2 - R - (hx + 6), W / 2 - R - (hx + 6) >= 0)
    add("jack hole to chin top", (CY - OPEN_D / 2 - INNER) - (JACK_Y + JACK_D / 2), True)
    front = T5 + T4
    back = T1 + T2
    add("front screws: grip through L5 + L4", front, True)
    add("back screws: grip through L1 + L2", back, True)
    return out, front, back


def pick_screw(grip, stock=(10, 12, 16, 20, 25, 30, 35, 40)):
    """Shortest stock countersunk length that bites >= 3 mm into the insert without bottoming."""
    for L in stock:
        if 3.0 <= L - grip <= INSERT_DEPTH - 0.5:
            return L, L - grip
    return None, None


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    face, n_holes = l6_face()
    parts = dict(L6_face=face, L5_filter_front=l5_filter_front(), L4_spacer=l4_spacer(), L3_fan=l3_fan(),
                 L2_filter_back=l2_filter_back(), L1_back=l1_back())
    flip = {"L3_fan", "L1_back"}          # print with the back face on the bed
    z, meta = 0.0, []
    for name, t in LAYERS:
        part = parts[name]
        vol = part.volume / 1000.0
        export_stl(part, str(OUT / f"{name}.stl"))
        printed = Rot(180, 0, 0) * part if name in flip else part
        export_stl(printed, str(OUT / f"{name}_print.stl"))
        meta.append(dict(name=name, z=z, t=t, cm3=round(vol, 1), g_petg=round(vol * 1.27, 0)))
        z += t
    res, front, back = checks()
    fl, fb = pick_screw(front)
    bl, bb = pick_screw(back)
    summary = dict(
        body=dict(w=W, h=H, depth=round(z, 1), r=R), grille_holes=n_holes,
        open_area_pct=round(100 * (math.pi / 4 * HOLE_D ** 2) / (HOLE_PITCH ** 2 * math.sqrt(3) / 2)),
        layers=meta, total_cm3=round(sum(m["cm3"] for m in meta), 1),
        total_g_petg=round(sum(m["g_petg"] for m in meta)),
        screws=dict(front=f"6 x M3 x {fl} CSK (grip {front:.1f}, bite {fb:.1f})",
                    back=f"6 x M3 x {bl} CSK (grip {back:.1f}, bite {bb:.1f})",
                    inserts="12 x M3 heat-set in L3", handle=f"2 x M{HANDLE_SCREW:.0f} pan head (length after the pull is measured)"),
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
