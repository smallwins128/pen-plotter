# Control box — one inlet, one rail, nineteen wires

An enclosure holding the PSU, the Uno and the shield, presenting every machine wire on a
keyed panel connector. Written to be built in the order given; each phase ends in a check.

**Status: design only. Nothing here has been built or measured.** Every number is either
from a datasheet (marked) or arithmetic from the loads in [SETUP.md](SETUP.md). Treat the
mechanical dimensions as a starting point, not as measured fact.

> **Do this after the servo reset is fixed, not before.** The open fault in
> [HANDOFF.md §7](HANDOFF.md) is unresolved. Build an enclosure around it and you will be
> debugging it through a lid. Cap at the servo, twist the pairs, shorten the arm, confirm
> clean — then build the box.

---

## 1. Why three supplies collapse into one

The sketch was one mains inlet feeding three PSUs: shield, Arduino, servo. It needs one.

| Load | Thought it needed | Actually needs |
|---|---|---|
| CNC shield / steppers | 24 V | 24 V |
| Arduino | its own 5 V | nothing — it runs on USB, and the USB **data** link to the Mac has to be there regardless. A second 5 V source only fights the on-board regulator. |
| Endstops | a supply | nothing — they are bare switches to GND. GRBL's internal pull-ups drive them (`limits.c`). |
| Servo | its own 6 V | a DC-DC from the 24 V. No one makes a 6 V mains PSU, so this was always going to be a converter. |

So: **one 24 V brick, one fused distribution block, one 0 V star point.** Common grounds
stop being something you wire correctly and become something the topology guarantees.

### Load budget

```
3 × NEMA 17 @ 0.84 A/phase, 24 V chopper      ~1.2 A worst case
pen branch (UBEC 6 V × 2.5 A stall ÷ 24 V ÷ η) ~0.7 A
60 mm fan                                      ~0.1 A
                                              --------
                                              ~2.0 A
```

### Which supply

Two work. `tools/enclosure_dxf.py --psu {lrs100,lrs350}` re-lays the whole box for either.

| Supply | Rating | Case | Box interior | Trade |
|---|---|---|---|---|
| **LRS-100-24** (buy) | 24 V 4.5 A | 129 × 97 × 30 | 265 × 200 × 75 | 2.2× margin. **You know which part you have.** ~£18 |
| LRS-350-24 (reuse) | 24 V 14.6 A | 215 × 115 × 30 | 350 × 220 × 75 | Free, 7× oversized, box 85 mm longer |

**LRS-100-24 is the default.** Mean Well case 238A. Note carefully *why* it is the safer
number: not because its datasheet is better than the LRS-350's — both are equally good — but
because buying a specific part new removes the open question, which is *which unit is
actually in your printer*. The stock Ender-3 Pro / V2 supply is a genuine LRS-350-24, but
the 2018 Ender-3 shipped more than one part. If you reuse it, read the label first.

Rejected: **LRS-50-24** (24 V 2.2 A, 99 × 82 × 30) — 2.2 A against a 2.0 A load is no margin
at all. **LRS-75-24** (24 V 3.2 A, 99 × 97 × 30) — enough current, but only 30 mm shorter
than the LRS-100 and the box it produces crowds the port row for nothing.

---

## 2. Power topology

```
  230 V ─► IEC C14 inlet ─► LRS-100-24 ─► +24 V BLOCK ─┬─ F1 3 A ──► shield V+
           fused T2 A                                  ├─ F2 1.5 A ► PEN pin 1
           switched                                    └─ F3 0.5 A ► fan
              │                                             (returns)
              │ PE                                              │
              ▼                                                 ▼
        ┌───────────┐        ✗ no bond         ╔═══════════════════════════╗
        │ PE block  │· · · · · · · · · · · · · ║  0 V — STAR POINT (block) ║
        │ + chassis │                          ╚═══════════════════════════╝
        └───────────┘                             ▲      ▲       ▲      ▲
                                             PSU −V  shield  PEN pin 2  fan −
                                                     GND
```

**The dashed link is the one you must not make.** The Mac's USB cable already ties 0 V to
the building earth through the laptop. Bonding 0 V to PE inside the box adds a second path
and puts a ground loop around the serial line — on a machine whose entire failure history
is grounding, that is not a risk worth taking. The PSUs are isolated; leave DC floating.

### Fusing

| | Rating | Protects |
|---|---|---|
| Inlet | T2 A slow-blow | ~0.3 A at 230 V for the real load; slow-blow rides the PSU inrush |
| F1 | 3 A | stepper branch (~1.2 A) |
| F2 | 1.5 A | pen branch (~0.7 A), sized above the converter's inrush |
| F3 | 0.5 A | fan |

