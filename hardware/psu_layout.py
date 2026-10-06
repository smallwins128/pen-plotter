#!/usr/bin/env python3
"""Power box: floor layout and every individual conductor, routed through ducts.

    python3 hardware/psu_layout.py      -> hardware/out/psu_layout.html

Data first, drawing second. The rail schedule, the gear placement, the terminal
strips, the duct grid and the 30 conductors are all tables. Every polyline in
the SVG comes out of route(), and the cut list comes out of the same polylines.
So the picture, the schedule and the wire lengths cannot disagree.

Terminal positions are taken from the real parts, not guessed:

  LRS-350-24   7-way strip on ONE 115 mm short end:  +V +V -V -V (E) N L
               -> AC and DC leave the same face. 215 mm is too long to stand
                  that face at the back wall, so it lies long-ways and the
                  face points at a vertical duct.
  RS-25-24     5-way strip on one short end:  +V -V (E) N L
  LM2596       IN+ IN- on one end, OUT+ OUT- on the OPPOSITE end
  IEC module   switched + fused inlet, spade terminals on the rear face
  fan          40 mm, flying leads

The duct grid is what makes the drawing clean: one horizontal collector H1
across the front of the rail, and a vertical duct beside each piece of gear so
that every terminal face points at a duct at 90 degrees. No wire crosses open
floor, and no wire leaves a terminal at an angle.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import panel  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent / "out" / "psu_layout.html"
FLOOR = (442.0, 265.0)          # UN4412 internal
MODULE = 17.5                   # one DIN module

# --- the rail, left to right, in the order power flows -----------------------
# name, width mm, kind, note
RAIL = [
    ("", 8.0, "clamp", "end clamp"),
    ("MCB1", 2 * MODULE, "mcb", "6 A 1P+N, C-curve — mains in, protects both PSUs"),
    ("", 2.0, "part", ""),
    ("L1", 5.2, "L", "line in from MCB1, out to the LRS-350"),
    ("L2", 5.2, "L", "line out to the RS-25"),
    ("N1", 5.2, "N", "neutral in from MCB1, out to the LRS-350"),
    ("N2", 5.2, "N", "neutral out to the RS-25"),
    ("PE1", 5.2, "E", "earth in from the IEC module"),
    ("PE2", 5.2, "E", "earth out to the LRS-350 chassis"),
    ("PE3", 5.2, "E", "earth out to the RS-25 chassis"),
    ("PE4", 5.2, "E", "earth out to the case + lid bonding stud"),
    ("", 2.0, "part", ""),
    ("F1", 6.2, "fuse", "fuse terminal, 5 A 5x20 mm — protects the 24 V trunk wiring"),
    ("", 2.0, "part", ""),
    ("K1", 16.0, "relay", "24 V coil, 1 N/O — drops the driver rail on E-stop"),
    ("", 2.0, "part", ""),
    ("+24", 5.2, "v24", "in from F1; also feeds the E-stop loop"),
    ("+24a", 5.2, "v24", "always on → the board, and K1's contact"),
    ("+24f", 5.2, "v24", "always on → the fan"),
    ("+24s", 5.2, "v24", "switched by K1 → the drivers"),
    ("0V", 5.2, "v0", "in from both supplies — the single-point 0 V bond"),
    ("0Va", 5.2, "v0", "→ the link, and the buck's return"),
    ("0Vb", 5.2, "v0", "→ the fan, and K1's coil return"),
    ("+6", 5.2, "v6", "in from the buck"),
    ("+6o", 5.2, "v6", "→ the link"),
    ("", 2.0, "part", ""),
    ("sp", 5.2, "sp", "spare"), ("sp", 5.2, "sp", "spare"), ("sp", 5.2, "sp", "spare"),
    ("", 8.0, "clamp", "end clamp"),
]

RAIL_START = 70.0               # mm from the left wall — the IEC module sits left of it
RAIL_Y = 18.0                   # mm from the back wall to the rail
RAIL_DEPTH = 70.0               # how far DIN gear projects from the wall
RAIL_FACE = RAIL_Y + RAIL_DEPTH # where a conductor leaves the gear, in plan

# sub-terminals on the multi-terminal modules: name, offset from the block's x
RAIL_SUBS = {
    "MCB1": [("MCB1.L-in", 4.0), ("MCB1.L-out", 13.0),
             ("MCB1.N-in", 22.0), ("MCB1.N-out", 31.0)],
    "K1":   [("K1.A1", 1.9), ("K1.A2", 5.9), ("K1.13", 10.9), ("K1.14", 14.9)],
}

# combs, not wires: adjacent blocks bridged by an insertable jumper bar
JUMPERS = [("L1", "L2"), ("N1", "N2"),
           ("+24", "+24a", "+24f"), ("0V", "0Va", "0Vb"), ("+6", "+6o")]

# --- the duct grid -----------------------------------------------------------
# name: (axis, c0, c1, s0, s1)
#   "h": c0..c1 are the y bounds, s0..s1 the x extent
#   "v": c0..c1 are the x bounds, s0..s1 the y extent
DUCTS = {
    "H1": ("h",  90.0, 132.0,   0.0, 430.0),   # the collector, across the rail face
    "V1": ("v", 221.0, 246.0,  90.0, 230.0),   # beside the LRS-350's terminal face
    "V2": ("v", 324.0, 349.0,  90.0, 192.0),   # between the RS-25 and the buck
    "V3": ("v", 414.0, 432.0,  90.0, 222.0),   # buck output and the fan
}
# Slotted duct comes in 25/40/60/80 mm widths; H1 and the two verticals are real
# duct, with 1 mm of clearance each side. V3 carries three conductors, which is
# not worth a duct: it is a spiral-wrapped pair and a single, in two P-clips.
DUCT_KIND = {"H1": ("duct", 40.0), "V1": ("duct", 25.0),
             "V2": ("duct", 25.0), "V3": ("clip", 0.0)}
LANE_PITCH, LANE_INSET = 2.1, 2.0
MAINS = {"L", "N", "E"}
# which band sits nearest the duct's "inner" edge
# Which band takes the lanes nearest a duct's inner edge. "a" is BAND_A below.
# In H1 that puts mains next to the rail it comes off; in the verticals it puts
# DC innermost, which is also the order the PSU strips read, so those fan out
# without a single crossing.
BANDS = {"H1": ("a", "b"), "V1": ("b", "a"), "V2": ("b", "a"), "V3": ("b", "a")}

# --- gear on the floor -------------------------------------------------------
# name, x, y, w, d, kind, note
GEAR = [
    ("LRS-350-24", 6.0, 134.0, 215.0, 115.0, "psu",
     "24 V 14.6 A, ex-Ender 3 — lies long-ways, +V end toward the back wall"),
    ("RS-25-24", 246.0, 134.0, 78.0, 51.0, "psu", "24 V 1.1 A, the servo's supply"),
    ("LM2596", 349.0, 134.0, 65.0, 45.0, "pcb", "24 → 6.0 V buck, IN and OUT opposite ends"),
    ("IEC", 0.0, 30.0, 30.0, 50.0, "abs", "panel-mount switched + fused inlet"),
    ("fan 40", 432.0, 182.0, 10.0, 40.0, "abs", "24 V 40 mm, exhaust"),
]

# gear, face x, body y, body depth, pitch, duct, [(terminal, class)] back → front
STRIPS = [
    ("LRS-350-24", "v", 221.0, 134.0, 115.0, 10.5, "V1",
     [("LRS.+V", "v24"), ("LRS.+V2", "v24"), ("LRS.-V", "v0"), ("LRS.-V2", "v0"),
      ("LRS.PE", "E"), ("LRS.N", "N"), ("LRS.L", "L")]),
    ("RS-25-24", "v", 324.0, 134.0, 51.0, 7.6, "V2",
     [("RS.+V", "v24"), ("RS.-V", "v0"), ("RS.PE", "E"), ("RS.N", "N"), ("RS.L", "L")]),
]

# loose terminals: name, x, y, duct, stub axis
LOOSE = [
    ("BUCK.IN+", 349.0, 154.0, "V2", "x"), ("BUCK.IN-", 349.0, 159.0, "V2", "x"),
    ("BUCK.OUT+", 414.0, 154.0, "V3", "x"), ("BUCK.OUT-", 414.0, 159.0, "V3", "x"),
    ("IEC.L", 30.0, 42.0, "H1", "y"), ("IEC.N", 30.0, 55.0, "H1", "y"),
    ("IEC.PE", 30.0, 68.0, "H1", "y"),
    ("ESTOP.1", 16.0, 100.0, "H1", "y"), ("ESTOP.2", 16.0, 108.0, "H1", "y"),
    ("FRAME", 6.0, 124.0, "H1", "y"),
    ("FAN.+", 432.0, 197.0, "V3", "x"), ("FAN.-", 432.0, 213.0, "V3", "x"),
    ("LINK.+24a", 430.0, 100.0, "H1", "y"), ("LINK.+24s", 430.0, 106.0, "H1", "y"),
    ("LINK.+6", 430.0, 112.0, "H1", "y"), ("LINK.0V", 430.0, 118.0, "H1", "y"),
]

# panel penetrations: label, x, y, wall
PANEL = [
    ("IEC inlet", 0.0, 55.0, "left"),
    ("E-stop loop, 2-pole", 0.0, 104.0, "left"),
    ("earth out → machine frame", 0.0, 124.0, "left"),
    ("link gland → control box", 442.0, 109.0, "right"),
    ("fan 40 mm, exhaust", 442.0, 202.0, "right"),
]

# --- every conductor ---------------------------------------------------------
# id, class, from, to, mm2, note
WIRES = [
    ("w01", "L",    "IEC.L",      "MCB1.L-in",  1.0, "inlet is already switched and fused"),
    ("w02", "N",    "IEC.N",      "MCB1.N-in",  1.0, ""),
    ("w03", "E",    "IEC.PE",     "PE1",        1.0, "earth never passes through a breaker"),
    ("w04", "L",    "MCB1.L-out", "L1",         1.0, ""),
    ("w05", "N",    "MCB1.N-out", "N1",         1.0, ""),
    ("w06", "L",    "L1",         "LRS.L",      1.0, ""),
    ("w07", "N",    "N1",         "LRS.N",      1.0, ""),
    ("w08", "E",    "PE2",        "LRS.PE",     1.0, ""),
    ("w09", "L",    "L2",         "RS.L",       0.75, ""),
    ("w10", "N",    "N2",         "RS.N",       0.75, ""),
    ("w11", "E",    "PE3",        "RS.PE",      0.75, ""),
    ("w12", "E",    "PE4",        "FRAME",      1.5, "out to the machine frame — see the note"),
    ("w13", "v24",  "LRS.+V",     "F1",         1.5, "the whole 24 V output, through its fuse"),
    ("w14", "v0",   "LRS.-V",     "0V",         1.5, ""),
    ("w15", "v24",  "F1",         "+24",        1.5, ""),
    ("w16", "v24",  "+24a",       "K1.13",      1.5, "relay common"),
    ("w17", "v24",  "K1.14",      "+24s",       1.5, "the only rail K1 cuts"),
    ("w18", "ctrl", "+24",        "ESTOP.1",    0.5, "coil feed, out to the button"),
    ("w19", "ctrl", "ESTOP.2",    "K1.A1",      0.5, "N/C loop returns — a cut wire stops it too"),
    ("w20", "ctrl", "K1.A2",      "0Vb",        0.5, "coil return"),
    ("w21", "v24",  "RS.+V",      "BUCK.IN+",   0.75, ""),
    ("w22", "v0",   "RS.-V",      "0V",         0.75, "the one place the two supplies' 0 V meet"),
    ("w23", "v0",   "BUCK.IN-",   "0Va",        0.75, "buck return to the rail, not through its own trace"),
    ("w24", "v6",   "BUCK.OUT+",  "+6",         0.75, ""),
    ("w25", "v24",  "+24f",       "FAN.+",      0.5, "always on — cooling must not stop at an E-stop"),
    ("w26", "v0",   "0Vb",        "FAN.-",      0.5, ""),
    ("w27", "v24",  "+24a",       "LINK.+24a",  0.75, "to the board"),
    ("w28", "v24",  "+24s",       "LINK.+24s",  0.75, "to the three drivers"),
    ("w29", "v6",   "+6o",        "LINK.+6",    0.75, "to the servo"),
    ("w30", "v0",   "0Va",        "LINK.0V",    2.5, "two sizes up: the servo's 2.5 A return shares it"),
]

COLOUR = {"L": "brown", "N": "blue", "E": "green/yellow", "v24": "red",
          "v0": "black", "v6": "orange", "ctrl": "violet"}
FERRULE = {0.5: "0.5 orange", 0.75: "0.75 white", 1.0: "1.0 yellow",
           1.5: "1.5 black", 2.5: "2.5 blue"}
SLACK = 60.0                    # 30 mm of dressing allowance at each end

LINK = [("+24 always", 0.75, "to the board — stays up through an E-stop"),
        ("+24 switched", 0.75, "to the three drivers — K1 drops this"),
        ("+6", 0.75, "to the servo, via the control box"),
        ("0V", 2.5, "two sizes up: the servo's 2.5 A return shares it")]


# --- what panel.py needs to know about this box ------------------------------
SPINE = RAIL_DUCT = "H1"          # the duct every other duct meets
BAND_A = MAINS                    # mains keeps the lanes nearest the rail
STRIP_SIDE = {}                   # strips sit on a right-hand face; mark to the left
MARKS = [("BUCK.IN+", "v24", -1), ("BUCK.IN-", "v0", -1),
         ("BUCK.OUT+", "v6", 1), ("BUCK.OUT-", "sp", 1)]

PLAN_ALT = ("Plan of the power box floor, drawn to scale: a DIN rail across the back,"
            " the two supplies and the buck converter in front with their terminal faces"
            " turned toward vertical wiring ducts, and all thirty conductors drawn"
            " individually, each in its own lane inside the ducts.")
ELEV_ALT = ("Front elevation of the DIN rail: mains breaker, line, neutral and earth"
            " terminals, the DC breaker, the E-stop relay, the DC distribution terminals"
            " and three spares, in the order power flows, with jumper combs marked across"
            " each bridged group.")
ELEV_NOTE = ("{rail:.0f} mm of rail — breakers and the relay stand 85 mm, terminals 58 mm,"
             " in a 124 mm cavity. Pale bars are jumper combs.")
ELEV_ZONES = [("mains, protected", RAIL_START + 8, RAIL_START + 86),
              ("DC fuse + E-stop relay", RAIL_START + 88, RAIL_START + 113),
              ("DC distribution", RAIL_START + 115, RAIL_START + 162),
              ("spare", RAIL_START + 164, RAIL_START + 179)]
LEGEND = [("L", "L, brown"), ("N", "N, blue"), ("E", "PE, green/yellow"),
          ("v24", "+24 V, red"), ("v0", "0 V, black"), ("v6", "+6 V, orange"),
          ("ctrl", "E-stop loop, violet")]
FLOOR_LABEL = "UN4412 base — 442 × 265 mm internal, terminals facing up into the lid cavity"

TERMINALS = panel.build_terminals(sys.modules[__name__])

PAGE = """<title>Power Box Wiring</title>
__HEAD__

