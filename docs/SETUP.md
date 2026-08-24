# Pen plotter — full setup, top to bottom

Arduino Uno + CNC Shield V3 + GRBL 1.1, dual-X belt gantry, servo pen lift on D11.

Work through the phases in order. Each phase ends in a check you can actually see or
measure; do not start the next phase until the check passes. Most of the pain in this
build has come from doing phase 5 things before phase 1 was true.

| Phase | What | Ends when |
|---|---|---|
| 0 | Safety and power-up order | — |
| 1 | [Firmware](FIRMWARE_SERVO.md) | `$I` shows `[OPT:VH,...]` and your build stamp |
| 2 | Pin map — know what every wire lands on | You can name the function of D9–D13 |
| 3 | Wiring: endstops, D12, servo, power | `?` shows `Pn:` empty at rest |
| 4 | Driver current and mechanics | Gantry square, motors warm not hot |
| 5 | GRBL settings | `$$` matches `settings/plotter.grbl.txt` |
| 6 | Bring-up test ladder | T0–T6 all pass |
| 7 | Daily run procedure | A plot lands on the paper where you aimed it |

---

## Phase 0 — Safety and power-up order

- **Never plug or unplug a stepper motor while the shield is powered.** That is the
  number-one killer of A4988s. Motors off → power off first, every time.
- **Power-up order: USB first, then the 24 V PSU.** GRBL boots and drives the stepper
  enable line and D11 to a known state; only then do you energise the drivers and the
  servo. Power down in reverse: PSU off, then USB.
- Expect the servo to **twitch on every Arduino reset** — and the serial port opening
  *is* a reset (DTR). Make sure the pen carriage cannot jam or stab the bed at either
  servo extreme.
- The 24 V PSU has mains on its input terminals. Cover them.

---

## Phase 1 — Firmware

See **[FIRMWARE_SERVO.md](FIRMWARE_SERVO.md)**. Short version: stock GRBL's D11 PWM runs
at 980 Hz and cannot drive a servo. Four small edits to `cpu_map.h` and `config.h` fix
that and fix homing for a machine with no Z switch. Do this before touching any wiring.

---

## Phase 2 — The pin map (this is where the confusion lives)

GRBL 1.1 compiled with `VARIABLE_SPINDLE` (the default) **swaps the Z-limit and spindle
pins** relative to what the CNC Shield V3 silkscreen says, so it can reach the hardware
PWM on D11. From `cpu_map.h`:

```c
#ifdef VARIABLE_SPINDLE // Z Limit pin and spindle enabled swapped to access hardware PWM on Pin 11.
  #define Z_LIMIT_BIT   4 // Uno Digital Pin 12
#else
  #define Z_LIMIT_BIT   3 // Uno Digital Pin 11
#endif
```

| Uno pin | Shield silkscreen | What GRBL 1.1 actually does with it here |
|---|---|---|
| D2 / D5 | X step / X dir | X axis (and the A-slot clone) |
| D3 / D6 | Y step / Y dir | Y axis |
| D4 / D7 | Z step / Z dir | unused — no Z motor |
| D8 | EN | stepper enable, active low |
| D9 | X+ / X− endstop | **X limit input** |
| D10 | Y+ / Y− endstop | **Y limit input** |
| **D11** | **Z+ / Z− endstop** | **servo signal (spindle PWM)** |
| **D12** | **SpnEn** | **Z limit input** |
| D13 | SpnDir | spindle direction — unused |
| A0 / A1 / A2 | Abort / Hold / Resume | reset, feed hold, cycle start |
| A3 | CoolEn | flood coolant — unused |
| A5 | — | probe input — unused |

