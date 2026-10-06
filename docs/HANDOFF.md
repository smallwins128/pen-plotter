# Pen plotter — session handoff

Paste this into a fresh chat to pick up where the last one left off. Everything here is
**verified on the machine**, not assumed. Where something is unverified it says so.

_Last updated: 2026-10-06_

---

## Status in one paragraph

**Motion works properly.** Homing is repeatable, work zero survives resets, both limit
switches work, all three motors move accurately, and long single-stroke plots run start to
finish without errors. **The pen lift does not work reliably.** The servo responds
correctly to commands, but actuating it while the machine is moving resets the controller.
Cause is narrowed to supply/grounding around the servo; the fix is on order. **In the
meantime the machine plots single-stroke artwork with the pen taped down**, which is what
the files in `gcode/art/` are for.

Separately, **the electronics have been redesigned on paper and not yet built**: a
parametric model of the machine in `hardware/`, and two enclosures — a power box and a
control box — wired down to the individual conductor. Nothing in section 8 has been
assembled; it is a design to order against, and the parts list is section 8's whole
point. The servo problem above is unaffected by it either way.

---

## How to work with Claude on this

**Claude cannot reach the plotter.** It runs in a cloud container with no access to the
Mac, the USB port, or the machine. It cannot open the serial port, run a plot, or see what
happened. Every physical action goes through Allwin. That shapes everything below.

**Claude sends files, you save them.** G-code, tools and firmware arrive as downloadable
attachments. Save them into the folder you run commands from — `~/Downloads`, alongside
`plot2.py`. Everything is committed to the repo too, so nothing is lost if a download goes
astray.

**Claude gives one copy-pasteable command at a time.** Not a procedure to adapt — a literal
line to paste. Where a command needs a value only the machine can tell you (a measurement,
a port name), it says so explicitly.

**You never have to edit code.** If a script or a G-code file needs changing, Claude edits
it and sends a fresh copy. Say what you want different; don't open the file.

### What to send back

Three things, and the third is the one people skip:

1. **The command you ran**, especially if you changed it.
2. **The complete terminal output, pasted verbatim.** Not a summary. `ALARM:8`, `ALARM:9`
   and `error:5` mean three unrelated things, and "it failed" cannot be debugged. The
   status line matters as much as the error: `WCO`, `Pn:` and `MPos` have each turned out
   to be the whole answer at some point.
3. **What the machine physically did.** Which way it moved and how far, whether it buzzed,
   whether the pen touched the paper, whether a line appeared. **The terminal regularly
   reports success while the gantry is jammed against the frame** — GRBL counts out the
   moves it was told to make and has no idea the machine didn't follow. That exact
   situation cost hours on this build.

A photo beats a description whenever something has been drawn.

### Two rules that save time

**Change one thing at a time.** Adjust the acceleration *and* swap the USB cable before the
next run, and a pass or a fail tells you nothing.

**Say when a number is a guess.** Several long detours came from figures Claude invented —
`$130=400`, `$131=250` — being treated later as measured fact. If it hasn't been measured,
say so, and it gets recorded as unknown instead of quietly becoming true.

### Safety

**The PSU switch is the emergency stop.** Not Ctrl-C, not closing the terminal. If the
machine heads somewhere wrong or makes a bad noise, kill the 24 V first and ask afterwards.

**Claude has no memory between chats.** This file is the memory. If something important is
learned, it belongs in here or in `FINDINGS.md`, not only in the conversation.

---

## 1. The machine

