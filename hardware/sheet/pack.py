#!/usr/bin/env python3
"""Fabricator pack: a cover sheet (PDF) + the six steel/aluminium DXFs + the window acrylic DXFs, zipped.

    python3 hardware/sheet/enclosure.py      # first: build + check the DXFs
    python3 hardware/sheet/pack.py           # then: cover sheet + zip

Needs Chromium for the PDF (Playwright's copy is used when present).
"""
import datetime
import json
import pathlib
import shutil
import subprocess
import sys
import zipfile

import enclosure as E

OUT = E.OUT
VERSION = sys.argv[1] if len(sys.argv) > 1 else "v1"
NAME = f"{datetime.date.today().isoformat()} Plotter enclosure cut pack {VERSION}"

FOLDED = {
    "control_body": f"{E.WO:.0f} W × {E.ZF - E.ZB:.0f} D × {E.T + E.H['control']:.0f} H",
    "power_body": f"{E.WO:.0f} W × {E.ZF - E.ZB:.0f} D × {E.T + E.H['power']:.0f} H",
    "control_lid": f"{E.WO + 2 * (E.CLR + E.T):.0f} W × {(E.ZF + E.CLR + E.T) - (E.ZB - E.T):.1f} D × {E.H['control'] + E.T:.0f} H (back)",
    "power_lid": f"{E.WO + 2 * (E.CLR + E.T):.0f} W × {(E.ZF + E.CLR + E.T) - (E.ZB - E.T):.1f} D × {E.H['power'] + E.T:.0f} H (back)",
    "control_base_plate": "flat, 440 × 285, notched",
    "power_base_plate": "flat, 440 × 285, notched",
    "acrylic_power_left": "flat",
    "acrylic_power_right": "flat",
    "acrylic_control": "flat",
}


def acrylic_parts():
    """Window acrylic: the opening + WIN['mar'] all round (the bezel covers the edge). No holes: screws pass outside it."""
    parts = []
    for name, title, (pl, _) in (("acrylic_power_left", "POWER FRONT · WINDOW ACRYLIC, LEFT", E.window_panes()[0]),
                                 ("acrylic_power_right", "POWER FRONT · WINDOW ACRYLIC, RIGHT", E.window_panes()[1]),
                                 ("acrylic_control", "CONTROL FRONT · WINDOW ACRYLIC", E.ctrl_window())):
        p = E.Part(name, title, "3 mm clear cast acrylic, protective film on both sides")
        p.solid = [pl.buffer(E.WIN["mar"], join_style=1, quad_segs=8)]
        p.notes = ["Laser cut. Edges hidden under a printed bezel: no polishing needed."]
        parts.append(p)
    return parts


