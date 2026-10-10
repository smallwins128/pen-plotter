#!/usr/bin/env python3
"""What to order for the two DIN rails, and how the parts go together.

    python3 hardware/din_parts.py      -> hardware/out/din_parts.html

The specifications here are written; the quantities are counted from the two
rail schedules, so the order list cannot drift from the layouts.

The one thing this page exists to explain: you do not wire a terminal block to
its neighbour to make a common bar. You push an insertable comb into the jumper
slots they all share. Everything else follows from that.
"""

import pathlib
import sys
from collections import defaultdict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import ctrl_layout                  # noqa: E402
import panel                        # noqa: E402
import psu_layout                   # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent / "out" / "din_parts.html"
BOXES = [("power box", psu_layout), ("control box", ctrl_layout)]


def counts():
    kinds, combs, rails = defaultdict(int), defaultdict(int), {}
    for label, mod in BOXES:
        sched, used = panel.rail_schedule(mod)
        rails[label] = used
        for _n, _x, _w, kind, _note in sched:
            kinds[kind] += 1
        for grp in mod.JUMPERS:
            combs[len(grp)] += 1
    feed = sum(kinds[k] for k in ("L", "N", "v24", "v0", "v6", "v5", "es", "pwm", "sp"))
    ways = sum(n * w for w, n in combs.items())
    return kinds, combs, rails, feed, ways


def ferrules():
    out = defaultdict(int)
    for _label, mod in BOXES:
        for r in panel.build_routes(mod)[0]:
            out[r["mm2"]] += 2
    return out


def wire():
    out = defaultdict(float)
    for _label, mod in BOXES:
        for r in panel.build_routes(mod)[0]:
            out[r["mm2"]] += r["len"]
    return out


BLOCK_SVG = """
<svg viewBox="0 0 560 320" role="img" xmlns="http://www.w3.org/2000/svg"
 aria-label="Section through one feed-through terminal block: a foot clipped over the
 DIN rail, a conductor clamped on each side, a single metal link joining the two clamps
 so the block is one electrical node, and a jumper slot in the top face with a comb
 prong dropping into it.">
  <defs><marker id="dp" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6"
    markerHeight="6" orient="auto"><path d="M0 0 L8 4 L0 8 z" fill="currentColor"/>
  </marker></defs>

  <!-- DIN rail in section, top-hat profile -->
  <path d="M150 266 L150 252 L168 252 L168 262 L352 262 L352 252 L370 252 L370 266 Z"
        fill="var(--rail)" stroke="currentColor" stroke-width="1.6"/>
  <!-- the block's foot, clipped over it -->
  <path d="M176 262 L176 248 L344 248 L344 262 L336 262 L336 256 L184 256 L184 262 Z"
        fill="var(--surface-2)" stroke="currentColor" stroke-width="1.4"/>

  <!-- body -->
  <rect x="166" y="104" width="188" height="146" rx="5"
        fill="var(--surface-2)" stroke="currentColor" stroke-width="1.8"/>
  <!-- jumper slot -->
  <rect x="238" y="104" width="44" height="34" fill="var(--paper)"
        stroke="currentColor" stroke-width="1.4"/>
  <!-- comb prong dropping in -->
  <rect x="250" y="40" width="20" height="92" rx="2" fill="var(--w-v24)" opacity=".9"/>

  <!-- the two clamps and the link between them -->
  <rect x="186" y="176" width="26" height="26" rx="2" fill="var(--ink-3)"/>
  <rect x="308" y="176" width="26" height="26" rx="2" fill="var(--ink-3)"/>
  <rect x="196" y="138" width="128" height="10" rx="3" fill="var(--w-v24)" opacity=".75"/>
  <line x1="199" y1="176" x2="199" y2="148" stroke="var(--w-v24)" stroke-width="7"
        opacity=".75"/>
  <line x1="321" y1="176" x2="321" y2="148" stroke="var(--w-v24)" stroke-width="7"
        opacity=".75"/>

  <!-- conductors -->
  <line x1="40" y1="189" x2="186" y2="189" stroke="var(--w-v0)" stroke-width="7"
        stroke-linecap="round"/>
  <line x1="334" y1="189" x2="480" y2="189" stroke="var(--w-v0)" stroke-width="7"
        stroke-linecap="round"/>

  <!-- labels -->
  <text x="44" y="174" font-size="12.5" fill="currentColor">wire in</text>
  <text x="476" y="174" font-size="12.5" fill="currentColor" text-anchor="end">wire out</text>
  <text x="134" y="266" font-size="12.5" fill="currentColor" text-anchor="end">DIN rail, TS35</text>
  <line x1="140" y1="262" x2="158" y2="262" stroke="currentColor" stroke-width="1.2"
        marker-end="url(#dp)"/>
  <text x="408" y="266" font-size="12.5" fill="currentColor">the foot clips over it</text>
  <line x1="402" y1="262" x2="350" y2="262" stroke="currentColor" stroke-width="1.2"
        marker-end="url(#dp)"/>
  <text x="396" y="118" font-size="12.5" fill="currentColor">the two clamps are</text>
  <text x="396" y="134" font-size="12.5" fill="currentColor">one piece of metal</text>
  <line x1="390" y1="140" x2="332" y2="143" stroke="currentColor" stroke-width="1.2"
        marker-end="url(#dp)"/>
  <text x="260" y="30" font-size="12.5" fill="currentColor" text-anchor="middle"
        font-weight="600">comb prong</text>
  <text x="130" y="112" font-size="12.5" fill="currentColor" text-anchor="end">jumper slot</text>
  <line x1="136" y1="108" x2="234" y2="118" stroke="currentColor" stroke-width="1.2"
        marker-end="url(#dp)"/>
  <text x="396" y="206" font-size="12.5" fill="currentColor">5.2 mm wide,</text>
  <text x="396" y="222" font-size="12.5" fill="currentColor">58 mm tall</text>
</svg>
"""

