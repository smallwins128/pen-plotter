# Gantry workstream: state of the world (2026-10-23)

Start here for anything on the plotter's frame, gantry, carriage or pen lift. This is a workstream inside room
R04 Etch, not a separate room: the Drive Handoff ([R04 Etch] Handoff) stays the room's memory, and this file is
the gantry's technical state. `docs/ENCLOSURE_STATE.md` is the same thing for the electronics boxes.

## Goal

One complete A3 artwork (Allwin's north star). Pens are changed by hand; no tool changer, no auto pen swap, no new
tool heads. Anything that is not on the path to a clean A3 plot waits.

## What exists (verified by Allwin unless marked)

- Base frame: 2040 extrusion, two 1000 mm rails (along the table) + two 560 mm ends, 1000 × 600 outside, on an IKEA
  LINNMON 100 × 60 top. The table is 1524 × 600.
- Cross bar: 2020, 700 mm, spans front to back (Y) and travels along X on the two 1000 rails, on OpenBuilds gantry
  plates (65.5 mm, 3-wheel, V-slot).
- Motion: GT2 belts, 20-tooth pulleys, dual X motors + one Y, Ender-3 42-34 steppers (~0.84 A/phase).
- Drivers: 3 × TB6600 and a FluidNC board, moving into the stacked stainless enclosure (see ENCLOSURE_STATE.md).
- Pen lift: MG996R servo on a whole Ender carriage (~400 g). The lift still resets the controller (FINDINGS 7a-7c);
  the fix is a mechanism that never stalls the servo at end of travel. Not designed yet.
- Acrylic plates: Allwin has acrylic gantry/mount plates; he will share their STLs (Drive folder below).

## Decided

- 2026-10-23, A3 bench layout (lofi https://claude.ai/artifact/KaVa1TQpxJwtchWTy21njC):
  - keep the base frame and the 700 bar;
  - add one 2040 cut at 560 as a divider at x 600 (the plotter bay is 0-600);
  - add stop blocks on both 1000 rails at x 600, so the bar can never run into the cabinets;
  - the cabinets sit turned 90° in the bay beyond, and the Bambu A1 sits on the last 524 mm of table.
  - Travel from the model (unverified): ~485 along X, ~465 along the bar. A3 landscape needs ~450 × ~330.
- Parked (not P0): raised rails on side plates over the 1000s.

## Open

1. Measure real X and Y travel after the divider and stop blocks are in, then set $130 / $131 (the values in
   settings/ were invented once; HANDOFF says so).
2. Pen-lift mechanism (tracker T17).
3. Bring Allwin's acrylic plate STLs into a gantry inspector.

## Files

| Path | Role |
|---|---|
| `hardware/params.py` | Frame, deck, bar and gantry-plate constants. Note: the frame/bar block appears twice (around lines 44 and 170); clean that up before changing values. |
| `hardware/parts/frame.py`, `cross_bar.py`, `deck.py`, `assembly.py` | build123d models of the machine. `cross_bar.x_travel()`, `deflection()` give travel and sag. |
| `hardware/web/machine.html` | Older 3D view of the machine (https://claude.ai/artifact/2AN2q4qFQ4fbEECBUUztsq). |
| `hardware/gantry/` | New home for gantry parts, the acrylic STLs (`hardware/gantry/acrylic/`) and the gantry inspector. |

## Inputs

- Drive: R04 Etch / Gantry (folder id 1LqnqajnVh5uIQSsz6jgPbedU7aNmEKlv). Allwin drops STLs and photos there.
  The agent downloads them with the Drive connector and commits them under `hardware/gantry/acrylic/`.

## How to work here

Same as the enclosure: show a lofi before modelling; ask before adding components; Allwin leads aesthetics; black
PETG for prints; mark guesses as unverified; one model drives the inspector so the view never drifts from the files.
Write any decision back here and in the R04 Handoff at room-close.
