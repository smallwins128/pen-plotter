"""Fit kit: small test prints that pin down every printed fit on Allwin's printer before the real parts.

Each coupon tests one interface in a few sizes. Print them all (PETG, 0.2 mm layers, 3 walls), try the real parts,
and the size that fits becomes the number every real part uses (FIT below).

    python3 hardware/parts/fit_kit.py          # writes hardware/out/fit_kit/*.stl + a preview PNG
    python3 hardware/parts/fit_kit.py I        # coupon I only

  A  screws + inserts   M3 clearance 3.2/3.4/3.6 · heat-set bores 4.0/4.2/4.4 · rivnut flange recess Ø8.5/9.0 × 1
  B  GX16               panel holes 16.0/16.2/16.4 in a 3 mm plate
  C  IEC module         three 1.5 mm frames: 47.0×27.0 / 47.5×27.5 / 48.0×28.0
  D  LED + stop         Ø12.0/12.2/12.4 (LEDs) · Ø22.0/22.3/22.6 (LA38 stop) in a 3 mm plate
  E  window bezel       three corners, acrylic pocket 3.0/3.2/3.4 deep, Ø2.6 pilot for a self-tapping M3 bezel screw
  F  pegs               snap pegs for the base plate's Ø6 holes: shaft 5.6/5.8/6.0, for 1 mm and 2 mm plate;
                        snap plugs for the Ø5 accessory holes in 1 mm steel: 4.6/4.8/5.0
  G  LED strip holder   clamps under a bezel screw inside; channel for 8 mm and 10 mm strip
  H  cable holders      cable-tie mount and two snap saddles (Ø6, Ø9), all on a 5.8 peg for 2 mm plate
  I  magnet panels     bezel section (11 × 2.5, 2 bolt holes) and panel section (2.6, lip), 3 pockets each for
                        Ø6 × 1.5 magnets: Ø5.95 / 6.05 / 6.15 × 1.6 deep. Press magnets in (bezel N out, panel S
                        in): the tightest pocket that doesn't crack sets the size; then feel the pull
"""
import math
import pathlib

from build123d import (Align, Axis, Box, BuildPart, BuildSketch, Cylinder, Locations, Mode, Plane, Pos, Rectangle,
                       Polygon, RegularPolygon, Rot, SlotOverall, Text, add, chamfer, export_stl, extrude, fillet)

OUT = pathlib.Path(__file__).resolve().parent.parent / "out" / "fit_kit"
TXT = 3.2            # label height
ENGRAVE = 0.5

# the numbers the real parts will use, until the kit says otherwise
FIT = dict(m3_clear=3.4, insert_bore=4.2, rivnut_recess=9.0, gx16=16.2, led=12.2, stop=22.3,
           acrylic_pocket=3.2, peg=5.8, plug=4.8, selftap_pilot=2.6, magnet_pocket=6.05)

# magnetic window panels (coupon I): Ø6 × 1.5 disc magnets glued flush, bezel 11 × 2.5, panel 2.6
MAG_D, MAG_T, MAG_DEPTH = 6.0, 1.5, 1.6
BEZEL_W, BEZEL_T, PANEL_T = 11.0, 2.5, 2.6


def label(part, text, x, y, top_z, size=TXT):
    """Engrave text into the face at height top_z."""
    with BuildSketch(Plane.XY.offset(top_z)) as s:
        with Locations((x, y)):
            Text(text, font_size=size)
    extrude(s.sketch, amount=-ENGRAVE, mode=Mode.SUBTRACT)


