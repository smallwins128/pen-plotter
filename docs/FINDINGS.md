# Bring-up findings

What was actually learned commissioning this machine, and what it cost to learn.
Written so none of it has to be rediscovered.

---

## 1. Stock GRBL cannot drive a hobby servo — confirmed and fixed

Default spindle PWM on D11 is **980 Hz** (Timer2, 1/64 prescaler). A servo needs a
50–60 Hz frame. The firmware in `firmware/` fixes this; `$I` reporting
`plotter-servo-1` is the proof it's flashed.

**Resolved.** The servo responds to `M3 S<n>` and holds position.

## 2. The servo's ground wire is not optional — this cost hours

The jumper from the buck's `VOUT−` to a shield `GND` pin looks redundant: the buck is
non-isolated, so its ground is already common with the shield's through the PSU. It is
not redundant, and removing it made the machine dramatically worse — a **6-unit** pen
twitch (one PWM step, with the steppers disabled) was enough to reset the board.

A signal is a voltage measured *between* two points. Without that wire, the servo's
ground reference reached the Arduino only via a long path through the PSU, and every
current pulse developed a voltage along it. The servo's ground and the Arduino's ground
stopped being the same node.

**Never remove it.** With it fitted, the servo cleared every swing from 6 to 60 units.

## 3. Every plot must home in the same connection that streams it

Opening the serial port resets the Arduino (DTR). Machine position is lost, so homing
performed in a *previous* command is already gone by the time the next one connects.
`plot2.py` homes by default for this reason.

## 4. A zero work offset drives the machine into its end stops

With `G54` at zero, `G0 X0 Y0` in a drawing file means **machine** zero — the homed
corner. X is parked 3 mm off its limit switch, so `X0` commands it *into* the switch and
then the frame. The resulting stall produces a current surge that resets the board, which
reads as an electrical fault but is a crash.

This masqueraded as a brownout for a long time. `plot2.py` now refuses to stream when the
G54 offset is zero.

**Set work zero without motion or motor power:**

```
G10 L2 P1 X-303 Y-107      # absolute machine coordinates, no homing needed
```

`G10 **L2**` takes coordinates. `G10 **L20**` uses the current position and therefore
needs a homed machine and a live PSU. Prefer L2.

## 5. Never write EEPROM with the PSU on

Settings and the work offset both live in EEPROM. A reset landing mid-write corrupts it
and GRBL falls back to defaults — which happened twice, each time silently undoing `$5`,
`$22` and `$23` and making the next symptom look like a new fault.

**Do all `$` settings and `G10` offsets on USB power with the 24 V supply switched off.**
Plotting can survive a reset; writing EEPROM cannot.

`$RST=*` restores clean defaults, faster than overwriting a corrupted set.

## 6. The servo's first energisation is its largest current draw

Until the first `M3`, the PWM pin is disconnected and the servo is limp — no holding
torque. Asking it to jump straight to an extreme (`M3 S140`) from that state is the
biggest current step it ever makes.

**Soft-start it.** Wake it at pen down and walk it out in stages:

```gcode
M3 S90
G4 P0.50
M3 S107
G4 P0.30
M3 S123
G4 P0.30
M3 S140
G4 P0.30
```

This measurably improved how far jobs got. It belongs in every generated file.

Note the trap it exposed in `tools/pentest.py`: that tool starts near centre and grows
its swings, so every jump it measures is from an *already energised* servo. It never
exercises the first-energisation case, and will happily report "no resets at any swing"
on a machine that dies on the first `M3` of a real file.

## 6a. The servo is an MG996R, not a 9 g servo — size everything for that

Confirmed from a photo of the carriage. This changes the numbers by an order of magnitude:

| | SG90 / MG90S | **MG996R** |
|---|---|---|
| Running current | ~150-250 mA | **~700 mA - 1 A** |
| Stall current | ~700 mA | **~2.5 A** |
| Voltage range | 4.8-6 V | **4.8-7.2 V** |

An LM2596 delivering a 2.5 A step down 1.5 m of 26 AWG servo lead explains every
symptom below. Size for it:

- **2200 uF, 16 V** at the servo, not 470 uF.
- **Buck at 6.0 V**, not 5.0-5.5 V. The MG996R is rated to 7.2 V and makes more torque
  at 6; running it at 5.2 V was starving it.
