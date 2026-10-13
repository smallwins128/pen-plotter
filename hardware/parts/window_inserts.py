"""Window panels for the three front openings (power left, power right, control): a bolted strip + snap-on panels.

Each window gets a bezel strip that stays on: it follows the opening, 11 mm wide and 6 mm tall, held by M3 bolts
through the 4 holes already cut in the steel (heads countersunk in the strip, nuts inside). Its outer edge has a
45° groove all round. Panels cover the strip and snap onto it: a skirt round the strip carries 4 latches (thin
walls joined to the panel only at their ends, so they bow out) whose barbs click into the groove, and pull off by
hand. A panel's front can be any shape. Barb size comes from fit-kit coupon I.

    python3 hardware/parts/window_inserts.py           # writes hardware/out/window_inserts/*.stl + card templates (.svg)
    python3 hardware/parts/window_inserts.py fast      # skip the reliefs (they take minutes)

Frame: u = x across the front, v = height above the base underside, w = out of the steel (steel outer face w = 0).
Panels: power left = relief / acrylic / card; power right = relief / acrylic / pens; control = all four.
"""
import json
import math
import pathlib
import sys

from build123d import (Align, BuildPart, BuildSketch, Cylinder, Face, Plane, Polygon as BPolygon, Pos, Vector, Wire,
                       export_stl, extrude)
from shapely.geometry import MultiPolygon, Point, Polygon, box as sbox
from shapely.ops import unary_union

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "sheet"))
import enclosure as E  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent.parent / "out" / "window_inserts"

# strip: outer edge offset from the opening, by height above the steel (w). 45° groove, 1 mm deep, centre w = 3.1
STRIP_H = 6.0
STRIP_EDGE = [(0.0, 11.0), (1.6, 11.0), (2.6, 10.0), (3.6, 10.0), (4.6, 11.0), (5.4, 11.0), (6.0, 10.4)]
CLEAR, CB_D, CB_H = 3.4, 6.2, 1.8             # M3 clearance; counterbore for a button head (Ø5.7 × 1.65)

# panels
PANEL_Z = STRIP_H + 0.4                       # underside of the panel plate (0.4 over the strip)
PLATE_T = 3.0
SKIRT = (11.2, 12.8)                          # skirt inner / outer offset from the opening (0.2 off the strip)
PANEL_OFF = 14.3                              # panel edge offset for contour panels (skirt + 1.5 rim)
STEEL_GAP = 0.4                               # skirt bottom above the steel
LATCH_L, LATCH_GAP, BARB_L, BARB_ZC = 30.0, 0.7, 20.0, 3.1
BARB = 0.8                                    # barb proud of the skirt: set from coupon I (0.6 / 0.8 / 1.0)
MID_GAP = 0.5                                 # rectangular power panels stop this far short of the bar's centre line

# relief
RIB_H = 1.2
# acrylic panel: 3 mm acrylic = opening + 3 (vendor DXFs), in a pocket in the back of a 5 mm plate
ACR_PLATE, ACR_POCKET, ACR_MAR = 5.0, 3.2, 3.0
# card panel: rectangular; card sits in a 1 mm slot in front of the plate, behind a glued-on front frame
CARD_SLOT, CARD_FRAME_T, CARD_RIM, CARD_MAR = 1.0, 1.8, 9.0, 3.0

# pen rack: slotted bars at the window's slant, 15 mm proud. Pens go in capped and lean on the downhill wall of
# their slot, so any size sits at the same angle. The marker slot is cut through the plate (its back sits just
# over the strip / inside the window) so a Ø15 marker fits under the same 15 mm bars.
RACK_ANG = math.radians(E.WIN["ang"])
RACK_PROUD = 15.0
RACK_FRONT = 2.0
RACK_BAND = 14.0                              # bar height
RACK_FLOOR = 3.0                              # floor under the bottom slots
RACK_WALL = 3.0                               # between slots, along u
RACK_SIDE = 2.5                               # round the outside
RACK_SLOTS = [16.5, 13.0, 13.0, 13.0]         # widths square to the pen: marker (<= Ø15), 3 pens (<= Ø12)
MARKER_BACK = PANEL_Z + 0.2                   # marker slot back face (over the strip top at 6.0)
MARKER_WALL = 2.0                             # back wall under the marker, inside the window


