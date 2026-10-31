"""Fume extractor: three printed parts that stack front to back around an 80 mm fan (Allwin, 2026-10-31).

v2: the stack screws run through the fan's own corner holes (71.5 square), so the body only wraps the fan (90 wide).
v3: one set of screws from the front, into heat-set inserts at the back; magnets on the screw heads hold the face.
v4 (Allwin): the spacer goes, the jack and switch move into the fan layer's chin, and the fan, rear filter and back
grille are one print. Only M3 x 50 countersunk are on hand, so the inserts sit where 50 mm screws reach them.

    P1 face    grille, flush and screwless; a lip in the pad pocket + 4 magnets that snap onto 4 magnets in P2
    P2 filter  front carbon pad on a rib grid, 3.5 mm plenum behind it; the 6 screw heads, hidden under P1
               (the 4 fan screws sit 2.1 deep with a magnet on each)
    P3 body    fan pocket, rear pad pocket and exhaust grille in one; DC jack + switch in the chin; 2 x M3 inserts on top
               for a 5-hole Meccano strip handle; 6 M3 inserts: 4 on bosses under the fan corners, 2 at the chin face

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
GRILLE_D, HOLE_D, HOLE_PITCH = 76.0, 3.0, 3.8   # round holes on a hex grid: about 56 % open
MAGNETS = True

# --- layer depths ---
T6 = 3.0                       # face: magnet pockets 2.1 deep leave 0.9 of face
MAG_SEAT = MAGNET_T + 0.1      # L5: a magnet sits on each fan-screw head, in a Ø6.1 counterbore this deep
PLENUM = 3.5                   # P2: rib grid that carries the pad, and the air gap in front of the fan
T5 = LIP_H + PAD_T + PLENUM    # the face lip fills the front 3 mm of the pocket
FT = FAN_T + FAN_GAP           # P3: fan pocket depth
GRILLE_T = 2.4                 # back grille: 1.2 skin + 1.2 ribs
T3 = FT + PAD_T + GRILLE_T     # P3: fan pocket, rear pad pocket, grille
SCREW_L = 50.0                 # the only M3 countersunk length on hand
JACK_Z, SWITCH_Z = 11.0, 27.0  # side by side in the chin's right wall, depth into P3 (the chin is open to the front)
LAYERS = [("P1_face", T6), ("P2_filter", T5), ("P3_body", T3)]

# --- fixings ---
FAN_SCREWS = [(sx * FAN_HOLE / 2, CY + sy * FAN_HOLE / 2) for sx in (-1, 1) for sy in (-1, 1)]
CHIN_SCREWS = [(-36.0, 9.0), (36.0, 9.0)]
SCREWS = FAN_SCREWS + CHIN_SCREWS
MAGNET_XY = FAN_SCREWS                          # over the front screw heads
JACK_Y = SWITCH_Y = 22.0       # above the chin screw boss


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


def p1_face():
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


def p2_filter():
    """Front pad pocket with a rib grid behind the pad (the plenum). Screw heads: the 4 fan screws countersunk under a
    Ø6.1 x 2.1 seat for a magnet (it clings to the steel head); the 2 chin screws flush. Prints back down: the ribs
    land on the bed, the seats face up."""
    p = slab(framed(PAD_POCKET), 0, T5)
    g, pitch, rib = [], 13.0, 1.2
    for k in range(-3, 4):
        g.append(box(k * pitch - rib / 2, 0, k * pitch + rib / 2, H))
        g.append(box(-W / 2, CY + k * pitch - rib / 2, W / 2, CY + k * pitch + rib / 2))
    p += slab(unary_union(g).intersection(PAD_POCKET.buffer(0.5)), LIP_H + PAD_T, T5)
    for x, y in FAN_SCREWS:
        p = through(p, x, y, T5)
        p -= Pos(x, y, MAG_SEAT / 2 - 0.01) * Cylinder(MAGNET_D / 2 + 0.05, MAG_SEAT)
        p = csk(p, x, y, MAG_SEAT, +1)
    for x, y in CHIN_SCREWS:
        p = csk(through(p, x, y, T5), x, y, 0, +1)
    return p


def p3_body():
    """Fan pocket (0..FT), rear pad pocket (FT..FT+PAD_T), grille. The fan sits on the four corner bosses and on the
    pad. Prints back down (grille on the bed); "up" in the print is -z here."""
    hx = HANDLE_PITCH / 2
    handle_cols = unary_union([Point(sx * hx, H).buffer(TOP_INSERT_BORE / 2 + 2.0).union(
        box(sx * hx - TOP_INSERT_BORE / 2 - 2.0, CY + FAN / 2 + FAN_GAP, sx * hx + TOP_INSERT_BORE / 2 + 2.0, H))
        for sx in (-1, 1)])
    wire = box(26, CY - FAN / 2 - FAN_GAP - INNER - 0.5, 34, CY - FAN / 2)       # fan lead into the chin
    p = slab(framed(FAN_POCKET, handle_cols.intersection(OUTLINE)).difference(wire), 0, FT)
    p += slab(framed(PAD_POCKET), FT - 0.01, FT + PAD_T)
    p += Pos(0, 0, FT + PAD_T - 0.01) * ribbed_plate(grille_holes(), GRILLE_T, 1.2, False)
    blind = T3 - 1.2                                                 # screw holes stop short of the back face
    for x, y in FAN_SCREWS:                                          # inserts on the bosses under the fan corners
        p -= Pos(x, y, (FT + blind) / 2) * Cylinder(M3_CLEAR / 2, blind - FT + 0.02)
        p -= Pos(x, y, FT + INSERT_DEPTH / 2 - 0.01) * Cylinder(INSERT_BORE / 2, INSERT_DEPTH)
    for x, y in CHIN_SCREWS:                                         # inserts at the front face of the chin
        p -= Pos(x, y, blind / 2) * Cylinder(M3_CLEAR / 2, blind + 0.02)
        p -= Pos(x, y, INSERT_DEPTH / 2 - 0.01) * Cylinder(INSERT_BORE / 2, INSERT_DEPTH)
    for y, z, d in ((JACK_Y, JACK_Z, JACK_D), (SWITCH_Y, SWITCH_Z, SWITCH_D)):   # right side, in the chin
        p -= teardrop("x", W / 2 - WALL / 2, y, z, d + 0.2, WALL + 2, -1)
    zc = FT / 2                                                      # handle: M3 inserts down into the top
    for sx in (-1, 1):
        p -= teardrop("y", sx * hx, H - TOP_INSERT_DEPTH / 2 + 0.01, zc, TOP_INSERT_BORE, TOP_INSERT_DEPTH, -1)
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
    for i, (x, y) in enumerate(FAN_SCREWS):
        add(f"fan hole {i + 1} inside the fan pocket", FAN_POCKET.exterior.distance(Point(x, y)),
            FAN_POCKET.contains(Point(x, y)))
    add("fan pocket keeps a 2.4 wall at its corners", inner.contains(FAN_POCKET) * 1.0, inner.contains(FAN_POCKET), "")
    add("pad pocket inside the wall", 1.0, inner.contains(PAD_POCKET), "")
    add("pad still covers the fan disc", PAD_POCKET.distance(Point(0, CY)) * 0 + 1.0,
        PAD_POCKET.buffer(-0.5).contains(Point(0, CY).buffer(GRILLE_D / 2)), "")
    hx = HANDLE_PITCH / 2
    add("top inserts on the flat top", W / 2 - R - (hx + TOP_INSERT_BORE / 2), W / 2 - R - (hx + TOP_INSERT_BORE / 2) >= 2)
    add("floor under the top inserts", TOP_WALL - TOP_INSERT_DEPTH, TOP_WALL - TOP_INSERT_DEPTH >= 1.2)
    top = CY - FAN / 2 - FAN_GAP - INNER
    add("jack hole below the fan pocket wall", top - (JACK_Y + JACK_D / 2), top - (JACK_Y + JACK_D / 2) >= 1.5)
    boss_top = CHIN_SCREWS[1][1] + BOSS_R
    add("jack hole above the chin screw boss", JACK_Y - JACK_D / 2 - boss_top, JACK_Y - JACK_D / 2 - boss_top >= 1.0)
    add("jack hole clear of the body's front face", JACK_Z - JACK_D / 2, JACK_Z - JACK_D / 2 >= 3)
    gap = (SWITCH_Z - SWITCH_D / 2) - (JACK_Z + JACK_D / 2)
    add("web between jack and switch holes", gap, gap >= 4)
    g = FT + PAD_T - (SWITCH_Z + SWITCH_D / 2)                      # the chin runs back to the grille
    add("switch hole in front of the grille", g, g >= 1.5)
    add("fan-screw seat leaves a boss under the head", T5 - MAG_SEAT, T5 - MAG_SEAT >= 6)
    blind = T3 - 1.2
    fan_in = SCREW_L - (T5 - MAG_SEAT)             # screw length past P2, into P3
    chin_in = SCREW_L - T5
    add("fan screws: bite in the insert under the fan", min(fan_in - FT, INSERT_DEPTH), fan_in - FT >= INSERT_DEPTH)
    add("fan screws: tip short of the back face", blind - fan_in, blind - fan_in >= 0.5)
    add("chin screws: tip short of the back face", blind - chin_in, blind - chin_in >= 0.5)
    return out, fan_in, chin_in


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    face, n_holes = p1_face()
    parts = dict(P1_face=face, P2_filter=p2_filter(), P3_body=p3_body())
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
    res, fan_in, chin_in = checks()
    summary = dict(
        body=dict(w=W, h=H, cy=CY, depth=round(z, 1), r=R), grille_holes=n_holes,
        open_area_pct=round(100 * (math.pi / 4 * HOLE_D ** 2) / (HOLE_PITCH ** 2 * math.sqrt(3) / 2)),
        layers=meta, total_cm3=round(sum(m["cm3"] for m in meta), 1),
        total_g_petg=round(sum(m["g_petg"] for m in meta)),
        screws=dict(stack=f"6 x M3 x {SCREW_L:.0f} CSK",
                    fan_fit=f"{fan_in:.1f} into the body, tip {T3 - 1.2 - fan_in:.1f} short of the back",
                    chin_fit=f"{chin_in:.1f} into the body, tip {T3 - 1.2 - chin_in:.1f} short of the back",
                    inserts="6 x M3 heat-set in the body (4 under the fan corners, 2 at the chin)",
                    magnets="8 x Ø6 x 2: 4 on the fan-screw heads in the filter part, 4 in the face",
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
