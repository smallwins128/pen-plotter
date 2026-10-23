"""Gantry lofi: the ACRO plates on Etch's frame and cross bar, three 2D views.

Writes hardware/web/lofi/gantry_lofi.html. Plate outlines and holes are traced
from the STL by acro_plates.py; frame and bar sizes come from params.py and
the bench decisions in docs/GANTRY_STATE.md. Anything not in either is listed
in ASSUMED below and shown on the page as unverified.

    python3 hardware/gantry/gantry_lofi.py
"""

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from acro_plates import STL, by_key, carriage_wheels, gantry_layout, parts
from params import (CROSS_BAR_H, CROSS_BAR_LEN, CROSS_BAR_W, DECK_T,
                    FRAME_OUTER_Y, GANTRY_PLATE_LEN, GANTRY_RISE, PROFILE_H,
                    PROFILE_W)

OUT = HERE.parent / "web" / "lofi" / "gantry_lofi.html"

# Bench plan (GANTRY_STATE.md, 2026-10-23): plotter bay is x 0..600, stop
# blocks on the 1000s just short of the divider.
BAY_X = 600.0
STOP_X = 575.0           # inner face of the stop blocks, as drawn in bench_lofi
A3_NEED = (450.0, 330.0)  # landscape, along X x along the bar [GANTRY_STATE]

# Not in the STL or params. OpenBuilds catalogue figures from memory: verify.
ASSUMED = {
    "wheel_od": 24.4,       # solid V wheel
    "wheel_w": 10.2,
    "span_20": 39.3,        # wheel centre spacing across a 20 mm face
    "spacer": 6.0,          # plate-to-wheel spacer
    "nema": 42.3,           # NEMA17 body
    "nema_len": 34.0,       # Ender-3 42-34
}


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;")


def path_d(pts, ox=0.0, oy=0.0, fx=1, fy=1, swap=False):
    """SVG path for a closed loop. fx/fy flip, swap exchanges x and y."""
    out = []
    for i, (x, y) in enumerate(pts):
        if swap:
            x, y = y, x
        out.append(f"{'M' if i == 0 else 'L'}{ox + fx * x:.2f} {oy + fy * y:.2f}")
    return "".join(out) + "Z"


def plate_svg(p, ox, oy, fx=1, fy=1, swap=False, cls="plate"):
    d = path_d(p["outline"], ox, oy, fx, fy, swap)
    d += "".join(path_d(h["pts"], ox, oy, fx, fy, swap) for h in p["holes"])
    return f'<path class="{cls}" fill-rule="evenodd" d="{d}"/>'


# ---------------------------------------------------------------------------
# Sheet 1: what is in the STL
# ---------------------------------------------------------------------------

def sheet_parts(ps):
    xs = [q["sheet_origin"][0] for q in ps]
    ys = [q["sheet_origin"][1] + q["size"][1] for q in ps]
    x0, ytop = min(xs) - 10, max(ys) + 10
    w = max(q["sheet_origin"][0] + q["size"][0] for q in ps) - x0 + 10
    h = ytop - min(q["sheet_origin"][1] for q in ps) + 30
    g = []
    for q in ps:
        sx, sy = q["sheet_origin"]
        ox, oy = sx - x0, ytop - sy           # flip Y so the sheet reads as in a slicer
        g.append(plate_svg(q, ox, oy, 1, -1, cls=f"plate {q['key']}"))
        cx, cy = ox + q["size"][0] / 2, oy - q["size"][1] - 3
        g.append(f'<text x="{cx:.1f}" y="{cy:.1f}" class="lbl s" text-anchor="middle">'
                 f'{esc(q["name"])}</text>')
    return f'<svg viewBox="0 -12 {w:.0f} {h:.0f}" class="fig" role="img" ' \
           f'aria-label="The 11 ACRO parts, traced from the STL">{"".join(g)}</svg>'


# ---------------------------------------------------------------------------
# Sheet 2: section across the front rail, looking along X
# ---------------------------------------------------------------------------

