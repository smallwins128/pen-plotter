"""Swappable window inserts for the three front openings (power left, power right, control).

Every insert shares one mount: a flange on the outside of the steel with 4 M3 button-head screws from the front
(counterbored), into captive nuts in a printed nut frame stuck to the inside of the steel (VHB tape). So any insert
swaps from the front without opening the box. The openings and the 4 Ø3.4 holes round each are fixed (steel is cut).

    python3 hardware/parts/window_inserts.py           # writes hardware/out/window_inserts/*.stl + card templates (.svg)
    python3 hardware/parts/window_inserts.py penrack   # pen racks only (fast)

Frame: u = x across the front, v = height above the base underside, w = out of the steel (steel outer face w = 0).
"""
import json
import math
import pathlib
import sys

from build123d import (Align, Axis, Box, BuildPart, Cylinder, Face, Location, Locations, Mode, Part, Plane, Pos, Rot,
                       RegularPolygon, Vector, Wire, export_stl, extrude)
from shapely.geometry import MultiPolygon, Point, Polygon, box as sbox
from shapely.ops import unary_union

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "sheet"))
import enclosure as E  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent.parent / "out" / "window_inserts"

STEEL = E.T
BAND = 9.0            # flange beyond the opening
FLANGE = 3.0          # flange thickness (outside the steel)
CB_D, CB_H = 6.2, 1.7 # counterbore for an M3 button head (Ø5.7 × 1.65)
CLEAR = 3.4           # M3 clearance
PLUG_GAP = 0.4        # plug into the opening, per side
NUT_AF, NUT_H = 5.7, 2.6   # M3 nut pocket (5.5 AF nut + 0.2)
NUTFRAME_T = 4.0      # nut frame thickness behind the steel
NUTFRAME_OUT = 10.0   # nut frame beyond the opening
ACRYLIC_T, ACRYLIC_POCKET, ACRYLIC_MAR = 3.0, 3.2, 3.0
BEZEL_T = 5.0
CARD_SLOT, CARD_MAR = 0.8, 3.0   # card slot depth, card beyond the window

# pen rack: two slotted bands (the insert's top and bottom), slots at the window's slant. Pens go in capped and
# lean on the downhill wall of each slot, so any diameter sits at the same angle. Leftmost slot takes a marker.
RACK_ANG = math.radians(E.WIN["ang"])
RACK_BAND = 16.0       # band height (top and bottom of the insert)
RACK_FLOOR = 4.0       # floor under the bottom slots
RACK_CELL_D = 17.0     # slot depth out of the face (Ø15 marker + clearance)
RACK_FRONT = 2.0       # closed front wall
RACK_SIDE = 2.5        # wall round the outside of the band
RACK_WALL = 3.0        # wall between slots, measured across (u)
RACK_SLOTS = [16.5] + [13.0] * 8    # slot widths square to the pen: marker (<= Ø15), then pens up to Ø12
RACK_ACCESS = 7.0      # driver hole through the band front over each screw


def openings():
    """{name: (opening polygon (u, v), [4 screw points], box kind)}."""
    (pl, sl), (pr, sr) = E.window_panes()
    pc, sc = E.ctrl_window()
    return {"power_left": (pl, sl, "power"), "power_right": (pr, sr, "power"), "control": (pc, sc, "control")}


# ---------------------------------------------------------------- shapely -> build123d
def face(poly):
    """Planar face in the XY plane from a shapely polygon (with holes)."""
    def wire(coords):
        return Wire.make_polygon([Vector(x, y, 0) for x, y in list(coords)[:-1]], close=True)
    return Face(wire(poly.exterior.coords), [wire(r.coords) for r in poly.interiors])


def slab(poly, w0, w1):
    """Extrude a shapely (multi)polygon between w0 and w1."""
    polys = list(poly.geoms) if isinstance(poly, MultiPolygon) else [poly]
    out = None
    for p in polys:
        s = extrude(Pos(0, 0, w0) * face(p), amount=w1 - w0, dir=(0, 0, 1))   # shapely rings can wind either way
        out = s if out is None else out + s
    return out


def rounded(poly, r):
    return poly.buffer(-r, join_style=1).buffer(r, join_style=1)


# ---------------------------------------------------------------- shared mount
def flange_outline(poly):
    return poly.buffer(BAND, join_style=1, quad_segs=8)


