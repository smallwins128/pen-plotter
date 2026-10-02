# Firmware: GRBL 1.1 with a real servo output on D11

**Read this first. Nothing else in the pen-lift chain works until this is done.**

Everything below is checked against the actual source of `gnea/grbl` (master, v1.1h),
not from memory. File and line references are to that source.

---

## 1. Why stock GRBL cannot drive a hobby servo

Stock GRBL 1.1 does output a PWM signal on **D11**. It is the wrong PWM.

`grbl/cpu_map.h`, in the ATmega328P block:

```c
// Prescaled, 8-bit Fast PWM mode.
#define SPINDLE_TCCRA_INIT_MASK   ((1<<WGM20) | (1<<WGM21))  // fast PWM
// #define SPINDLE_TCCRB_INIT_MASK   (1<<CS20)               // no prescaler -> 62.5 kHz
// #define SPINDLE_TCCRB_INIT_MASK   (1<<CS21)               // 1/8   -> 7.8 kHz  (v0.9)
// #define SPINDLE_TCCRB_INIT_MASK   ((1<<CS21) | (1<<CS20)) // 1/32  -> 1.96 kHz
#define SPINDLE_TCCRB_INIT_MASK      (1<<CS22)               // 1/64  -> 0.98 kHz  <-- DEFAULT
```

Default spindle PWM is **980 Hz** — a 1.02 ms frame. An RC servo wants a **50–60 Hz
frame with a 1–2 ms pulse inside it**. At 980 Hz the servo never sees a valid frame; it
either sits at an endpoint, buzzes, or twitches randomly. There is no S value that fixes
this, and **no G-code sender can fix it either** — the timer is configured in firmware.

This is the single reason the pen lift has not worked. Fix the timer, and the rest is
tuning.

## 2. Get the source

Use `gnea/grbl` v1.1h — the current, maintained GRBL for the Uno. Do **not** use
`bdring/Grbl_Pen_Servo`: it is a fork of GRBL **0.9**, which costs you `$J=` jogging,
real-time feed/rapid overrides, the 1.1 status report format, and the error/alarm code
tables that every modern sender and every troubleshooting page assumes.

```
https://github.com/gnea/grbl  ->  Code -> Download ZIP
```

Install into the Arduino IDE by copying the **inner** `grbl/` folder (the one containing
`grbl.h`) into `~/Documents/Arduino/libraries/grbl/`. The correct end state is:

```
~/Documents/Arduino/libraries/grbl/grbl.h        <-- this file must exist at this path
~/Documents/Arduino/libraries/grbl/config.h
~/Documents/Arduino/libraries/grbl/cpu_map.h
...
```

`grbl.h: No such file or directory` at compile time always means the folder was nested
one level too deep.

## 3. The four edits

### Edit 1 — `cpu_map.h`: servo frame rate

Find the `SPINDLE_TCCRB_INIT_MASK` line quoted above (it is in the
`#if !defined(ENABLE_DUAL_AXIS)` branch of the ATmega328P block) and replace it with:

```c
// 1/1024 prescaler -> 61.0 Hz frame, 64 us per PWM count. RC servo compatible.
#define SPINDLE_TCCRB_INIT_MASK   ((1<<CS22) | (1<<CS21) | (1<<CS20))
```

16 MHz / 1024 / 256 = **61.04 Hz**, frame period 16.4 ms, and **one OCR count = 64 µs**.
61 Hz is inside the tolerance of every analogue hobby servo and of the great majority of
digital ones.

### Edit 2 — `cpu_map.h`: map the S range onto 0.5–2.5 ms

A few lines above, replace the min/max PWM values:

```c
#define SPINDLE_PWM_MAX_VALUE     39   // 39 * 64us = 2496 us   (was 255)
#ifndef SPINDLE_PWM_MIN_VALUE
  #define SPINDLE_PWM_MIN_VALUE   8    //  8 * 64us =  512 us   (was 1)
#endif
```

`SPINDLE_PWM_MAX_VALUE` has no `#ifndef` guard, so it must be edited here in `cpu_map.h`
— setting it in `config.h` will not take. Its "Don't change" comment refers to the timer
TOP value; lowering the *mapping* ceiling is safe and is exactly what we want.

### Edit 3 — `config.h`: homing cycle for a machine with no Z switch

Default (line ~105) tries to home Z **first**, and this machine has no Z switch, so `$H`
can only ever end in `ALARM:9`:

```c
#define HOMING_CYCLE_0 (1<<Z_AXIS)                // REQUIRED: First move Z to clear workspace.
#define HOMING_CYCLE_1 ((1<<X_AXIS)|(1<<Y_AXIS))  // OPTIONAL: Then move X,Y at the same time.
```