def stack(gl):
    """Z levels of the plate-on-top layout. Z = 0 at the tabletop."""
    rail_top = DECK_T + PROFILE_H
    groove = rail_top - PROFILE_W / 2                 # top cell's side grooves
    plate_bot = groove + ASSUMED["wheel_w"] / 2 + ASSUMED["spacer"]
    t = gl["plate"]["size"][2]
    return {"rail_top": rail_top, "groove": groove, "plate_bot": plate_bot,
            "plate_top": plate_bot + t, "bar_bot": plate_bot + t,
            "bar_top": plate_bot + t + CROSS_BAR_H}


def sheet_section(gl):
    """Y across (front edge at Y 0, inward to the right), Z up."""
    s = stack(gl)
    k = 4.0                                            # px per mm
    y_rail = PROFILE_W / 2                             # front rail centreline
    # Plate-local y of the rail centre: adjustable wheel set for a 20 face.
    rail_in_plate = gl["fixed_y"] - ASSUMED["span_20"]
    to_world = lambda py: y_rail + (py - rail_in_plate)   # plate +y points inward
    Y0, Y1, Z1 = -110.0, 150.0, 110.0
    X = lambda y: (y - Y0) * k
    Z = lambda z: (Z1 - z) * k
    W, H = (Y1 - Y0) * k, (Z1 + 18) * k
    e = []
    # table + deck
    e.append(f'<rect x="{X(0):.1f}" y="{Z(0):.1f}" width="{X(Y1) - X(0):.1f}" height="{14 * k:.1f}" class="table"/>')
    e.append(f'<rect x="{X(0):.1f}" y="{Z(DECK_T):.1f}" width="{X(Y1) - X(0):.1f}" height="{DECK_T * k:.1f}" class="deck"/>')
    e.append(f'<text x="{X(Y1) - 8:.1f}" y="{Z(0) + 36:.1f}" class="lbl" text-anchor="end">table edge at Y 0 · deck {DECK_T:g}</text>')
    # rail 2040 standing
    e.append(f'<rect x="{X(0):.1f}" y="{Z(s["rail_top"]):.1f}" width="{PROFILE_W * k:.1f}" height="{PROFILE_H * k:.1f}" class="rail"/>')
    e.append(f'<text x="{X(PROFILE_W) + 8:.1f}" y="{Z(DECK_T + 12):.1f}" class="lbl">1000 rail, 2040 standing</text>')
    # wheels (axes vertical: seen edge-on as rectangles)
    r, ww = ASSUMED["wheel_od"] / 2, ASSUMED["wheel_w"]
    for wy in (y_rail + ASSUMED["span_20"] / 2, y_rail - ASSUMED["span_20"] / 2):
        e.append(f'<rect x="{X(wy - r):.1f}" y="{Z(s["groove"] + ww / 2):.1f}" width="{2 * r * k:.1f}" height="{ww * k:.1f}" rx="6" class="wheel"/>')
        e.append(f'<rect x="{X(wy - 2.5):.1f}" y="{Z(s["plate_bot"]):.1f}" width="{5 * k:.1f}" height="{(s["plate_bot"] - s["groove"] + ww / 2) * k:.1f}" class="spacer"/>')
    # plate
    py0, py1 = to_world(0), to_world(gl["plate"]["size"][1])
    e.append(f'<rect x="{X(py0):.1f}" y="{Z(s["plate_top"]):.1f}" width="{(py1 - py0) * k:.1f}" height="{(s["plate_top"] - s["plate_bot"]) * k:.1f}" class="plate gantry"/>')
    # motor below the plate, outboard
    by = to_world(gl["bore"][1])
    n = ASSUMED["nema"]
    e.append(f'<rect x="{X(by - n / 2):.1f}" y="{Z(s["plate_bot"]):.1f}" width="{n * k:.1f}" height="{ASSUMED["nema_len"] * k:.1f}" class="motor"/>')
    e.append(f'<text x="{X(by):.1f}" y="{Z(s["plate_bot"] - ASSUMED["nema_len"] / 2) + 5:.1f}" class="lbl" text-anchor="middle">NEMA17</text>')
    # bar on top, centred over the plate's bar bolts; seen end-on it runs into the page to the right
    bar_end = -(CROSS_BAR_LEN - FRAME_OUTER_Y) / 2
    e.append(f'<rect x="{X(bar_end):.1f}" y="{Z(s["bar_top"]):.1f}" width="{(Y1 - bar_end) * k:.1f}" height="{CROSS_BAR_H * k:.1f}" class="bar"/>')
    e.append(f'<text x="{X(Y1) - 8:.1f}" y="{Z(s["bar_top"]) - 8:.1f}" class="lbl" text-anchor="end">700 bar (2020) on the plates, runs on across the bay</text>')
    # dims
    def dim_z(y, za, zb, txt, side=1):
        xa = X(y)
        e.append(f'<line x1="{xa:.1f}" y1="{Z(za):.1f}" x2="{xa:.1f}" y2="{Z(zb):.1f}" class="dim" marker-start="url(#ar)" marker-end="url(#ar)"/>')
        e.append(f'<text x="{xa + 8 * side:.1f}" y="{(Z(za) + Z(zb)) / 2 + 5:.1f}" class="num" text-anchor="{"start" if side > 0 else "end"}">{txt}</text>')
    dim_z(125, s["rail_top"], s["bar_bot"], f'{s["bar_bot"] - s["rail_top"]:.1f} rise*')
    e.append(f'<text x="{X(Y0) + 8:.1f}" y="{Z(Z1) + 22:.1f}" class="lbl">◀ outside the frame</text>')
    e.append(f'<text x="{X(Y1) - 8:.1f}" y="{Z(Z1) + 22:.1f}" class="lbl" text-anchor="end">into the bay ▶</text>')
    over = -(by - n / 2)
    e.append(f'<line x1="{X(by - n / 2):.1f}" y1="{Z(-4):.1f}" x2="{X(0):.1f}" y2="{Z(-4):.1f}" class="dim" marker-start="url(#ar)" marker-end="url(#ar)"/>')
    e.append(f'<text x="{(X(by - n / 2) + X(0)) / 2:.1f}" y="{Z(-4) + 22:.1f}" class="num" text-anchor="middle">{over:.0f} past the edge</text>')
    svg = (f'<svg viewBox="0 0 {W:.0f} {H + 40:.0f}" class="fig" role="img" '
           f'aria-label="Section across the front rail">{defs()}{"".join(e)}</svg>')
    return svg, s, over


