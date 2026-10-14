"""Window panels for the three front openings (power left, power right, control): a bolted bezel + magnetic panels.

Each window gets a thin bezel that stays on: it follows the opening, 13 mm wide and 3.5 mm thick, held by M3 screws
into the 4 rivnuts in the steel (button heads sunk flush, a recess in its back over each rivnut flange). It carries 4 Ø6 × 1.5 disc
magnets glued flush (N out), 2 on the top edge and 2 on the bottom. Every panel has 4 matching magnets glued flush
in its back (S in) and a 1 mm lip that drops just inside the opening, so it locates and pulls off by hand. A panel's
front can be any shape. Magnet pocket size comes from fit-kit coupon I.

    python3 hardware/parts/window_inserts.py           # writes hardware/out/window_inserts/*.stl + card templates (.svg)
    python3 hardware/parts/window_inserts.py fast      # skip the reliefs (they take minutes)

Frame: u = x across the front, v = height above the base underside, w = out of the steel (steel outer face w = 0).
Panels: power left = relief / acrylic / card; power right = relief / acrylic / pens; control = all four.
"""
import json
import math
import pathlib
import sys

from build123d import Align, Cylinder, Face, Pos, Vector, Wire, export_stl, extrude
from shapely.geometry import MultiPolygon, Point, Polygon, box as sbox
from shapely.ops import unary_union

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "sheet"))
import enclosure as E  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent.parent / "out" / "window_inserts"

# bezel (sizes come from the steel: E.WIN band = bezel width)
BEZEL_W, BEZEL_T = E.WIN["band"], 3.5
FLANGE_REC = (9.0, 1.0)                       # recess in the bezel's back over each rivnut's Ø8 flange
CLEAR, CB_D, CB_H = 3.4, 6.2, 1.8             # M3 clearance; counterbore for a button head (Ø5.7 × 1.65)
MAG_POCKET, MAG_DEPTH = 6.05, 1.6             # Ø6 × 1.5 magnets, glued 0.1 under the face: pocket from coupon I
MAG_OFF = 6.5                                 # magnet centres this far out from the opening edge
MAG_BOLT_CLEAR = 14.0                         # magnet centre to rivnut centre, at least

# panels
PANEL_Z = BEZEL_T                             # panels sit on the bezel
PLATE_T = 2.6                                 # 1.6 magnet pocket + 1.0 front skin
PANEL_OFF = E.WIN["band"] + E.WIN["rim"]      # panel edge: bezel + rim
LIP_IN, LIP_W, LIP_H = 0.3, 1.2, 1.5          # locating lip just inside the opening edge
MID_GAP = 0.5                                 # rectangular power panels stop this far short of the bar's centre line

# relief
RIB_H = 1.2
# acrylic panel: 3 mm acrylic = opening + 3 (vendor DXFs), in a pocket in the back of the frame, on the bezel
ACR_POCKET, ACR_MAR, ACR_LIP = 3.2, 3.0, 1.2
# card panel: rectangular; card sits in a 1 mm slot in front of the plate, behind a glued-on front frame
CARD_T = 0.4                                  # card inlay: card stock on a printed backer, 3 mm together

# pen rack: slotted bars at the window's slant, 15 mm proud. Pens go in capped and lean on the downhill wall of
# their slot, so any size sits at the same angle. The marker slot is cut through the plate (its back sits just
# over the bezel / inside the window) so a Ø15 marker fits under the same bars.
RACK_ANG = math.radians(40.0)
RACK_PROUD = 15.7
RACK_FRONT = 2.0
RACK_BAND = 14.0                              # bar height
RACK_FLOOR = 3.0                              # floor under the bottom slots
RACK_WALL = 3.0                               # between slots, along u
RACK_SIDE = 2.5                               # round the outside
RACK_SLOTS = [16.5, 13.0, 13.0, 13.0]         # widths square to the pen: marker (<= Ø15), 3 pens (<= Ø12)
MARKER_BACK = BEZEL_T + 0.3                   # marker slot back face (clears the bezel where it crosses it)
MARKER_WALL = 2.0                             # back wall under the marker, inside the window