Replace with X then Y, sequentially (safer than simultaneous on a belt gantry — you can
watch one axis at a time during bring-up):

```c
#define HOMING_CYCLE_0 (1<<X_AXIS)
#define HOMING_CYCLE_1 (1<<Y_AXIS)
// #define HOMING_CYCLE_2
```

### Edit 4 — `config.h`: single-axis homing commands

Line ~124, uncomment:

```c
#define HOMING_SINGLE_AXIS_COMMANDS // Default disabled. Uncomment to enable.
```

This gives you `$HX` and `$HY`. During bring-up you want to home one axis at a time so a
switch wired backwards drives one motor into a stop instead of two.

### Optional edit 5 — stamp the build so `$I` proves what is flashed

In `grbl.h`:

```c
#define GRBL_VERSION_BUILD "20260823-servo"
```

Then `$I` answers "which firmware is actually on this board?" definitively, instead of
you inferring it from servo behaviour.

## 4. Flash

Arduino IDE → File → Examples → grbl → grblUpload → Board: **Arduino Uno** → Upload.

**Physically remove the CNC shield before uploading.** D0/D1 are the serial lines and
things plugged into the shield can block the upload; more importantly you do not want
the steppers live while the board is resetting.

**Flashing wipes EEPROM.** Restore `settings/plotter.grbl.txt` immediately afterwards —
including the `G10 L20` work zero, which also lives in EEPROM.

## 5. Verify the flash

```
$I
```

Expect something like:

```
[VER:1.1h.20260823-servo:]
[OPT:VH,15,128]
```

- **`V`** = `VARIABLE_SPINDLE` compiled in. Without `V`, D11 is not a PWM pin at all
  and the Z limit moves back to D11 — see the pin table in `SETUP.md`. Do not proceed.
- **`H`** = `HOMING_SINGLE_AXIS_COMMANDS`, from edit 4.
- The build string is your proof edits 1–3 are in this binary.

`[OPT:...]` does **not** report the timer change — that is why edit 5 is worth doing.

## 6. S value → pulse width

With `$30=180` and `$31=0`, GRBL computes
(`grbl/spindle_control.c`, `spindle_compute_pwm_value`):

```
pwm = floor( S * (39-8) / (180-0) ) + 8       -> pulse = pwm * 64 us
```

| S | PWM | pulse | | S | PWM | pulse |
|---|---|---|---|---|---|---|
| **0** | **off** | **no signal — servo goes limp** | | 100 | 25 | 1600 µs |
| 20 | 11 | 704 µs | | 110 | 26 | 1664 µs |
| 30 | 13 | 832 µs | | 120 | 28 | 1792 µs |
| 40 | 14 | 896 µs | | 130 | 30 | 1920 µs |
| 50 | 16 | 1024 µs | | 140 | 32 | 2048 µs |
| 60 | 18 | 1152 µs | | 150 | 33 | 2112 µs |
| 70 | 20 | 1280 µs | | 160 | 35 | 2240 µs |
| 80 | 21 | 1344 µs | | 170 | 37 | 2368 µs |
| 90 | 23 | 1472 µs | | 180 | 39 | 2496 µs |

Three consequences worth internalising:

1. **Resolution is ~64 µs, i.e. about 6 units of S.** `S70` and `S73` are the same pulse.
   Step S in units of 6 or more; anything finer is noise. Fine pen-height adjustment
   belongs in the pen holder, not in the S value.
2. **`S0` and `M5` are not "pen up".** Both call `spindle_stop()`, which clears
   `COM2A1` and disconnects the pin (`spindle_control.c:101`). The servo stops receiving
   pulses and goes slack — the pen falls. Use `M3 S<up>` for up and `M3 S<down>` for
   down, and never `M5` mid-job.
3. **0.5 ms and 2.5 ms are past the mechanical stops of many servos.** Start sweeping at
   `S90` (pen down on this build) and walk outward. If the servo buzzes and gets hot at an endpoint, it
   is stalled against its own stop — back off immediately.

## 7. What we are deliberately not doing

- **`ENABLE_DUAL_AXIS`.** GRBL 1.1 does have a ganged-motor mode that would drive the
  second X motor from its own step/dir pins and free D12. But `DUAL_AXIS_CONFIG_CNC_SHIELD_CLONE`
  puts step/dir on D12/D13 and, per its own comment in `cpu_map.h`, *"Variable spindle
  not supported with this shield"* — which costs you the servo. The A-slot jumper clone
  already works and costs nothing.
- **`bdring/Grbl_Pen_Servo` (pen driven by Z moves).** Cleaner G-code in principle, but
  it is GRBL 0.9 based. Revisit only if you move to an ESP32 and FluidNC, which has
  native `M280`-style servo support and none of these timer gymnastics.
