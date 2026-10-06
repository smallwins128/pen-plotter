#!/usr/bin/env python3
"""Control box: floor layout, DIN rail, and every individual conductor.

    python3 hardware/ctrl_layout.py     -> hardware/out/ctrl_layout.html

Same engine as the power box (panel.py); only the tables differ. Nothing in
this box is above 24 V -- the link from the power box brings +24 always,
+24 switched, +6 and ground, and that is all that comes in.

What decided the placement:

  TB6600     All twelve terminals are on ONE long face, in two six-way blocks
             side by side. So the drivers stand in a row with that face turned
             forward and a single duct, H2, takes the lot.
  grouping   Ports are grouped by what they are. The whole front wall goes to
             the machine -- three motors, the servo, two endstops, in that
             order. Power comes in on the right wall, beside the rail it lands
             on and nowhere near the outputs. USB is on the left wall, beside
             the board it plugs into.
  ducts      One vertical between each pair of drivers and one at the right, so
             nothing has to run the length of the box to change ducts.

Board header positions are PROVISIONAL -- see the note on the page. Everything
else is from the real parts.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import panel  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent / "out" / "ctrl_layout.html"

FLOOR = (442.0, 265.0)          # UN4412 internal, same case as the power box

# --- the rail ----------------------------------------------------------------
# No breakers here: the power box already protects everything that arrives, and
# nothing in this box is above 24 V. So the rail is all feed-through blocks and
# it is shallower -- 45 mm, not the 70 mm an MCB needs.
RAIL = [
    ("", 8.0, "clamp", "end clamp"),
    ("+24s", 5.2, "v24", "switched 24 V in from the link, out to driver X1"),
    ("+24sa", 5.2, "v24", "out to drivers X2 and Y"),
    ("+24a", 5.2, "v24", "always-on 24 V in from the link, out to the board"),
    ("+24f", 5.2, "v24", "always-on out to the fan — cooling outlives an E-stop"),
    ("", 2.0, "part", ""),
    ("+6", 5.2, "v6", "6 V in from the link, out to the servo connector"),
    ("", 2.0, "part", ""),
    ("0V", 5.2, "v0", "ground in from the link, out to driver X1"),
    ("0Va", 5.2, "v0", "out to drivers X2 and Y"),
    ("0Vb", 5.2, "v0", "out to the board, and the X endstop common"),
    ("0Vc", 5.2, "v0", "out to the Y endstop common, and the servo"),
    ("0Vd", 5.2, "v0", "out to the fan"),
    ("", 2.0, "part", ""),
    ("+5", 5.2, "v5", "5 V in from the board, out to driver X1's opto anodes"),
    ("+5a", 5.2, "v5", "out to drivers X2 and Y"),
    ("", 2.0, "part", ""),
    ("EX", 5.2, "es", "X endstop: in from the connector, out to the board"),
    ("EY", 5.2, "es", "Y endstop: in from the connector, out to the board"),
    ("PWM", 5.2, "pwm", "servo signal: in from the board, out to the connector"),
    ("", 2.0, "part", ""),
    ("sp", 5.2, "sp", "spare"), ("sp", 5.2, "sp", "spare"),
    ("sp", 5.2, "sp", "spare"), ("sp", 5.2, "sp", "spare"),
    ("", 8.0, "clamp", "end clamp"),
]

RAIL_START, RAIL_Y, RAIL_DEPTH = 295.0, 4.0, 45.0
RAIL_SUBS = {}
JUMPERS = [("+24s", "+24sa"), ("+24a", "+24f"),
           ("0V", "0Va", "0Vb", "0Vc", "0Vd"), ("+5", "+5a")]

# --- the duct grid -----------------------------------------------------------
DUCTS = {
    "H1": ("h",  91.0, 133.0,  10.0, 430.0),   # the spine: rail, board, link, fan
    "H2": ("h", 205.0, 247.0,  10.0, 425.0),   # the drivers' one terminal face
    "VA": ("v", 140.0, 165.0,  91.0, 247.0),   # one between each pair of drivers,
    "VB": ("v", 270.0, 295.0,  91.0, 247.0),   # as in the power box, so nothing has
    "V1": ("v", 400.0, 425.0,  91.0, 247.0),   # to run the length of the box
}
DUCT_LABEL_AT = {"H2": "start"}
DUCT_KIND = {"H1": ("duct", 40.0), "H2": ("duct", 40.0),
             "VA": ("duct", 25.0), "VB": ("duct", 25.0), "V1": ("duct", 25.0)}
SPINE = RAIL_DUCT = "H1"
# Band "a" is power and motor; band "b" is logic. A TB6600 puts both on the same
# face, so they do share H2 -- but never a lane next to each other.
BAND_A = {"v24", "v0", "v6", "motA", "motB"}
BANDS = {d: ("a", "b") for d in DUCTS}

# --- gear on the floor -------------------------------------------------------
# A TB6600 is 96.5 x 67.7 and ALL TWELVE terminals are on one long face, in two
# six-way blocks side by side with a gap. So the drivers stand in a row with that
# face turned forward, and one duct takes everything they have.
TBW, TBD = 96.5, 67.7
D1X, D2X, D3X = 40.0, 170.0, 300.0
DY0, DY1 = 135.0, 135.0 + TBD          # back edge, terminal face

GEAR = [
    ("TB6600 X1", D1X, DY0, TBW, TBD, "heatsink", "stepper driver, X left"),
    ("TB6600 X2", D2X, DY0, TBW, TBD, "heatsink", "stepper driver, X right"),
    ("TB6600 Y", D3X, DY0, TBW, TBD, "heatsink", "stepper driver, Y — rides the gantry"),
    ("Elecrow 6-axis", 10.0, 4.0, 125.0, 85.0, "pcb", "controller; header positions provisional"),
    ("fan 40", 432.0, 155.0, 10.0, 40.0, "abs", "24 V, always on"),
]

# The face, left to right: the motor and supply block, a gap, then the signal
# block. Mounted this way round the motor terminals sit above their own
# connector on the front wall and the signal terminals face the board.
# CHECK YOUR SILKSCREEN -- clone boards reorder within a block.
FACE = ["B-", "B+", "A-", "A+", "VCC", "GND", "ENA-", "ENA+", "DIR-", "DIR+", "PUL-", "PUL+"]  # noqa: E501
FACE_OFF = [2.65, 10.27, 17.89, 25.51, 33.13, 40.75,
            55.75, 63.37, 70.99, 78.61, 86.23, 93.85]
FACE_CLS = {"B-": "motB", "B+": "motB", "A-": "motA", "A+": "motA",
            "VCC": "v24", "GND": "v0", "ENA-": "sig", "ENA+": "v5",
            "DIR-": "sig", "DIR+": "v5", "PUL-": "sig", "PUL+": "v5"}

# Provisional. The Elecrow product page is unreachable from the build container,
# so this is a plausible strip along the board's front edge, not measured.
BRD = ["VIN", "GND", "5V", "PUL1", "DIR1", "ENA1", "PUL2", "DIR2", "ENA2",
       "PUL3", "DIR3", "ENA3", "LIMX", "LIMY", "PWM"]
BRD_CLS = {"VIN": "v24", "GND": "v0", "5V": "v5", "LIMX": "es", "LIMY": "es",
           "PWM": "pwm"}

STRIPS = [(f"TB6600 {n}", "h", DY1, x, TBW, FACE_OFF, "H2",
           [(f"D{i}.{t}", FACE_CLS[t]) for t in FACE])
          for i, (n, x) in enumerate((("X1", D1X), ("X2", D2X), ("Y", D3X)), start=1)] + [
          ("Elecrow 6-axis", "h", 89.0, 10.0, 125.0, 8.0, "H1",
           [(f"BRD.{n}", BRD_CLS.get(n, "sig")) for n in BRD])]
# The driver bodies are behind their face, the board's body behind its own.
STRIP_SIDE = {"TB6600 X1": -1, "TB6600 X2": -1, "TB6600 Y": -1,
              "Elecrow 6-axis": -1}
MARKS = []


def _pins(cx, n, pitch=9.0):
    return [cx - pitch * (n - 1) / 2 + i * pitch for i in range(n)]


# Front wall: everything that goes out to the machine, in the order you plug it.
MOTOR_X = {"1": D1X + 22.0, "2": D2X + 22.0, "3": D3X + 22.0}
SERVO_X, EX_X, EY_X = 352.0, 382.0, 412.0

LOOSE = (
    # power in: left wall, on its own, landing straight on the spine by the rail
    [("LINK.+24a", 430.0, 100.0, "H1", "y"), ("LINK.+24s", 430.0, 108.0, "H1", "y"),
     ("LINK.+6", 430.0, 116.0, "H1", "y"), ("LINK.0V", 430.0, 124.0, "H1", "y"),
     ("FAN.+", 432.0, 168.0, "V1", "x"), ("FAN.-", 432.0, 182.0, "V1", "x")]
    # front wall: three motor connectors, each under its own driver's motor block
    + [(f"M{d}.{i+1}", x, 246.0, "H2", "y")
       for d, cx in MOTOR_X.items() for i, x in enumerate(_pins(cx, 4))]
    # front wall: the servo and the two endstops, beside the motors
    + [("SRV.V+", SERVO_X - 9, 246.0, "H2", "y"), ("SRV.GND", SERVO_X, 246.0, "H2", "y"),
       ("SRV.SIG", SERVO_X + 9, 246.0, "H2", "y"),
       ("EXG.sig", EX_X - 5, 246.0, "H2", "y"), ("EXG.com", EX_X + 5, 246.0, "H2", "y"),
       ("EYG.sig", EY_X - 5, 246.0, "H2", "y"), ("EYG.com", EY_X + 5, 246.0, "H2", "y")]
)

PANEL = [
    ("USB-C to the laptop", 0.0, 46.0, "left"),
    ("power in — GX16-6", 442.0, 112.0, "right"),
    ("fan 40 mm, exhaust", 442.0, 175.0, "right"),
    ("X1 motor", MOTOR_X["1"], 265.0, "front"),
    ("X2 motor", MOTOR_X["2"], 265.0, "front"),
    ("Y motor", MOTOR_X["3"], 265.0, "front"),
    ("servo", SERVO_X, 265.0, "front"),
    ("endstop X", EX_X, 265.0, "front"),
    ("endstop Y", EY_X, 265.0, "front"),
]

# --- every conductor ---------------------------------------------------------
# id, class, from, to, mm2, note
WIRES = [
    ("w01", "v24", "LINK.+24a", "+24a", 0.75, "stays up through an E-stop"),
    ("w02", "v24", "LINK.+24s", "+24s", 0.75, "K1 in the power box drops this"),
    ("w03", "v6",  "LINK.+6",   "+6",   0.75, ""),
    ("w04", "v0",  "LINK.0V",   "0V",   2.5,  "two sizes up: the servo's return shares it"),

    ("w05", "v24", "+24s",  "D1.VCC", 0.75, ""),
    ("w06", "v24", "+24sa", "D2.VCC", 0.75, ""),
    ("w07", "v24", "+24sa", "D3.VCC", 0.75, ""),
    ("w08", "v0",  "0V",    "D1.GND", 0.75, ""),
    ("w09", "v0",  "0Va",   "D2.GND", 0.75, ""),
    ("w10", "v0",  "0Va",   "D3.GND", 0.75, ""),

    ("w11", "motA", "D1.A+", "M1.1", 0.5, "coil A — black on the Ender loom"),
    ("w12", "motA", "D1.A-", "M1.2", 0.5, "coil A — green"),
    ("w13", "motB", "D1.B+", "M1.3", 0.5, "coil B — red"),
    ("w14", "motB", "D1.B-", "M1.4", 0.5, "coil B — blue"),
    ("w15", "motA", "D2.A+", "M2.1", 0.5, ""),
    ("w16", "motA", "D2.A-", "M2.2", 0.5, ""),
    ("w17", "motB", "D2.B+", "M2.3", 0.5, ""),
    ("w18", "motB", "D2.B-", "M2.4", 0.5, ""),
    ("w19", "motA", "D3.A+", "M3.1", 0.5, ""),
    ("w20", "motA", "D3.A-", "M3.2", 0.5, ""),
    ("w21", "motB", "D3.B+", "M3.3", 0.5, ""),
    ("w22", "motB", "D3.B-", "M3.4", 0.5, ""),

    ("w23", "sig", "BRD.PUL1", "D1.PUL-", 0.25, ""),
    ("w24", "sig", "BRD.DIR1", "D1.DIR-", 0.25, ""),
    ("w25", "sig", "BRD.ENA1", "D1.ENA-", 0.25, ""),
    ("w26", "sig", "BRD.PUL2", "D2.PUL-", 0.25, ""),
    ("w27", "sig", "BRD.DIR2", "D2.DIR-", 0.25, ""),
    ("w28", "sig", "BRD.ENA2", "D2.ENA-", 0.25, ""),
    ("w29", "sig", "BRD.PUL3", "D3.PUL-", 0.25, ""),
    ("w30", "sig", "BRD.DIR3", "D3.DIR-", 0.25, ""),
    ("w31", "sig", "BRD.ENA3", "D3.ENA-", 0.25, ""),
    ("w32", "v5",  "+5",  "D1.PUL+", 0.25, "then linked to DIR+ and ENA+ at the driver"),
    ("w33", "v5",  "+5a", "D2.PUL+", 0.25, ""),
    ("w34", "v5",  "+5a", "D3.PUL+", 0.25, ""),

    ("w35", "v24", "+24a",   "BRD.VIN", 0.75, "check the board's regulator first — FINDINGS §10"),
    ("w36", "v0",  "0Vb",    "BRD.GND", 0.75, ""),
    ("w37", "v5",  "BRD.5V", "+5",      0.25, "the opto anode supply for all three drivers"),

    ("w38", "es",  "EXG.sig", "EX",       0.25, ""),
    ("w39", "es",  "EX",      "BRD.LIMX", 0.25, ""),
    ("w40", "v0",  "0Vb",     "EXG.com",  0.25, ""),
    ("w41", "es",  "EYG.sig", "EY",       0.25, ""),
    ("w42", "es",  "EY",      "BRD.LIMY", 0.25, ""),
    ("w43", "v0",  "0Vc",     "EYG.com",  0.25, ""),

    ("w44", "v6",  "+6",      "SRV.V+",  0.75, ""),
    ("w45", "v0",  "0Vc",     "SRV.GND", 0.75, "the servo's own return, not shared with logic"),
    ("w46", "pwm", "BRD.PWM", "PWM",     0.25, ""),
    ("w47", "pwm", "PWM",     "SRV.SIG", 0.25, ""),

    ("w48", "v24", "+24f", "FAN.+", 0.5, ""),
    ("w49", "v0",  "0Vd",  "FAN.-", 0.5, ""),
]

COLOUR = {"v24": "red", "v0": "black", "v6": "orange", "v5": "yellow",
          "motA": "black / green", "motB": "red / blue", "sig": "violet",
          "es": "teal", "pwm": "pink"}
# Ferrule colours to DIN 46228-4. Order by cross-section, never by colour:
# a second code is in wide use (0.5 orange, 0.75 white, 1.0 yellow, 1.5 red,
# 2.5 blue) and cheap assorted kits often ship it.
FERRULE = {0.25: "0.25 lilac", 0.5: "0.5 white", 0.75: "0.75 blue",
           1.0: "1.0 red", 1.5: "1.5 black", 2.5: "2.5 grey"}
SLACK = 60.0

GROUPS = [("in from the power box", ("v24", "v0", "v6")),
          ("motor phases", ("motA", "motB")),
          ("step, direction, enable", ("sig", "v5")),
          ("endstops and the servo signal", ("es", "pwm"))]

LEGEND = [("v24", "+24 V, red"), ("v0", "0 V, black"), ("v6", "+6 V, orange"),
          ("v5", "+5 V, yellow"), ("motA", "coil A"), ("motB", "coil B"),
          ("sig", "step/dir/enable"), ("es", "endstop"), ("pwm", "servo signal")]

PLAN_ALT = ("Plan of the control box floor, drawn to scale: a DIN rail of feed-through"
            " terminals across the back, three TB6600 drivers standing front-to-back with"
            " their signal ends facing the rail and their motor ends facing the front wall,"
            " the controller board at the right, and all forty-nine conductors drawn"
            " individually in lanes inside four ducts.")
ELEV_ALT = ("Front elevation of the control box DIN rail: switched and always-on 24 V,"
            " 6 V, five ground blocks, the 5 V opto supply, two endstops, the servo signal"
            " and four spares, with jumper combs across each bridged group.")
ELEV_NOTE = "{rail:.0f} mm of rail — feed-through blocks only, 58 mm tall"
ELEV_ZONES = [("24 V", RAIL_START + 8, RAIL_START + 28),
              ("6 V", RAIL_START + 31, RAIL_START + 38),
              ("0 V ×5", RAIL_START + 40, RAIL_START + 66),
              ("5 V", RAIL_START + 69, RAIL_START + 79),
              ("signals", RAIL_START + 82, RAIL_START + 97),
              ("spare", RAIL_START + 100, RAIL_START + 120)]
FLOOR_LABEL = "UN4412 base — 442 × 265 mm internal, same case as the power box"

TERMINALS = panel.build_terminals(sys.modules[__name__])

PAGE = """<title>Control Box Wiring</title>
__HEAD__