def openings():
    """{name: (opening polygon (u, v), [4 screw points], box kind)}."""
    (pl, sl), (pr, sr) = E.window_panes()
    pc, sc = E.ctrl_window()
    return {"power_left": (pl, sl, "power"), "power_right": (pr, sr, "power"), "control": (pc, sc, "control")}


def side_clip(name):
    """Rectangular windows sit 30 mm apart or more: no panel needs clipping."""
    return None


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


def rounded(poly, r):
    return poly.buffer(-r, join_style=1).buffer(r, join_style=1)


def straight_edge(op, top):
    """u range of the opening's straight top (or bottom) edge."""
    x0, y0, x1, y1 = op.bounds
    v = y1 if top else y0
    us = [x for x, y in op.exterior.coords if abs(y - v) < 1e-6]
    return min(us), max(us)


# ---------------------------------------------------------------- magnets, bezel, panel base
_MAGS = {}


def magnets(name):
    """The window's 4 magnet centres, shared by its bezel and every panel: 2 on the straight top edge, 2 on the
    bottom, as far apart as they go, clear of the bolts and (pen windows) of where the marker slot crosses the top."""
    if name in _MAGS:
        return _MAGS[name]
    op, screws, _ = openings()[name]
    x0, y0, x1, y1 = op.bounds
    avoid = []
    if name in ("power_right", "control"):
        p = pen_layout(name)[3][0][2]
        b = p.intersection(sbox(-1e3, y1 + MAG_OFF - 4, 1e3, y1 + MAG_OFF + 4)).bounds
        if b:
            avoid.append((b[0] - 4, b[2] + 4))
    out = []
    for top in (True, False):
        v = y1 + MAG_OFF if top else y0 - MAG_OFF
        a, b = straight_edge(op, top)
        ok = [a + 3 + 0.5 * i for i in range(int((b - a - 6) / 0.5) + 1)]
        ok = [u for u in ok if all(math.hypot(u - su, v - sv) >= MAG_BOLT_CLEAR for su, sv in screws)
              and not (top and any(lo <= u <= hi for lo, hi in avoid))]
        out += [(min(ok), v), (max(ok), v)]
    _MAGS[name] = out
    return out


def mag_pockets(name, w0, w1):
    return unary_union([Point(u, v).buffer(MAG_POCKET / 2, 48) for u, v in magnets(name)]), w0, w1


