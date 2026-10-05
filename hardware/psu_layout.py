#!/usr/bin/env python3
"""Flat layout drawing for the power box: DIN rail, floor plan, wiring.

    python3 hardware/psu_layout.py      -> hardware/out/psu_layout.html

Everything here is data first and drawing second: the rail schedule, the floor
positions and the wire runs are tables, and the SVG is generated from them. So
the picture cannot disagree with the schedule next to it.
"""

import pathlib

OUT = pathlib.Path(__file__).resolve().parent / "out" / "psu_layout.html"

FLOOR = (442.0, 265.0)          # UN4412 internal
MODULE = 17.5                   # one DIN module

# --- the rail, left to right, in the order power flows -----------------------
# name, width mm, kind, note
RAIL = [
    ("", 8.0, "clamp", "end clamp"),
    ("MCB1", 2 * MODULE, "mcb", "6 A 1P+N, C-curve — mains in, protects both PSUs"),
    ("", 2.0, "part", ""),
    ("L1", 5.2, "L", "line → LRS-350"),
    ("L2", 5.2, "L", "line → RS-25"),
    ("N1", 5.2, "N", "neutral → LRS-350"),
    ("N2", 5.2, "N", "neutral → RS-25"),
    ("PE1", 5.2, "E", "earth → LRS-350 chassis"),
    ("PE2", 5.2, "E", "earth → RS-25 chassis"),
    ("PE3", 5.2, "E", "earth → panel / spare"),
    ("", 2.0, "part", ""),
    ("MCB2", MODULE, "mcb", "5 A 1P DC — protects the 24 V trunk wiring"),
    ("", 2.0, "part", ""),
    ("K1", 16.0, "relay", "24 V coil — drops the driver rail on E-stop"),
    ("", 2.0, "part", ""),
    ("+24", 5.2, "v24", "in, from LRS-350"),
    ("+24a", 5.2, "v24", "always on → the board"),
    ("+24s", 5.2, "v24", "switched by K1 → the drivers"),
    ("0V", 5.2, "v0", "in, from LRS-350"),
    ("0Va", 5.2, "v0", "→ the link"),
    ("0Vb", 5.2, "v0", "→ the fan"),
    ("+6", 5.2, "v6", "in, from the buck"),
    ("+6o", 5.2, "v6", "→ the link"),
    ("", 2.0, "part", ""),
    ("sp", 5.2, "sp", "spare"), ("sp", 5.2, "sp", "spare"),
    ("sp", 5.2, "sp", "spare"), ("sp", 5.2, "sp", "spare"),
    ("", 8.0, "clamp", "end clamp"),
]

RAIL_START = 20.0               # mm from the left wall
RAIL_Y = 18.0                   # mm from the back wall to the rail
RAIL_DEPTH = 70.0               # how far DIN gear projects from the wall
DUCT = (20.0, 98.0, 402.0, 25.0)

# name, x, y, w, d, kind
FLOOR_ITEMS = [
    ("LRS-350-24", 20, 140, 215, 115, "psu"),
    ("RS-25-24", 250, 140, 51, 78, "psu"),
    ("LM2596 buck", 315, 140, 65, 45, "pcb"),
    ("spare", 315, 195, 107, 38, "spare"),
]

# label, (x, y) on a wall, which wall
PANEL = [
    ("IEC inlet", 0, 45, "left"),
    ("E-stop", 0, 110, "left"),
    ("link out", 442, 55, "right"),
]

# from, to, cores, kind, the path as (x, y) waypoints in floor mm
RUNS = [
    ("IEC inlet", "MCB1", "L N PE", "mains", [(0, 45), (12, 45), (12, 30), (28, 30)]),
    ("MCB1 out", "L/N/PE terminals", "3", "mains", [(43, 55), (43, 70), (62, 70), (62, 60)]),
    ("L1 N1 PE1", "LRS-350", "3", "mains", [(55, 88), (55, 110), (120, 110), (120, 140)]),
    ("L2 N2 PE2", "RS-25", "3", "mains", [(70, 88), (70, 110), (275, 110), (275, 140)]),
    ("LRS-350 DC out", "MCB2 / 0V in", "+24, 0V", "v24", [(200, 140), (200, 110), (92, 110), (92, 88)]),
    ("RS-25 DC out", "buck in", "+24, 0V", "v24", [(290, 140), (290, 125), (340, 125), (340, 140)]),
    ("buck out", "+6 terminal", "+6, 0V", "v6", [(360, 185), (360, 110), (155, 110), (155, 88)]),
    ("E-stop", "K1 coil", "2", "ctrl", [(0, 110), (10, 110), (10, 95), (110, 95), (110, 88)]),
    ("terminals", "link out", "+24a, +24s, +6, 0V", "link",
     [(140, 88), (140, 110), (430, 110), (430, 55), (442, 55)]),
]

