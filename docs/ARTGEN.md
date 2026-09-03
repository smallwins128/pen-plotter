# Generative art: scope, stack, plan

Software to make the art, not just plot it. Layered multi-pen work, and posters with
borders, title blocks and legends — blueprints rather than bare drawings.

**Status: v0 exists and works.** A browser studio for ideation, and a bridge that turns any
layered SVG into this machine's G-code. The Python half is scoped, not built.

---

## 1. Does vsketch help us?

**Yes, and it is the right engine for the production half.** Read at
`abey79/vsketch`, checked against the source rather than the README.

| What it gives us | Detail |
|---|---|
| **Layers, exactly as we want them** | `vsk.stroke(1)`, `vsk.stroke(2)` … puts geometry on numbered layers. One layer, one pen, swap between. This is a first-class concept, not a workaround. |
| **Single-stroke text** | `vsk.text(s, x, y, font="futural", width=…, align=…, justify=True)` — Hershey fonts, with wrapping and justification. A plotter cannot fill a letterform, so stroke fonts are the only way to get text on paper. This is the whole poster/legend problem, solved. |
| **Plot-time optimisation** | `vsk.vpype("linemerge linesimplify reloop linesort")` runs vpype's pipeline. On a contour plot this is the difference between 4000 pen lifts and 120. |
| **Parameters + live GUI** | `vsketch.Param(12)` auto-generates a slider. `vsk run` gives live reload, seed control and a viewer. That is the WYSIWYG loop. |
| **Batch + seeds** | `vsk save` sweeps seeds and configs with multiprocessing. Good for "print 25 variants, pick 3". |
| **Processing-shaped API** | `push/pop`, `translate`, `rotate`, `rect`, `circle`, `beginShape/vertex/endShape`, `random`, `noise`. If you know p5.js you already know it. |

### What it does not give us

1. **No G-code. At all.** `vsk.save()` writes SVG or HPGL. HPGL is for old HP pen plotters and
   is not GRBL. This is the only real gap, and it is small — see section 3.
2. **No poster furniture.** Borders, title blocks and legends are not a concept; they are
   something you write once as a reusable module and import.
3. **It is a desktop Python app.** `pipx install vsketch` pulls PySide6 (Qt), numpy, shapely,
   matplotlib and vpype. Fine, but it is an install, and the loop is *edit code → save →
   live reload*, not direct manipulation.

### And p5.js?

p5.js is the same idea in the browser and is the fastest place to ideate. One thing matters
more than everything else about using it for plotting:

> **p5 draws pixels. A plotter needs vectors.** `line()` on a p5 canvas paints and is gone —
> there is nothing left to export. You either use the `p5.js-svg` addon, or you record
> geometry yourself and use p5 purely as a preview.

The studio in section 2 takes the second route, and its drawing API is deliberately p5-shaped
so a sketch moves between p5.js, the studio and vsketch with almost no edits.

---

## 2. What exists now: the studio

A browser app, no install, WYSIWYG. Generators with live parameters, layers with a pen each,
a blueprint frame, and export to SVG or G-code.

**Four generators**, all chosen because they plot well (long continuous paths, not confetti):

| | |
|---|---|
| **Contour / topographic** | Marching squares over a noise field, one layer per band of height. The closest thing to a real blueprint, and the best-looking of the four. |
| **Flow field** | Streamlines through noise. Layers split by direction. |
| **Concentric moiré** | Offset circle families; the interference is the drawing. |
| **Truchet weave** | Quarter-arc tiles that connect across the grid, so merged paths run very long. |

**The blueprint frame** draws a border, an inner rule, corner registration ticks, a title
block (title / by / edition / date) and a legend listing each pen and its path count. All of
it is real geometry on a layer you choose, in a single-stroke font — so it plots like
everything else.

**Two numbers on the toolbar earn their place:**

