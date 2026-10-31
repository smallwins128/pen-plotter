"""Fume extractor: five printed layers that stack front to back around an 80 mm fan (Allwin, 2026-10-31).

v2: the stack screws run through the fan's own corner holes (71.5 square), so the body only wraps the fan (90 wide).
v3 (Allwin): one set of screws. Six M3 run from the front of L5 all the way into heat-set inserts in the back part, which
is the rear filter and the back grille in one print. The back and the face show no screws.

    L6 face    grille, flush and screwless; a lip in the pad pocket + 4 magnets that snap onto 4 magnets in L5
    L5 filter  front carbon pad; the 6 screw heads, hidden under L6; the 4 fan screws sit 2.1 deep with a magnet on each
    L4 spacer  plenum in front of the fan, grid that carries the front pad, DC jack + switch in its right side
    L3 fan     80 x 80 x 25 fan in a pocket on a back ring; 2 x M4 inserts on top for a 5-hole Meccano strip handle
    L1 back    rear carbon pad pocket + exhaust grille; 6 M3 heat-set inserts in its front face (blind)

Air: grille -> front pad -> plenum -> fan -> rear pad -> grille. Layers are walls with a hollow where there is room,
closed by the two grille plates. The chin under the fan carries the wiring.

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
W, R = 90.0, 8.0                      # width and corner radius (R 8 keeps 2.4 of wall at the fan's square corners)
WALL, INNER = 2.4, 1.6                # outer wall, wall around each layer's air opening
CY = 80.0                             # fan centre height: chin below, as in the sketch

# --- bought parts (unverified until measured: see NEED below) ---
FAN, FAN_T, FAN_GAP = 80.0, 25.0, 0.2           # 80 x 80 x 25, same as the enclosure fans (71.5 hole square measured)
FAN_HOLE = 71.5
PAD, PAD_T, PAD_CLIP = 80.0, 10.0, 16.0         # carbon pad cut 80 square, 16 mm snipped off each corner (clears the screws)
JACK_D, SWITCH_D = 8.0, 6.0                     # panel DC jack (M8 thread type), mini toggle (MTS-102)
MECCANO = 12.7                                  # Meccano hole pitch
HANDLE_PITCH = 4 * MECCANO                      # 5-hole strip: its end holes, three holes between them (2026-10-31)
M4_INSERT_BORE, M4_INSERT_DEPTH = 5.7, 7.0      # M4 heat-set insert (unmeasured: typical OD 5.6-6.0, length 6-8)
TOP_WALL = M4_INSERT_DEPTH + 1.5                # above the fan pocket: the insert plus a floor
H = CY + FAN / 2 + FAN_GAP + TOP_WALL           # 128.7
MAGNET_D, MAGNET_T = 6.0, 2.0                   # 4 discs in the face pull on the steel L5 screw heads

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
MAG_SEAT = MAGNET_T + 0.1      # L5: a magnet sits on each fan-screw head, in a Ø6.1 counterbore this deep
T5 = PAD_T + LIP_H             # the lip fills the front 3 mm of the pocket
T4 = 14.0                      # jack + nut
SKIN3 = 1.2                    # back ring the fan sits on
T3 = FAN_T + FAN_GAP + SKIN3   # fan pocket + back ring that holds the fan
GRILLE_T = 2.4                 # back grille: 1.2 skin + 1.2 ribs
T1 = PAD_T + GRILLE_T          # back part: rear pad pocket in front of the grille
LAYERS = [("L6_face", T6), ("L5_filter_front", T5), ("L4_spacer", T4), ("L3_fan", T3), ("L1_back", T1)]

# --- fixings ---
FAN_SCREWS = [(sx * FAN_HOLE / 2, CY + sy * FAN_HOLE / 2) for sx in (-1, 1) for sy in (-1, 1)]
CHIN_SCREWS = [(-36.0, 9.0), (36.0, 9.0)]
SCREWS = FAN_SCREWS + CHIN_SCREWS
MAGNET_XY = FAN_SCREWS                          # over the front screw heads
JACK_Y, SWITCH_Y = 18.0, 31.0


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
    hollow = hollow.difference(keep).buffer(-1.5).buffer(1.5)      # no slivers thinner than 3 mm
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
    lip_cut = unary_union([Point(x, y).buffer(BOSS_R + 0.3) for x, y in FAN_SCREWS])
    lip_out = PAD_POCKET.buffer(-LIP_GAP, join_style=2)
    p += slab(lip_out.difference(lip_out.buffer(-LIP_W, join_style=2)).difference(lip_cut), T6 - 0.01, T6 + LIP_H)
    if MAGNETS:
        for x, y in MAGNET_XY:
            p -= Pos(x, y, T6 - (MAGNET_T + 0.1) / 2 + 0.01) * Cylinder(MAGNET_D / 2 + 0.05, MAGNET_T + 0.1)
    return p, len(holes)


def l5_filter_front():
    """Screw heads: the 4 fan screws countersunk under a Ø6.1 x 2.1 seat for a magnet (it clings to the steel head);
    the 2 chin screws flush with the face."""
    p = slab(framed(PAD_POCKET), 0, T5)
    for x, y in FAN_SCREWS:
        p = through(p, x, y, T5)
        p -= Pos(x, y, MAG_SEAT / 2 - 0.01) * Cylinder(MAGNET_D / 2 + 0.05, MAG_SEAT)
        p = csk(p, x, y, MAG_SEAT, +1)
    for x, y in CHIN_SCREWS:
        p = csk(through(p, x, y, T5), x, y, 0, +1)
    return p


def diag_ribs(r_from, w=2.4):
    """Ribs from the opening ring out to the four fan-corner bosses (carry the fan and pad corners)."""
    ribs = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            a = Point(sx * r_from / math.sqrt(2), CY + sy * r_from / math.sqrt(2))
            b = Point(sx * FAN_HOLE / 2, CY + sy * FAN_HOLE / 2)
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
    handle_cols = unary_union([Point(sx * hx, H).buffer(M4_INSERT_BORE / 2 + 2.0).union(
        box(sx * hx - M4_INSERT_BORE / 2 - 2.0, CY + FAN / 2 + FAN_GAP, sx * hx + M4_INSERT_BORE / 2 + 2.0, H))
        for sx in (-1, 1)])
    wire = box(26, CY - FAN / 2 - FAN_GAP - INNER - 0.5, 34, CY - FAN / 2)       # fan lead into the chin
    shape = framed(FAN_POCKET, handle_cols.intersection(OUTLINE)).difference(wire)
    p = slab(shape, 0, FAN_T + FAN_GAP)
    ring = shape.union(FAN_POCKET.difference(OPEN))                            # back ring: the fan sits on it
    p += slab(ring, FAN_T + FAN_GAP - 0.01, T3)
    for x, y in SCREWS:
        p = through(p, x, y, T3)
    # handle: 2 x M4 heat-set inserts down into the top, 50.8 apart, for standoffs and a 5-hole Meccano strip.
    # Horizontal in the print, so the bore is a teardrop (L3 prints flipped: "up" in the print is -z here).
    zc = (FAN_T + FAN_GAP) / 2
    for sx in (-1, 1):
        p -= teardrop("y", sx * hx, H - M4_INSERT_DEPTH / 2 + 0.01, zc, M4_INSERT_BORE, M4_INSERT_DEPTH, -1)
    return p


def l1_back():
    """Rear pad pocket (z 0..PAD_T) on the back grille (PAD_T..T1). Inserts go into the front face; the screw holes
    stop 1.2 short of the back face so the back stays clean."""
    p = slab(framed(PAD_POCKET), 0, PAD_T) + Pos(0, 0, PAD_T - 0.01) * ribbed_plate(grille_holes(), GRILLE_T, 1.2, False)
    blind = T1 - 1.2
    for x, y in SCREWS:
        p -= Pos(x, y, blind / 2) * Cylinder(M3_CLEAR / 2, blind + 0.02)
        p -= Pos(x, y, INSERT_DEPTH / 2 - 0.01) * Cylinder(INSERT_BORE / 2, INSERT_DEPTH)
    return p


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
        d = OPEN.distance(c) - INSERT_BORE / 2
        add(f"screw {i + 1}: bore to plenum", d, d >= 1.5)
    for i, (x, y) in enumerate(FAN_SCREWS):
        add(f"fan hole {i + 1} inside the fan pocket", FAN_POCKET.exterior.distance(Point(x, y)),
            FAN_POCKET.contains(Point(x, y)))
    add("fan pocket keeps a 2.4 wall at its corners", inner.contains(FAN_POCKET) * 1.0, inner.contains(FAN_POCKET), "")
    add("pad pocket inside the wall", 1.0, inner.contains(PAD_POCKET), "")
    add("pad still covers the fan disc", PAD_POCKET.distance(Point(0, CY)) * 0 + 1.0,
        PAD_POCKET.buffer(-0.5).contains(Point(0, CY).buffer(GRILLE_D / 2)), "")
    hx = HANDLE_PITCH / 2
    add("top inserts on the flat top", W / 2 - R - (hx + M4_INSERT_BORE / 2), W / 2 - R - (hx + M4_INSERT_BORE / 2) >= 2)
    add("floor under the top inserts", TOP_WALL - M4_INSERT_DEPTH, TOP_WALL - M4_INSERT_DEPTH >= 1.2)
    add("switch hole below the plenum", (CY - OPEN_D / 2 - INNER) - (SWITCH_Y + SWITCH_D / 2),
        (CY - OPEN_D / 2 - INNER) - (SWITCH_Y + SWITCH_D / 2) >= 1.5)
    fan_grip = T5 - MAG_SEAT + T4 + T3            # from the seated head to the back part
    chin_grip = T5 + T4 + T3
    add("fan-screw seat leaves a boss under the head", T5 - MAG_SEAT, T5 - MAG_SEAT >= 6)
    return out, fan_grip, chin_grip


def pick_screw(grip, stock=(10, 12, 16, 20, 25, 30, 35, 40, 45, 50, 55, 60)):
    """Shortest stock countersunk length that bites >= 4 mm into the back part without reaching the blind end."""
    for L in stock:
        if 4.0 <= L - grip <= T1 - 1.2 - 0.5:
            return L, L - grip
    return None, None


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    face, n_holes = l6_face()
    parts = dict(L6_face=face, L5_filter_front=l5_filter_front(), L4_spacer=l4_spacer(), L3_fan=l3_fan(),
                 L1_back=l1_back())
    flip = {"L3_fan", "L1_back"}          # print with the back face on the bed
    z, meta = 0.0, []
    for name, t in LAYERS:
        part = parts[name]
        vol = part.volume / 1000.0
        export_stl(part, str(OUT / f"{name}.stl"))
        printed = Rot(180, 0, 0) * part if name in flip else part
        export_stl(printed, str(OUT / f"{name}_print.stl"))
        meta.append(dict(name=name, z=round(z, 2), t=round(t, 2), cm3=round(vol, 1), g_petg=round(vol * 1.27, 0)))
        z += t
    res, fan_grip, chin_grip = checks()
    fl, fb = pick_screw(fan_grip)
    cl, cb = pick_screw(chin_grip)
    for name, L in (("fan screws", fl), ("chin screws", cl)):
        res.append(dict(check=f"{name}: a stock length fits", value=L or 0, unit="mm", ok=L is not None))
    summary = dict(
        body=dict(w=W, h=H, cy=CY, depth=round(z, 1), r=R), grille_holes=n_holes,
        open_area_pct=round(100 * (math.pi / 4 * HOLE_D ** 2) / (HOLE_PITCH ** 2 * math.sqrt(3) / 2)),
        layers=meta, total_cm3=round(sum(m["cm3"] for m in meta), 1),
        total_g_petg=round(sum(m["g_petg"] for m in meta)),
        screws=dict(stack=(f"6 x M3 x {fl} CSK" if fl == cl else f"4 x M3 x {fl} + 2 x M3 x {cl} CSK"),
                    fan_fit=f"grip {fan_grip:.1f}, bite {fb:.1f}", chin_fit=f"grip {chin_grip:.1f}, bite {cb:.1f}",
                    inserts="6 x M3 heat-set in the back part",
                    magnets="8 x Ø6 x 2: 4 on the L5 fan-screw heads, 4 in the face",
                    handle=f"2 x M4 heat-set in the top, {HANDLE_PITCH:.1f} apart (5-hole Meccano strip on M4 standoffs)"),
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
