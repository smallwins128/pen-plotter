# Interference field art — the dense multi-colour look

The piece this is aimed at: a few hundred near-parallel lines snaking across a square,
each displaced by a smooth wave field, plotted twice in two inks so the layers moiré into
each other. Flat scan, reads as a three-dimensional surface.

**It needs no pen lift.** That is the whole reason it is the right thing to plot next on
this machine: the servo is still unreliable while moving (`FINDINGS.md` §7), and this
artwork never asks the pen to leave the paper. Tape the pen down, disconnect the servo,
plot for an hour and a quarter.

---

## What is in the repo

| File | |
|---|---|
| `tools/fieldart.py` | The generator. Writes G-code **and** an SVG preview. |
| `gcode/art/field_calm_L1.gcode` `_L2` | The flagship: two layers, two inks, 144 mm, ~73 min each. One broad dome, a few clean ridges, plenty of open surface. |
| `gcode/art/field_swell.gcode` | Single layer, a rolling swell rather than a dome. |
| `gcode/art/field_calm_proof.gcode` | 100 mm, coarse, **9 min** — run this first. |
| `gcode/art/field_18cm_blue.gcode` `_red` | The same field sized to **180 × 180 mm**, blue then red, ~108 min a layer. |
| `gcode/art/field_18cm_proof.gcode` | Coarse pass over the **full 180 mm extent**, 13 min. Run this before the 18 cm pair — see the note below. |
| `gcode/art/*.svg` | Previews. Open them before committing an hour to a plot. |

---

## The two rules the design is built around

**1. One continuous stroke, no pen lifts.** The turns at the end of each row are part of
the drawing. No Z words, no `M2`, no `M5`, no `M3` — the file contains nothing but `G1`.

**2. Every layer starts and ends at the same point.** The path sweeps up the square, then
sweeps back down between its own rows, which both doubles the line density and returns the
carriage to where it began. That closure is the *only* registration method available with a
fixed pen: when the file finishes, the carriage is back at the start, so you swap the pen in
the holder **without touching the carriage** and run the next layer. Registration is then
mechanically exact — nothing has moved.

Closure is verified numerically at generation time; the tool refuses to write a layer that
does not return to its origin.

---

## Running it

Relative art needs no homing and no work zero, exactly like the existing pieces:

```bash
python3 tools/plot2.py --no-home --unlock gcode/art/field_calm_proof.gcode
```

Full procedure:

1. **Disconnect the servo** (both wires) and tape the pen at drawing height.
2. Tape the paper down. Really tape it — 73 minutes of dragging a pen across it.
3. Jog the carriage to the start point. The file header names it, e.g. *0.0 mm right of,
   3.4 mm up from the bottom-left corner of the drawn area* — the pattern overshoots the
   nominal square by the wave amplitude, which is why the start is not the corner itself.
4. Run `field_calm_proof.gcode` first. Nine minutes tells you whether the pen, the paper,
   the tape and the feed rate are right, before you spend over an hour.
5. Run `field_calm_L1.gcode`. Leave it alone.
6. When it stops, **do not jog, do not home, do not reconnect anything.** Swap the pen for
   the second colour in the same holder and run `field_calm_L2.gcode`.

### Going past 150 mm

The machine's travel (`$130=400`, `$131=250`) has room for 180 mm in both axes, but
HANDOFF calls **~150 × 150 mm** the comfortable area and nothing larger has been plotted
yet. Nothing in the G-code can check that for you — these files are relative, so GRBL has
no idea where the paper is.

**Run `field_18cm_proof.gcode` first.** It is the same field at a coarse spacing and covers
the full 180 mm extent in 13 minutes, so a belt that binds, a carriage that fouls, or paper
that turns out to be too small shows up then rather than 90 minutes into the real plot.

### What will go wrong

- **A reset mid-plot loses the job.** The file is relative, so there is no resuming it —
  position is gone. Generate with `--split 3` if you would rather risk 25 minutes than 73.
  Split parts chain back to back with the carriage untouched, same as layers do.
- **The pen will run dry.** 36 metres of continuous line is far more than a fineliner
  holds. Use a gel or rollerball pen with real ink capacity, and prefer a 0.5 mm tip —
  the effective line pitch is 0.6 mm, so anything broader closes the gaps and the bands
  turn into solid ink.
- **`--no-home` needs `--unlock`**, because `$22=1` makes GRBL boot into Alarm.
- Do not raise the feed above `$110` (500). `$110` and `$120` are deliberately low while
  the reset problem is open; if T13 later passes at higher values, raise the setting first
  and regenerate with a matching `--feed`.

---

## Making your own

```bash
python3 tools/fieldart.py --name mine --seed 42 --preview-only   # look at the SVG
python3 tools/fieldart.py --name mine --seed 42 --layers 2       # then commit to it
```

| Flag | What it does |
|---|---|
| `--seed` | The whole design. Cycle it with `--preview-only` until an SVG looks right. |
| `--spacing` | Row spacing of the outward sweep; the return sweep halves it. 1.2 → 0.6 mm pitch. |
| `--amp` | Peak displacement. **Must exceed the spacing** or the lines never cross and the three-dimensional illusion never appears. 2–3× spacing is the sweet spot. |
| `--fold` | **The turbulence dial**, and the first one to reach for. It is how many times the field folds back on itself, so it sets the number of dark ridges. `1.0` is churning and busy; `0.7` is a calm surface with a handful of clean ridges; below `0.5` the drawing flattens out and the three-dimensional read goes with it. The shipped pieces use `0.70`–`0.75`. |
| `--scale` | Feature size. Stretches every wavelength, so `1.6` gives one broad dome across the sheet where `1.0` gives several competing hills. Raise it alongside lowering `--fold`. |
| `--sources` / `--waves` | Radial wave sources and plane waves. More sources → more separate hills fighting each other, which reads as turbulence even at a low `--fold`. Three or four is plenty. |
| `--layers` | Colour passes. Each gets a phase offset (`--layer-phase`) and half a row of vertical shift, which is what makes them interfere rather than overprint. |
| `--split` | Cut a layer into N consecutive files — ink refills, overnight stops, smaller blast radius on a reset. |
| `--size` | Square side, and the row length. |
| `--height` | Stack height, when it should differ from `--size`. The waves overshoot the stack by about `--amp` at each end, so a 180 mm square wants `--size 180 --height 174`. The tool prints the drawn bbox — size the paper from that, not from `--size`. |
| `--inks` | Names the layers after the pen you will actually load: `--inks blue,red` writes `field_<name>_blue.gcode` and `_red.gcode` and colours the previews to match. Implies `--layers`. |

### Turning the turbulence down

Busy is the default and it is easy to overshoot in either direction. In order:

1. Drop `--fold` to `0.7`. This alone removes most of the churn.
2. Raise `--scale` to `1.5`–`1.8` so the surviving features are big.
3. Keep `--sources` at 3–4. Cutting to 2 with a low fold gives an almost flat drawing.
4. Leave `--amp` at 2–3× `--spacing`. Amplitude is what makes the ridges dark; lowering it
   to calm the piece down just removes the effect instead.

Plotting time scales as `size² / spacing`, and the tool prints the estimate before you
commit to it. Halving `--spacing` doubles both the density and the hours.