COMB_SVG = """
<svg viewBox="0 0 600 316" role="img" xmlns="http://www.w3.org/2000/svg"
 aria-label="Five terminal blocks in a row seen from the front. A three-way comb is
 pushed into the jumper slots of the first three, making them one electrical node with
 no wire between them. The fourth and fifth blocks are a different net, and the last one
 in the row carries an end cover.">
  <!-- the comb -->
  <rect x="64" y="40" width="172" height="16" rx="3" fill="var(--w-v24)" opacity=".9"/>
  <rect x="80" y="56" width="16" height="36" fill="var(--w-v24)" opacity=".9"/>
  <rect x="140" y="56" width="16" height="36" fill="var(--w-v24)" opacity=".9"/>
  <rect x="200" y="56" width="16" height="36" fill="var(--w-v24)" opacity=".9"/>
  <text x="150" y="30" font-size="12.5" font-weight="600" text-anchor="middle"
        fill="currentColor">one 3-way comb</text>

  <!-- five blocks -->
  <g stroke="currentColor" stroke-width="1.6">
    <rect x="60" y="92" width="56" height="128" rx="3" fill="var(--surface-2)"/>
    <rect x="120" y="92" width="56" height="128" rx="3" fill="var(--surface-2)"/>
    <rect x="180" y="92" width="56" height="128" rx="3" fill="var(--surface-2)"/>
    <rect x="240" y="92" width="56" height="128" rx="3" fill="var(--surface-2)"/>
    <rect x="300" y="92" width="56" height="128" rx="3" fill="var(--surface-2)"/>
    <rect x="360" y="92" width="10" height="128" rx="2" fill="var(--ink-3)"/>
  </g>
  <!-- jumper slots -->
  <g fill="var(--paper)" stroke="currentColor" stroke-width="1.2">
    <rect x="78" y="92" width="20" height="12"/><rect x="138" y="92" width="20" height="12"/>
    <rect x="198" y="92" width="20" height="12"/><rect x="258" y="92" width="20" height="12"/>
    <rect x="318" y="92" width="20" height="12"/>
  </g>
  <!-- rail -->
  <path d="M40 240 L40 226 L58 226 L58 236 L382 236 L382 226 L400 226 L400 240 Z"
        fill="var(--rail)" stroke="currentColor" stroke-width="1.6"/>

  <line x1="64" y1="258" x2="232" y2="258" stroke="var(--w-v24)" stroke-width="2.5"/>
  <text x="148" y="278" font-size="12.5" text-anchor="middle" fill="currentColor"
        font-weight="600">one node — and not one wire</text>
  <line x1="244" y1="258" x2="356" y2="258" stroke="currentColor" stroke-width="1.6"
        opacity=".5"/>
  <text x="300" y="298" font-size="12.5" text-anchor="middle" fill="currentColor"
        opacity=".8">a different net</text>
  <text x="390" y="88" font-size="12.5" fill="currentColor">end cover — the last block</text>
  <text x="390" y="104" font-size="12.5" fill="currentColor">in a row is open on one side</text>
  <line x1="384" y1="110" x2="372" y2="130" stroke="currentColor" stroke-width="1.2"/>
  <text x="420" y="160" font-size="12.5" fill="currentColor">5.2 mm pitch —</text>
  <text x="420" y="176" font-size="12.5" fill="currentColor">the comb must</text>
  <text x="420" y="192" font-size="12.5" fill="currentColor">match it</text>
</svg>
"""