def openings():
    """{name: (opening polygon (u, v), [4 screw points], box kind)}."""
    (pl, sl), (pr, sr) = E.window_panes()
    pc, sc = E.ctrl_window()
    return {"power_left": (pl, sl, "power"), "power_right": (pr, sr, "power"), "control": (pc, sc, "control")}


def side_clip(name):
    """Half-plane a power panel must stay in: its own side of the slanted bar between the two windows."""
    if name == "control":
        return None
    t, cy, s = math.tan(RACK_ANG), E.WIN["cy"], 1 if name == "power_right" else -1
    big = 1e3
    line = lambda v: (v - cy) * t
    if s > 0:
        return Polygon([(line(-big) + MID_GAP, -big), (big, -big), (big, big), (line(big) + MID_GAP, big)])
    return Polygon([(-big, -big), (line(-big) - MID_GAP, -big), (line(big) - MID_GAP, big), (-big, big)])


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
        if p.area < 1e-6:
            continue
        s = extrude(Pos(0, 0, w0) * face(p), amount=w1 - w0, dir=(0, 0, 1))   # shapely rings can wind either way
        out = s if out is None else out + s
    return out


def prism_uv(pts_vw, u0, u1):
    """Prism from a (v, w) outline, running along u from u0 to u1."""
    with BuildPart() as p:
        with BuildSketch(Plane.YZ.offset(u0)):
            BPolygon(*pts_vw, align=None)
        extrude(amount=u1 - u0)
    return p.part


def rounded(poly, r):
    return poly.buffer(-r, join_style=1).buffer(r, join_style=1)


def straight_edge(op, top):
    """u range of the opening's straight top (or bottom) edge."""
    x0, y0, x1, y1 = op.bounds
    v = y1 if top else y0
    us = [x for x, y in op.exterior.coords if abs(y - v) < 1e-6]
    return min(us), max(us)