LINK = [("+24 always", 0.75, "to the board — stays up through an E-stop"),
        ("+24 switched", 0.75, "to the three drivers — K1 drops this"),
        ("+6", 0.75, "to the servo, via the control box"),
        ("0V", 2.5, "two sizes up: the servo's 2.5 A return shares it")]


def rail_schedule():
    out, x = [], RAIL_START
    for name, w, kind, note in RAIL:
        out.append((name, x, w, kind, note))
        x += w
    return out, x - RAIL_START


def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def plan_svg(scale=1.45):
    pad_l, pad_t = 56, 44
    W, H = FLOOR
    vw, vh = W * scale + pad_l + 70, H * scale + pad_t + 56
    X = lambda mm: pad_l + mm * scale
    Y = lambda mm: pad_t + mm * scale

    p = [f'<svg viewBox="0 0 {vw:.0f} {vh:.0f}" role="img" xmlns="http://www.w3.org/2000/svg"'
         ' aria-label="Plan view of the power box floor: DIN rail along the back wall,'
         ' two supplies and the buck in front, and every wire run routed through one duct.">']
    p.append('<defs><marker id="ar" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7"'
             ' markerHeight="7" orient="auto"><path d="M0 0 L8 4 L0 8 z" fill="currentColor"/>'
             '</marker></defs>')

    # the case floor
    p.append(f'<rect x="{X(0):.0f}" y="{Y(0):.0f}" width="{W*scale:.0f}" height="{H*scale:.0f}"'
             ' rx="4" fill="var(--surface-2)" stroke="currentColor" stroke-width="1.6"/>')
    p.append(f'<text x="{X(W/2):.0f}" y="{Y(0)-16:.0f}" text-anchor="middle" font-size="12.5"'
             f' fill="currentColor" opacity=".75">UN4412 base — {W:.0f} × {H:.0f} mm internal</text>')

    # wire duct
    dx, dy, dw, dd = DUCT
    p.append(f'<rect x="{X(dx):.0f}" y="{Y(dy):.0f}" width="{dw*scale:.0f}" height="{dd*scale:.0f}"'
             ' fill="none" stroke="currentColor" stroke-width="1" stroke-dasharray="5 4" opacity=".5"/>')
    p.append(f'<text x="{X(dx)+2:.0f}" y="{Y(dy)-5:.0f}" font-size="10" fill="currentColor"'
             ' opacity=".55">wire duct, 25 mm</text>')

    # DIN rail
    sched, rail_len = rail_schedule()
    p.append(f'<rect x="{X(RAIL_START):.0f}" y="{Y(RAIL_Y):.0f}" width="{rail_len*scale:.0f}"'
             f' height="{RAIL_DEPTH*scale:.0f}" fill="var(--rail)" stroke="currentColor"'
             ' stroke-width="1.2" opacity=".9"/>')
    for name, x, w, kind, note in sched:
        if kind in ("part", "clamp"):
            continue
        fill = {"mcb": "var(--w-mains)", "relay": "var(--accent)"}.get(kind, f"var(--w-{kind})")
        h = RAIL_DEPTH if kind in ("mcb", "relay") else RAIL_DEPTH * 0.62
        p.append(f'<rect x="{X(x):.0f}" y="{Y(RAIL_Y):.0f}" width="{max(w*scale-1,2):.0f}"'
                 f' height="{h*scale:.0f}" fill="{fill}" opacity=".85"/>')
        if kind in ("mcb", "relay"):
            p.append(f'<text x="{X(x+w/2):.0f}" y="{Y(RAIL_Y+RAIL_DEPTH/2)+4:.0f}" text-anchor="middle"'
                     f' font-size="11" font-weight="600" fill="var(--surface)">{_esc(name)}</text>')
    p.append(f'<text x="{X(RAIL_START):.0f}" y="{Y(RAIL_Y)-7:.0f}" font-size="11" fill="currentColor"'
             f' opacity=".75">DIN rail, {rail_len:.0f} mm</text>')

    # floor items
    for name, x, y, w, d, kind in FLOOR_ITEMS:
        dash = ' stroke-dasharray="5 4"' if kind == "spare" else ''
        fill = "none" if kind == "spare" else "var(--surface)"
        p.append(f'<rect x="{X(x):.0f}" y="{Y(y):.0f}" width="{w*scale:.0f}" height="{d*scale:.0f}"'
                 f' rx="2" fill="{fill}" stroke="currentColor" stroke-width="1.3"{dash}'
                 f' opacity="{0.45 if kind=="spare" else 1}"/>')
        p.append(f'<text x="{X(x+w/2):.0f}" y="{Y(y+d/2)+4:.0f}" text-anchor="middle" font-size="11.5"'
                 f' fill="currentColor" opacity="{0.55 if kind=="spare" else 0.9}">{_esc(name)}</text>')

    # wire runs
    for frm, to, cores, kind, path in RUNS:
        pts = " ".join(f"{X(a):.0f},{Y(b):.0f}" for a, b in path)
        p.append(f'<polyline points="{pts}" fill="none" stroke="var(--w-{kind})" stroke-width="2.4"'
                 ' stroke-linejoin="round" stroke-linecap="round" marker-end="url(#ar)" opacity=".92"/>')

    # panel items
    for label, x, y, wall in PANEL:
        ax = X(x) + (-7 if wall == "left" else 7)
        p.append(f'<circle cx="{X(x):.0f}" cy="{Y(y):.0f}" r="5" fill="var(--accent)"/>')
        p.append(f'<text x="{ax:.0f}" y="{Y(y)+4:.0f}" font-size="11" fill="currentColor"'
                 f' text-anchor="{"end" if wall=="left" else "start"}">{_esc(label)}</text>')

    lx, ly = X(250), Y(238)
    for i, (kind, label) in enumerate((("mains", "mains, 220 V"), ("v24", "24 V"),
                                       ("v6", "6 V"), ("ctrl", "E-stop coil"),
                                       ("link", "to the control box"))):
        yy = ly + i * 15
        p.append(f'<line x1="{lx:.0f}" y1="{yy:.0f}" x2="{lx+18:.0f}" y2="{yy:.0f}"'
                 f' stroke="var(--w-{kind})" stroke-width="2.6" stroke-linecap="round"/>')
        p.append(f'<text x="{lx+25:.0f}" y="{yy+4:.0f}" font-size="10.5" fill="currentColor"'
                 f' opacity=".8">{label}</text>')

    p.append("</svg>")
    return "\n".join(p)


