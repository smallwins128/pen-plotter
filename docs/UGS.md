# Testing the plotter from UGS

A ten-minute setup for driving this machine by hand from **Universal Gcode Sender** —
connect, unlock, jog, work the pen, run one short file. For poking at the machine and
tuning the pen, UGS beats typing `plot2.py --send` over and over.

**It is not the sender for real plots on this machine.** Streaming whole jobs through UGS
here produced desyncs, silent mid-job cancels, and — the one that wasted an afternoon —
iCloud placeholder files that had never downloaded, streamed as a truncated job and then
reported "done". Nothing in this doc fixes that; it was never diagnosed. Use UGS for
manual work and the short `U1`/`T0`/`T1` files, and `tools/plot2.py` for anything you
actually want to come out on paper. See [SETUP.md](SETUP.md) phase 7.3.

**One program per serial port.** UGS and `plot2.py` cannot both be connected. Disconnect
one before starting the other.

---

## 1. Connect

| Field | Value |
|---|---|
| Firmware | `GRBL` |
| Port | `/dev/cu.usbserial-A5069RR4` (macOS; check the menu, it can change) |
| Baud | `115200` |

Connecting **resets the Arduino** — the servo twitches, and any previous homing is gone.
That is normal and it is the single most important thing to remember about UGS here: every
connect starts the machine from scratch.

On connect you should see:

```
Grbl 1.1h ['$' for help]
[MSG:'$H'|'$X' to unlock]
```

**UGS will show the machine state as `Alarm`, and that is correct on boot.** `$22=1` means
homing is enabled, so GRBL starts in the Alarm *state* and refuses everything — jogging
included — until `$H` or `$X`. It is a state, not a fault, and it carries no number.