# ---------------------------------------------------------------------------
# Sheet 3: top view of the plotter bay
# ---------------------------------------------------------------------------

def travels(gl, ps):
    r = ASSUMED["wheel_od"] / 2
    p_len = gl["plate"]["size"][0]
    x_lo = PROFILE_W - (min(gl["wheel_x"]) - r)            # inner wheel clears the end rail
    x_hi = STOP_X - p_len                                   # plate edge on the stop block
    x_travel = x_hi - x_lo
    # along the bar: the carriage plate can't pass over a gantry plate
    rail_in_plate = gl["fixed_y"] - ASSUMED["span_20"]
    inner_edge = PROFILE_W / 2 + gl["plate"]["size"][1] - rail_in_plate
    c = by_key(ps, "carriage")[0]
    y_travel = (FRAME_OUTER_Y - 2 * inner_edge) - c["size"][0]
    return {"x_lo": x_lo, "x_hi": x_hi, "x": x_travel, "y": y_travel,
            "inner_edge": inner_edge, "x_old": x_travel + (p_len - GANTRY_PLATE_LEN)}


def sheet_top(gl, ps, tv):
    """World X right (0 = left end of the frame), Y up the page = away from you."""
    k = 1.25
    X0, X1, Y0, Y1 = -40.0, 660.0, -110.0, 710.0
    X = lambda x: (x - X0) * k
    Y = lambda y: (Y1 - y) * k
    e = []
    # frame: 1000s front and back (bay part), left end, divider
    e.append(f'<rect x="{X(0):.1f}" y="{Y(PROFILE_W):.1f}" width="{(X1 - 20) * k:.1f}" height="{PROFILE_W * k:.1f}" class="rail"/>')
    e.append(f'<rect x="{X(0):.1f}" y="{Y(FRAME_OUTER_Y):.1f}" width="{(X1 - 20) * k:.1f}" height="{PROFILE_W * k:.1f}" class="rail"/>')
    e.append(f'<rect x="{X(0):.1f}" y="{Y(FRAME_OUTER_Y - PROFILE_W):.1f}" width="{PROFILE_W * k:.1f}" height="{(FRAME_OUTER_Y - 2 * PROFILE_W) * k:.1f}" class="rail"/>')
    e.append(f'<rect x="{X(BAY_X):.1f}" y="{Y(FRAME_OUTER_Y - PROFILE_W):.1f}" width="{PROFILE_W * k:.1f}" height="{(FRAME_OUTER_Y - 2 * PROFILE_W) * k:.1f}" class="divider"/>')
    for yy in (0, FRAME_OUTER_Y - PROFILE_W):
        e.append(f'<rect x="{X(STOP_X):.1f}" y="{Y(yy + PROFILE_W + 4):.1f}" width="{20 * k:.1f}" height="{(PROFILE_W + 8) * k:.1f}" class="stop"/>')
    # A3 sheet inside the reachable area
    ax0 = tv["x_lo"] + gl["plate"]["size"][0] / 2
    ay0 = tv["inner_edge"] + by_key(ps, "carriage")[0]["size"][0] / 2
    e.append(f'<rect x="{X(ax0):.1f}" y="{Y(ay0 + tv["y"]):.1f}" width="{tv["x"] * k:.1f}" height="{tv["y"] * k:.1f}" class="reach"/>')
    e.append(f'<rect x="{X(ax0 + (tv["x"] - A3_NEED[0]) / 2):.1f}" y="{Y(ay0 + (tv["y"] + A3_NEED[1]) / 2):.1f}" width="{A3_NEED[0] * k:.1f}" height="{A3_NEED[1] * k:.1f}" class="a3"/>')
    e.append(f'<text x="{X(ax0 + tv["x"] / 4):.1f}" y="{Y(ay0 + tv["y"] / 2):.1f}" class="lbl" text-anchor="middle">A3 landscape {A3_NEED[0]:.0f} × {A3_NEED[1]:.0f}</text>')
    e.append(f'<text x="{X(ax0 + tv["x"] / 4):.1f}" y="{Y(ay0 + tv["y"] / 2) + 22:.1f}" class="num" text-anchor="middle">reach ≈ {tv["x"]:.0f} × {tv["y"]:.0f}*</text>')
    # gantry at mid-travel: plates (Y swapped: plate x along world X, plate y across)
    gx = (tv["x_lo"] + tv["x_hi"]) / 2
    rail_in_plate = gl["fixed_y"] - ASSUMED["span_20"]
    p = gl["plate"]
    # front plate: plate +y inward (world +Y), so world y = 10 + (py - rail_in_plate)
    e.append(plate_svg(p, X(gx), Y(PROFILE_W / 2 - rail_in_plate), k, -k, cls="plate gantry"))
    # back plate: mirrored
    e.append(plate_svg(p, X(gx), Y(FRAME_OUTER_Y - PROFILE_W / 2 + rail_in_plate), k, k, cls="plate gantry"))
    # motors under the plates, outboard
    n = ASSUMED["nema"]
    for wy in (PROFILE_W / 2 + gl["bore"][1] - rail_in_plate, FRAME_OUTER_Y - PROFILE_W / 2 - gl["bore"][1] + rail_in_plate):
        e.append(f'<rect x="{X(gx + gl["bore"][0] - n / 2):.1f}" y="{Y(wy + n / 2):.1f}" width="{n * k:.1f}" height="{n * k:.1f}" class="motor dashed"/>')
    # bar along Y, centred on the plates' bar bolt line
    bx = gx + gl["bore"][0]
    e.append(f'<rect x="{X(bx - CROSS_BAR_W / 2):.1f}" y="{Y(FRAME_OUTER_Y / 2 + CROSS_BAR_LEN / 2):.1f}" width="{CROSS_BAR_W * k:.1f}" height="{CROSS_BAR_LEN * k:.1f}" class="bar"/>')
    # carriage at mid-bar, plate standing in front of the bar: seen edge-on
    c = by_key(ps, "carriage")[0]
    e.append(f'<rect x="{X(bx - CROSS_BAR_W / 2 - 12):.1f}" y="{Y(FRAME_OUTER_Y / 2 + c["size"][0] / 2):.1f}" width="{6 * k:.1f}" height="{c["size"][0] * k:.1f}" class="plate carriage"/>')
    e.append(f'<text x="{X(bx - 22):.1f}" y="{Y(FRAME_OUTER_Y / 2 + c["size"][0] / 2) - 6:.1f}" class="lbl" text-anchor="end">carriage</text>')
    e.append(f'<text x="{X(bx):.1f}" y="{Y(FRAME_OUTER_Y / 2 + CROSS_BAR_LEN / 2) - 8:.1f}" class="lbl" text-anchor="middle">700 bar</text>')
    e.append(f'<text x="{X(BAY_X + 10):.1f}" y="{Y(FRAME_OUTER_Y / 2):.1f}" class="lbl" transform="rotate(90 {X(BAY_X + 10):.1f} {Y(FRAME_OUTER_Y / 2):.1f})" text-anchor="middle">divider at 600</text>')
    e.append(f'<text x="{X(STOP_X + 10):.1f}" y="{Y(-14):.1f}" class="lbl" text-anchor="middle">stop</text>')
    e.append(f'<text x="{X(0):.1f}" y="{Y(-60):.1f}" class="lbl">FRONT (you)</text>')
    e.append(f'<text x="{X(0):.1f}" y="{Y(Y1 - 30):.1f}" class="lbl">BACK / WALL</text>')
    W, H = (X1 - X0) * k, (Y1 - Y0) * k
    return f'<svg viewBox="0 0 {W:.0f} {H:.0f}" class="fig" role="img" aria-label="Top view of the plotter bay">{defs()}{"".join(e)}</svg>'


