"""R09 Cedar: a bench power supply. An ATX PSU stands on its side between two printed end plates, and DIN rails
run between the plates (Allwin, lo-fi v1 "Tower", 2026-11-02). CAD run 1, 2026-11-03.

    front (user side)   terminal rail at 165 mm, Proto 1 at 105, Proto 2 at 45 (rail centres, 60 apart)
    back                two rails behind the PSU: stretchers, and a free back face for later panels
    under               one rail lying flat, web up: the PSU sits on it
    top                 a deck with the HY-Z09 breakout board, over the cable bay
    right plate         window for the PSU's back face (fan, IEC socket, mains switch); 4 corner pads for its screws
    left plate          cable-bay side: vent slots, grip

Rails fix to the plates on printed tabs. Each tab has a nut channel running along the rail: an M3 nut slides in from
the tab's free end, and an M3 x 6 pan head + washer goes through whichever rail slot lands over the tab. Slots sit
wherever the rail was cut, so a channel (not a fixed insert) is what makes every piece fit.
Front rails: the tab sits behind the web, the screw comes from the module side. Rear and base rails: the tab sits
inside the hat channel and the screw comes through the web from outside. The base rail is screwed only at the left
(bay) end: at the right end the PSU sits on it, so that tab is a plain tongue.

Frame (mm): x along the rails (0 = left plate's inner face, 203 = right plate's inner face), y up (0 = bench),
z toward the user (0 = back face).

Placeholders, until measured: KV121 10 x 40 x 45; HY-Z09 80 x 70 (holes 3.5 in from its corners); rail slots 5.2 x 15
at 25 pitch; PSU screw holes 6 in from the face corners.

    python3 hardware/parts/cedar/cedar.py          # checks only
    python3 hardware/parts/cedar/cedar.py --stl    # also meshes: hardware/out/cedar/*.stl + summary.json
"""
import itertools
import json
import math
import pathlib
import sys

from build123d import Box, Cylinder, Plane, Pos, Rot, export_stl
from shapely.geometry import Point, Polygon, box as sbox
from shapely.ops import unary_union

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from window_inserts import slab  # noqa: E402

OUT = HERE.parent.parent / "out" / "cedar"

# --- bought parts (measured or placeholder) ---
SPAN = 203.0                                 # rail piece length = inner span between plates (measured, 2026-11-03)
RAIL_W, RAIL_H, RAIL_WEB, RAIL_T = 35.0, 7.5, 27.0, 1.0      # TS35 x 7.5
SLOT_W, SLOT_L, SLOT_P = 5.2, 15.0, 25.0     # placeholder
PSU_L, PSU_H, PSU_D = 140.0, 150.0, 87.0     # on its side: 140 along x, 150 up, 87 deep (Allwin, 2026-11-02)
KV_W, KV_H, KV_D = 10.0, 40.0, 45.0          # placeholder: width along rail, height across it, depth out from the web
BOARD_W, BOARD_D, BOARD_T, BOARD_HOLE_IN = 80.0, 70.0, 1.6, 3.5   # placeholder

# --- printed parts ---
PT = 6.0                                     # plate thickness
PLATE_D, TOE_D, PLATE_H, TOP_R = 112.0, 140.0, 215.0, 12.0
TAB_L = 30.0                                 # tabs run 30 along the rail from the plate face
NUT_AF, NUT_T = 5.5, 2.4                     # M3 nut
CH_W, CH_H, SKIN = NUT_AF + 0.4, NUT_T + 0.3, 1.2   # nut channel; skin between the rail web and the nut
SCREW_RANGE = (3.0, TAB_L - 3.0)             # where a screw can sit along the tab
INSERT_BORE, INSERT_DEPTH = 4.2, 4.5         # M3 heat-set inserts (as the fume extractor)
M3_CLEAR, CSK_D = 3.4, 6.4

