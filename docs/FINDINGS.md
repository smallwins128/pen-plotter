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
torque. Asking it to jump straight to an extreme (`M3 S120`) from that state is the
biggest current step it ever makes.

**Soft-start it.** Wake it near centre and walk it out in stages:

```gcode
M3 S90
G4 P0.50
M3 S100
G4 P0.30
M3 S110
G4 P0.30
M3 S120
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
   strictly better, and is what `hardware/psu_layout.py` builds.
2. **Regeneration.** A decelerating stepper pumps energy back into its supply. The
   LRS-350's bulk output capacitance absorbs it without noticing. A 25 W supply has
   a fraction of that capacitance and its over-voltage protection can trip. Small
   supplies are *more* exposed to this.
3. **Transient response.** A simultaneous three-axis acceleration is nothing to a
   supply at 5 % load. It is a real step for three supplies each near their limit.
4. **Four supplies is four of everything mains-side** — four L/N/PE landings, four
   earth bonds, four times the mains wiring, roughly double the DIN rail.

### The one separation that does earn its place

The servo, which already has it: RS-25-24 → LM2596 → 6 V. An MG996R stalls near
2.5 A, it is brushed, and its current steps are exactly what shifts a shared
reference. That is section 2 and section 7 of this document, and it is why that
supply is separate and its return is 2.5 mm².

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

## 9. Method note

Most of the time lost went to treating each new symptom as a new fault. The resets, the
garbled serial (`error:1`, `error:2`, `error:254`, a bogus `ALARM:8`) and the EEPROM
corruption were all downstream of two things: a machine being driven into its end stops,
and a missing ground wire.

**Read `WCO` in the status line before believing any position-related theory**, and change
one variable at a time.