- **20 AWG or thicker** for the red and brown pair. Signal can stay thin.

## 7. Open: the servo supply has no margin

**Status: unresolved.** With everything above correct, jobs still reset when the servo
actuates *after* a move. Ruled out by controlled test:

| Ruled out | How |
|---|---|
| Swing size | 6-unit swing fails as readily as 60 |
| Streaming protocol | `--lockstep` (one line per `ok`) fails identically |
| Move length | 20 mm relative square fails like a 300 mm traverse |
| Settle timing | 1 s dwells before every pen command changed nothing |
| Firmware pen path | `SPINDLE_PWM_*` is used in one function; `G4` uses a CPU busy-loop, not Timer2 |
| Servo mechanical load | Pen in or out of the holder made no difference |
| Limit switches, motors, drivers | T7 (pen-free square) completes cleanly, every time |
| Arduino power | Runs on USB; shield never fed `VIN` (power LED off with PSU on, USB out) |

What remains is the LM2596 buck's transient response. It holds 5.2–5.5 V at rest and
cannot supply a current step. Next steps, in order:

1. **Separate 5 V supply** for the servo — USB charger, power bank, or 4×AA — grounded to
   the shield. Decisive test of whether the buck is the weak link.
2. **470–1000 µF, 16 V electrolytic** across the servo's power and ground **at the servo**,
   striped leg to ground. The permanent fix.
3. **220–470 µF, 50 V** across the shield's 24 V terminals. A4988s require local bulk
   capacitance; the clone shield ships with very little.

## 7a. A motion-only reset at 180 mm — the servo was not involved

Running an 18 cm piece (`field_18cm_proof.gcode`, servo disconnected, pen taped) the board
reset mid-stream. The sender reported `GRBL RESET mid-stream at line 284 (brownout)`.

Section 7 says motion alone is fine — but that was established with **T7, a 50 mm square**,
and nothing had ever run for minutes at a stretch.

Two more followed: line 1116, then line 3014. Their positions relative to the row-end
turnarounds are 52, 20 and 70 moves — with rows 181–226 moves long, a random point averages
~45 moves from a turn, so that is scatter, not clustering. **An earlier draft of this
section called the reversal the trigger on the strength of the first two points. Three
points do not support it.**

What the three do show is **duration**: at F500 with 0.8 mm moves the machine runs about
10 moves a second, so the runs lasted roughly **27 s, 107 s and 290 s**. Random position,
increasing survival — the signature of an intermittent fault, not of any particular move.

**The detail that reframes it:** the Arduino is **USB-powered** and the shield never feeds
`VIN` (section 1 of HANDOFF, verified — the power LED is off with the PSU on and USB out).
A sag on the 24 V motor rail therefore cannot brown out the Arduino directly. For motor
current to reset it, the disturbance has to arrive through ground or as radiated noise.
Which leaves a candidate never yet tested: **the USB connection itself** — a marginal cable,
port or hub causing the Mac to re-enumerate, which resets the board exactly as opening the
serial port does.

**The decisive test costs nothing and moves nothing:**

> Switch the **24 V PSU off** and stream a full art file on USB power alone. GRBL executes
> the entire motion profile in software with identical timing; the steppers have no current
> so nothing moves. If it still resets, the motors are not involved at all and the fault is
> in the USB/serial path. If it runs to completion, motor current is implicated and the
> hunt moves to grounding and bulk capacitance.

Run it before buying any capacitors. `T16_reversal_sharp.gcode` and `T17_reversal_rounded.gcode`
remain useful for separating cusped from looped turns, but only once the PSU-off test has
said whether motion matters at all.

## 7b. A static hold at S180 resets the board — no motion involved

_Observed 2026-09-04, on the machine, during a `servo_sweep.py` session._

**Geometry at the time of this observation:** `S90` = pen **down**, arm pointing straight
down. `S180` = pen **up**, arm pointing right — a 90° swing, where the old values
(`S120`/`S60`) were 60 units apart.

**The horn was re-aligned on its spline later the same day**, and the working pair is now
`S90` down / `S140` up. The reset below was seen on the *earlier* alignment, so the exact
number `S180` is specific to that setup. What carries over is the mechanism, not the value:
driving the horn into its mechanical stop stalls the servo, and a stalled MG996R will reset
this board whether or not the gantry is moving.