<div class="wrap">
  <h1>Power box — every conductor</h1>
  <p class="sub">UN4412, 442 × 265 mm floor. Thirty individual wires, each one routed from
  the terminal it actually lands on, through a duct, to the terminal at the other end. The
  gear is placed so that every terminal face points at a duct at 90° — which is the whole
  trick behind a panel that looks tidy.</p>

  <figure>
    __PLAN__
    <figcaption><b>Floor plan, to scale.</b> The LRS-350's terminals are on one 115 mm short
    end, so it cannot face the back wall — 215 mm of depth would not fit. It lies long-ways
    with that face turned into <b>V1</b> — its second <code>+V</code>/<code>−V</code> pair is left spare for a future feed. The RS-25 does the same into <b>V2</b>, where the
    buck's IN terminals meet it; the buck's OUT terminals are on the opposite end and face
    <b>V3</b>, which also picks up the fan. Everything collects in <b>H1</b> across the face
    of the rail. Nothing crosses open floor at all.</figcaption>
  </figure>

  <figure>
    __ELEV__
    <figcaption><b>The rail, front on.</b> Four zones in the order power moves through them.
    The pale bars are insertable jumper combs — six groups bridged without a single wire,
    which is where most of the clutter in a hand-wired box comes from.</figcaption>
  </figure>

  <div class="panel">
    <h2>Wire schedule — __NWIRE__ conductors, __TOTAL__ m including dressing slack</h2>
    <table><thead><tr><th>#</th><th>From</th><th>To</th><th class="num">mm²</th>
      <th>Colour</th><th>Ferrule</th><th>Route</th><th class="num">mm</th>
      <th>Why</th></tr></thead><tbody>__WIRES__</tbody></table>
  </div>

  <div class="cols3">
    <div class="panel">
      <h2>Cut list</h2>
      <table><thead><tr><th class="num">mm²</th><th class="num">Cores</th>
        <th class="num">Metres</th></tr></thead><tbody>__CUT__</tbody></table>
    </div>
    <div class="panel">
      <h2>Jumper combs</h2>
      <table><thead><tr><th>Bridged</th><th class="num">Ways</th></tr></thead>
        <tbody>__JUMP__</tbody></table>
    </div>
    <div class="panel">
      <h2>The link out</h2>
      <table><thead><tr><th>Conductor</th><th class="num">mm²</th></tr></thead>
        <tbody>__LINK__</tbody></table>
    </div>
  </div>

  <div class="panel">
    <h2>Rail schedule</h2>
    <table><thead><tr><th>Pos</th><th class="num">mm</th><th class="num">Width</th>
      <th>Item</th></tr></thead><tbody>__SCHED__</tbody></table>
  </div>

  <div class="note"><b>The duct grid is doing the work, not neatness.</b> A wire that leaves
  its terminal at 90° into a duct 20 mm away has nowhere to wander. The drawing puts the duct
  lids <i>over</i> the conductors, so what you see is what the box looks like built: short,
  identical stubs into a clean band. Inside the ducts the conductors lie across each other
  (__XING__ times) — that is normal and invisible, and it is why a duct exists.</div>

  <div class="note"><b>Lay the LRS-350 with its <code>+V</code> end toward the back wall.</b>
  The strip reads <code>+V +V −V −V ⏚ N L</code> in one fixed order, and the unit can only be
  turned end-for-end, so this choice is the one thing that decides whether the heavy DC pair
  takes the short route or the long one up V1. Back-wall-side puts the 14.6 A pair nearest H1.</div>

  <div class="note"><b>0 V is a star, not a chain.</b> Both supplies' <code>−V</code> land on
  the <code>0V</code> block and nowhere else, so that is the single point where they meet. The
  buck's return goes to <code>0Va</code> on the rail rather than being daisy-chained off the
  RS-25's screw — and the servo's 6 V return is taken from the rail too, not from the buck's
  <code>OUT−</code>, so 2.5 A never travels through the module's thin ground trace.
  <code>BUCK.OUT−</code> is deliberately left empty.</div>

  <div class="note"><b>The relay earns its place by what it does <i>not</i> cut.</b> K1
  switches only <code>+24s</code>. The board sits upstream on <code>+24a</code> and the fan on
  <code>+24f</code>, so an E-stop drops the motors while GRBL stays awake to tell you it
  happened and the box keeps cooling. The button is wired <b>normally-closed in series with
  K1's coil</b>, so a cut wire stops the machine too. It lives on the machine, not on this
  box — the box only carries a 2-pole connector for the loop.</div>

  <div class="note"><b>F1 protects the wiring, not the supply.</b> The LRS-350 already
  limits its own output. What it cannot do is notice a pinched conductor in the drag chain
  drawing 4 A through a wire sized for 1.7. It is a <b>fuse terminal</b> rather than a
  miniature breaker because an ordinary MCB is tested on AC, where the arc self-extinguishes
  twice a cycle; on DC it does not. At 24 V that is survivable, but a 5 x 20 mm fuse in a
  terminal-sized carrier is cheaper, narrower, sits in the same family as its neighbours,
  and removes the question.</div>

  <div class="note"><b>The earth blocks are commoned by the rail, not by a comb.</b> A PE
  block has a metal foot that clamps the DIN rail, so every PE block on the same rail is
  already the same node — which is also why the rail must be a single piece with the
  incoming earth landing on <code>PE1</code>. Do not fit a jumper comb across them; most
  PE blocks have no jumper slot to fit one into.</div>

  <div class="note"><b>There is no case to bond.</b> The UN4412 is plastic, so the only
  things here that need earthing are the two supplies' metal chassis. <code>PE4</code>
  goes out to the <b>machine frame</b> instead — not because a 24 V fault could make it
  live, but because an earthed frame gives the endstop and servo runs a reference, and
  because the day a mains-powered spindle or laser gets added, the frame is already
  earthed.</div>

  <footer>Generated by <code>python3 hardware/psu_layout.py</code>. Lane assignment, path
  routing, wire lengths and the cut list all come from the same tables as the drawing, and
  the script refuses to write a layout whose wires pass through a part.</footer>
</div>
"""
GROUPS = [("mains, 220 V", ("L", "N", "E")), ("24 V DC", ("v24", "v0")),
          ("6 V DC", ("v6",)), ("E-stop loop", ("ctrl",))]


def build():
    return panel.write(sys.modules[__name__])


if __name__ == "__main__":
    build()