def screw_cuts(part, screws, w_front):
    """Through holes + counterbores from the front face at w_front."""
    for u, v in screws:
        part = part - Pos(u, v, -50) * Cylinder(CLEAR / 2, 100, align=(Align.CENTER, Align.CENTER, Align.MIN))
        part = part - Pos(u, v, w_front - CB_H) * Cylinder(CB_D / 2, 10, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return part


def nut_frame(poly, screws):
    """Inside the box, against the steel (w = -STEEL .. -STEEL-NUTFRAME_T); captive nuts, VHB to the steel."""
    ring = poly.buffer(NUTFRAME_OUT, join_style=1).difference(poly.buffer(PLUG_GAP + 0.3, join_style=1))
    w1, w0 = -STEEL, -STEEL - NUTFRAME_T
    part = slab(ring, w0, w1)
    for u, v in screws:
        part = part - Pos(u, v, -50) * Cylinder(CLEAR / 2, 100, align=(Align.CENTER, Align.CENTER, Align.MIN))
        nut = extrude(Pos(u, v, w0) * RegularPolygon(NUT_AF / 2, 6, major_radius=False).face(), amount=NUT_H, dir=(0, 0, 1))
        part = part - nut
    return part


# ---------------------------------------------------------------- inserts
def relief(poly, screws, seed_shift):
    """Solid tile with raised topographic contours over the whole flange."""
    F = flange_outline(poly)
    part = slab(F, 0, FLANGE) + slab(poly.buffer(-PLUG_GAP), -STEEL, 0)
    c = Point(poly.centroid.x + seed_shift, poly.centroid.y - 2)
    ribs = []
    for k in range(1, 40):
        r = k * 3.6
        ring = c.buffer(r, 96)
        ring = Polygon([(x + 1.6 * math.sin(y / 5.0 + k * 0.7), y + 0.8 * math.sin(x / 9.0 + k)) for x, y in ring.exterior.coords])
        band = ring.difference(ring.buffer(-1.0))
        ribs.append(band)
    ribs = unary_union(ribs).intersection(F.buffer(-1.2))
    ribs = ribs.difference(unary_union([Point(u, v).buffer(CB_D / 2 + 0.8) for u, v in screws]))
    if not ribs.is_empty:
        part = part + slab(ribs.buffer(0), FLANGE, FLANGE + 1.2)
    return screw_cuts(part, screws, FLANGE)


def acrylic_bezel(poly, screws):
    """Bezel over 3 mm acrylic (acrylic = opening + 3, cut by the vendor). Screws pass outside the acrylic."""
    F = flange_outline(poly)
    part = slab(F.difference(poly), 0, BEZEL_T)
    part = part - slab(poly.buffer(ACRYLIC_MAR + 0.2, join_style=1), 0, ACRYLIC_POCKET)
    return screw_cuts(part, screws, BEZEL_T)


def card_frame(poly, screws, open_side):
    """Front frame + back plate (printed apart, screwed together by the 4 screws). The card slides in from the side
    whose opening edge is vertical, and stays put between them; the window shows it."""
    F = flange_outline(poly)
    card = rounded(poly.buffer(CARD_MAR, join_style=2), 1.5)
    x0, y0, x1, y1 = F.bounds
    cy0, cy1 = card.bounds[1], card.bounds[3]
    # the slot runs out through the open side so the card can slide in
    run = sbox(x0 - 1, cy0 - 0.4, card.bounds[0] + 1, cy1 + 0.4) if open_side == "left" else \
        sbox(card.bounds[2] - 1, cy0 - 0.4, x1 + 1, cy1 + 0.4)
    slot = unary_union([card.buffer(0.4, join_style=2), run])
    back = slab(F, 0, 2.0)
    spacer = slab(F.difference(slot), 2.0, 2.0 + CARD_SLOT)
    front = slab(F.difference(poly), 0, 1.8)
    back_part = screw_cuts(back + spacer, screws, 2.0 + CARD_SLOT) + slab(poly.buffer(-PLUG_GAP), -STEEL, 0)
    front_part = screw_cuts(front, screws, 1.8)
    return back_part, front_part, card


def rack_layout(F, slots=RACK_SLOTS):
    """Slots in outline F, placed left to right (as many of `slots` as fit), then spread to use the width. Each slot
    is (u of the downhill wall at floor height, width along u, bottom-band polygon, top-band polygon)."""
    x0, y0, x1, y1 = F.bounds
    vb, vt, fl = y0 + RACK_BAND, y1 - RACK_BAND, y0 + RACK_FLOOR
    t = math.tan(RACK_ANG)
    inner = F.buffer(-RACK_SIDE)
    top_out = sbox(-1e3, y1 - RACK_SIDE - 0.5, 1e3, y1 + 50)     # top slots break out through the top edge

    def para(ur, wc, v0, v1):
        return Polygon([(ur - wc + (v0 - fl) * t, v0), (ur + (v0 - fl) * t, v0), (ur + (v1 - fl) * t, v1), (ur - wc + (v1 - fl) * t, v1)])

    def fits(ur, wc):
        return (para(ur, wc, fl, vb + 0.5).difference(inner).area < 1e-3
                and para(ur, wc, vt - 0.5, y1 + 2).difference(inner.union(top_out)).area < 1e-3)

    urs, wcs, prev = [], [], -1e9
    for wp in slots:
        wc = wp / math.cos(RACK_ANG)
        ur = max(x0, prev + RACK_WALL + wc)
        while ur < x1 + 80 and not fits(ur, wc):
            ur += 0.25
        if ur >= x1 + 80:
            break
        urs.append(ur); wcs.append(wc); prev = ur
    slack = 0.0                                              # spread the slots: last one as far right as it goes
    while slack < x1 - x0 and fits(urs[-1] + slack + 0.25, wcs[-1]):
        slack += 0.25
    n = len(urs)
    urs = [ur + slack * i / max(1, n - 1) for i, ur in enumerate(urs)]
    return F, (vb, vt, fl), [(ur, wc, para(ur, wc, fl, vb + 0.5), para(ur, wc, vt - 0.5, y1 + 2)) for ur, wc in zip(urs, wcs)]


def pen_rack(poly, screws):
    F, (vb, vt, fl), slots = rack_layout(flange_outline(poly))
    top_w = FLANGE + RACK_CELL_D + RACK_FRONT
    bands = F.intersection(sbox(-1e3, -1e3, 1e3, vb)).union(F.intersection(sbox(-1e3, vt, 1e3, 1e3)))
    part = slab(F, 0, FLANGE) + slab(poly.buffer(-PLUG_GAP), -STEEL, 0) + slab(bands, FLANGE - 0.01, top_w)
    part = part - slab(unary_union([p for s in slots for p in s[2:]]), FLANGE, FLANGE + RACK_CELL_D)
    for u, v in screws:
        part = part - Pos(u, v, -50) * Cylinder(CLEAR / 2, 100, align=(Align.CENTER, Align.CENTER, Align.MIN))
        part = part - Pos(u, v, FLANGE - CB_H) * Cylinder(RACK_ACCESS / 2, 40, align=(Align.CENTER, Align.CENTER, Align.MIN))
    info = dict(slots=[dict(u=round(ur, 2), width=round(wc * math.cos(RACK_ANG), 1)) for ur, wc, *_ in slots],
                floor_v=round(fl, 2), ang=round(math.degrees(RACK_ANG), 1), w_back=FLANGE, cell_d=RACK_CELL_D)
    return part, info


def card_svg(path, card):
    """Card outline to plot and cut: 1:1 mm."""
    x0, y0, x1, y1 = card.bounds
    pts = " ".join(f"{x - x0 + 5:.2f},{y1 - y + 5:.2f}" for x, y in card.exterior.coords)
    w, h = x1 - x0 + 10, y1 - y0 + 10
    path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.1f}mm" height="{h:.1f}mm" viewBox="0 0 {w:.1f} {h:.1f}">'
                    f'<polygon points="{pts}" fill="none" stroke="#000" stroke-width="0.2"/></svg>')