- `drawing N merged to M` — the linemerge result. A contour at default settings is ~3800 raw
  segments merged to ~116 paths. Every path you remove is a pen lift you do not make.
- `~N min` — ink length ÷ feed, plus travel, plus two dwells per pen lift. Sanity-check
  before you commit an hour.

The paper picker warns when a size exceeds the ~150 × 150 mm this machine can reach, because
soft limits abort with `ALARM:2` partway through rather than clipping.

**Downloads are blocked inside the artifact viewer**, so export is copy-to-clipboard into a
file. Not elegant; it works.

---

## 3. What exists now: the bridge

[`tools/svg2gcode.py`](../tools/svg2gcode.py) — layered SVG in, one G-code file per layer out,
in the dialect [SETUP.md](SETUP.md) phase 7.2 requires: `G21/G90/G94`, `M3 S<n>` for the pen,
servo soft-start preamble, dwell after every pen change, **no Z words, no `M2`, no mid-file
`M5`**.

```bash
# from vsketch, Inkscape, the studio, anything with Inkscape layers
vpype read drawing.svg linemerge linesimplify reloop linesort write opt.svg
python3 tools/svg2gcode.py opt.svg --out-dir plots
```

One file per layer is deliberate: `plot2.py` streams one file, so "plot a layer, swap the pen,
plot the next" is the natural seam.

It **refuses to write a file whose extents leave the usable area**. Soft limits abort mid-plot;
better to find out in a second than forty minutes in.

### Verified, not assumed

- vpype's own output parses (`vpype line … circle … write sample.svg` → correct layers, correct
  mm, correct y-flip to the bottom-left work origin).
- The studio's SVG is accepted by `vpype read` — so the whole vpype pipeline is available to it.
- Studio SVG → `svg2gcode.py` produces **byte-identical move counts and bounding box** to the
  studio's own direct G-code export: 2399 moves, X 0..141, Y 0..141. The two halves agree.

---

## 4. The gate

**Multi-layer plotting needs the pen lift, which does not work yet** ([HANDOFF §7](HANDOFF.md)).
Any drawing with more than one stroke needs pen up/down between strokes; that is exactly why
`gcode/art/` is single-stroke with the pen taped down.

So: design freely now, and plot single-layer single-stroke output today. The moment the servo
fault clears, everything here becomes plottable with no changes.

---

## 5. Plan

### Done
- [x] Studio: four generators, layers, blueprint frame, stroke font, SVG + G-code export
- [x] `tools/svg2gcode.py`, tested against real vpype output and round-tripped

### Next, in order
1. **Fix the servo.** Nothing multi-layer is real until then. Cap at the servo, twisted pairs,
   shortened arm.
2. **Plot one plate single-layer.** Contour, one pen, 150 × 150. Find out what the machine
   actually does with 116 paths and whether the estimate holds.
3. **Registration.** Multi-pen only works if layer 2 lands on layer 1. Homing plus a G54 work
   offset in EEPROM should give this for free — prove it with a two-layer crosshair test
   before trusting a real piece.
4. **Pen library.** Line width per pen, so the preview shows something like the real weight.
5. **Then, and only then, vsketch.** `pipx install vsketch`, port the four generators as
   sketch classes, use `vsk.text()` for real Hershey typography, and keep `svg2gcode.py` as
   the output stage. The studio stays as the sketchpad.

### Deliberately not doing yet
- Hidden-line removal and true fills — vsketch has both; no need to reinvent.
- A desktop app. The browser plus vsketch covers both ends.
- Selling infrastructure. Make ten plates worth selling first.

---

## 6. Where each piece lives

```
studio (browser)  ──SVG──►  vpype (optimise)  ──►  svg2gcode.py  ──►  plot2.py
      │                          ▲
      └────────G-code direct─────┘                 vsketch ──SVG──┘
```

Both routes end in the same G-code. The studio is for ideas; vsketch is for the pieces you
decide to make properly.