| Part | Detail |
|---|---|
| Frame | IKEA LINNMON 100 × 60 cm, aluminium extrusion gantry |
| Motion | GT2 belt, 20-tooth pulleys; **dual-X gantry** (2 motors) + single Y |
| Motors | NEMA 17, harvested Ender-3 42-34, ~0.84 A/phase, **1.5 m leads** |
| Drivers | A4988 on CNC Shield V3, 1/16 microstepping. **Vref never measured.** |
| Controller | Arduino Uno + CNC Shield V3, USB-powered (the shield does *not* feed VIN) |
| Pen lift | **TowerPro MG996R** servo on D11, ~2.5 A stall, **1.5 m leads**, fed by an LM2596 buck |
| Pen carrier | A whole Ender gantry carriage, ~400 g, floating on a lost-motion lift |
| Usable area | ~150 × 150 mm comfortable |
| Limit switches | X and Y, both **NC**. No Z switch — D12 is jumpered to GND. |

**Dual-X:** the 2nd X driver sits in the **A slot**, cloned to X by `A.STEP→X.STEP` /
`A.DIR→X.DIR` jumpers. One axis, two motors, one limit switch — so **homing cannot square
the gantry**. Square it by hand with the power off.

**Orientation**, standing in front of the table: **+X = right, +Y = away from you**, home
corner **front-right** (`$H` drives +X and −Y). Machine coordinates after homing are
negative — that is GRBL convention and it is correct.

---

## 2. Firmware — patched, and you must not lose this

Running **gnea/grbl 1.1h with five edits**, source in `firmware/grbl-servo/`, flashable zip
at `firmware/grbl-servo-plotter.zip`. Every edit is tagged `[PLOTTER EDIT n]` in the source.

**Stock GRBL cannot drive a hobby servo.** Its spindle PWM on D11 runs at **980 Hz**; a
servo needs a 50–60 Hz frame. No sender or setting fixes that — it is a timer prescaler in
firmware. That single fact cost two sessions before it was found.

**Verify what is flashed:**

```
$I   ->   [VER:1.1h.plotter-servo-1:]
          [OPT:VH,15,128]
```

`plotter-servo-1` = the patched build. `V` = D11 is the PWM pin. `H` = `$HX`/`$HY` enabled.
If `$I` shows a date instead, the patch is gone and the servo will not work.

Full detail: [`FIRMWARE_SERVO.md`](FIRMWARE_SERVO.md).

---

## 3. Pin map — the part everyone gets wrong

Compiling with `VARIABLE_SPINDLE` (the default) **swaps the Z-limit and spindle pins**
relative to the shield's silkscreen:

| Shield says | Actually is |
|---|---|
| X+ / X− | X limit (D9) |
| Y+ / Y− | Y limit (D10) |
| **Z+ / Z−** | **servo signal — D11, the spindle PWM pin** |
| **SpnEn** | **Z limit input — D12, jumpered to GND** |

The D12→GND jumper is **required**. Without it `$5=1` inverts a floating pin and you get a
permanent phantom `Pn:Z`.

**The servo's `VOUT−`→shield-`GND` wire is mandatory. Never remove it.** It looks redundant
(the buck is non-isolated) but it is the servo's actual return path. Removing it made a
single PWM step of servo movement enough to reset the board.

---

## 4. Settings

Live values are in [`../settings/plotter.grbl.txt`](../settings/plotter.grbl.txt) — that
file matches what `$$` returns today, not a default.

Notable: `$3=1` (X inverted — **fix mirroring here, never by flipping G-code**),
`$5=1` (NC switches), `$22=1` (homing on, so GRBL boots into Alarm), `$21=0`
(hard limits off, permanently), `$32=0` (laser mode off, must stay off),
`$110/$111=500` and `$120/$121=50` (deliberately slow while the resets are unresolved).

**Write settings with the 24 V PSU OFF, on USB power alone.** Two rounds of EEPROM
corruption came from writing while motor power was live.

---

## 5. Workflow — three rules that matter

**1. Home in the same connection that streams.** Opening the serial port resets the
Arduino, so homing done in a previous command is already gone. `tools/plot2.py` homes by
default for exactly this reason.

**2. Set work zero with `G10 L2`, not `L20`.** `L2` takes absolute machine coordinates, so
it needs neither homing nor motor power:

