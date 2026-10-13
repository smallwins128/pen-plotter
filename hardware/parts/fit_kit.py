"""Fit kit: small test prints that pin down every printed fit on Allwin's printer before the real parts.

Each coupon tests one interface in a few sizes. Print them all (PETG, 0.2 mm layers, 3 walls), try the real parts,
and the size that fits becomes the number every real part uses (FIT below).

    python3 hardware/parts/fit_kit.py          # writes hardware/out/fit_kit/*.stl + a preview PNG

  A  screws + inserts   M3 clearance 3.2/3.4/3.6 · heat-set bores 4.0/4.2/4.4 · rivnut flange recess Ø8.5/9.0 × 1
  B  GX16               panel holes 16.0/16.2/16.4 in a 3 mm plate
  C  IEC module         three 1.5 mm frames: 47.0×27.0 / 47.5×27.5 / 48.0×28.0
  D  LED + stop         Ø12.0/12.2/12.4 (LEDs) · Ø22.0/22.3/22.6 (LA38 stop) in a 3 mm plate
  E  window bezel       three corners, acrylic pocket 3.0/3.2/3.4 deep, Ø2.6 pilot for a self-tapping M3 bezel screw
  F  pegs               snap pegs for the base plate's Ø6 holes: shaft 5.6/5.8/6.0, for 1 mm and 2 mm plate;
                        snap plugs for the Ø5 accessory holes in 1 mm steel: 4.6/4.8/5.0
  G  LED strip holder   clamps under a bezel screw inside; channel for 8 mm and 10 mm strip
  H  cable holders      cable-tie mount and two snap saddles (Ø6, Ø9), all on a 5.8 peg for 2 mm plate
"""
import math
import pathlib

from build123d import (Align, Axis, Box, BuildPart, BuildSketch, Cylinder, Locations, Mode, Plane, Pos, Rectangle,
                       RegularPolygon, Rot, SlotOverall, Text, add, chamfer, export_stl, extrude, fillet)

OUT = pathlib.Path(__file__).resolve().parent.parent / "out" / "fit_kit"
TXT = 3.2            # label height
ENGRAVE = 0.5

# the numbers the real parts will use, until the kit says otherwise
FIT = dict(m3_clear=3.4, insert_bore=4.2, rivnut_recess=9.0, gx16=16.2, led=12.2, stop=22.3,
           acrylic_pocket=3.2, peg=5.8, plug=4.8, selftap_pilot=2.6)


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
    return parts


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, part in build().items():
        export_stl(part, str(OUT / f"{name}.stl"))
        bb = part.bounding_box()
        print(f"{name:34s} {bb.size.X:6.1f} x {bb.size.Y:5.1f} x {bb.size.Z:4.1f}  vol {part.volume / 1000:5.2f} cm3")


if __name__ == "__main__":
    main()