def plate_with_holes(name, holes, w, h, t=3.0, tag=None):
    """A t-thick plate with round holes [(x, y, d, text)], labels under each."""
    with BuildPart() as p:
        Box(w, h, t, align=(Align.CENTER, Align.CENTER, Align.MIN))
        for x, y, d, txt in holes:
            with Locations((x, y, 0)):
                Cylinder(d / 2, t, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
            label(p, txt, x, y - d / 2 - 3.2, t)
        if tag:
            label(p, tag, -w / 2 + 5, h / 2 - 4, t, size=3.6)
    return p.part


def coupon_a():
    """Screws, heat-set inserts, rivnut flange recess."""
    w, h, t = 78.0, 34.0, 6.0
    with BuildPart() as p:
        Box(w, h, t, align=(Align.CENTER, Align.CENTER, Align.MIN))
        for i, d in enumerate((3.2, 3.4, 3.6)):                      # clearance, through
            x = -30 + i * 12
            with Locations((x, 6, 0)):
                Cylinder(d / 2, t, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
            label(p, f"{d:.1f}", x, -1.2, t, 2.6)
        for i, d in enumerate((4.0, 4.2, 4.4)):                      # insert bores, 5.5 deep from the top
            x = 8 + i * 12
            with Locations((x, 6, t - 5.5)):
                Cylinder(d / 2, 5.5, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
            label(p, f"{d:.1f}", x, -1.2, t, 2.6)
        for i, d in enumerate((8.5, 9.0)):                           # rivnut flange recess on the underside + M3
            x = -24 + i * 22
            with Locations((x, -10, 0)):
                Cylinder(d / 2, 1.0, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
                Cylinder(1.7, t, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
            label(p, f"R{d:.1f}", x + 9, -11.2, t, 2.6)
        label(p, "A", w / 2 - 5, h / 2 - 5, t, 3.6)
    return p.part


def coupon_b():
    return plate_with_holes("B", [(-32 + i * 32, 2, d, f"{d:.1f}") for i, d in enumerate((16.0, 16.2, 16.4))],
                            100.0, 40.0, tag="B")


def coupon_c(i, cw, ch):
    """IEC snap-in frame: 1.5 mm, the thickness its clips grip."""
    t = 1.5
    with BuildPart() as p:
        Box(cw + 16, ch + 18, t, align=(Align.CENTER, Align.CENTER, Align.MIN))
        Box(cw, ch, t, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
        label(p, f"C {cw:.1f}x{ch:.1f}", 0, -(ch / 2) - 5, t, 3.0)
    return p.part


def coupon_d():
    holes = [(-58 + i * 15, 4, d, f"{d:.1f}") for i, d in enumerate((12.0, 12.2, 12.4))]
    holes += [(0 + i * 28, 4, d, f"{d:.1f}") for i, d in enumerate((22.0, 22.3, 22.6))]
    return plate_with_holes("D", holes, 150.0, 40.0, tag="D")


def coupon_e(pocket):
    """Window bezel corner, seen from the back (steel side up): 9 mm band, pocket for the acrylic, M3 insert boss.
    Bezel 5 mm thick; acrylic edge 3 mm past the window; screw 5.5 past the window, outside the acrylic."""
    band, depth, r = 9.0, 5.0, 3.0
    L = 34.0
    with BuildPart() as p:
        # L-shaped corner of the band, window corner at the origin, band outward (+x, +y are the window side)
        Box(L, band, depth, align=(Align.MIN, Align.MIN, Align.MIN))
        with Locations((0, 0, 0)):
            Box(band, L, depth, align=(Align.MIN, Align.MIN, Align.MIN))
        # window opening: x > band and y > band would be the window; here the band is the frame only
        # acrylic pocket: 3 mm over the window edge, on the back face (z = 0 is the steel side)
        with Locations((band - 3.0, band - 3.0, 0)):
            Box(L, L, pocket, align=(Align.MIN, Align.MIN, Align.MIN), mode=Mode.SUBTRACT)
        # screw 5.5 out from the window edge (fixed: the steel holes are cut). The acrylic edge is 3 out, so a heat-set
        # insert (Ø4.2 bore) would leave 0.4 mm of plastic: use a self-tapping M3 into a Ø2.6 pilot instead
        with Locations((L - 8, band - 5.5, 0)):
            Cylinder(FIT["selftap_pilot"] / 2, 4.5, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
        label(p, f"E{pocket:.1f}", 2.2 + 1.2, L - 6, depth, 2.6)
    return p.part


def peg(shaft, grip, base_t=2.0):
    """Snap peg: base tab, split shaft through a hole of `grip` thickness, barb 0.35 proud with a lead-in."""
    barb, tip, slot = 0.35, 2.2, 1.2
    with BuildPart() as p:
        Box(12, 12, base_t, align=(Align.CENTER, Align.CENTER, Align.MIN))
        with Locations((0, 0, base_t)):
            Cylinder(shaft / 2 - 0.1, grip + 0.15, align=(Align.CENTER, Align.CENTER, Align.MIN))
        with Locations((0, 0, base_t + grip + 0.15)):
            Cylinder(shaft / 2 + barb, 0.8, align=(Align.CENTER, Align.CENTER, Align.MIN))
        with Locations((0, 0, base_t + grip + 0.95)):
            from build123d import Cone
            Cone(shaft / 2 + barb, shaft / 2 - 0.9, tip, align=(Align.CENTER, Align.CENTER, Align.MIN))
        with Locations((0, 0, base_t + 0.6)):                          # split, so the barbs can close
            Box(slot, shaft + 2, grip + tip + 2, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
        label(p, f"{shaft:.1f}/{grip:.0f}", 0, -4.2, base_t, 2.2)
    return p.part


def coupon_g(strip_w):
    """LED strip holder: a tab under a bezel screw inside the box, and a channel with lips for the strip."""
    t, lip, wall = 2.0, 0.8, 1.6
    cw = strip_w + 0.5
    with BuildPart() as p:
        Box(14, 10, t, align=(Align.CENTER, Align.CENTER, Align.MIN))                        # screw tab
        with Locations((0, 0, 0)):
            Cylinder(FIT["m3_clear"] / 2, t, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
        with Locations((0, 5 + (cw + 2 * wall) / 2, 0)):                                      # channel body
            Box(30, cw + 2 * wall, t + 2.2, align=(Align.CENTER, Align.CENTER, Align.MIN))
        with Locations((0, 5 + (cw + 2 * wall) / 2, t)):
            Box(30, cw, 2.2, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
        with Locations((0, 5 + (cw + 2 * wall) / 2, t + 1.2)):                                # opening between lips
            Box(30, cw - 2 * lip, 1.0, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
        label(p, f"G{strip_w:.0f}", 0, -3.2, t, 2.6)
    return p.part


def coupon_h_tie():
    """Cable-tie mount on a peg: the tie passes under a bridge."""
    with BuildPart() as p:
        add(peg(FIT["peg"], 2))
        with Locations((0, 0, 0)):
            Box(12, 12, 2.0, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
        with BuildPart() as top:
            Box(16, 10, 5, align=(Align.CENTER, Align.CENTER, Align.MAX))
            with Locations((0, 0, -1.5)):                                   # tie tunnel through the block
                Box(20, 5, 2, align=(Align.CENTER, Align.CENTER, Align.MAX), mode=Mode.SUBTRACT)
        add(top.part)
    return p.part


def coupon_h_saddle(d):
    """Snap saddle for a bundle of diameter d, on a peg underneath."""
    wall = 1.8
    zc = d / 2 + wall - 0.6                       # saddle sits on the peg's base tab (top face at z = 0)
    with BuildPart() as p:
        add(Rot(180, 0, 0) * peg(FIT["peg"], 2))
        with Locations((0, 0, zc)):
            Cylinder(d / 2 + wall, 10, rotation=(0, 90, 0))
            Cylinder(d / 2, 12, rotation=(0, 90, 0), mode=Mode.SUBTRACT)
        with Locations((0, 0, zc + d * 0.35)):                                               # snap opening, 70 %
            Box(12, d * 0.7, d, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
    return p.part


def coupon_i_bezel(length=70.0):
    """Bezel section (y = 0 is the window edge): 2 bolt holes with counterbores, 3 magnet pockets Ø5.95/6.05/6.15."""
    with BuildPart() as p:
        Box(length, BEZEL_W, BEZEL_T, align=(Align.CENTER, Align.MIN, Align.MIN))
        for x in (-length / 2 + 6, length / 2 - 6):
            with Locations((x, 5.5, 0)):
                Cylinder(1.7, BEZEL_T, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
            with Locations((x, 5.5, BEZEL_T - 1.8)):
                Cylinder(3.1, 1.8, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
        for i, d in enumerate((5.95, 6.05, 6.15)):
            with Locations((-17 + i * 17, 6.5, BEZEL_T - MAG_DEPTH)):
                Cylinder(d / 2, MAG_DEPTH, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
            label(p, f"{d:.2f}"[1:], -17 + i * 17, 1.7, BEZEL_T, size=2.2)
    return p.part


def coupon_i_panel(length=70.0):
    """Matching panel section, printed face down: pockets on the back over the bezel's, 1 mm lip on the window side."""
    with BuildPart() as p:
        Box(length, BEZEL_W + 1.5, PANEL_T, align=(Align.CENTER, Align.MIN, Align.MIN))
        with Locations((0, -1.5, 0)):
            Box(length, 1.2, 1.5, align=(Align.CENTER, Align.MIN, Align.MAX))     # lip, drops inside the window edge
        for i, d in enumerate((5.95, 6.05, 6.15)):
            with Locations((-17 + i * 17, 6.5, 0)):
                Cylinder(d / 2, MAG_DEPTH, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
            label(p, f"{d:.2f}"[1:], -17 + i * 17, 10.0, PANEL_T, size=2.2)
    return p.part


# ---------------------------------------------------------------------------
# Pen lifter (docs/PEN_LIFTER.md): flexure, pick face + pen plate, dock channel
# ---------------------------------------------------------------------------

# Parallel-leaf flexure: 4 leaves (two pairs), L long, H tall, printed standing on the bed.
FLEX_L, FLEX_H = 40.0, 8.0
FLEX_TRAVEL = 4.0          # the shuttle's nose stands this far below the fixed block's foot
PICK = 32.0                # pick face / pen plate, square
PICK_MAG = 9.0             # magnet pockets on a 2 x 9 = 18 mm square
RIDGE_H = 1.5              # 90 deg locating ridges on the pick face; the plate's grooves are cut 0.2 shallower
FLANGE_T, FLANGE_W = 2.0, 3.0   # pen-plate side flange that slides into the dock channel


def coupon_j(t):
    """Flexure: fixed block, two pairs of leaves t thick, shuttle. Stand it on the fixed block's foot on a kitchen
    scale and press down: the shuttle's nose touches first and the reading just before the foot lands is the force
    at FLEX_TRAVEL."""
    blk, h_tot = 14.0, 30.0
    with BuildPart() as p:
        with BuildSketch():
            with Locations((-blk / 2, h_tot / 2)):
                Rectangle(blk, h_tot)                                   # fixed block, foot = its bottom edge
            with Locations((FLEX_L + blk / 2, h_tot / 2 + 1.0)):
                Rectangle(blk, h_tot - 2.0)                             # shuttle
            with Locations((FLEX_L + blk / 2, -FLEX_TRAVEL / 2 + 1.0)):
                Rectangle(6.0, FLEX_TRAVEL + 2.0)                       # nose, FLEX_TRAVEL below the foot
            for yc in (5.0, h_tot - 5.0):                               # two pairs, each 5 mm apart
                for dy in (-2.5, 2.5):
                    with Locations((FLEX_L / 2, yc + dy)):
                        Rectangle(FLEX_L + 0.2, t)
        extrude(amount=FLEX_H)
        label(p, f"J{t:.1f}", -blk / 2, h_tot / 2, FLEX_H, size=3.0)
    return p.part


def coupon_k_face():
    """Pick face: 4 magnet pockets (N out) and two 90 deg ridges in an L, one locating each axis. Ridges up."""
    t = 5.0
    with BuildPart() as p:
        Box(PICK, PICK, t, align=(Align.CENTER, Align.CENTER, Align.MAX))
        for x in (-PICK_MAG, PICK_MAG):
            for y in (-PICK_MAG, PICK_MAG):
                with Locations((x, y, -MAG_DEPTH)):
                    Cylinder(FIT["magnet_pocket"] / 2, MAG_DEPTH, align=(Align.CENTER, Align.CENTER, Align.MIN),
                             mode=Mode.SUBTRACT)
        add(_ridge(along_x=True).moved(Pos(0, 13.0, 0)))                # along X at the top: locates Y
        add(_ridge(along_x=False).moved(Pos(13.0, 0, 0)))               # along Y at the right: locates X
        label(p, "K face", 0, 0, 0, size=3.0)
    return p.part


def _ridge(along_x, depth=RIDGE_H, length=PICK - 8.0):
    """A 90 deg prism standing on z = 0, `depth` high."""
    with BuildPart() as r:
        with BuildSketch(Plane.YZ if along_x else Plane.XZ):
            Polygon((-depth, 0), (depth, 0), (0, depth), align=None)
        extrude(amount=length / 2, both=True)
    return r.part


def coupon_k_plate():
    """Pen plate's back: grooves 0.2 shallower than the ridges so the flanks seat before the faces touch, magnet
    pockets (S out). Modelled mating face down at z = 0, mirrored so it lines up with the face, then turned over."""
    t = 4.0
    with BuildPart() as p:
        Box(PICK, PICK, t, align=(Align.CENTER, Align.CENTER, Align.MIN))
        for x in (-PICK_MAG, PICK_MAG):
            for y in (-PICK_MAG, PICK_MAG):
                with Locations((x, y, 0)):
                    Cylinder(FIT["magnet_pocket"] / 2, MAG_DEPTH, align=(Align.CENTER, Align.CENTER, Align.MIN),
                             mode=Mode.SUBTRACT)
        for along_x, pos in ((True, (0, 13.0, -0.2)), (False, (13.0, 0, -0.2))):
            add(_ridge(along_x, length=PICK + 2.0).moved(Pos(*pos)), mode=Mode.SUBTRACT)
        for sx in (-1, 1):                                             # side flanges for the dock channel
            with Locations((sx * (PICK / 2 + FLANGE_W / 2), 0, t - FLANGE_T)):
                Box(FLANGE_W, PICK, FLANGE_T, align=(Align.CENTER, Align.CENTER, Align.MIN))
        label(p, "K plate", 0, -4, t, size=3.0)
    return p.part.rotate(Axis.X, 180)


def coupon_l(c):
    """Dock channel section: a slot FLANGE_T + c wide, FLANGE_W + 0.5 deep, lead-in at the entry end. Slide the
    K plate's flange in; it should run free by hand and not rock."""
    w, h, ln = 14.0, 10.0, 34.0
    slot = FLANGE_T + c
    with BuildPart() as p:
        Box(ln, w, h, align=(Align.CENTER, Align.MIN, Align.MIN))
        with Locations((0, w - (FLANGE_W + 0.5) / 2, h / 2)):
            Box(ln, FLANGE_W + 0.5, slot, mode=Mode.SUBTRACT)
        with Locations((ln / 2, w - (FLANGE_W + 0.5) / 2, h / 2)):        # lead-in
            Box(3.0, FLANGE_W + 0.5, slot + 1.6, mode=Mode.SUBTRACT)
        label(p, f"L{c:.1f}", -6, 4.0, h, size=3.0)
    return p.part


def build_pen():
    parts = {f"J_flexure_{t:.1f}": coupon_j(t) for t in (0.6, 0.8, 1.0)}
    parts["K_pick_face"] = coupon_k_face()
    parts["K_pen_plate"] = coupon_k_plate()
    parts.update({f"L_channel_{c:.1f}": coupon_l(c) for c in (0.2, 0.3, 0.4)})
    return parts


def build():
    parts = {"A_screws_inserts_rivnut": coupon_a(), "B_gx16": coupon_b(), "D_led_stop": coupon_d()}
    for i, (cw, ch) in enumerate(((47.0, 27.0), (47.5, 27.5), (48.0, 28.0))):
        parts[f"C{i + 1}_iec_{cw:.1f}x{ch:.1f}"] = coupon_c(i, cw, ch)
    for d in (3.0, 3.2, 3.4):
        parts[f"E_bezel_pocket_{d:.1f}"] = coupon_e(d)
    for g in (1, 2):
        for s in (5.6, 5.8, 6.0):
            parts[f"F_peg_{s:.1f}_for_{g}mm"] = peg(s, g)
    for s in (4.6, 4.8, 5.0):
        parts[f"F_plug_{s:.1f}_for_1mm_steel"] = peg(s, 1)
    for w in (8, 10):
        parts[f"G_ledstrip_{w}mm"] = coupon_g(w)
    parts["H_tie_mount"] = coupon_h_tie()
    for d in (6, 9):
        parts[f"H_saddle_{d}mm"] = coupon_h_saddle(d)
    parts.update(build_i())
    parts.update(build_pen())
    return parts


def build_i():
    return {"I_magnet_bezel": coupon_i_bezel(), "I_magnet_panel": coupon_i_panel()}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    import sys
    only = {"I": build_i, "P": build_pen}.get(sys.argv[1] if sys.argv[1:] else "", build)
    for name, part in only().items():
        export_stl(part, str(OUT / f"{name}.stl"))
        bb = part.bounding_box()
        print(f"{name:34s} {bb.size.X:6.1f} x {bb.size.Y:5.1f} x {bb.size.Z:4.1f}  vol {part.volume / 1000:5.2f} cm3")


if __name__ == "__main__":
    main()