# --- layout ---
PSU_X0, PSU_Y0, PSU_Z0 = SPAN - PSU_L, RAIL_H, 9.0          # PSU back face on the right plate, on the base rail
PSU_Z1 = PSU_Z0 + PSU_D                                     # 96
FRONT_YC = {"terminals": 165.0, "proto1": 105.0, "proto2": 45.0}
FRONT_TAB_Z = (PSU_Z1 + 1.0, PSU_Z1 + 6.5)                  # 97 .. 102.5, 1 mm clear of the PSU
FRONT_WEB_Z = FRONT_TAB_Z[1]                                # rail web's back face
REAR_YC = (45.0, 165.0)
BASE_ZC = PSU_Z0 + PSU_D / 2                                # 52.5, under the PSU's middle
CH_IN = RAIL_WEB / 2 - RAIL_T - 0.3                         # half-width of a tab inside a hat channel (12.2)
DECK_Y, DECK_T = 172.0, 4.0
DECK_Z = (PSU_Z0, PSU_Z1)
DECK_TAB = dict(x=12.0, y=(DECK_Y - 8.0, DECK_Y), z=(30.0, 75.0), ins_z=(38.0, 67.0))
CABLE_SLOT = dict(x=(10.0, 58.0), z=(11.0, 19.0))
STANDOFF_H, STANDOFF_D = 5.0, 7.5
BOARD_X0, BOARD_Z0 = 8.0, 20.0
WIN_LIP, PAD = 5.0, 13.0                     # right plate: window lip, corner pad size (carries the PSU screw)
PSU_HOLE_IN, PSU_HOLE_D = 6.0, 3.6           # placeholder: #6-32 clearance, 6 in from the face corners
VENTS = dict(z=(37.0, 49.0, 61.0, 73.0), w=6.0, y=(40.0, 140.0))
GRIP = dict(z=(30.0, 80.0), y=(192.0, 204.0))
BED = 256.0                                  # Bambu A1
PLA = 1.24


def bx(x0, x1, y0, y1, z0, z1):
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


def cyl(axis, c, r, a0, a1):
    """Cylinder of radius r along `axis` ('x', 'y' or 'z') from a0 to a1, through point c (the other two coords)."""
    h, m = a1 - a0, (a0 + a1) / 2
    if axis == "z":
        return Pos(c[0], c[1], m) * Cylinder(r, h)
    if axis == "y":
        return Pos(c[0], m, c[1]) * (Rot(90, 0, 0) * Cylinder(r, h))
    return Pos(m, c[0], c[1]) * (Rot(0, 90, 0) * Cylinder(r, h))


# ------------------------------------------------------------------ plates
def plate_outline():
    """End-plate outline in (z, y)."""
    body = sbox(0, 0, PLATE_D, PLATE_H - TOP_R).union(sbox(TOP_R, 0, PLATE_D - TOP_R, PLATE_H))
    body = body.union(Point(TOP_R, PLATE_H - TOP_R).buffer(TOP_R, 32)).union(Point(PLATE_D - TOP_R, PLATE_H - TOP_R).buffer(TOP_R, 32))
    toe = Polygon([(PLATE_D - 1, 0), (TOE_D, 0), (TOE_D, 5.0), (PLATE_D - 1, 24.0)])
    grip = sbox(GRIP["z"][0] + 6, GRIP["y"][0], GRIP["z"][1] - 6, GRIP["y"][1]).union(
        Point(GRIP["z"][0] + 6, sum(GRIP["y"]) / 2).buffer(6, 24)).union(Point(GRIP["z"][1] - 6, sum(GRIP["y"]) / 2).buffer(6, 24))
    return body.union(toe).difference(grip)


def psu_window():
    """Right plate's window over the PSU's back face, in (z, y), with the 4 corner pads left in."""
    z0, z1, y0, y1 = PSU_Z0, PSU_Z1, PSU_Y0, PSU_Y0 + PSU_H
    win = sbox(z0 + WIN_LIP, y0 + WIN_LIP, z1 - WIN_LIP, y1 - WIN_LIP)
    for cz, cy in itertools.product((z0, z1 - PAD), (y0, y1 - PAD)):
        win = win.difference(sbox(cz, cy, cz + PAD, cy + PAD))
    return win


def psu_holes():
    z0, z1, y0, y1 = PSU_Z0, PSU_Z1, PSU_Y0, PSU_Y0 + PSU_H
    return [(z, y) for z in (z0 + PSU_HOLE_IN, z1 - PSU_HOLE_IN) for y in (y0 + PSU_HOLE_IN, y1 - PSU_HOLE_IN)]


def plate_slab(outline, x0):
    """Extrude a (z, y) outline across x from x0 to x0 + PT. Local u = -z, v = y, w = x."""
    flip = Polygon([(-z, y) for z, y in outline.exterior.coords], [[(-z, y) for z, y in r.coords] for r in outline.interiors])
    pl = Plane(origin=(x0, 0, 0), x_dir=(0, 0, -1), z_dir=(1, 0, 0))
    return pl.location * slab(flip, 0, PT)


