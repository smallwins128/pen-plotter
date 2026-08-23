# GRBL settings

`plotter.grbl.txt` is the restore block. One `$n=v` per line, **no comments** — GRBL's
`$` parser does not strip them, so `$0=10 ; foo` returns `error:3`. Send it line by line:

```bash
while read -r l; do python3 plot.py --port <port> --send "$l"; done < settings/plotter.grbl.txt
```

Re-flashing the firmware wipes EEPROM, so this file plus your `G10 L20 P1` work zero are
what you restore afterwards.

## Deliberately shipped in the "off" state

```
$20=0    soft limits off
$21=0    hard limits off   <- leave this off permanently, see SETUP.md phase 5
$22=0    homing off
```

`$22=1` makes GRBL boot into Alarm and refuse everything until `$H` or `$X`, so the file
ships with homing off to keep first-power-up harmless. Turn `$22=1` on at the end of the
bring-up ladder (SETUP.md phase 6.8), and `$20=1` only **after** `$130`/`$131` have been
set to your real measured travel — soft limits protect nothing if the numbers are made up.

`$130`/`$131` ship at 200.000 as a placeholder. Measure and replace.

## Rationale for every value

See [`../docs/SETUP.md`](../docs/SETUP.md) phase 5.