---

## 3. Panel — where the 19 wires land

12 stepper + 4 endstop + 3 pen = 19 conductors, on six ports.

```
   left end          ┌─────────── 265 mm front face ───────────┐      right end
   ┌──────┐          │                                          │      ┌──────────┐
   │ IEC  │          │   (X)      (A)      (Y)    (LIM)  (PEN)  │      │  (FAN)   │
   │ C14  │          │  GX16-4   GX16-4   GX16-4  GX12-4 GX12-3 │      │   [USB]  │
   └──────┘          │   16mm     16mm     16mm    12mm   12mm  │      └──────────┘
                     └──────────────────────────────────────────┘
   u  =                 45        90       135     185    225           60 / 140
   all round ports on one centreline, v = 37.5 mm above the floor
```

**Steppers get GX16 (16 mm hole), endstops and pen get GX12 (12 mm).** Different shell
diameters, so a stepper lead physically cannot be pushed into the pen port. That matters
more than a label, because **PEN pin 1 is 24 V** and a servo plugged into it dies instantly.

Mains enters the **left end panel** and never crosses the front face. The fan and the USB
share the opposite end.

### Pin schedule

**X / A / Y — GX16-4, three off**

| Pin | Signal |
|---|---|
| 1 | A+ |
| 2 | A− |
| 3 | B+ |
| 4 | B− |

Wire to the driver's motor header in the socket's own order. **Identify coil pairs with a
meter** — continuity means same coil. Ender colour codes vary between batches; do not
trust them.

**LIM — GX12-4**

| Pin | Signal | To |
|---|---|---|
| 1 | X SIG | X endstop header signal (D9) |
| 2 | X RTN | a shield GND **pin** |
| 3 | Y SIG | Y endstop header signal (D10) |
| 4 | Y RTN | a shield GND **pin** |

NC switches, polarity irrelevant (SETUP §3.1). Two-pair screened cable; drain to shield
GND at the **box end only** — grounded at both ends it is a loop antenna.

**PEN — GX12-3**

| Pin | Signal | To |
|---|---|---|
| 1 | +24 V | F2 |
| 2 | 0 V | star block |
| 3 | SIG | D11 — the header silkscreened `Z+/Z−` (SETUP §2) |

---

## 4. Interior arrangement

Plan view, lid off, front face at the bottom:

```
 ┌──────┬───────────────────────────┬──────────────────────────────┐
 │VENTS │                           │   DIN mini-rail (~90 mm)     │
 │      │                           │  ┌──┬──┬──┬───┬────┐         │
 │ IEC  │      LRS-350-24           │  │PE│F1│F2│+24│0V ★│         │
 │ C14  │   (base-mounted brick)    │  └──┴──┴──┴───┴────┘         │
 │      │                           │                              │
 ├──────┴─ mains barrier ───────────┤                              │
 │                                  │                         ┌────┤
 │              ┌──────────────────┐│      ◄── airflow ───────│FAN │
 │              │  UNO + SHIELD    ││                         └────┤
 │              │  drivers up,     ││                              │
 │              │  heatsinks on    ││                              │
 │              └──────────────────┘│                              │
 └───(X)───(A)───(Y)────(LIM)─(PEN)─[USB]───────────────────────────┘
```

**Why the PSU sits along the back:** it frees the whole front face for connectors. Put the
supply along the left end instead and six ports have to crowd into what is left — under
30 mm centres, closer than a GX16 backshell lets you tighten.

Enclosure: **265 × 200 × 75 mm internal** with the LRS-100-24 — 219 mm used of 265 along
the back (25 mains + 129 PSU + 15 gap + 90 rail), 150 of 200 across. The larger LRS-350 box
is 350 × 220 with the identical arrangement.

**On the small box the USB moves to the right end wall**, beside the fan. Six connector
flanges will not fit a 265 mm front face: the tool's fit check puts the USB cutout 2 mm
*into* the corner tab. It is the better place for it anyway — the Uno is right there, so
the internal lead is 60 mm instead of 200.

---

## 5. Grounding — what lands where

| Node | Lands on | Why |
|---|---|---|
| PSU −V | 0 V star block | source of the node |
| Shield GND | 0 V star block | one 0.75 mm² wire; stepper return flows here |
| PEN pin 2 | 0 V star block | servo supply return **and** signal reference |
| Fan − | 0 V star block | — |
| LIM pins 2, 4 | shield GND **pins** | *not* the star block — keeps the switch reference off the stepper return path |
| Cable screen | shield GND, box end only | both ends = loop antenna |
| D12 | any shield GND pin | the mandatory jumper (SETUP §3.2) |
| PE / chassis | earth block only | never bonded to 0 V |