def channel(axis_face, xa, xb, c, face):
    """Nut channel along x under a tab face. axis_face: 'z+' (face at depth `face`, nut below it toward -z), 'z-' (face
    at `face`, nut toward +z), 'y-' (face at height `face`, nut below). c = the across-rail centre (y for z-faces, z for y)."""
    x0, x1 = xa, xb
    out = []
    if axis_face == "z+":
        out.append(bx(x0, x1, c - CH_W / 2, c + CH_W / 2, face - SKIN - CH_H, face - SKIN))
        out.append(bx(x0, x1, c - M3_CLEAR / 2, c + M3_CLEAR / 2, face - SKIN - 0.1, face + 0.1))
    elif axis_face == "z-":
        out.append(bx(x0, x1, c - CH_W / 2, c + CH_W / 2, face + SKIN, face + SKIN + CH_H))
        out.append(bx(x0, x1, c - M3_CLEAR / 2, c + M3_CLEAR / 2, face - 0.1, face + SKIN + 0.1))
    else:
        out.append(bx(x0, x1, face - SKIN - CH_H, face - SKIN, c - CH_W / 2, c + CH_W / 2))
        out.append(bx(x0, x1, face - SKIN - 0.1, face + 0.1, c - M3_CLEAR / 2, c + M3_CLEAR / 2))
    return out


def tabs(side):
    """Rail tabs and the deck tab for one plate. side = -1 (left) or +1 (right). Returns (solid, cuts)."""
    xa, xb = (0.0, TAB_L) if side < 0 else (SPAN - TAB_L, SPAN)
    solid, cuts = [], []
    for yc in FRONT_YC.values():                      # behind the web; screws from the front
        solid.append(bx(xa, xb, yc - RAIL_WEB / 2, yc + RAIL_WEB / 2, *FRONT_TAB_Z))
        cuts += channel_open("z+", side, yc, FRONT_TAB_Z[1])
    for yc in REAR_YC:                                # inside the channel; screws from the back
        solid.append(bx(xa, xb, yc - CH_IN, yc + CH_IN, RAIL_T, RAIL_H - 0.5))
        cuts += channel_open("z-", side, yc, RAIL_T)
    solid.append(bx(xa, xb, 0.5, RAIL_H - RAIL_T, BASE_ZC - CH_IN, BASE_ZC + CH_IN))   # base tongue
    if side < 0:                                      # screws from above, bay end only
        cuts += channel_open("y-", side, BASE_ZC, RAIL_H - RAIL_T)
    dx = (0.0, DECK_TAB["x"]) if side < 0 else (SPAN - DECK_TAB["x"], SPAN)
    solid.append(bx(*dx, *DECK_TAB["y"], *DECK_TAB["z"]))
    xd = sum(dx) / 2
    cuts += [cyl("y", (xd, z), INSERT_BORE / 2, DECK_Y - INSERT_DEPTH, DECK_Y + 0.1) for z in DECK_TAB["ins_z"]]
    return solid, cuts


def channel_open(kind, side, c, face):
    """Channel from SCREW_RANGE start to the tab's free end (open there, closed toward the plate)."""
    if side < 0:
        x0, x1 = SCREW_RANGE[0] - CH_W / 2, TAB_L + 0.1
    else:
        x0, x1 = SPAN - TAB_L - 0.1, SPAN - SCREW_RANGE[0] + CH_W / 2
    return channel(kind, x0, x1, c, face)


def plate(side):
    outline = plate_outline()
    if side < 0:
        vents = unary_union([sbox(z - VENTS["w"] / 2, VENTS["y"][0] + 3, z + VENTS["w"] / 2, VENTS["y"][1] - 3).union(
            Point(z, VENTS["y"][0] + 3).buffer(3, 16)).union(Point(z, VENTS["y"][1] - 3).buffer(3, 16)) for z in VENTS["z"]])
        outline = outline.difference(vents)
        p = plate_slab(outline, -PT)
    else:
        outline = outline.difference(psu_window())
        for z, y in psu_holes():
            outline = outline.difference(Point(z, y).buffer(PSU_HOLE_D / 2, 24))
        p = plate_slab(outline, SPAN)
    solid, cuts = tabs(side)
    for s in solid:
        p = p + s
    for b in cuts:
        p = p - b
    return p


# ------------------------------------------------------------------ deck
def board_holes():
    return [(BOARD_X0 + dx, BOARD_Z0 + dz) for dx in (BOARD_HOLE_IN, BOARD_W - BOARD_HOLE_IN)
            for dz in (BOARD_HOLE_IN, BOARD_D - BOARD_HOLE_IN)]


