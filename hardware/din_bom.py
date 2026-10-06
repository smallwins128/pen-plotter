#!/usr/bin/env python3
"""Seller-facing bill of materials for the two DIN rails.

    python3 hardware/din_bom.py       -> hardware/out/din_bom.html

A quotation sheet, not a build guide: line references, full ratings, and
quantities, with no project reasoning. Quantities are counted from the two rail
schedules so they cannot drift from the layouts; the ratings are written.

Everything a supplier needs to quote against is in the Specification column.
The one constraint they must honour is at the top: items A-03 to A-08 have to
come from one manufacturer's series, because jumper combs, end covers and
marker strips are not interchangeable between families.
"""

import datetime
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import din_parts                    # noqa: E402
import panel                        # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent / "out" / "din_bom.html"

KINDS, COMBS, RAILS, FEED, WAYS = din_parts.counts()
FER, WIR = din_parts.ferrules(), din_parts.wire()
DUCT = {}
for _label, _mod in din_parts.BOXES:
    for d, (_a, _c0, _c1, s0, s1) in _mod.DUCTS.items():
        kind, nom = _mod.DUCT_KIND[d]
        if kind == "duct":
            DUCT[nom] = DUCT.get(nom, 0.0) + (s1 - s0) / 1000.0

COMBTXT = ", ".join(f"{n} × {w}-way" for w, n in sorted(COMBS.items()))
RAILTOT = sum(RAILS.values())