def html(summary):
    rows = "".join(
        f"<tr><td>{i + 1}</td><td><code>{p['part']}.dxf</code></td><td>{p['title']}</td><td>{p['material']}</td>"
        f"<td class=n>{p['qty']}</td><td class=n>{p['flat'][0]:.1f} × {p['flat'][1]:.1f}</td><td class=n>{p['bends']}</td>"
        f"<td>{FOLDED[p['part']]}</td></tr>" for i, p in enumerate(summary["parts"]))
    b = summary["bend"]
    n_ok = sum(1 for c in summary["checks"] if c[0])
    refold = "".join(f"<li>{c[2]}</li>" for c in summary["checks"] if c[2].startswith("refold"))
    pages = "".join(
        f'<section class=page><h2>{i + 1} · {p["title"]}</h2><p class=meta><code>{p["part"]}.dxf</code> · {p["material"]} · qty {p["qty"]} · '
        f'flat {p["flat"][0]:.1f} × {p["flat"][1]:.1f} mm · folded {FOLDED[p["part"]]}</p>'
        f'<img src="{p["part"]}.svg" alt="{p["title"]} flat pattern"></section>' for i, p in enumerate(summary["parts"]))
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{NAME}</title><style>
@page {{ size: A3 landscape; margin: 12mm }}
body {{ font: 10.5pt/1.45 Helvetica, Arial, sans-serif; color: #111 }}
h1 {{ font-size: 18pt; margin: 0 0 2mm }} h2 {{ font-size: 13pt; margin: 0 0 1mm }}
table {{ border-collapse: collapse; width: 100%; margin: 3mm 0 }} td, th {{ border: 0.3mm solid #999; padding: 1.2mm 2mm; text-align: left; vertical-align: top }}
th {{ background: #eee }} td.n {{ text-align: right; font-variant-numeric: tabular-nums }}
.cols {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6mm }} .box {{ border: 0.3mm solid #999; padding: 3mm 4mm }}
.box h3 {{ margin: 0 0 1.5mm; font-size: 11pt }} ul {{ margin: 0; padding-left: 5mm }}
.page {{ page-break-before: always }} .page img {{ width: 100%; max-height: 240mm; object-fit: contain }} .meta {{ color: #444; margin: 0 0 2mm }}
code {{ font-size: 9.5pt }}
</style></head><body>
<h1>Plotter enclosures · cut &amp; bend pack</h1>
<p>Two stacked electronics boxes (control on top, power below), each a folded body + a folded lid, plus two flat base plates
and three flat acrylic window pieces.
Prepared by Allwin Tom · {datetime.date.today().isoformat()} · {VERSION}</p>
<table><tr><th>#</th><th>File</th><th>Part</th><th>Material</th><th>Qty</th><th>Flat (mm)</th><th>Bends</th><th>Folded outside (mm)</th></tr>{rows}</table>
<div class=cols>
<div class=box><h3>Bending</h3><ul>
<li>Every flat is drawn from the <b>inside face</b>. Every bend is <b>UP 90°</b>, inner radius <b>R1</b>.</li>
<li>Flats assume K {b['K']}, bend allowance {b['BA']} mm, bend deduction {b['BD']} mm per 90° bend (1 mm 304, R = t).
<b>If your bend deduction for 1 mm 304 at R1 differs, tell us the number</b>: we re-issue the flats so every hole lands where it should.</li>
<li>Bend order: small lips first (top lips, back lips, corner tabs, base back lip), then the side walls, then the front wall last.
Lid: return lips first, then the top-to-back bend.</li>
<li>Corner reliefs and end-of-flange reliefs are already cut into the outline.</li>
<li><b>Deliberate gaps, please keep:</b> flange ends stop {E.FOLD_GAP} mm short of neighbouring flanges; side-wall front edges and corner tabs
stop {E.TAB_GAP} mm short of the front wall (the rivets close it); the lid is {E.CLR} mm per side larger than the body.</li></ul></div>
<div class=box><h3>Layers</h3><ul>
<li><b>Visible</b> — cut (outline, holes, cutouts, vents).</li>
<li><b>Bend Center</b> (dash-dot) and <b>Visible Narrow</b> (bend-zone edges) — bend references, <b>do not cut</b>.</li>
<li><b>Bend Notes</b>, <b>Leaders</b>, <b>Title</b> — information only, do not cut or engrave.</li>
<li>DXF R12, millimetres, 1:1.</li></ul></div>
<div class=box><h3>Finish &amp; handling</h3><ul>
<li>304 stainless, brushed, protective film left on. Grain the same direction on all visible faces of both boxes.</li>
<li>Deburr all edges. No paint or coating.</li>
<li>Base plates: 2 mm 5052 aluminium (1.5 mm 304 acceptable). Deburr.</li>
<li>Acrylic: 3 mm clear cast acrylic, laser cut, film left on both sides. Edges are hidden, no polishing.</li>
<li>Tolerances: laser ±0.2 mm, bends ±0.5 mm.</li></ul></div>
<div class=box><h3>Fitted by the customer — do not insert</h3><ul>
<li>M3 rivnuts (Ø5 holes) in the body lips, round the control-front connector openings, on the control lid top and the power front;
solid rivets Ø3 (Ø3.2 holes) in the front corner tabs.</li>
<li>Window bezels, connector plates and side panels are 3D printed and screwed on later (Ø3.4 holes).</li>
<li>M4 rivnuts (Ø6 grid) in the base plates as needed; M4 standoffs, rubber feet, panels, fans.</li></ul></div>
</div>
<p><b>Checks:</b> {n_ok} design checks passed before these files were written — holes clear of bends (≥ 5 mm), webs ≥ 1.5 mm,
folded parts free of clashes, folded flanges at least 2 mm apart wherever they are not meant to touch, whole assembly (fans, panels, rivnuts,
base plate, standoffs) clear by 2 mm, lid clear of the body, every lid hole over its rivnut, base-plate standoffs over the floor's, panel cutouts and
screw patterns matched to the printed panels, every bend end relieved. The files were then read back and folded in software from the DXFs alone
(bends UP, R1): every hole lands where the design puts it, no part touches another, and with an inner radius anywhere from R0.6 to R2.5 the lid still
fits. Re-fold from their own bend lines:</p>
<ul>{refold}</ul>
{pages}
</body></html>"""


def chromium():
    for c in ("/opt/pw-browsers/chromium-1194/chrome-linux/chrome", shutil.which("chromium"), shutil.which("google-chrome")):
        if c and pathlib.Path(c).exists():
            return c
    return None


def main():
    summary = json.loads((OUT / "summary.json").read_text())
    for p in acrylic_parts():                       # acrylic is written here, not by enclosure.py: it is not folded or fitted
        dxf = OUT / f"{p.name}.dxf"
        E.write_dxf(p, dxf)
        v = E.verify_and_preview(dxf, OUT / f"{p.name}.svg")
        assert v["open_ends"] == 0, p.name
        summary["parts"].append(dict(part=p.name, title=p.title, material=p.material, qty=p.qty,
                                     flat=[round(v["size"][0], 1), round(v["size"][1], 1)], bends=0, holes=0, notes=p.notes))
    page = OUT / f"{NAME}.html"
    page.write_text(html(summary))
    pdf = OUT / f"{NAME}.pdf"
    ch = chromium()
    if ch:
        subprocess.run([ch, "--headless", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={pdf}", page.as_uri()], check=True, capture_output=True)
        print("wrote", pdf)
    zp = OUT / f"{NAME}.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        for p in summary["parts"]:
            z.write(OUT / f"{p['part']}.dxf", f"{p['part']}.dxf")
        if pdf.exists():
            z.write(pdf, pdf.name)
    print("wrote", zp)


if __name__ == "__main__":
    sys.exit(main())