def build(only=None):
    """All parts, or only the families named in `only` (e.g. {"penrack"}): the reliefs take minutes."""
    ops = openings()
    out, info = {}, {}
    if only:
        for name in ("power_right", "control"):
            poly, screws, kind = ops[name]
            out[f"penrack_{name}"], info[f"penrack_{name}"] = pen_rack(poly, screws)
        return out, info
    for name, (poly, screws, kind) in ops.items():
        out[f"nutframe_{name}"] = nut_frame(poly, screws)
        out[f"relief_{name}"] = relief(poly, screws, {"power_left": 30, "power_right": -30, "control": 20}[name])
        out[f"acrylic_bezel_{name}"] = acrylic_bezel(poly, screws)
    for name, side in (("power_left", "left"), ("control", "right")):
        poly, screws, kind = ops[name]
        back, front, card = card_frame(poly, screws, side)
        out[f"cardframe_{name}_back"], out[f"cardframe_{name}_front"] = back, front
        info[f"card_{name}"] = card
    for name in ("power_right", "control"):
        poly, screws, kind = ops[name]
        out[f"penrack_{name}"], info[f"penrack_{name}"] = pen_rack(poly, screws)
    return out, info


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    parts, info = build(set(sys.argv[1:]) or None)
    for name, part in parts.items():
        export_stl(part, str(OUT / f"{name}.stl"))
        bb = part.bounding_box()
        print(f"{name:34s} {bb.size.X:6.1f} x {bb.size.Y:5.1f} x {bb.size.Z:5.1f}  {part.volume / 1000:5.1f} cm3")
    for k, v in info.items():
        if k.startswith("card_"):
            card_svg(OUT / f"{k}_template.svg", v)
            print(f"{k}: card {v.bounds[2] - v.bounds[0]:.1f} x {v.bounds[3] - v.bounds[1]:.1f} mm -> {k}_template.svg")
        else:
            print(k, v)
    racks = {k[len("penrack_"):]: v for k, v in info.items() if k.startswith("penrack_")}
    if racks:                                   # slot positions, for the inspector's demo pens
        (OUT / "penrack.json").write_text(json.dumps(racks, indent=1))


if __name__ == "__main__":
    main()