# ref, item, [spec lines], qty, unit, equivalents
SECTIONS = [
 ("A", "DIN rail assembly", [
  ("A-01", "DIN rail, TS35", [
    "Top-hat section to <b>EN 60715 / IEC 60715</b> (DIN 46277-3)",
    "Width <b>35 mm</b>, height <b>7.5 mm</b> &mdash; <i>not</i> the 15 mm deep section",
    "Cold-rolled steel, zinc plated; 1.0 mm material",
    "Slotted (perforated) preferred, unslotted acceptable",
   ], "1", "× 1 m length",
   f"{RAILTOT:.0f} mm is actually used (two rails, {RAILS['power box']:.0f} mm and "
   f"{RAILS['control box']:.0f} mm). Any brand."),

  ("A-02", "End clamp (end stop)", [
    "For 35 mm TS35 rail",
    "Screw-tightened or spring-clip type",
   ], f"{KINDS['clamp']}", "pcs", "Any brand. Two per rail."),

  ("A-03", "Feed-through terminal block, 2.5 mm²", [
    "Standard <b>IEC 60947-7-1</b>",
    "Nominal cross-section <b>2.5 mm²</b>, width / pitch <b>5.2 mm</b>",
    "Rated current <b>24 A</b>, rated voltage <b>800 V</b>, impulse 8 kV, pollution degree 3",
    "Conductor range 0.14&ndash;4 mm² solid, 0.14&ndash;2.5 mm² stranded "
    "(0.25&ndash;2.5 mm² with ferrule), AWG 26&ndash;12",
    "<b>Must have a jumper / bridge slot</b> for an insertable comb",
    "Colour grey; screw or push-in clamp (push-in preferred)",
    "Mounting: TS35",
   ], f"{FEED}", "pcs",
   f"{KINDS['sp']} of these are planned spares. Generic <code>UK-2.5B</code>, Phoenix "
   "<code>PT 2,5</code> / <code>UT 2,5</code>, Wago <code>2002-1201</code>, "
   "Weidmüller <code>A2C 2.5</code> or equivalent."),

  ("A-04", "Earth / PE terminal block, 2.5 mm²", [
    "Standard <b>IEC 60947-7-2</b> (protective conductor terminal)",
    "Nominal cross-section <b>2.5 mm²</b>, width / pitch <b>5.2 mm</b> &mdash; "
    "same series as A-03",
    "Green / yellow body with a <b>metal foot that contacts the DIN rail</b>",
    "Conductor range as A-03",
   ], f"{KINDS['E']}", "pcs", "Same manufacturer and series as A-03."),

  ("A-05", "Fuse terminal block, 5 × 20 mm", [
    "Standard <b>IEC 60947-7-3</b>",
    "Swing-out or pull-out carrier for a <b>5 × 20 mm</b> cartridge fuse",
    "Rated 500 V, fuse-limited to 6.3 A; conductor range 0.5&ndash;4 mm²",
    "Width 6.2&ndash;8.2 mm depending on series &mdash; either fits, the rail has slack",
    "Same series as A-03",
   ], f"{KINDS['fuse']}", "pcs",
   "Phoenix <code>UT 4-HESI</code> / <code>UK 5-HESI</code>, Wago <code>2002-1611</code> "
   "or equivalent. Fuse itself is B-07."),

  ("A-06", "Insertable jumper comb, 10-way", [
    "<b>5.2 mm pitch</b>, to suit A-03",
    "Insulated, rated ≥ 24 A (match the block)",
    "Cuttable to shorter widths with side cutters",
    "<b>Same manufacturer and series as A-03</b> &mdash; combs are not interchangeable",
   ], "3", "pcs",
   f"Required bridges: {COMBTXT} = {WAYS} ways total. Supplied as 10-ways and cut down."),

  ("A-07", "End cover / partition plate", [
    "To suit A-03, approx. 1.5&ndash;2 mm thick",
    "Same manufacturer and series as A-03",
   ], "10", "pcs",
   "Four are needed (one per block row across the two enclosures); the rest are stock."),

  ("A-08", "Marker strip, blank", [
    "Snap-in marker strip to suit A-03 (5.2 mm pitch)",
    "Blank, write-on or printer-compatible",
    "Same manufacturer and series as A-03",
   ], "2", "packs", "Approx. 100 markers needed."),

  ("A-09", "MCB, 6 A, C-curve, 1P+N", [
    "Standard <b>IEC / EN 60898-1</b>",
    "Rated current <b>6 A</b>, tripping characteristic <b>C</b>",
    "Rated voltage 230/240 V AC, 50 Hz",
    "Breaking capacity <b>6 kA</b> (10 kA acceptable)",
    "<b>1P+N</b>, width 2 modules (35 mm), DIN TS35 clip mount",
   ], "1", "pcs",
   "C-curve is required: two switch-mode supplies have a cold-start inrush that trips a "
   "B-curve. Any reputable brand."),

  ("A-10", "Relay, 24 V DC coil", [
    "Standard <b>IEC 61810-1</b>",
    "Coil <b>24 V DC</b>, coil power ≤ 0.5 W",
    "<b>1 or 2 changeover</b> (SPDT / DPDT) contacts",
    "Contact rated <b>≥ 2 A at 24 V DC resistive</b> &mdash; the DC figure, not only "
    "the AC one. Switched load is 0.63 A",
    "Plug-in type, to suit the socket at A-11",
   ], "1", "pcs", "Finder <code>40.52.9.024</code> or equivalent."),

  ("A-11", "Relay socket, DIN mount", [
    "Screw-clamp terminals, TS35 mounting",
    "To suit A-10; approx. 15.8 mm wide",
    "With retaining clip",
   ], "1", "pcs", "Finder <code>95.05</code> or equivalent."),

  ("A-12", "Relay LED + free-wheeling diode module", [
    "<b>24 V DC</b>, polarised, with LED indication",
    "<b>Must include the free-wheeling (flyback) diode</b>",
    "Plugs into the socket at A-11",
   ], "1", "pcs",
   "Finder <code>99.02.9.024.99</code> or equivalent. Without the diode the coil's "
   "collapse puts a spike on the 24 V rail at every operation."),
 ]),

 ("B", "Panel wiring accessories", [
  ("B-01", "Slotted wiring duct with lid, 40 mm", [
    "PVC, grey, finger-slotted, clip-on lid included",
    "<b>40 mm wide</b> × 40 mm or 60 mm high",
   ], "1", "× 2 m length", f"{DUCT[40.0]:.2f} m required."),

  ("B-02", "Slotted wiring duct with lid, 25 mm", [
    "PVC, grey, finger-slotted, clip-on lid included",
    "<b>25 mm wide</b> × 40 mm or 60 mm high",
   ], "1", "× 2 m length", f"{DUCT[25.0]:.2f} m required."),
 ]),
]