def elevation_svg(scale=2.4):
    sched, rail_len = rail_schedule()
    pad_l, pad_t = 14, 26
    H_MCB, H_TB = 85.0, 58.0
    vw = rail_len * scale + pad_l * 2
    vh = H_MCB * scale + pad_t + 76
    X = lambda mm: pad_l + (mm - RAIL_START) * scale
    base = pad_t + H_MCB * scale

    p = [f'<svg viewBox="0 0 {vw:.0f} {vh:.0f}" role="img" xmlns="http://www.w3.org/2000/svg"'
         ' aria-label="Front elevation of the DIN rail: breaker, mains terminals, DC breaker,'
         ' relay, DC terminals and spares, in the order power flows through them.">']
    p.append(f'<line x1="{X(RAIL_START):.0f}" y1="{base:.0f}" x2="{X(RAIL_START+rail_len):.0f}"'
             f' y2="{base:.0f}" stroke="currentColor" stroke-width="3" opacity=".7"/>')

    for name, x, w, kind, note in sched:
        if kind in ("part", "clamp"):
            continue
        h = H_MCB if kind in ("mcb", "relay") else H_TB
        fill = {"mcb": "var(--w-mains)", "relay": "var(--accent)"}.get(kind, f"var(--w-{kind})")
        p.append(f'<rect x="{X(x):.0f}" y="{base - h*scale:.0f}" width="{max(w*scale-1.2,2.5):.0f}"'
                 f' height="{h*scale:.0f}" rx="1.5" fill="{fill}" opacity=".88"/>')
        if kind in ("mcb", "relay"):
            p.append(f'<text x="{X(x+w/2):.0f}" y="{base - h*scale/2 + 4:.0f}" text-anchor="middle"'
                     f' font-size="12" font-weight="600" fill="var(--surface)">{_esc(name)}</text>')
        else:
            p.append(f'<text x="{X(x+w/2):.0f}" y="{base - h*scale - 6:.0f}" text-anchor="middle"'
                     f' font-size="9" fill="currentColor" opacity=".75"'
                     f' transform="rotate(-90 {X(x+w/2):.0f} {base - h*scale - 6:.0f})">{_esc(name)}</text>')

    for label, a, b in (("mains, protected", RAIL_START + 8, RAIL_START + 81),
                        ("DC protect + switch", RAIL_START + 83, RAIL_START + 119),
                        ("DC distribution", RAIL_START + 121, RAIL_START + 163),
                        ("spare", RAIL_START + 164, RAIL_START + 185)):
        y = base + 16
        p.append(f'<line x1="{X(a):.0f}" y1="{y:.0f}" x2="{X(b):.0f}" y2="{y:.0f}"'
                 ' stroke="currentColor" stroke-width="1.2" opacity=".5"/>')
        p.append(f'<text x="{X((a+b)/2):.0f}" y="{y+15:.0f}" text-anchor="middle" font-size="10.5"'
                 f' fill="currentColor" opacity=".72">{_esc(label)}</text>')

    p.append(f'<text x="{X(RAIL_START):.0f}" y="{pad_t-10:.0f}" font-size="11" fill="currentColor"'
             f' opacity=".7">{rail_len:.0f} mm of rail — MCBs 85 mm tall, terminals 58 mm,'
             f' in a 124 mm cavity</text>')
    p.append("</svg>")
    return "\n".join(p)