# ---------------------------------------------------------------- the strip
def strip(name, op, screws):
    """Bolted strip: ring round the opening, groove on the outer edge (stacked slabs; 45° faces in 0.25 mm steps)."""
    clip = side_clip(name)
    def ring(off):
        r = op.buffer(off, join_style=1, quad_segs=8).difference(op)
        return r.intersection(clip) if clip is not None else r
    z, parts = 0.0, []
    for (z0, o0), (z1, o1) in zip(STRIP_EDGE, STRIP_EDGE[1:]):
        n = 1 if abs(o1 - o0) < 1e-9 else max(1, round((z1 - z0) / 0.25))
        for k in range(n):
            za, zb = z0 + (z1 - z0) * k / n, z0 + (z1 - z0) * (k + 1) / n
            parts.append((za, zb, o0 + (o1 - o0) * (k + 0.5) / n))
    part = None
    for za, zb, off in parts:
        s = slab(ring(off), za, zb)
        part = s if part is None else part + s
    for u, v in screws:
        part -= Pos(u, v, -1) * Cylinder(CLEAR / 2, STRIP_H + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
        part -= Pos(u, v, STRIP_H - CB_H) * Cylinder(CB_D / 2, 5, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return part


# ---------------------------------------------------------------- the snap base every panel shares
def latch_spots(op, avoid=None):
    """Latch centres: 2 on the straight top edge, 2 on the straight bottom edge (1 if the edge is short).
    Slid along the edge to keep clear of `avoid` (u ranges the plate is cut through at that edge)."""
    out = []
    for top in (True, False):
        a, b = straight_edge(op, top)
        a, b = a + LATCH_L / 2 + 3, b - LATCH_L / 2 - 3
        cs = [(a + b) / 2] if b - a < LATCH_L + 10 else [a + (b - a) / 4, a + 3 * (b - a) / 4]
        for c in cs:
            for d in [0] + [s * k for k in range(1, 200) for s in (1, -1)]:
                cc = c + d * 0.5
                if a <= cc <= b and not any(lo - 2 < cc + LATCH_L / 2 and cc - LATCH_L / 2 < hi + 2 for lo, hi in (avoid or {}).get(top, [])):
                    out.append((top, cc)); break
    return out


def snap_base(name, op, outline, plate_t=PLATE_T, avoid=None):
    """Plate over the strip + skirt round it with 4 latches. Returns (part, plate top w)."""
    clip = side_clip(name)
    x0, y0, x1, y1 = op.bounds
    ring = op.buffer(SKIRT[1], join_style=1, quad_segs=8).difference(op.buffer(SKIRT[0], join_style=1, quad_segs=8))
    if clip is not None:
        ring = ring.intersection(clip)
    spots = latch_spots(op, avoid)
    gaps = [sbox(c - LATCH_L / 2, (y1 if top else y0 - 20), c + LATCH_L / 2, (y1 + 20 if top else y0)) for top, c in spots]
    skirt = slab(ring, STEEL_GAP, PANEL_Z - LATCH_GAP) + slab(ring.difference(unary_union(gaps)), PANEL_Z - LATCH_GAP - 0.01, PANEL_Z + 0.01)
    part = skirt + slab(outline, PANEL_Z, PANEL_Z + plate_t)
    for top, c in spots:                                     # barbs on the skirt's inner face, pointing at the groove
        vf = y1 + SKIRT[0] if top else y0 - SKIRT[0]
        s = -1 if top else 1
        pts = [(vf - s * 0.01, BARB_ZC - 0.5 - BARB), (vf + s * BARB, BARB_ZC - 0.5), (vf + s * BARB, BARB_ZC + 0.5), (vf - s * 0.01, BARB_ZC + 0.5 + BARB)]
        part += prism_uv(pts, c - BARB_L / 2, c + BARB_L / 2)
    return part, PANEL_Z + plate_t


def contour(name, op):
    o = op.buffer(PANEL_OFF, join_style=1, quad_segs=8)
    c = side_clip(name)
    return o.intersection(c) if c is not None else o


def rect(name, op, extra_right=0.0):
    x0, y0, x1, y1 = op.buffer(PANEL_OFF).bounds
    r = rounded(sbox(x0, y0, x1 + extra_right, y1), 3.0)
    c = side_clip(name)
    return r.intersection(c) if c is not None else r


# ---------------------------------------------------------------- panels
def relief_panel(name, op, seed_shift):
    """Contour panel with raised topographic ribs."""
    outline = contour(name, op)
    part, top = snap_base(name, op, outline)
    c = Point(op.centroid.x + seed_shift, op.centroid.y - 2)
    ribs = []
    for k in range(1, 40):
        ring = c.buffer(k * 3.6, 96)
        ring = Polygon([(x + 1.6 * math.sin(y / 5.0 + k * 0.7), y + 0.8 * math.sin(x / 9.0 + k)) for x, y in ring.exterior.coords])
        ribs.append(ring.difference(ring.buffer(-1.0)))
    ribs = unary_union(ribs).intersection(outline.buffer(-1.2))
    if not ribs.is_empty:
        part += slab(ribs.buffer(0), top - 0.01, top + RIB_H)
    return part


def acrylic_panel(name, op):
    """Contour frame, 5 mm: the acrylic (opening + 3) sits in a pocket in its back, against the strip."""
    outline = contour(name, op)
    part, top = snap_base(name, op, outline, ACR_PLATE)
    part -= slab(op, PANEL_Z - 1, top + 1)
    part -= slab(op.buffer(ACR_MAR + 0.2, join_style=1, quad_segs=8), PANEL_Z - 1, PANEL_Z + ACR_POCKET)
    return part


def card_panel(name, op, open_side):
    """Rectangular. Back: plate + skirt + a spacer that leaves a 1 mm card slot, open on one side. Front: a thin
    frame, printed flat and glued on once. The card slides in from the side."""
    outline = rect(name, op)
    part, top = snap_base(name, op, outline)
    x0, y0, x1, y1 = outline.bounds
    aperture = rounded(sbox(x0 + CARD_RIM, y0 + CARD_RIM, x1 - CARD_RIM, y1 - CARD_RIM), 2.0)
    if name == "power_left":                                  # keep the frame rim even along the slanted cut
        aperture = aperture.intersection(outline.buffer(-CARD_RIM))
    card = rounded(aperture.buffer(CARD_MAR, join_style=2), 1.0)
    cx0, cy0, cx1, cy1 = card.bounds
    run = sbox(x0 - 1, cy0 - 0.3, cx0 + 1, cy1 + 0.3) if open_side == "left" else sbox(cx1 - 1, cy0 - 0.3, x1 + 1, cy1 + 0.3)
    slot = unary_union([card.buffer(0.3, join_style=2), run])
    part += slab(outline.difference(slot), top - 0.01, top + CARD_SLOT)
    front = slab(outline.difference(aperture), 0, CARD_FRAME_T)     # modelled flat, sits at w = top + CARD_SLOT
    return part, front, card, top + CARD_SLOT


def rack_layout(F, slots, deep_ok, op):
    """Slots placed left to right inside outline F, then spread to use the width. The bars sit across the window
    rows (so the marker slot, cut through the plate, has the window behind it); deep_ok: where the marker slot may
    sit. Returns (bars (vb0, vb1, vt0, vt1), floor v, slots), each slot (u of the downhill wall at floor height,
    width along u, polygon from the floor up past the top bar)."""
    x0, y0, x1, y1 = F.bounds
    t = math.tan(RACK_ANG)
    inner = F.buffer(-RACK_SIDE)
    oy0, oy1 = op.bounds[1], op.bounds[3]
    fl = oy0 + MARKER_WALL + 0.5
    vb0, vb1 = fl - RACK_FLOOR, fl - RACK_FLOOR + RACK_BAND
    vt1 = oy1 - MARKER_WALL - 0.5
    vt0 = vt1 - RACK_BAND

    def para(ur, wc, v0, v1):
        return Polygon([(ur - wc + (v0 - fl) * t, v0), (ur + (v0 - fl) * t, v0), (ur + (v1 - fl) * t, v1), (ur - wc + (v1 - fl) * t, v1)])

    def fits(i, ur, wc):
        region = deep_ok if i == 0 else inner
        return (para(ur, wc, fl, vb1).difference(region).area < 1e-3
                and para(ur, wc, vt0, vt1).difference(region).area < 1e-3)

    urs, wcs, prev = [], [], -1e9
    for i, wp in enumerate(slots):
        wc = wp / math.cos(RACK_ANG)
        ur = max(x0, prev + RACK_WALL + wc)
        while ur < x1 + 80 and not fits(i, ur, wc):
            ur += 0.25
        if ur >= x1 + 80:
            break
        urs.append(ur); wcs.append(wc); prev = ur
    slack = 0.0                                              # spread the pen slots: last one as far right as it goes
    while slack < x1 - x0 and fits(len(urs) - 1, urs[-1] + slack + 0.25, wcs[-1]):
        slack += 0.25
    n = len(urs)
    urs = urs[:1] + [ur + slack * i / max(1, n - 1) for i, ur in enumerate(urs) if i]
    return (vb0, vb1, vt0, vt1), fl, [(ur, wc, para(ur, wc, fl, vt1 + 40)) for ur, wc in zip(urs, wcs)]


def pen_panel(name, op):
    """Rectangular panel, two slotted bars 15 mm proud; marker slot first (left), cut through the plate."""
    ext = 20.0 if name == "control" else 0.0                 # control: 20 mm more on the right for the 3rd pen
    outline = rect(name, op, ext)
    deep_ok = op.buffer(-(MARKER_WALL + 0.5), join_style=1)  # marker back wall stays inside the window
    (vb0, vb1, vt0, vt1), fl, slots = rack_layout(outline, RACK_SLOTS, deep_ok, op)
    marker = slots[0][2]
    x0, y0, x1, y1 = op.bounds
    # where the marker's plate cut crosses the panel's top and bottom edges: keep latches away from it
    cut_top = marker.intersection(sbox(-1e3, y1 + SKIRT[0] - 1, 1e3, y1 + SKIRT[1] + 1)).bounds
    avoid = {True: [(cut_top[0], cut_top[2])] if cut_top else [], False: []}
    part, top = snap_base(name, op, outline, avoid=avoid)
    front = top + RACK_PROUD
    bands = outline.intersection(sbox(-1e3, vb0, 1e3, vb1)).union(outline.intersection(sbox(-1e3, vt0, 1e3, vt1)))
    part += slab(bands, top - 0.01, front)
    cell_front = front - RACK_FRONT
    for i, (ur, wc, p) in enumerate(slots):
        if i == 0:                                           # through the plate; back walls under the bars, in the window
            part -= slab(p.intersection(outline.buffer(1)), PANEL_Z - 0.01, cell_front)
            pb = p.buffer(MARKER_WALL, join_style=2)
            back = unary_union([pb.intersection(sbox(-1e3, fl - MARKER_WALL, 1e3, vb1)), pb.intersection(sbox(-1e3, vt0, 1e3, vt1))])
            part += slab(back.intersection(op.buffer(-0.5)), MARKER_BACK - MARKER_WALL, MARKER_BACK)
        else:
            part -= slab(p.intersection(outline.buffer(1)), top, cell_front)
    info = dict(slots=[dict(u=round(ur, 2), width=round(wc * math.cos(RACK_ANG), 1), w_back=round(MARKER_BACK if i == 0 else top, 2))
                       for i, (ur, wc, _) in enumerate(slots)], floor_v=round(fl, 2), ang=round(math.degrees(RACK_ANG), 1))
    return part, info


def card_svg(path, card):
    """Card outline to plot and cut: 1:1 mm."""
    x0, y0, x1, y1 = card.bounds
    pts = " ".join(f"{x - x0 + 5:.2f},{y1 - y + 5:.2f}" for x, y in card.exterior.coords)
    w, h = x1 - x0 + 10, y1 - y0 + 10
    path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.1f}mm" height="{h:.1f}mm" viewBox="0 0 {w:.1f} {h:.1f}">'
                    f'<polygon points="{pts}" fill="none" stroke="#000" stroke-width="0.2"/></svg>')


