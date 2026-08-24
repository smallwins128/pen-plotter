# Pen plotter — session handoff

Paste this into a fresh chat to pick up where the last one left off. Everything here is
**verified on the machine**, not assumed. Where something is unverified it says so.

_Last updated: 2026-08-24_

---

## Status in one paragraph

**Motion works properly.** Homing is repeatable, work zero survives resets, both limit
switches work, all three motors move accurately, and long single-stroke plots run start to
finish without errors. **The pen lift does not work reliably.** The servo responds
correctly to commands, but actuating it while the machine is moving resets the controller.
Cause is narrowed to supply/grounding around the servo; the fix is on order. **In the
meantime the machine plots single-stroke artwork with the pen taped down**, which is what
the files in `gcode/art/` are for.

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

## 8. Repo layout

```
firmware/     patched GRBL 1.1h source + flashable zip
docs/         SETUP.md (8-phase build), FIRMWARE_SERVO.md, FINDINGS.md, this file
settings/     plotter.grbl.txt — live values, restore after any re-flash
tools/        plot2.py (sender), pentest.py (servo swing sweep), servo_sweep.py
gcode/tests/  T0-T13, in bring-up order
gcode/art/    single-stroke pieces: Hilbert, rosette, ripples, Gosper, dragon,
              Sierpinski, one-line labyrinth, and the dense interference fields
              (field_*.gcode, with .svg previews) generated by tools/fieldart.py
```

**Multi-colour work is possible today, without the pen lift.** Every `field_*` piece
starts and ends at the same point, so a layer finishes with the carriage exactly where it
began: swap the pen in the holder without touching the carriage and the next colour
registers. See [`FIELD_ART.md`](FIELD_ART.md).

**Read [`FINDINGS.md`](FINDINGS.md) before re-debugging anything.** Most of the time lost
on this build went to treating each new symptom as a new fault, when the resets, the
garbled serial (`error:1`, `error:2`, `error:254`, a bogus `ALARM:8`) and the EEPROM
corruption were all downstream of two things: a machine driven into its end stops, and a
missing ground wire.

---

## 9. Gotchas, kept

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