def defs():
    return ('<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
            'markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" '
            'fill="var(--mute)"/></marker></defs>')


CSS = """
:root{--bg:#f3f2ee;--paper:#fff;--ink:#1d1d1b;--mute:#76746e;--line:#c9c6bf;--acr:#2f6f9f;--bar:#7a5c2e;--warn:#c8432f;--ok:#3d8a4f;--steel:#d9d6cf;
--display:"Archivo Narrow","Arial Narrow",Arial,sans-serif;--body:"IBM Plex Sans",Helvetica,Arial,sans-serif;--mono:"IBM Plex Mono",ui-monospace,monospace}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#1c1c1a;--paper:#262624;--ink:#ecebe6;--mute:#a19f98;--line:#4a4844;--acr:#6fa8d6;--bar:#c49a5c;--warn:#ec7663;--ok:#6cc283;--steel:#3a3936;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#1c1c1a;--paper:#262624;--ink:#ecebe6;--mute:#a19f98;--line:#4a4844;--acr:#6fa8d6;--bar:#c49a5c;--warn:#ec7663;--ok:#6cc283;--steel:#3a3936;color-scheme:dark}
body{background:var(--bg);color:var(--ink);font-family:var(--body);margin:0;padding-block:20px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
.wrap{max-width:1180px;margin:0 auto;display:grid;gap:16px}
h1{font-family:var(--display);font-size:2rem;margin:0;text-wrap:balance}
h2{font-family:var(--display);font-size:1.15rem;margin:0 0 6px}
p.lead{margin:0;color:var(--mute);max-width:72ch}
.sheet{background:var(--paper);border:1px solid var(--line);border-radius:6px;padding:12px 14px;overflow-x:auto}
.sheet p{margin:4px 0 8px;color:var(--mute);max-width:72ch}
.fig{display:block;width:100%;min-width:600px;height:auto}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px}
.card{background:var(--paper);border:1px solid var(--line);border-radius:6px;padding:14px 16px;min-width:0}
.card ul,.card ol{margin:0;padding-left:18px;line-height:1.5}
.num{font-family:var(--mono);font-variant-numeric:tabular-nums}
svg .num{font-size:15px;fill:var(--ink)} svg .lbl{font-size:15px;fill:var(--mute)} svg .lbl.s{font-size:5px}
.plate{fill:var(--acr);fill-opacity:.28;stroke:var(--acr);stroke-width:1.2}
.plate.gantry{fill-opacity:.4}
.rail{fill:var(--steel);stroke:var(--mute);stroke-width:1.2}
.divider{fill:var(--warn);opacity:.6}.stop{fill:var(--acr)}
.bar{fill:var(--bar);fill-opacity:.55;stroke:var(--bar)}
.wheel{fill:var(--ink);opacity:.75}.spacer{fill:var(--mute)}
.motor{fill:var(--mute);fill-opacity:.35;stroke:var(--mute)}.dashed{stroke-dasharray:6 4}
.table{fill:var(--line);opacity:.5}.deck{fill:var(--mute)}
.reach{fill:var(--ok);fill-opacity:.1;stroke:var(--ok);stroke-dasharray:6 4}
.a3{fill:none;stroke:var(--ok);stroke-width:2}
.dim{stroke:var(--mute);stroke-width:1.2}
.warn{color:var(--warn)}
table{border-collapse:collapse;width:100%;font-size:.92rem}
td,th{text-align:left;padding:4px 8px 4px 0;border-bottom:1px solid var(--line);vertical-align:top}
"""