**So: the servo signal goes into the header labelled "Z endstop", and the header labelled
"SpnEn" is the one GRBL reads as the Z limit switch.** Both of your source documents get
this half-right. The handoff has it right. Your research note ("the PWM pin, commonly
found on the Z-Endstop *or* Spindle (SpnEn) pin header") is only true for GRBL 0.9-era
builds *without* variable spindle — on this firmware they are two different pins with two
different jobs, and swapping them means shorting an output to ground.

---

## Phase 3 — Wiring

### 3.1 Endstops (X and Y)

Both harvested Ender switches are **NC — normally closed**, closed at rest, open when
pressed.

```
X switch  ──►  X endstop header (D9),  two wires: signal + GND   (polarity irrelevant)
Y switch  ──►  Y endstop header (D10), two wires: signal + GND
```

GRBL enables the internal pull-up on every limit pin. With `$5=0` (default) a LOW pin
reads as triggered — which for an NC switch is its *resting* state, so GRBL would think
both switches are permanently pressed. `$5=1` inverts that: closed/LOW = clear,
open/HIGH = triggered. **NC switches require `$5=1`.** (`limits.c`, `limits_get_state()`.)

Use two-conductor wire and keep it away from the stepper cables. NC has one genuinely
nice property: a broken wire looks like a permanently-triggered switch, so it fails loud.

### 3.2 D12 — the pin that must be tied to ground

`$5=1` inverts **all** limit pins including Z. D12 has nothing on it, the internal pull-up
holds it HIGH, and HIGH-when-inverted means "triggered" — that is the phantom `Pn:Z` that
sits in the status report forever and would make `$21=1` unusable.

```
D12 (SpnEn header)  ──►  any shield GND pin
```

A single jumper wire. Required before hard limits are even thinkable, and harmless
otherwise. (Alternative if you prefer no jumper: compile with
`#define INVERT_LIMIT_PIN_MASK (1<<Z_LIMIT_BIT)` in `config.h`, which inverts Z only. The
wire is simpler.)

### 3.3 Servo

```
Servo SIGNAL (yellow/orange, outer wire) ──►  D11  = the "Z endstop" header signal pin
Servo V+     (red, MIDDLE wire)          ──►  buck VOUT+
Servo GND    (brown/black, outer wire)   ──►  buck VOUT−  AND a shield GND pin
```

- The middle wire is always power. Get this wrong and the servo dies instantly.
- **Set the buck output voltage with the servo disconnected**, meter on the output, before
  the servo ever sees it.
- **The servo on this machine is an MG996R** (4.8-7.2 V), so **6.0 V is correct**. The 5.0-5.5 V figure below applies only to 9 g SG90/MG90S-class servos. Those are 4.8–6 V
  parts and run hot and jittery at the top of that range. Set the buck to **5.0–5.5 V**.
  6.0 V is fine only if the servo is an MG996R-class part rated 4.8–7.2 V.
- **Never** power the servo from the Arduino 5 V pin or the shield's 5 V rail. A stalled
  9 g servo pulls ~700 mA; the Uno's regulator browns out and the board resets mid-plot.
- **470–1000 µF electrolytic across the servo's V+ and GND, physically at the servo.**
  Not optional in practice — the lift current spike is what causes random resets.
- **The buck `VOUT-` to shield `GND` wire is mandatory. Never remove it.** It looks
  redundant — the buck is non-isolated, so its ground is already common with the shield's
  through the PSU — but it is the servo's actual return path. Removed, a single PWM step
  of servo movement was enough to reset the board. See
  [FINDINGS.md](FINDINGS.md) section 2.
- If the servo jitters even so, check whether your shield has a filter capacitor fitted
  across that endstop pin (some V3.51 clones do). It will round off the servo pulse. Remove it.

### 3.4 Power chain

```
Mean Well LRS-350-24  (24 V, 14.6 A)
  ├─► CNC Shield V+ / GND   (steppers)
  └─► LM2596 buck, set to 5.0–5.5 V  ─►  servo  (+ bulk cap at the servo)
```

24 V is within the A4988's 35 V ceiling and gives the Ender motors good top speed, but
**A4988s at 24 V run hot**. Heatsinks on all three drivers, and a small fan blowing across
them if the enclosure is closed. If you ever get random mid-plot stalls that are not
mechanical, thermal shutdown of a driver is the first suspect.

### 3.5 Optional, worth doing

- **Abort button on A0** (to GND). One button, and `Ctrl-X` over serial stops being your
  only emergency stop.
- **10 µF between RESET and GND on the Uno** suppresses the DTR auto-reset, so opening the
  serial port stops resetting the controller. Remove it to flash firmware. See phase 7 for
  why this matters much less once homing is on.

---

## Phase 4 — Drivers and mechanics

### 4.1 A4988 current

Ender 42-34 motors are ~0.84 A/phase. Set each driver's Vref with a meter on the pot:

```
Vref = I_target × 8 × R_sense
```

- `R_sense = 0.100 Ω` (most common) → for 0.84 A: **Vref ≈ 0.67 V**
- `R_sense = 0.050 Ω` → **Vref ≈ 1.34 V**

**Check which sense resistors your boards have** (marked R100 or R050 next to the chip) —
getting this backwards is a factor-of-two current error. Start at ~80 % of the numbers
above and only raise if you skip steps. A plotter needs very little torque; running cool
is worth more than headroom.

Set the pot with the motors connected and the board powered, driver enabled, motor idle.

### 4.2 Microstepping

1/16 on the CNC Shield V3 = **all three jumpers fitted** under each driver (MS0/MS1/MS2
high). All three X/A/Y drivers identical, or the two X motors fight each other.

`$100 = 200 steps × 16 ÷ (20 teeth × 2 mm) = 80 steps/mm` — correct, and confirmed by the
calibration test in phase 6.

### 4.3 Squaring the dual-X gantry

Two motors, one axis, **one** limit switch. Homing cannot square the gantry — it only
finds one end. If the beam is racked, it stays racked.

Before each session: power off (so both motors are de-energised), push the gantry gently
against a hard mechanical reference at both ends until it seats square, then power up.
With `$1=255` (phase 5) the motors stay energised from then on and it holds.

If racking becomes a recurring annoyance, the real fix is a second X limit switch and a
proper auto-squaring controller — which the Uno cannot do while also driving the servo.
That is an ESP32/FluidNC upgrade, not a GRBL-on-Uno one.

### 4.4 Pen holder

The single biggest determinant of line quality, and it is mechanical, not electrical:

- The pen should be **spring-loaded or gravity-floating**, with the servo only lifting it.
- Tune pen-down so the servo arm travels slightly **past** the point where the pen touches,
  so the pen floats on its spring rather than being pressed by the servo. A servo holding
  the pen against the paper stalls, buzzes, draws current, and gives you line weight that
  varies with how flat your bed is.
- Aim for **25–40° of servo travel** between up and down. Much less and the ~6-units-of-S
  resolution becomes visible; much more and the lift is slow.
- Set the horn on the spline at mid-travel before tightening, so `S90` is roughly centre.

---

## Phase 5 — GRBL settings

Full paste-able block: **[`settings/plotter.grbl.txt`](../settings/plotter.grbl.txt)**
(one `$n=v` per line, no comments — GRBL's `$` parser does not strip them — safe to send
line by line). That file deliberately ships with `$20=0` and `$22=0` so that a
freshly-flashed board powers up harmless; the target values below are what you set at the
end of the bring-up ladder.

```
$0=10     $1=255    $2=0      $3=1      $4=0      $5=1      $6=0
$10=3     $11=0.020 $12=0.002 $13=0
$20=1     $21=0     $22=1     $23=2
$24=25    $25=500   $26=250   $27=3.000
$30=180   $31=0     $32=0
$100=80.000  $101=80.000  $102=80.000
$110=2000.000 $111=2000.000 $112=500.000
$120=200.000  $121=200.000  $122=200.000
$130=<measured>  $131=<measured>  $132=200.000
```

> **Write settings with the 24 V supply switched OFF, on USB power alone.** Settings and
> the work offset both live in EEPROM, and a reset landing mid-write corrupts it — GRBL
> then silently falls back to defaults, which undoes `$5`, `$22` and `$23` and makes the
> next symptom look like a new fault. `$RST=*` restores clean defaults if it happens.

### Changes from the last-known-good block, and why

| Setting | Was | Now | Reason |
|---|---|---|---|
| `$1` | 25 | **255** | 255 = never disable the steppers. At 25 ms the motors de-energise during every pen-change dwell and belt tension can drag the gantry. On a plotter you want them held. The motors will run warm — that is correct. |
| `$10` | 10 | **3** | `$10=10` is a GRBL 0.9 value. In 1.1 only bits 0 (MPos) and 1 (buffer) exist; 10 gave you WPos and buffer with a stray bit. `3` = MPos + `Bf:` buffer counts, which is what you want while debugging. Switch to `2` later if you prefer WPos in the raw stream. |
| `$11` | 0.010 | **0.020** | Junction deviation. 0.010 is the CNC default and makes GRBL crawl through the many short segments a plot is made of. 0.020 visibly smooths curves with no accuracy cost at these speeds. |
| `$20` | 0 | **1** | Soft limits. Once homing works these are strictly better than hard limits: they act on the *planned* target before motion starts, and cannot false-trip on wire noise. |
| `$22` | 0 | **1** | Homing on. This is what makes work zero survive a reset — see phase 7. |
| `$27` | 1.0 | **3.0** | Pull-off. 1 mm is marginal for reclaiming an NC switch reliably; 3 mm guarantees release and costs nothing. |
| `$120/$121` | 50 | **200** | 50 mm/s² is very low: at that rate reaching 2000 mm/min takes 0.66 s and 11 mm of travel, so nearly every segment in a real plot is acceleration-limited. Tune upward per phase 6, test T5. |
| `$102/$122` | — | — | Z values are irrelevant (no Z motor). Left sane rather than zero. |
| `$130/$131` | 200 | **measure** | Set these to the travel you actually have, not a round number. Soft limits are only protective if the number is true. |

### Ones to leave exactly as they are

- **`$3=1`** — inverts X direction. Mirroring is fixed here and **never** by flipping
  G-code files. If a plot comes out mirrored, this setting is the only thing to touch.
- **`$5=1`** — required by the NC switches (phase 3.1).
- **`$21=0`** — hard limits stay **off**. NC switches on unshielded wire next to stepper
  cables plus a pin-change interrupt equals `ALARM:1` at random. Homing plus soft limits
  gives you the same protection without the false trips.
- **`$23=2`** — Y homes toward negative, X toward positive. Result: home corner is
  front-right, `$H` drives +X and −Y.
- **`$30=180`, `$31=0`** — makes S values map linearly across the servo's full pulse
  range (see the table in FIRMWARE_SERVO.md). Do not change one without the other.
- **`$32=0`** — laser mode **off**, and it must stay off. Laser mode makes S changes take
  effect *during* motion without draining the planner. For a pen that means the lift
  happens somewhere in the middle of a line instead of at its end.

### Why machine coordinates are negative after homing, and why that is correct

`limits.c` sets, for each homed axis:

```c
if (bit_istrue(settings.homing_dir_mask, bit(idx))) {
  set_axis_position = (settings.max_travel[idx] + settings.homing_pulloff) * steps_per_mm;  // homed negative
} else {
  set_axis_position = -settings.homing_pulloff * steps_per_mm;                              // homed positive
}
```

X homes positive → X ends at ≈ −3 mm, travel runs to −$130 (leftward).
Y homes negative → Y ends at ≈ −($131 − 3), travel runs up to 0 (backward).

So the whole workspace is the box **X ∈ [−$130, 0], Y ∈ [−$131, 0]** — all negative, which
is exactly what GRBL's soft-limit checker requires ("assumes the workspace volume is in
all negative space", `limits.c:409`). Nothing is wrong. Front-right is near (0, −max),
back-left is near (−max, 0), and a drawing authored in Quadrant I from a work zero at the
paper's bottom-left runs toward (0, 0) — safely inside the box the whole way.

### One rule this imposes on generated G-code

**No Z words. At all.** Soft limits check every axis including the unhomed Z, and any
`G0 Z5` will throw `ALARM:2` and abort the job. The pen is `M3 S<n>`; there is no Z axis
on this machine.

---

## Phase 6 — Bring-up test ladder

Files are in [`gcode/tests/`](../gcode/tests). **Edit the two pen values at the top of each
file** once T0 has told you what they are. Run them in order; each one only makes sense if
the previous passed.

### 6.0 — Before any G-code: read the pins

```bash
python3 plot.py --port /dev/cu.usbserial-A5069RR4 --send '?'
```

At rest, with nothing pressed, you want `Pn:` **absent entirely** from the status line.

- `Pn:Z` present → D12 is not grounded (phase 3.2).
- `Pn:XY` present → `$5` is wrong for NC switches, or the switches are wired to the wrong pins.
- Press X switch by hand, re-read: `Pn:X` should appear, and vanish on release. Same for Y.
  **Do this before homing.** A switch that does not toggle here will drive the gantry into
  the frame at `$25=500` mm/min.

### 6.1 — T0: servo only, no motion

```bash
python3 tools/servo_sweep.py --port /dev/cu.usbserial-A5069RR4
```

Interactive: `u`/`d` nudge by 6 (one PWM count), a number jumps to that S value, `q` quits
at the up position. Find:

- **pen up** — clears the paper by 3–5 mm, no more.
- **pen down** — pen touching with the holder's spring taking the pressure, servo *not*
  straining. If it buzzes, you have gone past the mechanical stop or you are pressing the
  pen into the bed. Back off.

Write both values into the test files and into your generator. Then run
`gcode/tests/T0_servo_only.gcode` — five clean up/down cycles, no motor motion, no buzzing
at either end and no board resets.

**If the servo does not move at all, or slams to one end and stays there: the firmware
timer edit did not take.** Go back to FIRMWARE_SERVO.md §5 and check `$I`.

### 6.2 — T1: motion, pen up

`T1_square_50_airmove.gcode` — four laps of a 50 mm square in the air, returning to work
zero. Nothing should touch the paper. Watch for: both X motors turning together, no
buzzing, no missed corners. Mark the start point and confirm it comes back to it.

### 6.3 — T2: first line on paper

`T2_square_50_draw.gcode` — one 50 mm square, pen down. Check corners are square and the
line closes cleanly on itself.

### 6.4 — T3: calibrate steps/mm

`T3_calibration_100mm.gcode` — a 100 mm line along X and a 100 mm line along Y. Measure
both with calipers.

```
$100_new = $100_old × (100 / measured_X)
$101_new = $101_old × (100 / measured_Y)
```

If they come out at 80.0, your belts and pulleys are what you think they are. More than
~2 % off means a 16-tooth pulley, a 1/8 microstep jumper missing, or belt slip — find the
cause rather than fudging the number.

### 6.5 — T4: pen lift reliability

`T4_penlift_comb.gcode` — ten 10 mm dashes with a lift between each. This is the test that
matters most: every dash the same length and weight, gaps genuinely blank, no dots or
tails where the servo was still moving. If you see tails, increase the `G4 P` dwell after
each pen change (0.20 → 0.30 s).

### 6.6 — T5: acceleration tuning

`T5_accel_torture.gcode` — a fast zigzag that returns to origin. Run it, then check the
pen is back exactly on the start mark.

Raise `$120`/`$121` **together** in steps: 200 → 300 → 400, re-running T5 each time. The
first value that loses position is your ceiling; **back off 30 %** and stay there. Then do
the same for `$110`/`$111` if you want more speed — the Uno can push far more step rate
than this machine needs, so mechanics will be the limit, not GRBL.

### 6.7 — T6: squareness

`T6_square_100_diagonals.gcode` — a 100 mm square with both diagonals. Measure the two
diagonals. Equal = gantry square. A difference means the beam is racked; re-do phase 4.3.

### 6.8 — Homing, last

Only after T0–T6 pass, and with a hand on the USB cable:

```bash
python3 plot.py --port <port> --send '$HX'    # X alone, watch it
python3 plot.py --port <port> --send '$HY'    # then Y alone
python3 plot.py --port <port> --send '$H'     # then the full cycle
```

Each axis moves **twice** — fast seek, pull off, slow locate, pull off. That is
`N_HOMING_LOCATE_CYCLE 1` doing its job, not a bug.

Then set `$130`/`$131` to the travel you actually measured, and only then `$20=1`.

---

## Phase 7 — The daily run procedure

### 7.1 Set work zero once — it lives in EEPROM

`G10 L20 P1` writes the G54 offset to EEPROM, so it **survives resets, power cycles, and
serial reconnects**. Homing gives you a repeatable machine origin for it to be measured
from. Together they solve the "opening the port resets the Arduino and I lose my position"
problem completely:

Prefer **`G10 L2`** over `G10 L20`: `L2` takes absolute machine coordinates, so it needs
neither homing nor motor power and can be set with the PSU off. `L20` uses the current
position, so it needs a homed machine and a live supply.

```
G10 L2 P1 X-303 Y-107     # set G54 origin by coordinates, PSU off, no motion
```

**First time on a new paper position:**
```bash
python3 plot.py --port <port> --send '$H'                      # establish machine origin
python3 plot.py --port <port> --jog X-40                       # jog to the paper's bottom-left
python3 plot.py --port <port> --send 'G10 L20 P1 X0 Y0'        # store work zero
```

**Every session after that:**
```bash
python3 plot.py --port <port> --send '$H'                      # that's it
python3 plot.py --port <port> --send '$#'                      # optional: confirm G54 is still there
python3 plot.py --port <port> plot.gcode
```

The reset on port-open no longer costs you anything, because `$H` re-establishes exactly
the same machine origin and G54 is remembered relative to it.

For jogging, prefer GRBL 1.1's jog command over `G0`:

```
$J=G91 G21 X10 F1000
```

It does not disturb modal state, it respects soft limits, and it is cancellable
(`Ctrl-X`, or the 0x85 real-time byte) mid-move.

### 7.2 File conventions

Preamble on every generated file. The servo is limp until the first `M3`, and jumping
straight to an extreme from that state is the largest current draw it ever makes — so wake
it near centre and walk it out:

```gcode
G21          ; mm
G90          ; absolute
G94          ; units per minute
M3 S90       ; wake the servo at centre
G4 P0.50
M3 S100      ; walk it out in stages
G4 P0.30
M3 S110
G4 P0.30
M3 S120      ; pen up
G4 P0.30
```

Postamble:

```gcode
M3 S120      ; pen up
G4 P0.30
G0 X0 Y0     ; back to work zero
```

- **No `M2` / `M30`.** Not because it is dangerous — because of what it actually does. In
  `gcode.c`, program end runs `spindle_set_state(SPINDLE_DISABLE, 0)` (pen drops), then
  resets the modal state: back to `G90`, back to `G54`, plane to `G17`, **and feed rate to
  0**. That is why it looked like a controller reset. Anything streamed afterwards throws
  `error:22` (undefined feed rate). Just end the file after the last move.
- **No `M5` mid-file** — it disconnects the PWM pin and the servo goes slack. `M3 S<up>`
  is pen up. `M5` is only reasonable as the very last line, with the pen parked off the
  paper, if you want the servo to stop holding.
- Feeds at `F2000` or below while `$110/$111=2000` — anything higher is silently clamped,
  so time estimates must assume 2000 mm/min.
- **No Z words** (phase 5).
- Prefer `G90` absolute for long plots: if a stream dies you can resume from a line number.
  `G91` relative cannot be resumed.

### 7.3 Streaming

`plot.py` (character-counting flow control, reads the whole file itself) over UGS. The
UGS failures on this machine were real: desyncs, silent mid-job cancels, and — the nasty
one — iCloud placeholder files that had not downloaded, which UGS streams as a truncated
file and then reports "done".

```bash
pip3 install pyserial
python3 plot.py --list                       # find the port
python3 plot.py --port <port> --send '$$'    # raw command
python3 plot.py --port <port> --jog X10      # relative jog
python3 plot.py --port <port> --unlock       # $X
python3 plot.py --port <port> file.gcode     # stream
```

- **Close UGS first** — one program per serial port.
- `ok` means **accepted into the planner buffer**, not executed. Motion can be in flight
  for seconds after the last `ok`. Wait for `Idle` in `?` before concluding anything.
- Check status *inside* the same connection. A separate invocation resets the board.

---

## Reference: reading the status line

```
<Idle|MPos:-3.000,-197.000,0.000|Bf:15,128|FS:0,0|WCO:-40.000,-150.000,0.000>
```

- `Idle` / `Run` / `Jog` / `Hold` / `Alarm` / `Home` / `Door` / `Check`
- `MPos` machine position; `WPos` if `$10` bit 0 is clear. `WCO` = the G54 offset, emitted
  periodically so a sender can convert between the two.
- `Bf:15,128` planner blocks free, RX bytes free. Watch this while streaming: if the first
  number sits at 15, the sender is not keeping the buffer fed and the machine is stopping
  between segments.
- `Pn:XYZPDHRS` appears **only** when something is triggered. Empty is what you want.

### Alarms

| Code | Meaning | Usual cause here |
|---|---|---|
| `ALARM:1` | Hard limit | Why `$21` stays 0 |
| `ALARM:2` | Soft limit — target exceeds travel | Work zero too close to an edge, or a stray Z word |
| `ALARM:3` | Reset while in motion | Position lost; `$H` before continuing |
| `ALARM:8` | Homing fail — could not clear the switch | `$27` pull-off too small, or a stuck switch |
| `ALARM:9` | Homing fail — switch not found in the search distance | Switch not wired, `$5` wrong, `$23` sending the axis the wrong way, or `$13x` too small |

`$X` unlocks. It does **not** restore position — after `ALARM:1`/`3`, home before drawing.

### Errors

| Code | Meaning |
|---|---|
| `error:2` | Bad number format |
| `error:8` | `$` command only valid when idle |
| `error:9` | G-code locked out during alarm — you owe it a `$H` or `$X` |
| `error:20` | Unsupported command |
| `error:22` | Feed rate undefined — almost always an `M2` earlier in the file |
| `error:24` | Two G-codes needing axis words in one line |

### Real-time bytes (take effect immediately, no newline, no `ok`)

`?` status · `~` cycle start/resume · `!` feed hold · `Ctrl-X` (0x18) soft reset ·
`0x85` jog cancel

---

## Known-good gotchas, kept

- `$22=1` makes GRBL **boot into Alarm** and refuse everything including jogging until
  `$H` or `$X`. By design (`HOMING_INIT_LOCK`), and thoroughly confusing if you forget.
- Homing moves each axis twice. Correct.
- Re-flashing **wipes EEPROM** — settings *and* your G54 work zero. Restore both.
- The OSM converter graph-routes connectors along real roads so retraces stay invisible.
  With a working pen lift, multi-stroke art (Truchet tiles etc.) no longer needs
  single-stroke chaining at all — plot the original file.