def ferrule_rows():
    """One line per cross-section, ordered by size, with the wire that goes with it."""
    out, n = [], 3
    for mm2 in sorted(FER, reverse=True):
        colour = din_parts.psu_layout.FERRULE.get(mm2) or \
            din_parts.ctrl_layout.FERRULE[mm2]
        out.append((f"B-{n:02d}", f"Bootlace ferrule, {mm2:g} mm²", [
            "Insulated, <b>DIN 46228-4</b>",
            f"Cross-section <b>{mm2:g} mm²</b>, pin length 8 mm",
            f"Colour to DIN 46228-4: <b>{colour.split()[1]}</b>",
        ], f"{FER[mm2]}", "pcs",
            f"Pairs with {WIR[mm2]/1000:.2f} m of {mm2:g} mm² wire. "
            "<b>Order by cross-section, not by colour</b> &mdash; a second colour code "
            "is in wide use (0.5 orange, 0.75 white, 1.0 yellow, 1.5 red, 2.5 blue)."))
        n += 1
    out.append((f"B-{n:02d}", "Fuse, 5 A, 5 × 20 mm", [
        "<b>Time-lag (T)</b> characteristic, 250 V",
        "Ceramic preferred, glass acceptable",
    ], "5", "pcs", "For the fuse terminal at A-05, plus spares."))
    out.append((f"B-{n+1:02d}", "Fuse, 2 A, 5 × 20 mm", [
        "<b>Time-lag (T)</b> characteristic, 250 V",
        "Ceramic preferred, glass acceptable",
    ], "5", "pcs", "For the panel-mount IEC inlet's own fuse holder, plus spares."))
    return out


def wire_rows():
    out, n = [], 1
    for mm2 in sorted(WIR, reverse=True):
        out.append((f"C-{n:02d}", f"Panel wire, {mm2:g} mm² flexible", [
            "Single-core <b>flexible</b> (class 5) copper, PVC insulated",
            "<b>300/500 V</b> minimum (H05V-K); 450/750 V (H07V-K) acceptable",
            f"Cross-section <b>{mm2:g} mm²</b>",
        ], f"{WIR[mm2]/1000:.1f}", "m",
            "Colours are per the wiring schedules; split the length across them as "
            "convenient. Allow a full 100 m roll per colour if sold that way."))
        n += 1
    return out


import re  # noqa: E402

ALL = [(k, t, rows) for k, t, rows in SECTIONS]
ALL[1] = ("B", "Panel wiring accessories", SECTIONS[1][2] + ferrule_rows())
ALL.append(("C", "Wire", wire_rows()))

MATCH = "A-03 A-04 A-05 A-06 A-07 A-08"
TODAY = datetime.date.today().isoformat()


def _plain(html):
    return re.sub(r"<[^>]+>", "", html).replace("&mdash;", "—").replace("&ndash;", "–") \
        .replace("&nbsp;", " ").replace("&amp;", "&").replace("×", "x")


def plain_text():
    out = [f"PEN PLOTTER — DIN RAIL BILL OF MATERIALS   rev {TODAY}", ""]
    out.append("IMPORTANT: items " + MATCH + " must all come from ONE manufacturer's")
    out.append("series. Jumper combs, end covers and marker strips are not")
    out.append("interchangeable between families. Everything is 5.2 mm pitch.")
    for key, title, rows in ALL:
        out += ["", f"{key}. {title.upper()}", ""]
        for ref, item, specs, qty, unit, note in rows:
            out.append(f"{ref}  {_plain(item)}  —  {qty} {_plain(unit)}")
            for sp in specs:
                out.append(f"        - {_plain(sp)}")
            if note:
                out.append(f"        ({_plain(note)})")
            out.append("")
    out.append(f"{sum(len(r) for _k, _t, r in ALL)} line items.")
    return "\n".join(out)