def deck_screws():
    return [(xd, z) for xd in (DECK_TAB["x"] / 2, SPAN - DECK_TAB["x"] / 2) for z in DECK_TAB["ins_z"]]


def deck():
    d = bx(0, SPAN, DECK_Y, DECK_Y + DECK_T, *DECK_Z)
    d -= bx(*CABLE_SLOT["x"], DECK_Y - 1, DECK_Y + DECK_T + 1, *CABLE_SLOT["z"])
    for x, z in board_holes():
        d += cyl("y", (x, z), STANDOFF_D / 2, DECK_Y + DECK_T - 0.01, DECK_Y + DECK_T + STANDOFF_H)
        d -= cyl("y", (x, z), INSERT_BORE / 2, DECK_Y + DECK_T + STANDOFF_H - INSERT_DEPTH, DECK_Y + DECK_T + STANDOFF_H + 0.1)
    h = (CSK_D - M3_CLEAR) / 2                         # countersunk M3 from the top into the deck tabs
    for x, z in deck_screws():
        d -= cyl("y", (x, z), M3_CLEAR / 2, DECK_Y - 1, DECK_Y + DECK_T + 1)
        from build123d import Cone
        d -= Pos(x, DECK_Y + DECK_T - h / 2 + 0.01, z) * (Rot(-90, 0, 0) * Cone(M3_CLEAR / 2, CSK_D / 2 + 0.01, h))
    return d


# ------------------------------------------------------------------ bought stand-ins
def rail_section(yc, zc_web, facing, along="x", flip_y=False):
    """TS35 hat as boxes. The web lies at depth zc_web (its back face); `facing` = +1 means the flanges are at larger depth."""
    w0 = zc_web if facing > 0 else zc_web - RAIL_T
    d0, d1 = (zc_web, zc_web + RAIL_H) if facing > 0 else (zc_web - RAIL_H, zc_web)
    fl = (d1 - RAIL_T, d1) if facing > 0 else (d0, d0 + RAIL_T)
    pieces = [(yc - RAIL_WEB / 2, yc + RAIL_WEB / 2, w0, w0 + RAIL_T)]
    for s in (-1, 1):
        wy = (yc + s * (RAIL_WEB / 2 - RAIL_T), yc + s * RAIL_WEB / 2)
        pieces.append((min(wy), max(wy), d0, d1))
        fy = (yc + s * RAIL_WEB / 2, yc + s * RAIL_W / 2)
        pieces.append((min(fy), max(fy), *fl))
    return pieces


def rail(kind, yc_or_zc):
    out = None
    if kind == "base":                               # lies flat, web up at y 6.5..7.5; across-rail coordinate is z
        for (z0, z1, y0, y1) in rail_section(yc_or_zc, RAIL_H, -1):
            b = bx(0, SPAN, y0, y1, z0, z1)
            out = b if out is None else out + b
        web = (RAIL_H - RAIL_T, RAIL_H)
        for k in range(8):
            xc = SLOT_P / 2 + k * SLOT_P
            out -= bx(xc - SLOT_L / 2, xc + SLOT_L / 2, web[0] - 0.1, web[1] + 0.1, yc_or_zc - SLOT_W / 2, yc_or_zc + SLOT_W / 2)
        return out
    zw, facing = (FRONT_WEB_Z, 1) if kind == "front" else (0.0, 1)
    for (y0, y1, z0, z1) in rail_section(yc_or_zc, zw, facing):
        b = bx(0, SPAN, y0, y1, z0, z1)
        out = b if out is None else out + b
    for k in range(8):
        xc = SLOT_P / 2 + k * SLOT_P
        out -= bx(xc - SLOT_L / 2, xc + SLOT_L / 2, yc_or_zc - SLOT_W / 2, yc_or_zc + SLOT_W / 2, zw - 0.1, zw + RAIL_T + 0.1)
    return out


def psu():
    return bx(PSU_X0, SPAN, PSU_Y0, PSU_Y0 + PSU_H, PSU_Z0, PSU_Z1)


KV_TERMINALS = [(4.0, "12V"), (14.0, "GND"), (24.0, "5V"), (34.0, "GND"), (44.0, "3V3"), (54.0, "GND"),
                (68.0, "12V"), (78.0, "5V"), (88.0, "GND")]
KV_FEEDS = [(4.0, "+"), (14.0, "-")]