**S180 held the board for a few seconds and then reset it.** The gantry was stationary and
no motion command had been sent in that connection.

This is the first reset observed **without a preceding move**, and it narrows section 7
rather than repeating it. `S180` is the top of GRBL's S range and, on this linkage, the end
of the servo's mechanical travel — so the horn is stalled against its stop, and an MG996R
stalled draws its full ~2.5 A for as long as the signal holds it there. A hold, not a
transient. That is enough on its own to collapse the rail, which means:

- The buck's **transient** response is not the only problem; its **sustained** capability
  matters too, and section 7's fix list should be read with that in mind.
- **Never park the pen at an extreme.** Pen-up wants the smallest S that clears the paper,
  not the biggest S the servo accepts. A pen lift needs a few millimetres; 90° of horn
  travel is many times more than that, and every degree past contact is stall current.
- A reset while idle is no longer evidence of the motion-coupled fault. Check where the
  servo is parked first.

**Open:** the minimum S that lifts the pen clear, and whether holding *that* value is
stable. Until it is measured, treat any S above ~S150 as a stall risk.

## 7c. A repeatable cycle-count to failure — the number to test fixes against

_Observed 2026-09-04 on the machine, first run of `gcode/tests/T15_pen_cycle_grid.gcode`,
new arm alignment (S90 down / S140 up)._

```
Streaming 994 lines ...
   75/994
   !! GRBL RESET mid-stream at line 91 (brownout)
Position: <Alarm|MPos:0.000,0.000,0.000|Bf:15,128|FS:0,0|WCO:-303.000,-107.000,0.000>
```

Stream line 91 is `M3 S90` — pen **down** — and line 90 is `G0 X-5.0`. **The board reset on
a pen actuation immediately following a move**, which is section 7's signature exactly. The
re-aligned arm and the new S values changed nothing about it.

**11 pen cycles completed before the reset**, roughly 30 seconds in.

What is new is not the fault but the measurement. Every previous reproduction was "somewhere
in a long job". T15 fails **in about half a minute, at a countable cycle number**, which
turns the open problem into something with a metric:

- **Before any fix: dies at cycle ~12 of 140.**
- A fix that gets it to 40 is progress even if it still fails. A fix that completes all 140
  is the answer. Previously there was no way to tell a partial improvement from noise.
- It also means each hardware change can be evaluated in a minute rather than a long plot,
  so **change one thing at a time** is finally cheap to obey.

Read the cycle count **off the paper**, not the console: `plot2.py` reports lines accepted
into GRBL's buffer, which runs seconds ahead of the pen, and a reset discards whatever was
still in flight. Expect the paper to show slightly fewer ticks than the line number implies.

## 8. Working right now, without the servo

Motion is in better shape than it has ever been: homing repeatable, work zero persistent,
T7 draws a clean square with no errors. **Single-stroke plots run start to finish today** —
disconnect the servo (both wires), tape the pen at drawing height, and plot as before.

## 10. One 24 V supply feeds all three drivers and the board — on purpose

The question was whether the LRS-350-24 can carry three TB6600s plus the Elecrow
board, and whether a small dedicated supply per component would be better. The
answer is that capacity was never the constraint, and splitting would make the
real problem worse.

### What the rail actually carries

Per stepper, from first principles rather than the driver's 3 A rating — the
motors are Ender 42-34s run at ~0.84 A/phase into ~2.3 Ω coils:

| | at 24 V |
|---|---|
| copper loss, two phases energised: 2 × 0.84² × 2.3 | 3.2 W |
| mechanical + iron, at plotter speeds | ~1 W |
| TB6600 losses | ~1 W |
| **per driver** | **~5 W, 0.21 A** |
| three drivers | ~15 W, 0.63 A |
| Elecrow board + endstops | ~3 W, 0.13 A |
| **total** | **~18 W, 0.75 A of 14.6 A — about 5 %** |

Double every line and it is still under 1.5 A. The LRS series has no minimum-load
requirement, so running it at 5 % is fine; it costs a few watts of efficiency and
nothing else.

**This is the same mistake as section 6a in a different place.** The first trunk
sizing used the TB6600's 3 A rating instead of what the motors draw, and came out
roughly 5× high. Size from the load, not from the device that feeds it.