```
python3 plot2.py --no-home --unlock --send 'G10 L2 P1 X-303 Y-107'
```

Current work zero is **machine X−303, Y−107**. It lives in EEPROM and survives resets.

**3. A zero work offset drives the machine into its end stops.** With G54 at zero,
`G0 X0 Y0` means *machine* zero — the homed corner — and the gantry stalls against the
frame. The resulting current surge resets the board, which looks electrical but is a crash.
`plot2.py` now refuses to stream when G54 is zero. **Read `WCO` in the status line before
believing any position-related theory.**

### Running a plot

```
python3 plot2.py drawing.gcode                    # homes, then streams
python3 plot2.py --no-home --unlock art.gcode     # relative art, no homing needed
python3 plot2.py --pen up                         # or down
python3 plot2.py --jog X10
python3 plot2.py --send '$$'                      # repeatable
python3 plot2.py --lockstep file.gcode            # one line per ok, no buffering
```

Port defaults to `/dev/cu.usbserial-A5069RR4`.

**Do not use the old `plot.py`.** It cannot combine a command with a file, and its 10-second
reply timeout misreads any long move as a crash — GRBL legitimately withholds `ok` while its
buffer is full.

---

## 6. G-code conventions

- mm (`G21`), `G94`, feeds at or below `$110`
- **No Z words at all** — soft limits check the unhomed Z and will abort the job
- **No `M2`/`M30`** — it drops the pen and resets feed rate to 0, so everything after
  throws `error:22`
- **No mid-file `M5`** — it disconnects the PWM pin and the servo goes slack
- **Soft-start the servo.** It is limp until the first `M3`, and jumping straight to an
  extreme is the largest current draw it ever makes. Wake it at S90 and walk it out.
- Pen values before the arm was shortened: **S120 up, S60 down**. Re-tune after any
  mechanical change with `tools/pentest.py` or `tools/servo_sweep.py`.
- Art files are `G91` relative so they need no work zero — **each one's header says which
  corner to start the pen from, and they do not all grow the same way.**

---

## 7. The open problem

**Symptom:** actuating the servo *after* the machine has moved resets the controller.
Servo alone is fine (all swings 6→60 units pass). Motion alone is fine (pen-free squares
draw perfectly). Together they fail.

**Ruled out by controlled test:** swing size, streaming protocol (`--lockstep` fails
identically), move length, settle dwells, the firmware pen path, limit switches, motors,
drivers, work offset, and Arduino power (it runs on USB; the shield never fed VIN).

**Prime suspect:** 1.5 m of thin wire between the buck and an MG996R. Voltage at the buck
is not voltage at the servo — that length has enough inductance to stop a 2.5 A step
arriving, while a meter at the buck still reads a comfortable 5.5 V.

**Fixes queued:**

1. **2200 µF, 16 V** electrolytic across the servo's power and ground **at the servo end**,
   striped leg to ground, legs trimmed short, anchored so it cannot flap.
2. **220–470 µF, 50 V** across the shield's 24 V terminals — A4988s require local bulk
   capacitance and the clone shield ships with very little.
3. **Twist the wire pairs** — servo red/brown, and each motor's A+/A− and B+/B−. Free, and
   it attacks the noise at source.
4. Shorten the servo arm — a 30 mm crank needs 1.2 kg·cm to lift 400 g; a 2.5 mm eccentric
   cam needs 0.10 kg·cm. **Twelve times less torque, so twelve times less current.** Worth
   trying before buying anything.

**Under consideration:** replacing the servo with a small NEMA 17 pancake driving a cam, or
moving to an ESP32 running FluidNC, which has a native `rc_servo` motor type and drives the
pen with ordinary Z moves. Full reasoning in [`FINDINGS.md`](FINDINGS.md) section 7.

---

## 8. The electronics boxes — designed, not built