def kv121(x0, yc):
    """Foot in the hat channel, body in front of the flanges; KV_D measured from the web."""
    zw = FRONT_WEB_Z + RAIL_T
    zf = FRONT_WEB_Z + RAIL_H + 0.05
    foot = bx(x0 + 0.2, x0 + KV_W - 0.2, yc - CH_IN, yc + CH_IN, zw + 0.05, zf)
    return foot + bx(x0 + 0.2, x0 + KV_W - 0.2, yc - KV_H / 2, yc + KV_H / 2, zf, FRONT_WEB_Z + KV_D)


def board():
    y0 = DECK_Y + DECK_T + STANDOFF_H
    b = bx(BOARD_X0, BOARD_X0 + BOARD_W, y0, y0 + BOARD_T, BOARD_Z0, BOARD_Z0 + BOARD_D)
    b += bx(BOARD_X0 + 4, BOARD_X0 + 56, y0 + BOARD_T, y0 + BOARD_T + 13, BOARD_Z0 + 56, BOARD_Z0 + 68)    # 24-pin socket
    b += bx(BOARD_X0 + 68, BOARD_X0 + 78, y0 + BOARD_T, y0 + BOARD_T + 12, BOARD_Z0 + 8, BOARD_Z0 + 50)    # screw terminal
    for dx, dz in ((10, 10), (40, 22), (52, 22), (52, 36)):                                               # glass fuses
        b += bx(BOARD_X0 + dx, BOARD_X0 + dx + 22, y0 + BOARD_T, y0 + BOARD_T + 7, BOARD_Z0 + dz, BOARD_Z0 + dz + 7)
    return b


def assembly():
    printed = {"plate_left": plate(-1), "plate_right": plate(1), "deck": deck()}
    bought = {"psu": psu(), "rail_base": rail("base", BASE_ZC), "board": board()}
    for n, yc in FRONT_YC.items():
        bought[f"rail_{n}"] = rail("front", yc)
    for i, yc in enumerate(REAR_YC):
        bought[f"rail_rear{i + 1}"] = rail("rear", yc)
    for x0, lab in KV_TERMINALS:
        bought[f"kv_terminals_{int(x0)}_{lab}"] = kv121(x0, FRONT_YC["terminals"])
    for n in ("proto1", "proto2"):
        for x0, lab in KV_FEEDS:
            bought[f"kv_{n}_{int(x0)}_{'pos' if lab == '+' else 'neg'}"] = kv121(x0, FRONT_YC[n])
    return printed, bought