Land every return **on the block**. No daisy chains between loads.

---

## 6. The one non-obvious move: regulate at the servo

HANDOFF §7's prime suspect is 1.5 m of thin wire between the buck and an MG996R.
Centralising power in a box makes that run *longer*. So don't send 6 V up the umbilical —
send 24 V, and put the step-down on the carriage.

```
NOW:   [LM2596 in box, 6 V] ══ 1.5 m thin pair, 2.5 A step ══► [MG996R]   resets the Uno

NEW:   [PEN port, 24 V]  ── 1.5 m, ~0.7 A steady ──► [UBEC 6.0 V] ─80 mm─► [MG996R]
                                                     + 2200 µF        on the carriage
```

The 2.5 A transient shrinks from a 1.5 m loop to an 80 mm one, and the umbilical carries a
smooth ~0.7 A that the UBEC's input capacitance has already softened. Voltage at the
regulator is now voltage at the servo, which is the thing that was not true before.

Two more things this buys:

- **Pin 2 doubles as the servo's signal return**, so the `VOUT−` → shield GND wire that
  [FINDINGS §2](FINDINGS.md) says must never be removed becomes structurally impossible to
  omit — it is a conductor in the umbilical, not an extra wire someone can tidy away.
- The LM2596 goes. It is a ~2 A part being asked for 2.5 A. A 6 V-selectable UBEC rated
  ≥ 5 A is built for exactly this current profile.

### 5 V or 6 V?

Either. The MG996R's range is 4.8-7.2 V, and **a 5 V rail is arguably the better choice
here**: stall current scales with supply voltage over winding resistance, so the ~2.5 A
quoted at 6 V becomes roughly **2.1 A at 5 V**. That is a smaller transient in the exact
wire that has been resetting the board. The cost is torque - about 9.4 kg-cm instead of
11 - against a requirement of 1.2 kg-cm for a 30 mm crank, or 0.10 kg-cm for the 2.5 mm
cam in HANDOFF section 7. There is an order of magnitude in hand either way.

So a fixed 5 V 3 A module is fine, and 3 A against a 2.1 A stall is adequate headroom. Two
conditions:

- **The 2200 uF still goes at the servo.** A potted module's internal output capacitance is
  small, and it is the bulk cap, not the converter, that supplies the lift transient. This
  is not optional with any regulator.
- **Do not let the servo stall in normal use.** SETUP section 4.4 already requires this -
  the pen floats on its spring and the servo only lifts it. Some potted modules fold back
  on over-current and stay folded back, which reads as a limp servo rather than an error.

Still three wires. If you later want the last few dB, run a 4-core and give the PWM its own
return to a shield GND pin. At 0.7 A the shared-return offset is tens of millivolts against
a 5 V logic threshold — it was the 2.5 A version of that same wire that was killing you.

---

## 7. Build order

Each step ends in a check. Do not start the next until it passes.

**7.1 — Drill and dry-fit, no wire.** 16 mm × 3, 12 mm × 2, USB cutout, IEC rectangle,
60 mm fan + four M4 on 50 mm centres. Drop all six connectors in loose.
→ *Check:* every backshell tightens without fouling its neighbour, and the lid closes over
the driver heatsinks.

**7.2 — Mains, complete and covered, before any DC.** 0.75 mm², ferrules on every
conductor. Inlet L/N to the PSU input; inlet earth to the PE block; PE block to the PSU
earth terminal and to the box metalwork. Shroud the inlet and PSU input terminals
(SETUP §0).
→ *Check:* plug in, switch on, meter 24 V at the PSU output, switch off. Nothing else
connected.

**7.3 — DC distribution and the star point.** +V to the +24 block, −V to the 0 V block,
F1/F2 in their branches.
→ *Check:* continuity from each 0 V landing to the block. **No** continuity from 0 V to PE.

**7.4 — Board in, bulk cap at its terminals.** Shield V+ and GND on 0.75 mm², with the
220–470 µF 50 V electrolytic right at the screw terminals (HANDOFF §7 fix 2). Short
USB-B lead to the panel socket. Re-fit the D12 jumper.
→ *Check:* USB only, 24 V off — `$I` returns `[VER:1.1h.plotter-servo-1:]`.