### Why four small supplies would be worse, not better

1. **The grounds cannot actually be separate.** Step/dir/enable and the endstops
   reference the board's 0 V against the drivers' 0 V. Four supplies still have to
   have their 0 V rails bonded — and then there are multiple return paths between
   them. That is a ground loop, which is the *cause* of the noise that splitting
   supplies is meant to avoid. One supply with a star point at the rail is
   strictly better, and is what `ENCLOSURE_HANDOFF.md` builds (G1 / G2, joined only at
   the star).
2. **Regeneration.** A decelerating stepper pumps energy back into its supply. The
   LRS-350's bulk output capacitance absorbs it without noticing. A 25 W supply has
   a fraction of that capacitance and its over-voltage protection can trip. Small
   supplies are *more* exposed to this.
3. **Transient response.** A simultaneous three-axis acceleration is nothing to a
   supply at 5 % load. It is a real step for three supplies each near their limit.
4. **Four supplies is four of everything mains-side** — four L/N/PE landings, four
   earth bonds, four times the mains wiring, roughly double the DIN rail.

### The one separation that does earn its place

The servo, which already has it: a separate **12 V supply → buck → 6 V** (the 12 V supply
also runs the fans). An MG996R stalls near 2.5 A, it is brushed, and its current steps are
exactly what shifts a shared reference. That is section 2 and section 7 of this document.
The buck is non-isolated, so its return is the 12 V supply's return (G2), and G2 meets the
24 V return (G1) at the star point and nowhere else. See `ENCLOSURE_HANDOFF.md`.

_The two-box design used an RS-25-24 → LM2596 for this; it is superseded._

### Open: what regulator the Elecrow board uses for its 5 V

If it is a linear 7805, then 24 V in at ~150 mA burns (24 − 5) × 0.15 ≈ 2.9 W in a
TO-220 with no heatsink — thermal shutdown, or a dead regulator. If it is a
switcher (MP1584, LM2596, or an AMS1117 behind a pre-regulator) then 24 V is fine.

**Check before first power-up:** read the silkscreen on the regulator beside the
VIN terminal, or power the board alone at 24 V and feel it after a minute. If it
is linear, the fix is one small 24 → 12 V buck on the rail for the board — not
four power supplies. Elecrow's own site is unreachable from the build container,
so this has not been confirmed from the datasheet.

### Later, not now

TB6600s accept 9–42 V, and a higher rail means faster coil current rise and more
torque at speed. If rapids ever need to be quicker, 36 V would help — and at that
point the board needs its own buck regardless. A pen plotter does not need it.

## 11. DC wiring and protection — sized to the supply, not the load

_Worked out 2026-10-08/09 while planning the build. Arithmetic, not measurement; the
load figures are section 10's first-principles estimates._

The decision recorded in `ENCLOSURE_HANDOFF.md` is **no DC fuses**: each wire is sized to
carry whatever its supply will deliver before the supply's own protection acts. This
section is why that works, and what it requires.

### The mains fuse does not protect the DC side

The fuse in the IEC inlet sees mains current. If the LRS-350-24 delivers its full 15 A
into a fault:

| | |
|---|---|
| DC power | 24 V × 15 A = 360 W |
| from the wall, at ~88 % efficiency | 360 / 0.88 ≈ 409 W |
| mains current | 409 / 230 ≈ **1.8 A** |

That never blows the inlet fuse. A dead short is not the danger — it trips the PSU's own
over-current protection. The danger is a **partial fault** (chafed insulation on the
frame, a failing driver) drawing, say, 8 A: below the PSU's trip point, invisible to the
inlet fuse, and able to run for hours. With no DC fuse, the wire must carry that safely.

### So the minimum wire is set by the supply's current limit

| Circuit | What can flow before something trips | Minimum |
|---|---|---|
| **24 V and G1** (LRS-350-24) | 14.6 A rated, over-current trip above that, ~15–19 A | **1.5 mm²** |
| **12 V and G2** | the 12 V supply's limit — **read its label**, take ~1.3 × rated | size to that |
| **6 V** (buck output) | the buck's current limit: ~3 A for an LM2596, ~5 A for an XL4015 | 0.5 mm² / 0.75 mm² |
| Signals (step/dir/enable, endstops, PWM) | milliamps | 0.25 mm², limited only by what the terminal will clamp |

