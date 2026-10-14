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

# pen cup: one open-top pocket across the bottom of the panel; pens drop in and lean on the plate
CUP_H_FRAC = 0.7                               # cup height = 70 % of the card height
CUP_DEPTH, CUP_WALL, CUP_FLOOR, CUP_SIDE = 22.0, 2.0, 3.0, 3.0

# logo mount (power front centre): spine through the keyhole slot, logo plate slides down onto it (E.LOGO)
LOGO_T, LOGO_SKIN, LOGO_GAP = 4.4, 1.1, 0.2   # plate thickness, solid front skin, plate off the steel
LUG = dict(h=12.0, narrow=7.2, wide=10.0, t=2.5, neck=4.0)
SPINE_PLATE = (30.0, 2.5)


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


def prism_wu(pts_uw, v0, v1):
    """Prism from a (u, w) outline, running along v from v0 to v1."""
    from build123d import BuildPart, BuildSketch, Plane, Polygon as BPolygon
    with BuildPart() as p:
        with BuildSketch(Plane.XZ.offset(-v0)):
            BPolygon(*pts_uw, align=None)
        extrude(amount=-(v1 - v0))
    return p.part


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
    bottom, as far apart as they go, clear of the rivnuts."""
    if name in _MAGS:
        return _MAGS[name]
    op, screws, _ = openings()[name]
    x0, y0, x1, y1 = op.bounds
    avoid = []
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


def cup_panel(name, op):
    """Rounded panel with one open-top cup across its bottom: 70 % of the card height, 22 mm deep inside."""
    outline = contour(name, op)
    part, top = base(name, op, outline)
    x0, y0, x1, y1 = outline.bounds
    card_h = op.bounds[3] - op.bounds[1] + 2 * ACR_MAR
    v0 = op.bounds[1] - ACR_MAR
    v1 = v0 + CUP_H_FRAC * card_h
    outer = sbox(x0 + CUP_SIDE, v0, x1 - CUP_SIDE, v1).intersection(outline.buffer(-1.0))
    inner = sbox(x0 + CUP_SIDE + CUP_WALL, v0 + CUP_FLOOR, x1 - CUP_SIDE - CUP_WALL, v1 + 1)
    part += slab(outer, top - 0.01, top + CUP_DEPTH + CUP_WALL)
    part -= slab(inner, top, top + CUP_DEPTH)
    ib = inner.bounds
    info = dict(u0=round(ib[0], 2), u1=round(ib[2], 2), floor_v=round(v0 + CUP_FLOOR, 2), top_v=round(v1, 2),
                w_back=round(top, 2), w_front=round(top + CUP_DEPTH, 2))
    return part, info


def logo_parts():
    """Spine (fits from inside: lugs out through the keyhole entries, then drops) and the logo plate (slides down
    from above; a hidden spring finger in its back clicks under the bottom lug). Assembled positions."""
    L = E.LOGO
    cx, (s0, s1) = L["cx"], L["slot"]
    lugs = [(v - L["drop"] - LUG["h"] / 2, v - L["drop"] + LUG["h"] / 2) for v in L["entries"]]   # seated lug spans
    STEEL = E.T
    # --- spine: inside plate behind the steel, neck through the slot, 2 dovetail lugs outside
    pw, pt = SPINE_PLATE
    rv0, rv1 = lugs[0][0], lugs[1][1]
    spine = slab(sbox(cx - pw / 2, rv0 - 6, cx + pw / 2, rv1 + 6).buffer(-3).buffer(3), -STEEL - pt, -STEEL)
    spine += slab(sbox(cx - LUG["neck"] / 2, rv0, cx + LUG["neck"] / 2, rv1), -STEEL - 0.01, LOGO_GAP + 0.01)
    for a, b in lugs:
        n, wd = LUG["narrow"] / 2, LUG["wide"] / 2
        spine += prism_wu([(cx - n, LOGO_GAP), (cx + n, LOGO_GAP), (cx + wd, LOGO_GAP + LUG["t"]), (cx - wd, LOGO_GAP + LUG["t"])], a, b)
    # --- logo plate
    W_, H_ = L["plate"]
    pv0, pv1 = L["cy"] - H_ / 2, L["cy"] + H_ / 2
    w0, w1 = LOGO_GAP, LOGO_GAP + LOGO_T
    plate = slab(sbox(cx - W_ / 2, pv0, cx + W_ / 2, pv1).buffer(-6).buffer(6), w0, w1)
    c = 0.2                                                   # dovetail channel: lug + 0.2, open at the bottom, stop above the top lug
    n, wd, dt = LUG["narrow"] / 2 + c, LUG["wide"] / 2 + c, LUG["t"] + c
    plate -= prism_wu([(cx - n, w0 - 1), (cx + n, w0 - 1), (cx + wd, w0 + dt), (cx - wd, w0 + dt)], pv0 - 1, lugs[1][1] + c)
    # spring finger beside the channel (+u side), root at its top end: cut free by a slit and a gap under the skin;
    # its nose sits under the seated bottom lug
    fu0, fu1, fv1 = cx + wd, cx + wd + 1.6, pv0 + 18.0
    plate -= slab(sbox(fu1, pv0 - 1, fu1 + 1.0, fv1), w0 - 1, w1 - LOGO_SKIN)                 # slit (back layer only)
    plate -= slab(sbox(cx + n, pv0 - 1, fu1 + 1.0, fv1), w0 + dt, w1 - LOGO_SKIN)             # gap between finger and skin
    lb = lugs[0][0]                                            # seated bottom lug's underside
    nose = Polygon([(fu0 + 0.2, lb - 4.2), (cx + n - 1.2, lb - 2.2), (cx + n - 1.2, lb - 2.0), (fu0 + 0.2, lb)])
    plate += slab(nose, w0, w0 + dt)
    return spine, plate


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
    for name, (op, _, _) in ops.items():
        out[f"cup_{name}"], info[f"cup_{name}"] = cup_panel(name, op)
    out["logo_spine"], out["logo_plate"] = logo_parts()
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
    meta = {"cups": {}, "card_front_w": {}, "cards": {}, "magnets": {n: [[round(u, 2), round(v, 2)] for u, v in magnets(n)] for n in openings()},
            "acrylic_w": PANEL_Z + 0.05}
    for k, v in info.items():
        if k.startswith("card_"):
            card_svg(OUT / f"{k}_template.svg", v)
            meta["cards"][k[len("card_"):]] = [[round(x, 2), round(y, 2)] for x, y in v.exterior.coords[:-1]]
            print(f"{k}: card {v.bounds[2] - v.bounds[0]:.1f} x {v.bounds[3] - v.bounds[1]:.1f} mm -> {k}_template.svg")
        elif k.startswith("cardfront_"):
            meta["card_front_w"][k[len("cardfront_"):]] = v
        else:
            meta["cups"][k[len("cup_"):]] = v
            print(k, v)
    (OUT / "meta.json").write_text(json.dumps(meta, indent=1))


if __name__ == "__main__":
    main()