A parametric model lives in `hardware/`, written in **build123d** (Python code-CAD on
OpenCASCADE; exports STEP, STL and DXF). It was chosen over Blender because this is
dimensioned engineering, not meshes, and over FreeCAD/Fusion because a script can be
diffed, checked and re-run. All of the work below is on the branch
`claude/3d-modeling-hardware-design-fkp2d1`.

```
python3 hardware/make.py           # build every part -> hardware/out/
python3 hardware/bom.py            # full bill of materials (--csv for a spreadsheet)
python3 hardware/viewer.py         # interactive 3D pages
python3 hardware/psu_layout.py     # power box: rail schedule, floor plan, every wire
python3 hardware/ctrl_layout.py    # control box: the same
python3 hardware/din_parts.py      # what to order for the rails, and why
python3 hardware/din_bom.py        # the same as a supplier quote sheet
```

### What is modelled

The machine: a 1000 × 600 outer frame of 2040, a 700 mm 2020 cross bar riding OpenBuilds
plates along the 1000 mm side, a 1000 × 600 × 1.5 mm steel deck bolted under the frame,
and a 1524 × 600 bench with the machine hard left.

The electronics: **two UN4412 cases**, split so the box you open to change a driver has
nothing above 24 V in it.

- **Power box.** Panel-mount fused + switched IEC inlet → `MCB1` (6 A, C-curve, 1P+N) →
  L/N/PE terminals → the LRS-350-24 and the RS-25-24. The LRS's 24 V goes through `F1`
  (a 5 A fuse terminal) to the `+24` rail. `K1`, a 24 V relay in series with a
  normally-closed E-stop loop, switches **only** `+24s`. The RS-25 feeds an LM2596 set
  to 6.0 V for the servo. Out: one GX16-6 carrying `+24a`, `+24s`, `+6`, `0V`.
- **Control box.** Link in on the right wall beside the rail. Three TB6600s in a row,
  their single terminal face forward into one duct. The Elecrow board at the back-left
  with USB-C beside it. **The whole front wall goes to the machine** — three motor
  connectors, the servo, two endstops, in that order.

Both boxes are routed conductor by conductor: **30 wires in the power box, 49 in the
control box**, each from the terminal it actually lands on, through a duct, to the
terminal at the other end.

### DIN rail totals

187 mm of rail for the power box, 125 mm for the control box — **one 1 m length covers
both**. 35 feed-through terminals (2.5 mm², 5.2 mm pitch), 4 PE terminals, 1 fuse
terminal, 3 × 10-way jumper combs cut to length, 1 MCB, 1 relay and socket. Full ratings
in `din_bom.py`.

**Terminal blocks are commoned by an insertable comb, not by wiring one to the next.**
That is what the ten combs are for, and it is why there are 79 wires instead of 93.
Earth blocks are the exception: they clamp the rail, so the rail is the common.

### The layout engine

`hardware/panel.py` is shared by both boxes; `psu_layout.py` and `ctrl_layout.py` are
tables and prose. It builds the duct adjacency graph from where duct rectangles actually
overlap, routes each conductor through the shortest path, and gives it its own lane so a
wire can be followed end to end. **It refuses to write a layout** that runs a wire
through a part, overlaps the rail with a part, lands three conductors on a two-screw
block, crosses on open floor, or fills a duct past 50%. Every one of those checks exists
because it caught something.

### The pages

All private unless noted — use the Share menu before sending one to anybody.

| | |
|---|---|
| Machine, 3D | https://claude.ai/artifact/2AN2q4qFQ4fbEECBUUztsq — link-shared |
| Electronics cases, 3D | https://claude.ai/artifact/QBGDB6BF3KFNdK2vdznUtU |
| Power box wiring | https://claude.ai/artifact/BGLa9GLqQQn4MzRDbeGE45 |
| Control box wiring | https://claude.ai/artifact/FMTWRsi1MVCqrYTcgt6NCq |
| DIN parts, explained | https://claude.ai/artifact/Ua6RjD4LC6M6x7vyRNg7eF |
| DIN BOM for a supplier | https://claude.ai/artifact/BYFjNCtQzwpjw3YpGsvE38 |