**AWG trap: 16 AWG is 1.31 mm², below 1.5.** For the 24 V and G1 runs buy metric 1.5 mm²,
or 14 AWG (2.08 mm²). 18 AWG is 0.82 mm², 20 AWG 0.52 mm², 22 AWG 0.33 mm², 24 AWG 0.20 mm².

**Fuse-and-thin-wire is the other valid scheme** — e.g. 20 AWG on 24 V behind a
**T2A** (time-lag) 5×20 fuse at the PSU terminal: the normal 0.75 A load is 38 % of 2 A,
and the time-lag rides through the drivers' input-capacitor inrush. It was considered and
not chosen. **Thin wire with no fuse is the one combination that is not allowed.**

### Voltage drop is not the constraint here

Copper is 0.0172 Ω·mm²/m. On the servo pair (2.5 A stall, about 1 A running):

- 0.75 mm² × 1.5 m return at 2.5 A: 2.5 × 1.5 × 0.023 = **86 mV**
- 0.5 mm² × 1 m at 1 A: **33 mV**

Both are trivial against a ~2.5 V logic threshold. What matters for the servo is that
its return current does not share a conductor with the logic reference (section 2), and
the **2200 µF at the servo end** (section 6a), which no wire size replaces.

### Grounds

- **A non-isolated buck's IN− and OUT− are the same copper.** Run one 0 V conductor
  between any two points, never two in parallel — a second path is a loop through the
  buck's board.
- **DC 0 V stays off PE.** 0 V already reaches the building earth through the Mac's USB
  lead; a second bond inside the box is a ground loop through that cable.
- A supply that feeds nothing referenced to the board (e.g. one that runs only fans)
  need not join the star at all.

### Cable and termination

- **Anything that moves** (servo and endstop leads on the gantry) is **high-flex** —
  fine-stranded silicone. Ordinary multicore cracks inside within weeks.
- **Endstops: twisted pair or screened** over 1.5 m next to motor leads, screen at the
  box end only. Otherwise false limit trips.
- **Ferrules by cross-section, never by colour** — two colour codes are in wide use.
  0.25 lilac / 0.5 white / 0.75 blue / 1.0 red / 1.5 black / 2.5 grey (DIN 46228-4).
- On **3.5 mm-pitch** board terminals, use **uninsulated** ferrules: an insulated 1.0 mm²
  collar is ~4 mm across. Never solder-tin a wire under a screw — the solder creeps and
  the clamp loosens.
- **Distinct pin counts per function** (GX16-4 for the servo, GX16-3 for endstops): plug
  6 V into an endstop socket and it lands on a 5 V logic input.
- **Never hot-plug a stepper connector.** A TB6600 whose motor is pulled live often dies.

### Parts that look interchangeable and are not

- **LED drivers as supplies:** constant-**voltage** only (e.g. Mean Well LPV/HLG CV). A
  constant-**current** driver raises its voltage until it reaches its set current — it
  destroys a logic board.
- **Lever splitters (PCT-22x, Wago 221 clones):** every port of one splitter is one
  node. Fine for low-voltage commons. On mains prefer genuine Wago 221 — clone clamp
  force and ratings vary by batch. A DIN-carrier lever splice does **not** bond to the
  rail, so it is not an earth terminal.
- **DIN terminal blocks:** the signal wires are 0.25 mm², so a block whose range starts
  at 0.5 mm² cannot hold them. Seen while shopping: **JCST 2.5** (7 mm wide, 0.5–4 mm²,
  36 A) — rejected for that reason; **Vital RM2.5U/CU** (24 A / 800 V, screw-in shorting
  link "RM2.5") — pitch and minimum wire size unconfirmed with the seller, and the
  catalogue has no PE block and no fuse block yet.

## 9. Method note

Most of the time lost went to treating each new symptom as a new fault. The resets, the
garbled serial (`error:1`, `error:2`, `error:254`, a bogus `ALARM:8`) and the EEPROM
corruption were all downstream of two things: a machine being driven into its end stops,
and a missing ground wire.

**Read `WCO` in the status line before believing any position-related theory**, and change
one variable at a time.