<div class="wrap">
  <h1>Control box — every conductor</h1>
  <p class="sub">UN4412, 442 × 265 mm floor, the same case as the power box. Four
  conductors arrive and nothing in here is above 24 V. __NWIRE__ individual wires,
  each routed from the terminal it actually lands on, through a duct, to the terminal
  at the other end.</p>

  <figure>
    __PLAN__
    <figcaption><b>Floor plan, to scale.</b> A TB6600 carries all twelve of its
    terminals on <i>one</i> long face, in two six-way blocks side by side. So the three
    drivers stand in a row with that face turned forward and one duct, <b>H2</b>, takes
    everything they have — motor and supply from the left block, step/dir/enable from
    the right. Each driver's motor connector is on the front wall directly below its own
    motor block, so those four phase wires drop 45 mm and leave. The ports are grouped
    by what they are, not by what is nearest: <b>the whole front wall goes to the
    machine</b>, power comes in on the right beside the rail it lands on, and USB sits
    on the left beside the board it plugs into. Nothing crosses open floor.</figcaption>
  </figure>

  <figure>
    __ELEV__
    <figcaption><b>The rail, front on.</b> Feed-through blocks only — no breakers,
    because the power box already protects everything that arrives here. Pale bars are
    insertable jumper combs: four groups bridged without a wire.</figcaption>
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
      <h2>Links at each driver</h2>
      <table><thead><tr><th>Link</th><th class="num">Qty</th></tr></thead><tbody>
        <tr><td><code>PUL+</code> → <code>DIR+</code></td><td class="num">3</td></tr>
        <tr><td><code>DIR+</code> → <code>ENA+</code></td><td class="num">3</td></tr>
      </tbody></table>
    </div>
  </div>

  <div class="panel">
    <h2>Rail schedule — __RAIL__ mm</h2>
    <table><thead><tr><th>Pos</th><th class="num">mm</th><th class="num">Width</th>
      <th>Item</th></tr></thead><tbody>__SCHED__</tbody></table>
  </div>

  <div class="note"><b>The board's header positions are the one thing here that is
  guessed.</b> Elecrow's site is unreachable from the build container, so the strip
  down the top edge is a plausible order, not a measured one — it is drawn so you can
  see the routing idea, and the idea survives the headers being somewhere else. Measure
  yours and change <code>BRD</code> in <code>hardware/ctrl_layout.py</code>; the drawing,
  the lengths and the cut list all follow from it. Everything else on this page is from
  the real parts.</div>

  <div class="note"><b>Check the TB6600's silkscreen before you wire a single core.</b>
  The face is drawn <code>B− B+ A− A+ VCC GND</code> then, after the gap,
  <code>ENA− ENA+ DIR− DIR+ PUL− PUL+</code>. That is the common arrangement, but clones
  reorder within a block and some label the motor pair the other way round. What the
  layout actually depends on is that all twelve are on one face with the motor block at
  one end — if yours has the blocks the other way round, turn the driver end for end and
  the motor connector below it still lines up.</div>

  <div class="note"><b>Find the coil pairs with a meter, not with the wire colours.</b>
  Two wires that read a couple of ohms between them are one coil; two that read open are
  from different coils. The colours in the schedule are what an Ender 3 loom usually
  carries, and a 42-34 bought loose may not match. Getting A and B swapped turns the
  motor the wrong way; getting one coil reversed makes it buzz and not turn.</div>

  <div class="note"><b>USB is not on this drawing because it is not a conductor.</b>
  The panel socket on the left wall is a short moulded USB-C extension that plugs into
  the board — buy it made up, do not build one. A hand-wired USB lead is the fastest way
  to a port that enumerates intermittently, and <code>docs/FINDINGS.md</code> §3 is about
  what an intermittent connection costs you mid-plot.</div>

  <div class="note"><b>Only <code>PUL+</code> is fed from the rail.</b> The three opto
  anodes on each driver sit side by side, so one wire from <code>+5</code> and two 10 mm
  links at the driver do the job of three wires across the box. That is the same trick as
  the jumper combs on the rail: the tidiest wire is the one you do not run.</div>

  <div class="note"><b>Nothing here is switched except the drivers.</b>
  <code>+24s</code> feeds the three TB6600s and is what K1 in the power box drops on an
  E-stop. The board is on <code>+24a</code> and the fan on <code>+24f</code>, so GRBL
  stays awake to report the stop and the box keeps cooling. See
  <code>docs/FINDINGS.md</code> §10 for why all of this runs off one 24 V supply, and
  what to check about the board's own regulator before first power-up.</div>

  <footer>Generated by <code>python3 hardware/ctrl_layout.py</code>, on the same engine
  as the power box (<code>hardware/panel.py</code>). Lane assignment, routing, wire
  lengths and the cut list all come from the tables in this file, and the script refuses
  to write a layout whose wires pass through a part or whose ducts overflow.</footer>
</div>
"""


def build():
    return panel.write(sys.modules[__name__])


if __name__ == "__main__":
    build()
