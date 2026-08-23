# firmware/

**`grbl-servo-plotter.zip`** — the file you flash. GRBL 1.1h, patched for this machine.
`grbl-servo/` is the same code unzipped, so the edits are visible in git.

Compile-tested here before shipping: builds clean for atmega328p, 30,700 bytes
(the Uno has 30,720 usable after the bootloader — it fits, with nothing to spare).

## What was changed vs stock gnea/grbl

Every edit is tagged `[PLOTTER EDIT n]` in the source — search for that string.

| # | File | Change | Why |
|---|---|---|---|
| 1 | `cpu_map.h` | Timer2 prescaler 1/64 → **1/1024** | Servo PWM frame 980 Hz → **61 Hz**. Without this no hobby servo can decode the signal. |
| 2 | `cpu_map.h` | `SPINDLE_PWM_MAX_VALUE` 255 → **39**, `MIN_VALUE` 1 → **8** | Maps S0–S180 onto **512–2496 µs** pulses instead of 0–100 % duty. |
| 3 | `config.h` | `HOMING_CYCLE_0/1` → **X then Y** | Stock homes Z first. There is no Z switch, so `$H` could only ever end in `ALARM:9`. |
| 4 | `config.h` | `HOMING_SINGLE_AXIS_COMMANDS` on | Enables `$HX` / `$HY` for safe one-axis-at-a-time bring-up. |
| 5 | `grbl.h` | Build string → `plotter-servo-1` | `$I` now proves which firmware is on the board. |

Edits 1 and 2 are applied in **both** the normal and the dual-axis blocks of `cpu_map.h`,
so they hold whichever one is compiled.

## Verify after flashing

```
$I
```

Must return `[VER:1.1h.plotter-servo-1:]` and an `[OPT:...]` string containing **`V`**
(variable spindle — D11 is the PWM pin) and **`H`** (single-axis homing).

## Then restore settings

Flashing wipes EEPROM. Re-send `../settings/plotter.grbl.txt` and re-set work zero
with `G10 L20 P1 X0 Y0`.

## S value → servo pulse

`pwm = floor(S × 31 / 180) + 8`, pulse = `pwm × 64 µs`. One PWM count ≈ 6 units of S,
so `S70` and `S73` are the identical pulse. **`S0` and `M5` disconnect the pin entirely**
— no pulses, servo goes slack. Use `M3 S<up>` / `M3 S<down>` only.