# ------------------------------------------------------------------ checks
def checks(printed, bought):
    res = []

    def add(name, ok, detail):
        res.append(dict(name=name, ok=bool(ok), detail=detail))

    allp = {**printed, **bought}
    worst = []
    for (a, sa), (b, sb) in itertools.combinations(allp.items(), 2):
        if a.startswith("kv_") and b.startswith("kv_"):
            continue                                   # terminals touch side by side on the rail, by design
        bba, bbb = sa.bounding_box(), sb.bounding_box()
        if (bba.min.X > bbb.max.X or bbb.min.X > bba.max.X or bba.min.Y > bbb.max.Y or bbb.min.Y > bba.max.Y
                or bba.min.Z > bbb.max.Z or bbb.min.Z > bba.max.Z):
            continue
        v = (sa & sb).volume
        if v > 0.05:
            worst.append(f"{a} x {b}: {v:.1f} mm3")
    add("No two parts overlap", not worst, "; ".join(worst) or "every pair clear or face-to-face")

    for n, s in printed.items():
        bb = s.bounding_box()
        dims = sorted([bb.size.X, bb.size.Y, bb.size.Z])
        add(f"{n} fits the A1 bed", dims[1] <= BED and dims[2] <= BED,
            f"{bb.size.X:.0f} x {bb.size.Y:.0f} x {bb.size.Z:.0f} mm")

    gap = FRONT_TAB_Z[0] - PSU_Z1
    add("Front tabs clear the PSU", gap >= 0.8, f"{gap:.1f} mm between the PSU's front and the tabs")
    side_wall = CH_IN - CH_W / 2
    add("Wall beside each nut channel", side_wall >= 1.5, f"{side_wall:.1f} mm each side (rear and base tabs)")

    # a rail slot always offers a screw position over the tab's channel, for any cut
    miss = 0
    for k in range(250):
        phase = k * 0.1                                   # where the first slot starts, from the plate face
        ok = False
        for j in range(-1, 3):
            s0 = phase + j * SLOT_P
            lo, hi = max(s0 + 1.7, SCREW_RANGE[0]), min(s0 + SLOT_L - 1.7, SCREW_RANGE[1])
            ok |= hi >= lo
        miss += not ok
    add("A rail slot always lands over a tab's nut channel", miss == 0,
        f"channel {SCREW_RANGE[1] - SCREW_RANGE[0]:.0f} long vs slots {SLOT_L:.0f} at {SLOT_P:.0f} pitch (placeholder)")
    skin_floor = (FRONT_TAB_Z[1] - FRONT_TAB_Z[0]) - SKIN - CH_H
    add("Front tab floor under the nut channel", skin_floor >= 1.0, f"{skin_floor:.1f} mm")
    rear_floor = (RAIL_H - 0.5 - RAIL_T) - SKIN - CH_H
    add("Rear tab floor over the nut channel", rear_floor >= 1.0, f"{rear_floor:.1f} mm")
    y_board_top = DECK_Y + DECK_T + STANDOFF_H + BOARD_T + 13
    add("Board stays below the plate tops", y_board_top <= PLATE_H, f"tallest board part at {y_board_top:.0f}, plates at {PLATE_H:.0f}")
    add("Deck clears the PSU top", DECK_Y - (PSU_Y0 + PSU_H) >= 5, f"{DECK_Y - (PSU_Y0 + PSU_H):.1f} mm (deck tabs underneath)")
    fan_r = 40.0
    open_w = PSU_D - 2 * WIN_LIP
    add("Window over the fan", open_w >= 2 * fan_r - 4, f"window {open_w:.0f} wide vs an 80 fan (placeholder size)")
    xs = [x for x, _ in KV_TERMINALS]
    add("Terminal rail has 9 places plus spare", max(xs) + KV_W <= SPAN - 40, f"terminals end at {max(xs) + KV_W:.0f} of {SPAN:.0f}")
    pitch = FRONT_YC["terminals"] - FRONT_YC["proto1"]
    add("Room between rails for wire entries", pitch - KV_H >= 15, f"{pitch - KV_H:.0f} mm between terminal bodies (placeholder KV121)")
    # tipping: PSU mass centre vs the footprint's front and back edges
    zc = PSU_Z0 + PSU_D / 2
    add("Footprint around the heavy part", zc > 30 and TOE_D - zc > 60,
        f"PSU centre {zc:.0f} from the back, {TOE_D - zc:.0f} from the toe")
    return res


def main():
    stl = "--stl" in sys.argv
    printed, bought = assembly()
    res = checks(printed, bought)
    for r in res:
        print(("PASS " if r["ok"] else "FAIL ") + r["name"] + ": " + r["detail"])
    failed = [r["name"] for r in res if not r["ok"]]
    parts = []
    for n, s in printed.items():
        bb = s.bounding_box()
        parts.append(dict(name=n, kind="printed", cm3=round(s.volume / 1000, 1), g_pla=round(s.volume / 1000 * PLA),
                          size=[round(bb.size.X), round(bb.size.Y), round(bb.size.Z)]))
    for n in bought:
        parts.append(dict(name=n, kind="bought"))
    total = sum(p.get("g_pla", 0) for p in parts)
    print(f"printed: {total} g PLA (solid estimate); {len(failed)} failing")
    if stl:
        OUT.mkdir(parents=True, exist_ok=True)
        for n, s in {**printed, **bought}.items():
            export_stl(s, str(OUT / f"{n}.stl"), tolerance=0.05, angular_tolerance=0.3)
        summary = dict(size=[SPAN + 2 * PT, PLATE_H, TOE_D], parts=parts, checks=res, failed=failed, total_g_pla=total,
                       rails=dict(front=FRONT_YC, rear=REAR_YC, base_zc=BASE_ZC, web_z=FRONT_WEB_Z),
                       terminals=KV_TERMINALS, feeds=KV_FEEDS, kv=[KV_W, KV_H, KV_D],
                       psu=dict(x0=PSU_X0, y0=PSU_Y0, z0=PSU_Z0, l=PSU_L, h=PSU_H, d=PSU_D),
                       board=dict(x0=BOARD_X0, z0=BOARD_Z0, y0=DECK_Y + DECK_T + STANDOFF_H, w=BOARD_W, d=BOARD_D),
                       slot=CABLE_SLOT, deck_y=DECK_Y, span=SPAN, pt=PT)
        (OUT / "summary.json").write_text(json.dumps(summary, indent=1))
        print("wrote", OUT)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