### What is not verified, in the order it will bite

1. **The Elecrow board's 5 V regulator.** If it is a linear 7805, 24 V in at ~150 mA
   burns 2.9 W in a TO-220 with no heatsink. Read the silkscreen beside the VIN terminal
   before first power-up. `FINDINGS.md` section 10 has the fix if it is linear.
2. **The Elecrow board's header positions are guessed.** Their site is unreachable from
   the build container. Measure yours and edit `BRD` in `ctrl_layout.py`; the drawing,
   the lengths and the cut list all follow from it.
3. **The TB6600 block order.** All twelve terminals are on one long face — that part is
   confirmed and the layout depends on it. The order *within* each block is drawn as the
   common one, but clones reorder it. Check the silkscreen.
4. **The two boxes do not fit on the table as the model places them.** `case.origin_x()`
   puts the power box at x 1005–1460 while the free zone ends at 1024, so it hangs off
   the end. Side by side needs 910 mm of a 524 mm gap; front-to-back needs 680 mm of a
   600 mm depth. **They have to stack**, and nothing in the model says so yet.
5. **Internal placement is real for the two boxes, provisional for nothing else.** Both
   wiring layouts are laid out deliberately; `case.py`'s `pack()` still shelf-packs and
   says so in its own docstring.
6. Smaller ones: `CASE_EXT` is estimated from the UN4020's deltas; `GANTRY_RISE` is an
   eyeballed 15 mm; `case.py` still models a 60 mm fan where the one in hand is 40 mm;
   the frame and cross bar are modelled as T-slot and the real extrusion may be V-slot;
   the deck needs to be 430 ferritic if magnets are ever wanted.
7. `hardware/wiring.py` is **parked** — it targets the single-case layout that no longer
   exists. Its docstring says what was worth keeping from it.

---

## 9. Repo layout

```
firmware/     patched GRBL 1.1h source + flashable zip
docs/         SETUP.md (8-phase build), FIRMWARE_SERVO.md, FINDINGS.md, this file
hardware/     build123d model of the machine and the two electronics boxes.
              panel.py is the layout engine; psu_layout.py and ctrl_layout.py
              are its two sets of tables. See section 8.
settings/     plotter.grbl.txt — live values, restore after any re-flash
tools/        plot2.py (sender), pentest.py (servo swing sweep), servo_sweep.py
gcode/tests/  T0-T13, in bring-up order
gcode/art/    single-stroke pieces: Hilbert, rosette, ripples, Gosper, dragon,
              Sierpinski, one-line labyrinth
```

**Read [`FINDINGS.md`](FINDINGS.md) before re-debugging anything.** Most of the time lost
on this build went to treating each new symptom as a new fault, when the resets, the
garbled serial (`error:1`, `error:2`, `error:254`, a bogus `ALARM:8`) and the EEPROM
corruption were all downstream of two things: a machine driven into its end stops, and a
missing ground wire.

---

## 10. Gotchas, kept

- `$22=1` makes GRBL **boot into Alarm** and refuse everything, jogging included, until
  `$H` or `$X`.
- Homing moves each axis **twice** — fast seek, pull off, slow locate, pull off. Correct.
- Re-flashing **wipes EEPROM** — settings *and* work zero.
- `$RST=*` restores clean defaults, faster than overwriting a corrupted set.
- `ok` from GRBL means **accepted into the buffer**, not executed. Motion can be in flight
  for seconds afterwards.
- The servo **twitches on every Arduino reset**, and opening the serial port *is* a reset.
- UGS proved unreliable here: desyncs, silent mid-job cancels, and iCloud placeholder files
  streamed as truncated jobs then reported as "done".
