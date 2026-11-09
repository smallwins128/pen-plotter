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
from params import CROSS_BAR_W, DECK_T, FRAME_OUTER_Y, PROFILE_H, PROFILE_W

OUT = HERE.parent / "web" / "lofi" / "gantry_lofi.html"

# Bench plan (GANTRY_STATE.md, 2026-10-23): plotter bay is x 0..600, stop
# blocks on the 1000s just short of the divider.
BAY_X = 600.0
A3_NEED = (450.0, 330.0)  # landscape, along X x along the bar [GANTRY_STATE]

# Not in the STL or params. OpenBuilds catalogue figures from memory: verify.
ASSUMED = {
    "wheel_od": 24.4,       # solid V wheel
    "wheel_w": 10.2,
    "spacer": 6.0,          # plate-to-wheel spacer
    "nema": 42.3,           # NEMA17 body
    "nema_len": 34.0,       # Ender-3 42-34
    "clear": 2.0,           # bottom wheel to deck, our choice
    "head_x": 50.0,         # head footprint along X (carriage + tool plate + pen): not designed
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
    """Geometry of the standing-plate layout. Y = 0 at the frame's outer face
    (the table edge), inward positive; Z = 0 at the tabletop.

    The plate stands outside the 1000 rail. Its top wheels ride the rail's top
    face and its bottom wheels (short slot) the bottom face, so the rail has to
    be lifted off the deck. The bar's end bolts to the plate's inner face.
    """
    r = ASSUMED["wheel_od"] / 2
    span = gl["fixed_y"] - gl["short_slot_y"]          # wheel centres, from the file
    lift = (span - PROFILE_H) / 2 + r + ASSUMED["clear"]
    rail_bot = DECK_T + lift
    rail_mid = rail_bot + PROFILE_H / 2
    z = lambda py: rail_mid + py - (gl["fixed_y"] + gl["short_slot_y"]) / 2
    y_in = PROFILE_W / 2 - ASSUMED["wheel_w"] / 2 - ASSUMED["spacer"]
    t = gl["plate"]["size"][2]
    bar_bot = z(gl["bar_bores"][0] - CROSS_BAR_W / 2)
    bar_top = z(gl["bar_bores"][-1] + CROSS_BAR_W / 2)
    # carriage wheels ride the bar's top and bottom faces the same way
    car_low = bar_bot - (span - PROFILE_H) / 2 - r
    return {"span": span, "lift": lift, "rail_bot": rail_bot,
            "rail_top": rail_bot + PROFILE_H, "rail_mid": rail_mid, "z": z,
            "y_in": y_in, "y_out": y_in - t, "bar_bot": bar_bot, "bar_top": bar_top,
            "bar_len": FRAME_OUTER_Y - 2 * y_in, "plate_bot": z(0),
            "plate_top": z(gl["plate"]["size"][1]), "car_low": car_low}


def sheet_section(gl):
    """Y across (outside on the left, into the bay on the right), Z up."""
    s = stack(gl)
    z = s["z"]
    k = 3.2
    Y0, Y1, Z0, Z1 = -75.0, 120.0, -46.0, s["plate_top"] + 20
    X = lambda y: (y - Y0) * k
    Z = lambda zz: (Z1 - zz) * k
    W, H = (Y1 - Y0) * k, (Z1 - Z0) * k
    e = []
    # table (from its edge at Y 0) and deck
    e.append(f'<rect x="{X(0):.1f}" y="{Z(0):.1f}" width="{X(Y1) - X(0):.1f}" height="{18 * k:.1f}" class="table"/>')
    e.append(f'<rect x="{X(0):.1f}" y="{Z(DECK_T):.1f}" width="{X(Y1) - X(0):.1f}" height="{DECK_T * k:.1f}" class="deck"/>')
    e.append(f'<text x="{X(Y1) - 6:.1f}" y="{Z(0) + 34:.1f}" class="lbl" text-anchor="end">tabletop, deck {DECK_T:g}</text>')
    # lifted rail, 2040 standing
    e.append(f'<rect x="{X(0):.1f}" y="{Z(s["rail_top"]):.1f}" width="{PROFILE_W * k:.1f}" height="{PROFILE_H * k:.1f}" class="rail"/>')
    e.append(f'<rect x="{X(2):.1f}" y="{Z(s["rail_bot"]):.1f}" width="{(PROFILE_W - 4) * k:.1f}" height="{(s["rail_bot"] - DECK_T) * k:.1f}" class="lift"/>')
    e.append(f'<text x="{X(PROFILE_W) + 8:.1f}" y="{Z(s["rail_bot"] - s["lift"] / 2) + 5:.1f}" class="lbl">lift ≥ {s["lift"]:.0f}* (bracket, block or riser)</text>')
    e.append(f'<text x="{X(PROFILE_W) + 8:.1f}" y="{Z(s["rail_mid"] - 8) + 5:.1f}" class="lbl">1000 rail</text>')
    # wheels: axes along Y, seen side-on
    r, ww = ASSUMED["wheel_od"] / 2, ASSUMED["wheel_w"]
    for py in (gl["fixed_y"], gl["short_slot_y"]):
        e.append(f'<rect x="{X(PROFILE_W / 2 - ww / 2):.1f}" y="{Z(z(py) + r):.1f}" width="{ww * k:.1f}" height="{2 * r * k:.1f}" rx="5" class="wheel"/>')
        e.append(f'<rect x="{X(s["y_in"]):.1f}" y="{Z(z(py) + 2.5):.1f}" width="{(PROFILE_W / 2 - ww / 2 - s["y_in"]) * k:.1f}" height="{5 * k:.1f}" class="spacer"/>')
    # plate, standing
    e.append(f'<rect x="{X(s["y_out"]):.1f}" y="{Z(s["plate_top"]):.1f}" width="{(s["y_in"] - s["y_out"]) * k:.1f}" height="{(s["plate_top"] - s["plate_bot"]) * k:.1f}" class="plate gantry"/>')
    e.append(f'<text x="{X(s["y_out"]) - 6:.1f}" y="{Z(s["plate_top"]) + 14:.1f}" class="lbl" text-anchor="end">gantry plate</text>')
    # motor on the outer face
    n, nl = ASSUMED["nema"], ASSUMED["nema_len"]
    bz = z(gl["bore"][1])
    e.append(f'<rect x="{X(s["y_out"] - nl):.1f}" y="{Z(bz + n / 2):.1f}" width="{nl * k:.1f}" height="{n * k:.1f}" class="motor"/>')
    e.append(f'<text x="{X(s["y_out"] - nl / 2):.1f}" y="{Z(bz) + 5:.1f}" class="lbl" text-anchor="middle">NEMA17</text>')
    # bar, end bolted to the plate's inner face, running on into the bay
    e.append(f'<rect x="{X(s["y_in"]):.1f}" y="{Z(s["bar_top"]):.1f}" width="{(Y1 - s["y_in"]) * k:.1f}" height="{(s["bar_top"] - s["bar_bot"]) * k:.1f}" class="bar"/>')
    e.append(f'<text x="{X(Y1) - 6:.1f}" y="{Z(s["bar_top"]) - 8:.1f}" class="lbl" text-anchor="end">bar, 2040 on edge, end-bolted to the plate</text>')
    # carriage's lowest wheel, as a dashed line
    e.append(f'<line x1="{X(PROFILE_W):.1f}" y1="{Z(s["car_low"]):.1f}" x2="{X(Y1):.1f}" y2="{Z(s["car_low"]):.1f}" class="dim dashed"/>')
    e.append(f'<text x="{X(Y1) - 6:.1f}" y="{Z(s["car_low"]) - 8:.1f}" class="lbl" text-anchor="end">carriage\'s lowest wheel*</text>')
    e.append(f'<text x="{X(PROFILE_W) + 8:.1f}" y="{Z(s["bar_top"]) + 22:.1f}" class="lbl">top wheels sit either side of the bar end</text>')

    def dim_z(y, za, zb, txt):
        e.append(f'<line x1="{X(y):.1f}" y1="{Z(za):.1f}" x2="{X(y):.1f}" y2="{Z(zb):.1f}" class="dim" marker-start="url(#ar)" marker-end="url(#ar)"/>')
        e.append(f'<text x="{X(y) + (8 if y < 0 else -8):.1f}" y="{(Z(za) + Z(zb)) / 2 + 5:.1f}" class="num" text-anchor="{"start" if y < 0 else "end"}">{txt}</text>')
    dim_z(119, DECK_T, s["bar_bot"], f'deck to bar {s["bar_bot"] - DECK_T:.0f}*')
    dim_z(-72, 0, s["plate_bot"], f'{-s["plate_bot"]:.0f}*')
    e.append(f'<text x="{X(-72) + 8:.1f}" y="{Z(s["plate_bot"]) + 22:.1f}" class="lbl">plate bottom, below the tabletop</text>')
    e.append(f'<text x="{X(Y0) + 6:.1f}" y="{Z(Z1) + 18:.1f}" class="lbl">◀ past the table edge</text>')
    e.append(f'<text x="{X(Y1) - 6:.1f}" y="{Z(Z1) + 18:.1f}" class="lbl" text-anchor="end">into the bay ▶</text>')
    svg = (f'<svg viewBox="0 0 {W:.0f} {H:.0f}" class="fig" role="img" '
           f'aria-label="Section across the front rail">{defs()}{"".join(e)}</svg>')
    return svg, s


# ---------------------------------------------------------------------------
# Sheet 3: top view of the plotter bay
# ---------------------------------------------------------------------------

def travels(gl, ps, s):
    """Pen reach. The plates ride outside the frame, so they no longer limit
    anything; the head does, wherever it hangs below the rail tops."""
    c = by_key(ps, "carriage")[0]
    inner = FRAME_OUTER_Y - 2 * PROFILE_W
    low = s["car_low"] < s["rail_top"]
    y = inner - c["size"][0] if low else s["bar_len"] - c["size"][0]
    x = (BAY_X - PROFILE_W) - ASSUMED["head_x"]
    return {"x": x, "y": y, "x0": PROFILE_W + ASSUMED["head_x"] / 2,
            "y0": (FRAME_OUTER_Y - y) / 2, "carriage_low": low}


def sheet_top(gl, s, tv, ps):
    """World X right (0 = left end of the frame), Y up the page = away from you."""
    k = 1.25
    X0, X1, Y0, Y1 = -40.0, 660.0, -110.0, 710.0
    X = lambda x: (x - X0) * k
    Y = lambda y: (Y1 - y) * k
    e = []
    for yy in (0, FRAME_OUTER_Y - PROFILE_W):
        e.append(f'<rect x="{X(0):.1f}" y="{Y(yy + PROFILE_W):.1f}" width="{(X1 - 20) * k:.1f}" height="{PROFILE_W * k:.1f}" class="rail"/>')
    e.append(f'<rect x="{X(0):.1f}" y="{Y(FRAME_OUTER_Y - PROFILE_W):.1f}" width="{PROFILE_W * k:.1f}" height="{(FRAME_OUTER_Y - 2 * PROFILE_W) * k:.1f}" class="rail"/>')
    e.append(f'<rect x="{X(BAY_X):.1f}" y="{Y(FRAME_OUTER_Y - PROFILE_W):.1f}" width="{PROFILE_W * k:.1f}" height="{(FRAME_OUTER_Y - 2 * PROFILE_W) * k:.1f}" class="divider"/>')
    # reach and A3
    e.append(f'<rect x="{X(tv["x0"]):.1f}" y="{Y(tv["y0"] + tv["y"]):.1f}" width="{tv["x"] * k:.1f}" height="{tv["y"] * k:.1f}" class="reach"/>')
    ax = tv["x0"] + (tv["x"] - A3_NEED[0]) / 2
    ay = tv["y0"] + (tv["y"] - A3_NEED[1]) / 2
    e.append(f'<rect x="{X(ax):.1f}" y="{Y(ay + A3_NEED[1]):.1f}" width="{A3_NEED[0] * k:.1f}" height="{A3_NEED[1] * k:.1f}" class="a3"/>')
    e.append(f'<text x="{X(ax + A3_NEED[0] / 4):.1f}" y="{Y(ay + A3_NEED[1] / 2):.1f}" class="lbl" text-anchor="middle">A3 {A3_NEED[0]:.0f} × {A3_NEED[1]:.0f}</text>')
    e.append(f'<text x="{X(ax + A3_NEED[0] / 4):.1f}" y="{Y(ay + A3_NEED[1] / 2) + 22:.1f}" class="num" text-anchor="middle">reach ≈ {tv["x"]:.0f} × {tv["y"]:.0f}*</text>')
    # gantry at mid-bay: plates stand outside the rails, seen edge-on
    bx = (tv["x0"] + tv["x"] / 2)
    px = bx - gl["bar_x"]
    L = gl["plate"]["size"][0]
    n, nl = ASSUMED["nema"], ASSUMED["nema_len"]
    for y_in, sgn in ((s["y_in"], -1), (FRAME_OUTER_Y - s["y_in"], 1)):
        y_out = y_in + sgn * (s["y_in"] - s["y_out"])
        e.append(f'<rect x="{X(px):.1f}" y="{Y(max(y_in, y_out)):.1f}" width="{L * k:.1f}" height="{abs(y_out - y_in) * k:.1f}" class="plate gantry solid"/>')
        m0, m1 = y_out, y_out + sgn * nl
        e.append(f'<rect x="{X(bx - n / 2):.1f}" y="{Y(max(m0, m1)):.1f}" width="{n * k:.1f}" height="{nl * k:.1f}" class="motor"/>')
    e.append(f'<rect x="{X(bx - CROSS_BAR_W / 2):.1f}" y="{Y(FRAME_OUTER_Y - s["y_in"]):.1f}" width="{CROSS_BAR_W * k:.1f}" height="{s["bar_len"] * k:.1f}" class="bar"/>')
    c = by_key(ps, "carriage")[0]
    e.append(f'<rect x="{X(bx + CROSS_BAR_W / 2 + 12):.1f}" y="{Y(FRAME_OUTER_Y / 2 + c["size"][0] / 2):.1f}" width="{6 * k:.1f}" height="{c["size"][0] * k:.1f}" class="plate carriage"/>')
    e.append(f'<text x="{X(bx + 30):.1f}" y="{Y(FRAME_OUTER_Y / 2 + c["size"][0] / 2) - 6:.1f}" class="lbl">carriage</text>')
    e.append(f'<text x="{X(bx):.1f}" y="{Y(-60):.1f}" class="lbl" text-anchor="middle">plate + motor outside the frame</text>')
    e.append(f'<text x="{X(bx):.1f}" y="{Y(FRAME_OUTER_Y + 60) + 14:.1f}" class="lbl" text-anchor="middle">bar ≈ {s["bar_len"]:.0f}*</text>')
    e.append(f'<text x="{X(BAY_X + 10):.1f}" y="{Y(FRAME_OUTER_Y / 2):.1f}" class="lbl" transform="rotate(90 {X(BAY_X + 10):.1f} {Y(FRAME_OUTER_Y / 2):.1f})" text-anchor="middle">divider at 600</text>')
    e.append(f'<text x="{X(0):.1f}" y="{Y(-90):.1f}" class="lbl">FRONT (you)</text>')
    e.append(f'<text x="{X(0):.1f}" y="{Y(Y1 - 20):.1f}" class="lbl">BACK / WALL</text>')
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
.plate.gantry{fill-opacity:.4}.plate.solid{fill-opacity:.8}.lift{fill:var(--warn);fill-opacity:.25;stroke:var(--warn);stroke-dasharray:4 3}
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
    sec, s = sheet_section(gl)
    tv = travels(gl, ps, s)
    counts = {}
    for q in ps:
        counts.setdefault(q["key"], [q, 0])[1] += 1
    rows = "".join(
        f'<tr><td>{n} × {esc(q["name"])}</td><td class="num">{q["size"][0]:.1f} × {q["size"][1]:.1f} × {q["size"][2]:g}</td>'
        f'<td>{esc(q["role"])}</td></tr>' for q, n in counts.values())
    x_margin = tv["x"] - A3_NEED[0]
    y_margin = tv["y"] - A3_NEED[1]
    over = -(s["y_out"] - ASSUMED["nema_len"])
    html = f"""<title>Etch Gantry Lofi</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo+Narrow:wght@600;700&family=IBM+Plex+Mono&family=IBM+Plex+Sans:wght@400;600&display=swap">
<style>{CSS}</style>
<div class="wrap">
  <h1>Gantry: ACRO acrylic plates on the Etch frame</h1>
  <p class="lead">Lofi v2, 2D: the gantry plates stand upright outside the 1000 rails, the way ACRO uses them. Plate shapes are traced from <span class="num">{esc(STL.name)}</span> (11 parts, all 6 mm). Frame and bay come from params.py and the 2026-10-23 bench plan. Numbers marked * rest on figures not yet measured (wheel, spacer, motor, head), listed at the bottom.</p>

  <div class="sheet"><h2>1 · What's in the file</h2>
    <p>As laid out in the STL. Part roles are read from the hole patterns; confirm them against the kit.</p>
    {sheet_parts(ps)}
    <table><tr><th>Part</th><th>mm</th><th>Reading (guess)</th></tr>{rows}</table>
  </div>

  <div class="sheet"><h2>2 · Section across the front rail</h2>
    <p>The plate stands outside the rail. Its top wheels ride the rail's top face and its bottom wheels the bottom face, <span class="num">{s['span']:.2f}</span> apart: the plate's 2040 holes. The bar is a 2040 on edge, its end bolted to the plate's inner face over the rail. Because the bottom wheels run under the rail, <b>the rail has to come off the deck</b>.</p>
    {sec}
  </div>

  <div class="sheet"><h2>3 · Top view of the plotter bay</h2>
    <p>Bar at mid-bay. Plates and motors sit outside the frame, past the table edge. Green dashes show where the pen can reach; solid green is an A3 landscape sheet.</p>
    {sheet_top(gl, s, tv, ps)}
  </div>

  <div class="grid">
    <div class="card"><h2>What changes</h2><ul>
      <li><b>Rails lifted</b> at least <span class="num">{s['lift']:.0f}</span>* off the deck so the bottom wheels clear. The 4 end brackets (108.7 tall) look made for this. The 560 ends and the divider go up with them.</li>
      <li><b>Bar ≈ <span class="num">{s['bar_len']:.0f}</span>*</b> of 2040, cut to fit between the plates' inner faces. Neither the 700 nor a 560 fits; the spacers set the exact length.</li>
      <li>The paper is <span class="num">{s['bar_bot'] - DECK_T:.0f}</span>* below the bar, so the pen reaches down through the tool plate's 97 mm slots.</li>
      <li>Motors stand <span class="num">{over:.0f}</span>* outside the frame, front and back, and the plates hang <span class="num">{-s['plate_bot']:.0f}</span>* below the tabletop past its edge. Needs a clear table edge, and about <span class="num">{over + 5:.0f}</span> at the wall.</li></ul></div>
    <div class="card"><h2>What it does to the plot</h2><ul>
      <li>The plates no longer limit X: they ride outside. The head against the end rail and divider does. Along X ≈ <span class="num">{tv['x']:.0f}</span>* (A3 needs {A3_NEED[0]:.0f}: <span class="num">{x_margin:+.0f}</span>).</li>
      <li>Along the bar ≈ <span class="num">{tv['y']:.0f}</span>* (A3 needs {A3_NEED[1]:.0f}: <span class="num">{y_margin:+.0f}</span>). The carriage's bottom wheels sit below the rail tops, so it stays between the rails.</li>
      <li>The carriage plate's <span class="num">{cw['spacing']:.2f}</span> wheels fit the 2040 bar, so it fits as-is.</li>
      <li>The stop blocks on the rail tops would catch the top wheels. The divider becomes the hard end for the head instead.</li></ul></div>
    <div class="card"><h2>Your call</h2><ol>
      <li>Rail lift: the ACRO end brackets, or blocks under the frame? How high do you want the frame?</li>
      <li>The table edge: anything (lip, apron, legs) within <span class="num">{-s['plate_bot']:.0f}</span> below the top at the front and back? And how far is the wall?</li>
      <li>Do you have the wheels and spacers, or only the plates?</li></ol></div>
  </div>
  <div class="card"><h2>Assumed, not measured</h2>
    <p class="num" style="margin:0">{' · '.join(f'{k} {v:g}' for k, v in ASSUMED.items())}</p></div>
</div>
"""
    OUT.write_text(html)
    return OUT, tv, s, over


if __name__ == "__main__":
    out, tv, s, over = build()
    print("wrote", out.relative_to(HERE.parent.parent))
    print(f"  lift >= {s['lift']:.1f}  bar {s['bar_len']:.1f}  deck to bar {s['bar_bot'] - DECK_T:.1f}  "
          f"plate bottom {s['plate_bot']:.1f}  motor out {over:.1f}")
    print(f"  reach ~{tv['x']:.0f} x {tv['y']:.0f}  carriage below rail tops: {tv['carriage_low']}")