**7.5 — Endstops.**
→ *Check:* `?` with nothing pressed shows no `Pn:` field at all. Press each switch by hand:
`Pn:X`, then `Pn:Y`, each clearing on release. **Before homing** (SETUP §6.0).

**7.6 — Pen port and the carriage pod.** Build the pod first: UBEC, 2200 µF 16 V with its
striped leg to 0 V, legs trimmed short, anchored so it cannot flap. Set the UBEC to 6.0 V
**with the servo disconnected**, meter on the output (SETUP §3.3).
→ *Check:* T0 — five clean up/down cycles, no buzzing at either end, no reset.

**7.7 — Motors last.** Switch off at the panel for every plug and unplug. A panel connector
makes hot-plugging easy; hot-plugging a stepper is still the fastest way to kill an A4988
(SETUP §0).
→ *Check:* both X motors turn together on T1. If they fight, swap one coil pair on **one**
motor — not `$3`, which flips the whole axis.

**7.8 — Fan, lid, back to the ladder.**
→ *Check:* T1–T6 pass as before, drivers warm rather than hot after a long plot.

---

## 8. Power sequencing is preserved for free

The panel switch cuts **24 V only**; USB arrives separately from the Mac. So the documented
order survives without a second switch:

- **Up:** plug USB (GRBL boots, drives the enable line and D11 to a known state), then flip
  the panel switch.
- **Down:** panel switch off, then unplug USB.

That rocker is also the emergency stop — the one that still works when the terminal has
stopped listening (HANDOFF, Safety).

---

## 9. Parts

| Qty | Part | Note |
|---|---|---|
| 1 | Folded steel enclosure, 350 × 220 × 75 mm internal | section 10; `tools/enclosure_dxf.py` cuts the flat patterns |
| 1 | IEC C14 inlet, fused + switched | T2 A slow-blow; UK lead plugs straight in |
| — | Mean Well LRS-350-24 | you already have it — the Ender's own supply. MEASURE the label |
| 3 | GX16-4 panel socket + plug | ~5 A/pin, far above the 0.84 A the motors draw |
| 1 | GX12-4 panel socket + plug | endstops |
| 1 | GX12-3 panel socket + plug | pen — different shell size on purpose |
| 1 | Panel USB-B ↔ USB-B pass-through | so the lid never comes off to re-flash |
| 1 | 5 V or 6 V DC-DC, ≥ 3 A | lives on the carriage, replaces the LM2596. A fixed 5 V 3 A module is fine - see section 6 |
| 1 | 2200 µF 16 V electrolytic | at the servo |
| 1 | 220–470 µF 50 V electrolytic | at the shield's 24 V terminals |
| 1 | 60 mm 24 V fan + finger guard | blowing in over the drivers |
| ~200 mm | DIN rail, PE block, 2 × 5×20 fuse carrier, 2 × distribution block | F1 3 A, F2 1.5 A |
| — | 0.75 mm² wire + ferrules, 3-core 0.5 mm² umbilical, 2-pair screened | the 0.5 mm² umbilical is what replaces the thin servo wire |

---


## 10. Fabrication

Laser-cut and folded: **one blank for the floor and all four walls, plus a separate lid.**
`tools/enclosure_dxf.py` generates both flat patterns, the adapter plates and an SVG
preview. Every dimension it uses is at the top of the file.

```
python3 tools/enclosure_dxf.py --report      # just the numbers
python3 tools/enclosure_dxf.py               # writes enclosure/*.dxf and *.svg
```

It self-checks after every run:

- **Holes** — no two leaving less than 1.5 mm of web, nothing within 3 mm of a bend line.
  Corner reliefs are exempt; straddling the bend is their job.
- **Connectors** — flange to flange, and flange to corner tab. This is the check that
  decides whether a row of ports actually fits, and the hole-to-hole check cannot see it: a
  cutout can clear its neighbour by millimetres and still be unfittable because the
  backshell will not pass the tab. Flange diameters are marked MEASURE like everything else.

Change a dimension, re-run, read the check.

### What is known, and what you must measure

