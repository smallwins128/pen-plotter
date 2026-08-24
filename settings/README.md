# GRBL settings

`plotter.grbl.txt` is the restore block. One `$n=v` per line, **no comments** — GRBL's
`$` parser does not strip them, so `$0=10 ; foo` returns `error:3`. Send it line by line:

```bash
while read -r l; do python3 plot.py --port <port> --send "$l"; done < settings/plotter.grbl.txt
```

Re-flashing the firmware wipes EEPROM, so this file plus your `G10 L20 P1` work zero are
what you restore afterwards.

## These are the values actually on the machine

Not defaults, not aspirations — this is what `$$` returns after commissioning.

```
$22=1    homing ON. GRBL boots into Alarm and refuses everything until $H or $X.
         That is by design and it is confusing if you forget.
$20=0    soft limits still OFF
$21=0    hard limits off  <- leave this off permanently, see SETUP.md phase 5
```

`$20=1` only **after** `$130`/`$131` are set to your real measured travel. They currently
read 400 and 250, which are generous guesses rather than measurements — soft limits
protect nothing if the numbers are invented.

`$110`/`$111` are at **500** and `$120`/`$121` at **50** — deliberately conservative while
the resets described in [FINDINGS.md](../docs/FINDINGS.md) are unresolved. Ramp them with
`gcode/tests/T13_speed_ramp.gcode` once the machine is stable.

## Write these with the PSU switched OFF

EEPROM writes with motor power live is how the settings got corrupted twice. USB power
alone, 24 V off. See [FINDINGS.md](../docs/FINDINGS.md) section 5.

## Rationale for every value

See [`../docs/SETUP.md`](../docs/SETUP.md) phase 5.
