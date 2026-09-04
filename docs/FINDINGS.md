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

## 7a. A static hold at S180 resets the board — no motion involved

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

## 8. Working right now, without the servo

Motion is in better shape than it has ever been: homing repeatable, work zero persistent,
T7 draws a clean square with no errors. **Single-stroke plots run start to finish today** —
disconnect the servo (both wires), tape the pen at drawing height, and plot as before.

## 9. Method note

Most of the time lost went to treating each new symptom as a new fault. The resets, the
garbled serial (`error:1`, `error:2`, `error:254`, a bogus `ALARM:8`) and the EEPROM
corruption were all downstream of two things: a machine being driven into its end stops,
and a missing ground wire.

**Read `WCO` in the status line before believing any position-related theory**, and change
one variable at a time.