PAGE = """<title>DIN Rail BOM</title>
__HEAD__
<style>
.doc{border:1px solid var(--line); background:var(--surface); border-radius:4px;
     padding:22px; margin-top:20px}
.meta{display:flex; flex-wrap:wrap; gap:10px 32px; margin-top:14px; font-size:12.5px;
      color:var(--ink-2)}
.meta b{color:var(--ink); font-weight:600}
.sec{margin-top:30px}
.sec h2{display:flex; align-items:baseline; gap:10px; font-size:11px; margin-bottom:0}
.sec h2 span{font-family:"IBM Plex Mono",monospace; font-size:13px; color:var(--accent);
             letter-spacing:0}
.line{display:grid; grid-template-columns:70px 1fr 118px; gap:10px 18px;
      padding:14px 0; border-top:1px solid var(--line-2); align-items:start}
.line:first-of-type{border-top:1px solid var(--line)}
.ref{font-family:"IBM Plex Mono",monospace; font-size:12.5px; color:var(--ink-3);
     font-weight:500; padding-top:1px}
.item{font-size:15px; font-weight:600; margin:0 0 6px}
.spec{margin:0; padding-left:16px; font-size:13px; color:var(--ink-2); line-height:1.5}
.spec li{margin:2px 0}
.ln{margin:8px 0 0; padding:0 0 0 12px; font-size:12.5px; color:var(--ink-3);
    max-width:70ch; border-left:2px solid var(--line-2); background:none}
.qty{text-align:right; font-family:"IBM Plex Mono",monospace;
     font-variant-numeric:tabular-nums; padding-top:1px}
.qty b{display:block; font-size:19px; font-weight:600; color:var(--ink);
       letter-spacing:-.01em}
.qty span{font-size:11.5px; color:var(--ink-3)}
@media (max-width:680px){
  .line{grid-template-columns:1fr auto; gap:6px 14px}
  .ref{grid-column:1; grid-row:1}
  .qty{grid-column:2; grid-row:1; text-align:right}
  .qty b{display:inline; font-size:15px}
  .qty span{display:inline; margin-left:5px}
  .body{grid-column:1 / -1; grid-row:2}
}
.warn{margin-top:18px; padding:14px 16px; border:1px solid var(--accent);
      border-left-width:3px; border-radius:0 3px 3px 0; background:var(--surface-2);
      font-size:13.5px; color:var(--ink-2)}
.warn b{color:var(--ink)}
.warn code{color:var(--ink)}
details{margin-top:24px; border:1px solid var(--line); border-radius:4px;
        background:var(--surface)}
summary{padding:12px 16px; cursor:pointer; font-size:13px; font-weight:600;
        color:var(--ink-2)}
summary:focus-visible{outline:2px solid var(--accent); outline-offset:-2px}
.plainwrap{padding:0 16px 16px}
pre{margin:0; padding:14px; background:var(--surface-2); border:1px solid var(--line-2);
    border-radius:3px; font-family:"IBM Plex Mono",monospace; font-size:11.5px;
    line-height:1.5; overflow-x:auto; white-space:pre; color:var(--ink-2)}
button{font:inherit; font-size:13px; font-weight:600; color:var(--surface);
       background:var(--accent); border:0; border-radius:3px; padding:8px 14px;
       cursor:pointer; margin-bottom:12px}
button:focus-visible{outline:2px solid var(--ink); outline-offset:2px}
.total{margin-top:22px; padding-top:14px; border-top:1px solid var(--line);
       font-size:13px; color:var(--ink-2)}
</style>

<div class="wrap">
  <h1>DIN rail bill of materials</h1>
  <p class="sub">Two control enclosures for a pen plotter. Everything below mounts on,
  or wires to, a 35 mm DIN rail. Quantities include the planned spares.</p>

  <div class="doc">
    <div class="meta">
      <div>Revision <b>__DATE__</b></div>
      <div>Line items <b>__NLINES__</b></div>
      <div>Rail required <b>__RAILMM__ mm</b> across two enclosures</div>
      <div>Supply voltage <b>230 V AC, 50 Hz</b> &rarr; <b>24 V DC</b></div>
    </div>

    <div class="warn"><b>One constraint before quoting.</b> Items
    <code>__MATCH__</code> must all come from <b>one manufacturer's series</b>. Jumper
    combs, end covers and marker strips are not interchangeable between manufacturers,
    and often not between series from the same manufacturer. Every terminal is
    <b>2.5 mm&sup2;, 5.2 mm pitch</b>. If your preferred series uses a different pitch,
    quote it &mdash; but quote the accessories from the same series, and say so.</div>

    __SECTIONS__

    <p class="total">__NLINES__ line items. Quantities are counted from the wiring
    schedules and include __SPARES__ spare terminals and spare fuses. Brand names in the
    notes are examples that carry the right accessories &mdash; equivalents are fine
    where the ratings match.</p>
  </div>

  <details>
    <summary>Plain text version &mdash; for email or WhatsApp</summary>
    <div class="plainwrap">
      <button type="button" id="copy">Copy to clipboard</button>
      <pre id="plain">__PLAIN__</pre>
    </div>
  </details>

  <footer>Generated by <code>python3 hardware/din_bom.py</code>. Quantities come from the
  same tables as the wiring layouts, so this sheet cannot disagree with them.</footer>
</div>

<script>
(function () {
  var btn = document.getElementById('copy');
  var pre = document.getElementById('plain');
  if (!btn || !pre) return;
  btn.addEventListener('click', function () {
    var text = pre.textContent;
    function done(ok) { btn.textContent = ok ? 'Copied' : 'Select the text below';
      setTimeout(function () { btn.textContent = 'Copy to clipboard'; }, 2000); }
    try {
      navigator.clipboard.writeText(text).then(function () { done(true); },
                                              function () { select(); });
    } catch (e) { select(); }
    function select() {
      try {
        var r = document.createRange(); r.selectNodeContents(pre);
        var s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
      } catch (e) {}
      done(false);
    }
  });
})();
</script>
"""