# Every row: what it is, what the spec actually has to say, and where the
# quantity comes from. Quantities marked None are filled in from the model.
def order_rows():
    kinds, combs, rails, feed, ways = counts()
    fer, wir = ferrules(), wire()
    total_rail = sum(rails.values())
    combtxt = ", ".join(f"{n} x {w}-way" for w, n in sorted(combs.items()))

    duct = defaultdict(float)
    for _label, mod in BOXES:
        for d, (_a, _c0, _c1, s0, s1) in mod.DUCTS.items():
            kind, nom = mod.DUCT_KIND[d]
            if kind == "duct":
                duct[nom] += (s1 - s0) / 1000.0

    rows = [
        ("rail", "DIN rail, TS35",
         "35 mm top-hat to EN 60715, <b>7.5 mm deep</b>, slotted, zinc-plated steel",
         "1 x 1 m",
         f"{total_rail:.0f} mm used — {rails['power box']:.0f} for the power box, "
         f"{rails['control box']:.0f} for the control box. Cut both from one length with a "
         "hacksaw and file the burr off, or the blocks will not slide on."),

        ("rail", "End clamp (end stop)",
         "for TS35, screw or spring type — brand does not matter",
         f"{kinds['clamp']}",
         "Two per rail. Without them the whole row slides along the rail when you push a "
         "wire in."),

        ("block", "Feed-through terminal, 2.5 mm²",
         "<b>5.2 mm pitch</b>, grey, 24 A / 800 V, accepts 0.14–4 mm², with a "
         "<b>jumper slot</b>. Push-in or screw. Generic <code>UK-2.5B</code>; or Phoenix "
         "<code>PT 2,5</code> / <code>UT 2,5</code>, Wago <code>2002-1201</code>, "
         "Weidmüller <code>A2C 2.5</code>",
         f"{feed}",
         f"{kinds['sp']} of them are deliberate spares. One size does the whole job — a "
         "2.5 mm² block takes a 0.25 mm² wire happily once it has a ferrule on it."),

        ("block", "Earth terminal, 2.5 mm²",
         "same family and pitch, green/yellow, with a <b>metal foot that clamps the "
         "rail</b> (this is what makes it an earth block)",
         f"{kinds['E']}",
         "Power box only. These are commoned <i>by the rail</i>, so they take no comb — "
         "and most have no jumper slot to put one in."),

        ("block", "Fuse terminal, 5 × 20 mm",
         "same family and pitch, swing-out or pull-out carrier, for a 5 × 20 mm cartridge",
         f"{kinds['fuse']}",
         "F1, in the power box. A fuse rather than a small breaker because an ordinary MCB "
         "is tested on AC, where the arc dies twice a cycle; on DC it does not."),

        ("block", "Jumper comb, 10-way",
         "<b>same brand and family as the blocks</b>, 5.2 mm pitch, insulated",
         "3",
         f"You need {combtxt} = {ways} ways in total. Buy 10-ways and <b>cut them to "
         "length with side cutters</b> — that is what they are for, and it is far cheaper "
         "than buying each width."),

        ("block", "End cover / partition plate",
         "same family, 1–2 mm, matches the block profile",
         "10",
         "One for the open side of the last block in each row. There are four rows across "
         "the two boxes; the rest of the pack is for when you add a block later."),

        ("block", "Marker strip, blank",
         "same family, snaps into the block's label slot",
         "2 packs",
         "Label every block with the names in the two rail schedules. This is the "
         "difference between a box you can service and a box you have to trace."),

        ("gear", "MCB, 6 A, C-curve, 1P+N",
         "230 V AC, 6 kA breaking capacity, 2 modules (35 mm), DIN clip",
         "1",
         "Mains in, power box. C-curve because two switch-mode supplies have a cold-start "
         "inrush that a B-curve may trip on. If it nuisance-trips at switch-on, go to a "
         "<b>10 A C</b> — the wiring is 1.0 mm² and still protected."),

        ("gear", "Relay, 24 V DC coil, + DIN socket",
         "1 or 2 changeover, contact rated <b>at 24 V DC</b> (not just the AC figure), "
         "socket ~16 mm wide. Finder <code>40.52</code> + <code>95.05</code> socket + "
         "<code>99.02</code> LED/diode module, or equivalent",
         "1",
         "K1, the E-stop relay. It switches 0.63 A, so contact rating is not the "
         "constraint — but <b>get the module with the free-wheeling diode</b>, or the "
         "coil's collapse puts a spike on the 24 V rail every time you hit the button."),

        ("gear", "Slotted wiring duct + lid, 40 mm",
         "PVC, 40 mm wide, finger-slotted, with a clip-on lid",
         f"{duct[40.0]:.2f} m",
         "H1 in both boxes, and H2 in the control box."),

        ("gear", "Slotted wiring duct + lid, 25 mm",
         "PVC, 25 mm wide, finger-slotted, with a clip-on lid",
         f"{duct[25.0]:.2f} m",
         "The vertical ducts. Both boxes run at 3–14% fill, so the size is set by what "
         "will fit a finger, not by the copper."),
    ]

    first = True
    for mm2 in sorted(fer, reverse=True):
        why = f"Pairs with {wir[mm2]/1000:.2f} m of {mm2:g} mm² wire."
        if first:
            why += (" One for every stranded end in both boxes — <b>never tin one with "
                    "solder instead</b>, it creeps and the clamp goes loose months later.")
            first = False
        rows.append(("consumable", f"Bootlace ferrule, {mm2:g} mm²",
                     "insulated, DIN 46228-4 colour code", f"{fer[mm2]}", why))
    rows.append(("consumable", "Fuse, 5 A 5 × 20 mm, time-lag (T)", "ceramic or glass",
                 "5", "F1, plus spares."))
    rows.append(("consumable", "Fuse, 2 A 5 × 20 mm, time-lag (T)", "ceramic or glass",
                 "5", "The IEC inlet's own fuse. The whole box draws about 0.2 A at 230 V, "
                 "so 2 A is already generous; time-lag rides out the inrush."))
    return rows