def build(fast=False):
    ops = openings()
    out, info = {}, {}
    for name, (op, screws, kind) in ops.items():
        out[f"strip_{name}"] = strip(name, op, screws)
        out[f"acrylic_{name}"] = acrylic_panel(name, op)
        if not fast:
            out[f"relief_{name}"] = relief_panel(name, op, {"power_left": 30, "power_right": -30, "control": 20}[name])
    for name, side in (("power_left", "left"), ("control", "right")):
        back, front, card, w_front = card_panel(name, ops[name][0], side)
        out[f"card_{name}_back"], out[f"card_{name}_front"] = back, front
        info[f"card_{name}"] = card
        info[f"cardfront_{name}"] = round(w_front, 2)
    for name in ("power_right", "control"):
        out[f"pens_{name}"], info[f"pens_{name}"] = pen_panel(name, ops[name][0])
    return out, info


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fast = "fast" in sys.argv[1:]
    if not fast:                                  # full build: clear out parts from older versions
        for old in OUT.glob("*.stl"):
            old.unlink()
    parts, info = build(fast)
    for name, part in parts.items():
        export_stl(part, str(OUT / f"{name}.stl"))
        bb = part.bounding_box()
        print(f"{name:26s} {bb.size.X:6.1f} x {bb.size.Y:5.1f} x {bb.size.Z:5.1f}  {part.volume / 1000:5.1f} cm3")
    meta = {"racks": {}, "card_front_w": {}, "cards": {}}
    for k, v in info.items():
        if k.startswith("card_"):
            card_svg(OUT / f"{k}_template.svg", v)
            meta["cards"][k[len("card_"):]] = [[round(x, 2), round(y, 2)] for x, y in v.exterior.coords[:-1]]
            print(f"{k}: card {v.bounds[2] - v.bounds[0]:.1f} x {v.bounds[3] - v.bounds[1]:.1f} mm -> {k}_template.svg")
        elif k.startswith("cardfront_"):
            meta["card_front_w"][k[len("cardfront_"):]] = v
        else:
            meta["racks"][k[len("pens_"):]] = v
            print(k, v)
    (OUT / "meta.json").write_text(json.dumps(meta, indent=1))


if __name__ == "__main__":
    main()