PAGE = """<title>Power Box Rail Layout</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap">
<style>
:root{
  --paper:#e9edf1; --surface:#fff; --surface-2:#f3f6f8; --rail:#dfe5ea;
  --ink:#131b22; --ink-2:#4a5a67; --ink-3:#7d8d9a; --line:#ccd6de; --line-2:#dde4ea;
  --accent:#c2622c;
  --w-mains:#8a4b2f; --w-L:#8a4b2f; --w-N:#35628f; --w-E:#5d7f2e;
  --w-v24:#c2622c; --w-v0:#4a5a67; --w-v6:#9c7520; --w-ctrl:#7a4fa3; --w-link:#2f7fa6;
  --w-sp:#aab6c0;
}
@media (prefers-color-scheme:dark){ :root:not([data-theme="light"]){
  --paper:#0c1218; --surface:#141d25; --surface-2:#19232c; --rail:#223039;
  --ink:#e4ecf2; --ink-2:#9aabb8; --ink-3:#6c7d8a; --line:#26333d; --line-2:#1e2a33;
  --accent:#e08a52;
  --w-mains:#c47a52; --w-L:#c47a52; --w-N:#5f94c4; --w-E:#90b85c;
  --w-v24:#e08a52; --w-v0:#8fa0ad; --w-v6:#d2a948; --w-ctrl:#a67fd0; --w-link:#5aa8cc;
  --w-sp:#55646f;
}}
:root[data-theme="dark"]{
  --paper:#0c1218; --surface:#141d25; --surface-2:#19232c; --rail:#223039;
  --ink:#e4ecf2; --ink-2:#9aabb8; --ink-3:#6c7d8a; --line:#26333d; --line-2:#1e2a33;
  --accent:#e08a52;
  --w-mains:#c47a52; --w-L:#c47a52; --w-N:#5f94c4; --w-E:#90b85c;
  --w-v24:#e08a52; --w-v0:#8fa0ad; --w-v6:#d2a948; --w-ctrl:#a67fd0; --w-link:#5aa8cc;
  --w-sp:#55646f;
}
*{box-sizing:border-box}
body{margin:0; background:var(--paper); color:var(--ink);
  font-family:"IBM Plex Sans",system-ui,sans-serif; font-size:15px; line-height:1.55;
  -webkit-font-smoothing:antialiased}
.wrap{max-width:1000px; margin:0 auto; padding:30px 22px 60px}
h1{margin:0; font-size:27px; font-weight:600; letter-spacing:-.02em}
.sub{margin:5px 0 0; color:var(--ink-2); font-size:14px; max-width:66ch}
h2{margin:0 0 10px; font-size:10.5px; font-weight:600; text-transform:uppercase;
   letter-spacing:.1em; color:var(--ink-3)}
figure{margin:26px 0 0; padding:16px; background:var(--surface);
       border:1px solid var(--line); border-radius:4px; overflow-x:auto}
figure svg{display:block; max-width:100%; height:auto; color:var(--ink)}
figcaption{margin-top:12px; font-size:12.5px; color:var(--ink-2); max-width:72ch}
table{width:100%; border-collapse:collapse; font-size:13px; margin-top:4px}
th{text-align:left; font-size:10px; text-transform:uppercase; letter-spacing:.09em;
   color:var(--ink-3); font-weight:600; padding:0 8px 6px 0; border-bottom:1px solid var(--line)}
td{padding:6px 8px 6px 0; border-bottom:1px solid var(--line-2); vertical-align:top}
tr:last-child td{border-bottom:none}
.num{font-family:"IBM Plex Mono",monospace; font-variant-numeric:tabular-nums; white-space:nowrap}
.sw{display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:7px;
    vertical-align:-1px}
.panel{background:var(--surface); border:1px solid var(--line); border-radius:4px;
       padding:16px; margin-top:16px}
.cols{display:grid; grid-template-columns:1fr 1fr; gap:16px}
@media (max-width:820px){.cols{grid-template-columns:1fr}}
.note{margin-top:16px; padding:12px 14px; font-size:13.5px; color:var(--ink-2);
      background:var(--surface); border-left:2px solid var(--accent); border-radius:0 3px 3px 0}
.note b{color:var(--ink)}
code{font-family:"IBM Plex Mono",monospace; font-size:.92em}
footer{margin-top:26px; padding-top:14px; border-top:1px solid var(--line);
       font-size:12px; color:var(--ink-3)}
</style>

<div class="wrap">
  <h1>Power box — rail layout</h1>
  <p class="sub">UN4412, 442 × 265 mm floor. Everything mains-side lives here; the control
  box gets four conductors and nothing above 24 V. Drawn to scale from the same tables
  printed below it.</p>

  <figure>
    __PLAN__
    <figcaption><b>Floor plan.</b> DIN gear along the back wall, supplies in front, and a
    single 25 mm duct that every run passes through — so nothing crosses open floor and
    any wire can be followed end to end. Arrows point the direction power flows.</figcaption>
  </figure>

  <figure>
    __ELEV__
    <figcaption><b>The rail, front on.</b> Four zones in the order power moves through
    them. Breakers and the relay stand 85 mm; terminals 58 mm. The cavity is 124 mm, so
    the tall parts clear the lid with ~39 mm to spare.</figcaption>
  </figure>

  <div class="panel">
    <h2>Rail schedule</h2>
    <table><thead><tr><th>Pos</th><th class="num">mm</th><th class="num">Width</th>
      <th>Item</th></tr></thead><tbody>__SCHED__</tbody></table>
  </div>

  <div class="cols">
    <div class="panel">
      <h2>The link to the control box</h2>
      <table><thead><tr><th>Conductor</th><th class="num">mm²</th><th>Why</th></tr></thead>
        <tbody>__LINK__</tbody></table>
    </div>
    <div class="panel">
      <h2>Wire runs</h2>
      <table><thead><tr><th>From → to</th><th>Cores</th></tr></thead>
        <tbody>__RUNS__</tbody></table>
    </div>
  </div>

  <div class="note"><b>The relay earns its place by what it does <i>not</i> cut.</b>
  K1 switches only the driver feed. The board sits upstream of it on <code>+24 always</code>,
  so an E-stop drops the motors while GRBL stays awake and can tell you it happened —
  rather than rebooting and losing where it was. The E-stop button is wired
  <b>normally-closed in series with K1's coil</b>, so a cut wire stops the machine too.</div>

  <div class="note"><b>This is why the link is four wires, not three.</b> Splitting
  always-on from switched is what makes the above possible. The ground stays at 2.5 mm²
  for the reason in <code>FINDINGS.md</code> §7 — the servo's 2.5 A return shares it.</div>

  <div class="note"><b>MCB2 protects the wiring, not the supply.</b> The LRS-350 already
  limits its own output. What it cannot do is notice a pinched conductor in the drag chain
  drawing 4 A through a wire sized for 1.7.</div>

  <footer>Generated by <code>python3 hardware/psu_layout.py</code> — the drawing and the
  tables come from the same data, so they cannot disagree.</footer>
</div>
"""