GROUPS = [("rail", "The rail itself"), ("block", "On the rail"),
          ("gear", "Gear and duct"), ("consumable", "Consumables")]


PAGE = """<title>DIN Rail Parts</title>
__HEAD__
<style>
.lede{margin:18px 0 0; font-size:17px; line-height:1.5; color:var(--ink); max-width:62ch}
.qty{font-family:"IBM Plex Mono",monospace; font-variant-numeric:tabular-nums;
     white-space:nowrap; font-weight:600}
td.spec{color:var(--ink-2)}
td.why{color:var(--ink-2); font-size:12px}
h3{margin:26px 0 6px; font-size:17px; font-weight:600; letter-spacing:-.01em}
h3:first-of-type{margin-top:18px}
p{margin:8px 0 0; max-width:64ch}
ol{margin:10px 0 0; padding-left:20px; max-width:64ch}
li{margin:6px 0}
</style>

<div class="wrap">
  <h1>DIN rail parts</h1>
  <p class="sub">Everything that goes on the two rails, what the specification has to
  say, and how many. The quantities come from the same tables as the two layout
  drawings, so they cannot disagree with them.</p>

  <p class="lede">The thing worth understanding before you order: <b>you never wire one
  terminal block to the next.</b> Blocks that should be the same node are bridged by a
  comb that drops into a slot they all share. That is what a common bar is, and it is
  why the two boxes need only 79 wires between them instead of ninety-three.</p>

  <h3>What one block is</h3>
  <figure>
    __BLOCK__
    <figcaption><b>A feed-through block, in section.</b> A foot clips over the rail, and
    a conductor clamps on each side. The two clamps are <i>one piece of metal</i> — the
    block is a single electrical node with two places to land a wire, not a connector
    that joins two things. That is why the layouts allow exactly two wires per block and
    the script refuses a third.</figcaption>
  </figure>

  <h3>How you make a common bar</h3>
  <figure>
    __COMB__
    <figcaption><b>The comb does the commoning.</b> Push it into the jumper slots of
    adjacent blocks and they become one node. A 10-way comb cuts down to any width with
    side cutters, so three of them cover every group in both boxes. The pitch must match
    the blocks — a 5.2 mm comb on 6.2 mm blocks fits nothing.</figcaption>
  </figure>

  <p>Worked example, the ground group in the control box. Five blocks sit side by side:
  <code>0V 0Va 0Vb 0Vc 0Vd</code>. One 5-way comb bridges all five. Nine wires land on
  them — one in from the power box and eight out to the drivers, the board, the servo,
  the two endstop commons and the fan — and <b>none of those nine wires joins one block
  to another</b>. Every one of them goes somewhere real. Without the comb the same job
  needs four extra link wires and the ground star stops being a star.</p>

  <h3>The order</h3>
  <div class="panel">
    <table><thead><tr><th>Item</th><th>Specification</th><th class="qty">Qty</th>
      <th>Notes</th></tr></thead><tbody>__ROWS__</tbody></table>
  </div>

  <h3>Specifications that actually matter</h3>
  <ol>
    <li><b>Pitch, and only one of them.</b> Every block, every comb, every end cover is
    5.2 mm pitch, which is what a 2.5 mm² block is. Mixing pitches means the combs fit
    nothing.</li>
    <li><b>One family, one brand.</b> Combs, end covers and marker strips are
    <i>not</i> interchangeable between manufacturers, and often not between series from
    the same manufacturer. Pick a family and buy the accessories with the blocks. This is
    the mistake that costs a second order.</li>
    <li><b>7.5 mm rail, not 15 mm.</b> Both are called TS35. Terminal blocks want the
    7.5 mm one; the deep rail is for heavy gear.</li>
    <li><b>Current rating is not the constraint.</b> A 2.5 mm² block is good for 24 A and
    the heaviest thing here is 1.7 A. Size blocks by the wire you can get into them, not
    by the current.</li>
    <li><b>Push-in beats screw for a first build.</b> Screw clamps need the right torque
    and want re-checking after the box has warmed and cooled a few times. Push-in takes a
    ferruled wire with a shove and holds it. Either works; push-in is less to get
    wrong.</li>
  </ol>

  <h3>Things that catch people out</h3>
  <ol>
    <li><b>The last block in a row is open on one side.</b> Its clamp is exposed metal.
    That is what the end cover is for, and it is the part everyone forgets.</li>
    <li><b>Earth blocks are commoned by the rail.</b> They have a metal foot that grips
    it, so every earth block on that rail is already one node — no comb, and the
    incoming earth must land on one of them for the rail to be live with earth at all.
    Keep the rail one unbroken piece.</li>
    <li><b>A comb is a bus bar, so treat it like one.</b> Nothing stops you combing two
    groups together by accident. Count the ways twice before you push it home; cut it
    short rather than long.</li>
    <li><b>Ferrule everything stranded.</b> A bare stranded end in a clamp splays, and
    the strand that escapes is the one that finds its neighbour.</li>
    <li><b>Label as you go.</b> The marker strips are cheap and the rail schedules on the
    two layout pages are the names to write. Six months from now the colours will not be
    enough.</li>
  </ol>

  <div class="note"><b>Order of assembly.</b> Rail cut, deburred and screwed down first.
  Then end clamp, blocks pushed on in schedule order, second end clamp. Then the combs,
  then the end covers, then the markers — and only then start landing wires. Fitting a
  comb after the wires are in means taking wires out.</div>

  <footer>Generated by <code>python3 hardware/din_parts.py</code>. Quantities are counted
  from <code>psu_layout.py</code> and <code>ctrl_layout.py</code>; the specifications are
  written. Brand names are examples of families that carry the right accessories, not a
  claim about what is in stock near you.</footer>
</div>
"""


def build():
    rows = []
    for key, title in GROUPS:
        rows.append(f'<tr><td class="grp" colspan="4">{panel.esc(title)}</td></tr>')
        for g, name, spec, qty, why in order_rows():
            if g != key:
                continue
            rows.append(f'<tr><td><b>{panel.esc(name)}</b></td><td class="spec">{spec}</td>'
                        f'<td class="qty">{panel.esc(qty)}</td><td class="why">{why}</td></tr>')
    html = (PAGE.replace("__HEAD__", panel.HEAD)
                .replace("__BLOCK__", BLOCK_SVG)
                .replace("__COMB__", COMB_SVG)
                .replace("__ROWS__", "".join(rows)))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html)
    print(f"wrote {OUT.relative_to(OUT.parent.parent.parent)} "
          f"({OUT.stat().st_size/1024:.0f} KB)")
    return OUT


if __name__ == "__main__":
    build()