| | Figure | Where it comes from |
|---|---|---|
| **Mean Well LRS-100-24** | 129 × 97 × 30 mm | Datasheet, case 238A. Safe because you buy it new and therefore know which part you have |
| **Mean Well LRS-350-24** | 215 × 115 × 30 mm | Same datasheet confidence. **MEASURE** — read the label; the open question is which unit is in your printer, not whether the datasheet is right |
| **Arduino Uno R3 outline** | 68.6 × 53.4 mm | Published, reliable |
| **Uno mounting holes** | (13.97, 2.54) (15.24, 50.80) (66.04, 35.56) (66.04, 7.62), Ø3.2 | Published, but **the four holes are not on any grid and none of the spacings is round.** Trace them off your board |
| Uno + shield stack height | ~50 mm | **MEASURE** — depends on your standoffs, drivers and heatsinks |
| GX16 panel hole | Ø16 mm | The number in the name |
| GX12 panel hole | Ø12 mm | Same |
| TS35 DIN rail | 35 mm wide, 25 mm slot pitch | Standard |
| 60 mm fan | Ø57 air hole, 4 × M4 on 50 × 50 | Standard |
| **IEC fused/switched inlet** | ~47 × 27 mm cutout | **MEASURE** — snap-in power entry modules vary between vendors |
| **USB-B panel coupler** | 27.5 × 15.5 + 2 × M3 at 30 | **MEASURE** — also sold as a D-hole part |

Everything marked MEASURE is a number that would cost you a sheet of steel if it were
wrong. None of them gates the cut, because of the next section.

### The perforated base does the work

The base is a **field of Ø3.5 holes on a 25 mm square grid**, 104 of them, and nothing
else. No component-specific mounting holes at all.

25 mm is the slot pitch of TS35 DIN rail, so the rail bolts down anywhere. The PSU, the
board and anything bought later mount through whichever holes land — and where a hole
pattern does not land on the grid, which for the Uno it never will, it gets a small flat
**adapter plate**: the awkward pattern on one side, four grid holes on the other, cut from
the offcut. `adapters.dxf` has one for the Uno and one blank.

This is the whole reason the unknowns above are survivable. **Being wrong about a
component costs you an adapter plate, not a box.**

### Material and construction

| | |
|---|---|
| Sheet | **1.5 mm CR steel**, powder coated. Or 2 mm 5052 aluminium |
| Inner bend radius | 1.5 mm (1 × t) |
| Corners | Full-height tabs on the end walls, lapping inside the front and rear walls, 2 × M3 each |
| Corner relief | Ø3 mm at each point where two bend lines meet — without it the corner tears |
| Lid | Shallow pan, 15 mm skirt, telescopes **over** the base with 0.4 mm clearance per side. Open butt corners — a tab there would foul the base wall |
| Lid fixing | 6 × M3 into **self-clinching nuts** (PEM S-M3) pressed into the base walls. 1.5 mm sheet is too thin to tap |
| Earth | One dedicated M6 stud in the base, in the mains corner, **shared with no other fastener** |

### Flat pattern

| | `--psu lrs100` | `--psu lrs350` |
|---|---|---|
| Folded interior | 265 × 200 × 75 | 350 × 220 × 75 |
| Folded exterior | 268.0 × 203.0 × 76.5 | 353.0 × 223.0 × 76.5 |
| Base blank | 415.69 × 350.69 | 500.69 × 370.69 |
| Lid blank | 299.49 × 234.49 | 384.49 × 254.49 |
| Base grid | 70 holes | 104 holes |
| Rear vents | 92 holes | 128 holes |
| Bend deduction | 2.654 mm per 90° bend | same |

That deduction comes from R = 1.5, t = 1.5, K = 0.42:

```
BA = (π/180) × 90 × (R + K·t)   = 3.346 mm     arc at the neutral axis
BD = 2 × (R + t) − BA           = 2.654 mm
```

**The shop's bend deduction wins.** K depends on their tooling, and every hole in a wall
shifts in the flat if their number differs from ours. Hand them the *folded* dimensions and
let them do their own unfold; use these DXFs for the cutouts and hole positions, or as a
cross-check. If they want the flat as-is, tell them the deduction it assumes.

### Layers in the DXF

| Layer | |
|---|---|
| `CUT` | everything the laser cuts, corner reliefs included |
| `BEND` | fold lines. Not cut — reference for the brake |
| `ETCH` | port labels, if you want them marked |

### Ventilation

Fan blows **in** through the right end wall, air leaves through a Ø5 perf field in the rear
wall over the PSU — 128 holes, 2513 mm², against the fan's 2827 mm² of swept area. Ø5 keeps
a finger out. Nothing vents through the left end wall, which is where mains lives.

---

## 11. What this box does not do

**It does not fix the servo reset.** See the note at the top. The fixes queued in
HANDOFF §7 are mechanical and electrical at the servo end; none of them is an enclosure.

**It does not square the gantry, add a second X switch, or remove the Uno's ceiling.** If
you end up going ESP32/FluidNC (FINDINGS §7), the box, the panel connectors and the
umbilical all carry over unchanged — only the board on the standoffs changes. Nothing here
is wasted by that move.