**A numbered `ALARM:n` message is different — that is a fault, and the number is the whole
diagnosis.** See [section 7](#7-alarms-what-the-number-means) before clearing it. Never
reflexively `$X` a numbered alarm: unlocking discards the reason without fixing anything,
and on this machine `ALARM:3` in particular means the controller lost its position and
must be re-homed, not unlocked.

Then check the firmware is still the patched build:

```
$I   ->   [VER:1.1h.plotter-servo-1:]
          [OPT:VH,15,128]
```

If that says a date instead of `plotter-servo-1`, the servo patch is gone and the pen will
not work no matter what you send. See [FIRMWARE_SERVO.md](FIRMWARE_SERVO.md).

## 2. First five minutes, in order

1. **Home** — toolbar home button, or type `$H`. Both X and Y move twice (fast seek, pull
   off, slow locate, pull off). That is correct.
   No motor power / don't want to home? Type `$X` to unlock instead, and skip to step 2 —
   but then the machine has no idea where it is, so only jog small and watch it.
2. **Set the work offset.** Run the `Work zero` macro below, or type it:
   `G10 L2 P1 X-303 Y-107`. **Do this before you jog to X0 Y0 or send any file.**
   With G54 at zero, `X0 Y0` means *machine* zero — the homed corner — and the gantry
   drives into the frame. `plot2.py` refuses to stream in that state; **UGS will happily
   do it.** This is the one way UGS can break the machine, so check it every session.
3. **Confirm the offset took.** Type `?` and read `WCO` in the reply:
   `<Idle|MPos:...|WCO:-303.000,-107.000,0.000>`. If `WCO` is all zeros, step 2 did not
   happen. Believe `WCO`, not your memory.
4. **Jog** with the jog panel. Start at 1 mm steps, F500. **Never touch the Z jog buttons**
   — there is no Z motor and no Z switch, and Z words are not part of this machine's
   G-code (see conventions below).
5. **Wake the pen** with the `Servo wake` macro, then `Pen up` / `Pen down`. The servo is
   limp until the first `M3`, and jumping straight to an extreme is the largest current
   draw it ever makes — always wake at S90 first.
6. **Send one short file:** `gcode/tests/U1_ugs_smoke_20mm.gcode`. Pen-free, relative, back
   to its start point, about twenty seconds.
7. **Then soak it:** `gcode/tests/T14_square_soak_10min.gcode` — the same 20 mm square 58
   times, about ten minutes. U1 proves the machine moves; T14 proves it keeps moving, and
   it is the one that catches lost steps, belt slip and drivers going thermal. Mark the
   start point first so you can see whether it walked.

## 3. Macros

UGS Platform: **Settings → Macros**. UGS Classic: the **Macros** tab under the console.
Commands within one macro are separated by `;`. **No comments inside a macro** — `;` is the
separator there, not a comment character, and a `; note` becomes a command GRBL rejects.

| Name | Macro | What it is for |
|---|---|---|
| `Unlock` | `$X` | Clear the boot alarm without homing |
| `Home` | `$H` | Same as the toolbar button |
| `Work zero` | `G10 L2 P1 X-303 Y-107` | The current work zero, in absolute machine coordinates. `L2` needs neither homing nor motor power — that is why it is `L2` and not `L20` |
| `Where am I` | `?` | Status line: state, `MPos`, `WCO`, `Pn` |
| `Settings` | `$$` | Dump settings; compare against `settings/plotter.grbl.txt` |
| `Version` | `$I` | Confirm the servo patch is still flashed |
| `Servo wake` | `M3 S90;G4 P0.5;M3 S107;G4 P0.3;M3 S123;G4 P0.3;M3 S140` | Soft-start from pen down. Run once per connection, before any other pen command |
| `Pen up` | `M3 S140;G4 P0.3` | |
| `Pen down` | `M3 S90;G4 P0.3` | |
| `Go to work zero` | `G90 G0 X0 Y0` | Only after `Work zero` — read step 2 |
| `Park` | `G90 G0 X0 Y150` | Pen up first; gets the carriage off the paper |

`S140` up / `S90` down, set on the machine on **2026-09-04, after the servo arm was
re-aligned on its spline**. The ladder wakes at `S90` because that is pen down, and pen
down is the gentlest place to energise a limp servo.

**Do not raise pen-up towards `S180`.** On the alignment before this one, that was the end
of the horn's mechanical travel, and simply *holding* it there stalled the servo and reset
the board — gantry stationary, no move sent. See [FINDINGS.md](FINDINGS.md) section 7a.

Re-tune after any mechanical change and edit all three macros together.

Copy-paste list: [`../settings/ugs-macros.txt`](../settings/ugs-macros.txt).

## 4. UGS buttons that do the wrong thing here

- **Return to Zero** sends a `Z0` along with X and Y. Soft limits are off (`$20=0`) so it
  will not abort the job, but it commands an axis this machine does not have. Use the
  `Go to work zero` macro instead.
- **Reset Zero** sends `G10 L20 P1 X0 Y0 Z0` — it zeroes G54 *at wherever the pen is now*.
  Fine if you meant it, a crash waiting to happen if you fire it at the homed corner: that
  sets the work offset to zero, and then `X0 Y0` is the end stops. Prefer the `Work zero`
  macro.
- **Z jog buttons** — as above, don't.
- **Firmware settings editor** works, but **only write settings with the 24 V PSU off**.
  Two rounds of EEPROM corruption came from writing while motor power was live.
- **Soft reset (Ctrl-X / the reset button)** twitches the servo and throws away homing,
  same as reconnecting.

## 5. Files you send from UGS

The G-code rules do not change because the sender did — mm (`G21`), absolute (`G90`) for
anything long, feeds at or below `$110=500`, **no Z words**, **no `M2`/`M30`**, **no
mid-file `M5`**. Reasons for each in [SETUP.md](SETUP.md) phase 7.2.

Two things specific to sending from UGS:

- **Keep the file on local disk.** Not iCloud Drive, not a cloud-synced Desktop or
  Documents folder. A placeholder that has not downloaded streams as a truncated job and
  UGS reports it as finished. If in doubt, copy the file to `~/Downloads` first and open it
  from there.
- **`ok` and "done" both mean *sent*, not *drawn*.** GRBL's `ok` means accepted into the
  buffer; motion runs on for seconds afterwards. Wait for `Idle` in `?` before concluding
  anything, and watch the machine, not the progress bar. **The console regularly reports
  success while the gantry is jammed against the frame.**

## 6. The pen problem, so it doesn't surprise you

Actuating the servo *after* the machine has moved resets the controller. Servo alone is
fine, motion alone is fine, together they fail; it is narrowed to supply and grounding
around the servo and the fix is not in yet. Full detail in
[HANDOFF.md](HANDOFF.md) section 7 and [FINDINGS.md](FINDINGS.md).

So while testing in UGS: a reset mid-session — the console goes quiet, the board
re-announces `Grbl 1.1h`, position is lost — is the known fault, not something you did.
Re-home before continuing. The single-stroke pieces in `gcode/art/` are the way around it:
tape the pen down and never actuate the servo during the plot.

**The PSU switch is the emergency stop.** Not the UGS stop button, not disconnecting.

---

## 7. Alarms — what the number means

`Alarm` as the **state** in the UGS status field, straight after connecting, is normal —
that is `$22=1`, clear it with `$H` or `$X`.

A numbered **`ALARM:n` in the console** is a fault. Read the number before you clear it.

| | Means | On this machine |
|---|---|---|
| `ALARM:1` | Hard limit triggered | Should not happen — `$21=0`, hard limits are off permanently. If you see it, `$21` got turned back on |
| `ALARM:2` | Target exceeds machine travel (soft limit) | Should not happen — `$20=0`. If you see it, either `$20` got turned on, or a `Z` word reached the controller (UGS's **Return to Zero** sends one) |
| `ALARM:3` | Reset while in motion — **position is lost** | The known pen-lift fault: actuating the servo after the machine has moved resets the controller. `$X` is *not* the fix; you must `$H` before trusting any coordinate again |
| `ALARM:6` | Homing failed — reset during homing | Something reset the board mid-`$H` |
| `ALARM:8` | Homing failed — could not clear the switch after pull-off | `$27=3` pull-off too small, or a switch stuck closed |
| `ALARM:9` | Homing failed — **could not find the limit switch** within the search distance | The common one. Ladder below |

### `ALARM:9` — the ladder

The axis was told to seek a switch and never found one within `$25`/`$130`–`$131`. Four
causes, in the order worth checking. **Change one thing at a time.**

1. **Did the axis move the wrong way?** `$H` must drive **+X and −Y** (home corner is
   front-right). If an axis ran away from its switch, that is `$23` — the homing direction
   mask — not a wiring fault.
2. **Did the axis move at all?** If the motor buzzed, or the belt slipped, or the gantry was
   already jammed, GRBL is seeking with nothing happening. **The console reports the same
   `ALARM:9` either way** — watch the machine, not the log.
3. **Is the switch actually making?** Both are **NC** with `$5=1`. Type `?` and read the
   `Pn:` field: it appears **only** when something is triggered. Press each switch by hand
   and re-send `?` — you should see `Pn:X` / `Pn:Y` appear and vanish. A broken NC wire
   reads as permanently triggered; a disconnected one as never triggered.
4. **Was it already sitting on the switch?** Jog off it by 5–10 mm and re-home.

`$130=400` / `$131=250` are **guesses, not measurements** — see `settings/README.md`. They
are generous, so they are an unlikely cause of `ALARM:9`, but they are not evidence of
anything either.