def build():
    sched, _ = rail_schedule()
    rows = []
    for i, (name, x, w, kind, note) in enumerate(sched):
        if kind in ("part", "clamp"):
            continue
        rows.append(f'<tr><td><span class="sw" style="background:var(--w-{kind})"></span>'
                    f'{_esc(name)}</td><td class="num">{x:.1f}</td>'
                    f'<td class="num">{w:.1f}</td><td>{_esc(note)}</td></tr>')

    link = "".join(f'<tr><td>{_esc(n)}</td><td class="num">{mm2}</td><td>{_esc(w)}</td></tr>'
                   for n, mm2, w in LINK)
    runs = "".join(f'<tr><td><span class="sw" style="background:var(--w-{k})"></span>'
                   f'{_esc(a)} → {_esc(b)}</td><td class="num">{_esc(c)}</td></tr>'
                   for a, b, c, k, _ in RUNS)

    html = (PAGE.replace("__PLAN__", plan_svg())
                .replace("__ELEV__", elevation_svg())
                .replace("__SCHED__", "".join(rows))
                .replace("__LINK__", link)
                .replace("__RUNS__", runs))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html)
    return OUT


if __name__ == "__main__":
    path = build()
    print(f"wrote {path.relative_to(path.parent.parent.parent)}  ({path.stat().st_size/1024:.0f} KB)")