def bezel(name, op, screws):
    """Bolted bezel round the opening; magnet pockets open on the front."""
    part = slab(op.buffer(BEZEL_W, join_style=1, quad_segs=8).difference(op), 0, BEZEL_T)
    for u, v in screws:
        part -= Pos(u, v, -1) * Cylinder(CLEAR / 2, BEZEL_T + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
        part -= Pos(u, v, BEZEL_T - CB_H) * Cylinder(CB_D / 2, 5, align=(Align.CENTER, Align.CENTER, Align.MIN))
        part -= Pos(u, v, -1) * Cylinder(FLANGE_REC[0] / 2, FLANGE_REC[1] + 1, align=(Align.CENTER, Align.CENTER, Align.MIN))
    m, _, _ = mag_pockets(name, 0, 0)
    return part - slab(m, BEZEL_T - MAG_DEPTH, BEZEL_T + 1)


def base(name, op, outline, plate_t=PLATE_T, lip=True):
    """Panel plate on the bezel: magnet pockets open on the back, locating lip inside the opening.
    Returns (part, plate front w)."""
    part = slab(outline, PANEL_Z, PANEL_Z + plate_t)
    m, _, _ = mag_pockets(name, 0, 0)
    part -= slab(m, PANEL_Z - 1, PANEL_Z + MAG_DEPTH)
    if lip:
        ring = op.buffer(-LIP_IN, join_style=1).difference(op.buffer(-LIP_IN - LIP_W, join_style=1))
        part += slab(ring, PANEL_Z - LIP_H, PANEL_Z + 0.01)
    return part, PANEL_Z + plate_t


def contour(name, op):
    o = op.buffer(PANEL_OFF, join_style=1, quad_segs=8)
    c = side_clip(name)
    return o.intersection(c) if c is not None else o


def rect(name, op, extra_right=0.0):
    x0, y0, x1, y1 = op.buffer(PANEL_OFF).bounds
    r = rounded(sbox(x0, y0, x1 + extra_right, y1), E.WIN["r"] + PANEL_OFF)   # same corners as the other panels
    c = side_clip(name)
    return r.intersection(c) if c is not None else r


# ---------------------------------------------------------------- panels
def relief_panel(name, op, seed_shift):
    """Contour panel with raised topographic ribs."""
    outline = contour(name, op)
    part, top = base(name, op, outline)
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


def inlay_panel(name, op):
    """Frame with a 3 mm inlay in a pocket in its back: the window acrylic (opening + 3, the vendor DXF) or a card on
    a printed backer, same outline. The inlay sits on the bezel; pull the panel off to swap it. No locating lip: the
    inlay covers the opening edge."""
    outline = contour(name, op)
    part, top = base(name, op, outline, ACR_POCKET + ACR_LIP, lip=False)
    part -= slab(op, PANEL_Z - 1, top + 1)
    part -= slab(inlay_outline(op).buffer(0.2, join_style=1, quad_segs=8), PANEL_Z - 1, PANEL_Z + ACR_POCKET)
    return part


def inlay_outline(op):
    return op.buffer(ACR_MAR, join_style=1, quad_segs=8)


def card_backer(op):
    """Printed backer for a card inlay: inlay outline, 3 mm less the card (card ~0.3 sits in front of it)."""
    return slab(inlay_outline(op), PANEL_Z + 0.05, PANEL_Z + ACR_POCKET - CARD_T)


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


_PENS = {}


def pen_layout(name):
    """Rectangular outline (widened on the right until the 4 slots fit) and the slot layout."""
    if name not in _PENS:
        op = openings()[name][0]
        deep_ok = op.buffer(-(MARKER_WALL + 0.5), join_style=1)   # marker back wall stays inside the window
        for ext in range(0, 61, 2):
            outline = rect(name, op, ext)
            bars, fl, slots = rack_layout(outline, RACK_SLOTS, deep_ok, op)
            if len(slots) == len(RACK_SLOTS):
                break
        _PENS[name] = (outline, bars, fl, slots)
    return _PENS[name]


def pen_panel(name, op):
    """Rectangular panel, two slotted bars; marker slot first (left), cut through the plate."""
    outline, (vb0, vb1, vt0, vt1), fl, slots = pen_layout(name)
    part, top = base(name, op, outline)
    front = top + RACK_PROUD
    bars = outline.intersection(sbox(-1e3, vb0, 1e3, vb1)).union(outline.intersection(sbox(-1e3, vt0, 1e3, vt1)))
    part += slab(bars, top - 0.01, front)
    cell_front = front - RACK_FRONT
    for i, (ur, wc, p) in enumerate(slots):
        if i == 0:                                           # through the plate; back walls under the bars, in the window
            part -= slab(p.intersection(outline.buffer(1)), PANEL_Z - LIP_H - 0.5, cell_front)
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
        out[f"bezel_{name}"] = bezel(name, op, screws)
        out[f"inlay_{name}"] = inlay_panel(name, op)
        if not fast:
            out[f"relief_{name}"] = relief_panel(name, op, {"power_left": 30, "power_right": -30, "control": 20}[name])
    for name, (op, _, _) in ops.items():
        out[f"cardbacker_{name}"] = card_backer(op)
        info[f"card_{name}"] = inlay_outline(op)
        info[f"cardfront_{name}"] = round(PANEL_Z + ACR_POCKET - CARD_T, 2)
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
    meta = {"racks": {}, "card_front_w": {}, "cards": {}, "magnets": {n: [[round(u, 2), round(v, 2)] for u, v in magnets(n)] for n in openings()},
            "acrylic_w": PANEL_Z + 0.05}
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