def build():
    nlines = sum(len(r) for _k, _t, r in ALL)
    secs = []
    for key, title, rows in ALL:
        secs.append(f'<div class="sec"><h2><span>{key}</span>{panel.esc(title)}</h2>')
        for ref, item, specs, qty, unit, note in rows:
            spec = "".join(f"<li>{s}</li>" for s in specs)
            secs.append(
                f'<div class="line"><div class="ref">{ref}</div>'
                f'<div class="body"><p class="item">{item}</p>'
                f'<ul class="spec">{spec}</ul>'
                + (f'<p class="ln">{note}</p>' if note else "")
                + f'</div><div class="qty"><b>{qty}</b><span>{unit}</span></div></div>')
        secs.append("</div>")

    html = (PAGE.replace("__HEAD__", panel.HEAD)
                .replace("__SECTIONS__", "".join(secs))
                .replace("__DATE__", TODAY)
                .replace("__NLINES__", str(nlines))
                .replace("__RAILMM__", f"{RAILTOT:.0f}")
                .replace("__SPARES__", str(KINDS["sp"]))
                .replace("__MATCH__", MATCH)
                .replace("__PLAIN__", panel.esc(plain_text())))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html)
    print(f"wrote {OUT.relative_to(OUT.parent.parent.parent)} "
          f"({OUT.stat().st_size/1024:.0f} KB) — {nlines} line items")
    return OUT


if __name__ == "__main__":
    build()