def build():
    ps = parts()
    gl = gantry_layout(ps)
    cw = carriage_wheels(ps)
    sec, s, over = sheet_section(gl)
    tv = travels(gl, ps)
    counts = {}
    for q in ps:
        counts.setdefault(q["key"], [q, 0])[1] += 1
    rows = "".join(
        f'<tr><td>{n} × {esc(q["name"])}</td><td class="num">{q["size"][0]:.1f} × {q["size"][1]:.1f} × {q["size"][2]:g}</td>'
        f'<td>{esc(q["role"])}</td></tr>' for q, n in counts.values())
    x_margin = tv["x"] - A3_NEED[0]
    y_margin = tv["y"] - A3_NEED[1]
    rise_old = GANTRY_RISE
    html = f"""<title>Etch Gantry Lofi</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo+Narrow:wght@600;700&family=IBM+Plex+Mono&family=IBM+Plex+Sans:wght@400;600&display=swap">
<style>{CSS}</style>
<div class="wrap">
  <h1>Gantry: ACRO acrylic plates on the Etch frame</h1>
  <p class="lead">Lofi, 2D. Plate shapes are traced from <span class="num">{esc(STL.name)}</span> (11 parts, all 6 mm). Frame, bar and bay come from params.py and the 2026-10-23 bench plan. Numbers marked * rest on catalogue figures that haven't been measured (wheel size, spacer, motor), listed at the bottom.</p>

  <div class="sheet"><h2>1 · What's in the file</h2>
    <p>As laid out in the STL. Part roles are read from the hole patterns; confirm them against the kit.</p>
    {sheet_parts(ps)}
    <table><tr><th>Part</th><th>mm</th><th>Reading (guess)</th></tr>{rows}</table>
  </div>

  <div class="sheet"><h2>2 · Section across the front rail</h2>
    <p>The gantry plate lies flat on top of the 1000 rail. Its wheels grip the top cell's side grooves, and the adjustable wheel goes in the long slot. The plate can't stand on the rail's outer face: its bottom wheel would ride the bottom groove, and that is sitting on the deck.</p>
    {sec}
  </div>

  <div class="sheet"><h2>3 · Top view of the plotter bay</h2>
    <p>Bar parked mid-travel. The motors hang under the plates, outboard (dashed). Green dashes: where the pen can reach. Solid green: an A3 landscape sheet.</p>
    {sheet_top(gl, ps, tv)}
  </div>

  <div class="grid">
    <div class="card"><h2>What the file says</h2><ul>
      <li>Gantry plate wheels sit <span class="num">{gl['wheel_x'][1] - gl['wheel_x'][0]:.0f}</span> apart along the rail. The slot sets the cross-rail spacing from <span class="num">{gl['fixed_y'] - gl['slot_y'][1]:.1f}</span> to <span class="num">{gl['fixed_y'] - gl['slot_y'][0]:.1f}</span>, which fits a 20 mm face. A second hole at <span class="num">{gl['fixed_y'] - gl['short_slot_y']:.2f}</span> fits a 40 mm face.</li>
      <li>NEMA17 on the gantry plate: <span class="num">{gl['nema_pitch']:.0f}</span> square, Ø<span class="num">{gl['bore'][2]:.0f}</span> boss. The X motor rides on the plate (ACRO style).</li>
      <li class="warn">The carriage plate's wheels are fixed at <span class="num">{cw['spacing']:.2f}</span>, which fits a <b>2040</b> bar. Ours is a 2020.</li></ul></div>
    <div class="card"><h2>What it does to the plot</h2><ul>
      <li>Along X ≈ <span class="num">{tv['x']:.0f}</span>* (A3 needs {A3_NEED[0]:.0f}: <span class="num">{x_margin:+.0f}</span>). The plate is <span class="num">{gl['plate']['size'][0]:.1f}</span> long against <span class="num">{GANTRY_PLATE_LEN}</span> today.</li>
      <li>Along the bar ≈ <span class="num">{tv['y']:.0f}</span>* (A3 needs {A3_NEED[1]:.0f}: <span class="num">{y_margin:+.0f}</span>). The carriage can't pass over a gantry plate.</li>
      <li>Bar underside <span class="num">{s['bar_bot'] - s['rail_top']:.1f}</span>* above the rails, against the {rise_old:g} placeholder in params.</li>
      <li>Motors overhang the frame by about <span class="num">{over:.0f}</span>, front and back. That's inside the bar's own 50 overhang, so it needs no new space if the bar already clears the wall.</li></ul></div>
    <div class="card"><h2>Your call</h2><ol>
      <li>Bar: change to a <b>700 × 2040</b> to suit the carriage plate (stiffer too), or keep the 2020 and print a carriage with ~39 mm wheel spacing?</li>
      <li>X motors: move them onto the plates (ACRO style, belt anchored at the rail ends), or keep them where they are today?</li>
      <li>Do you have the wheels, eccentric spacers and 6 mm spacers, or only the plates?</li></ol></div>
  </div>
  <div class="card"><h2>Assumed, not measured</h2>
    <p class="num" style="margin:0">{' · '.join(f'{k} {v:g}' for k, v in ASSUMED.items())}</p></div>
</div>
"""
    OUT.write_text(html)
    return OUT, tv, s, cw, over


if __name__ == "__main__":
    out, tv, s, cw, over = build()
    print("wrote", out.relative_to(HERE.parent.parent))
    print(f"  reach ~{tv['x']:.0f} x {tv['y']:.0f}  (x was ~{tv['x_old']:.0f} with 65.5 plates)")
    print(f"  bar underside {s['bar_bot']:.1f} (rise {s['bar_bot'] - s['rail_top']:.1f})  motor overhang {over:.0f}")
