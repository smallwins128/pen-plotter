# Gantry workstream: state of the world (2026-10-23)

Start here for anything on the plotter's frame, gantry, carriage or pen lift. This is a workstream inside room
R04 Etch, not a separate room: the Drive Handoff ([R04 Etch] Handoff) stays the room's memory, and this file is
the gantry's technical state. `docs/ENCLOSURE_STATE.md` is the same thing for the electronics boxes.

## Current (2026-11-09): ACRO-style frame, CAD run 5

Supersedes the 10-23 bench plan and lofi v2 below. Model: `hardware/gantry/frame.py` (checks; `--stl` for the
inspector, https://claude.ai/artifact/RYZArV4f7bo7fA559fdyH7; `--print` for flat print STLs). Lo-fi v4 (older
raised-rail layout): https://claude.ai/artifact/LQRCHp84mVaVaTB294fUjW (`frame_lofi.py`).

- Two 1000 2040 rails (standing) rest on two 560 2040 ends on the LINNMON; rails flush with its ends, frame 20 in
  from the front and back edges. No divider: the bar stops at 50-60 cm, enclosures beyond.
- End plate (x4, PLA): one flat 6 mm plate per corner on the rails' outer face: 28 column (2 M5 into the 560's
  tapped end), 64 arm along the rail (4 M5 into drop-in nuts), 45° chamfer. Left limit x ~112 (the arm).
- X plates (x2, PETG): ACRO gantry outline (traced from the STL), 6 mm, motor at the bottom; the 700 2020 bar
  passes through a 20.4 window and a 20 collar (one M5 + T-nut).
- Corner grab (x4, PLA, placeholder; Allwin may redesign): pad 20 lifts the frame so the X plates clear the
  table by 8.6; lips halfway down the LINNMON edge and end; the end plate keys 5 mm into a 28.4 x 6.4 x 5.3 pocket.
- Y carriage: plain plate for now; redesign is in scope; the pen must drop ~125 to the table.
- Unverified: wheel Ø24.4 x 10.2 and spacer 6 (catalogue), LINNMON 34 thick (placeholder), printed hole fits.
- Next: PLA test print (1 X plate, grabs A + B, key/pocket fit tester), then the full set.
- Rejected: rails raised 28 above the 560s; inner L-brackets; a wrap-round bracket with a gusset.

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
- Acrylic plates: OpenBuilds ACRO set, 6 mm acrylic, one STL with 11 parts (Drive file 1GCvAh8MUwtIzEuWDRKBjuIZjAEE99_Pn,
  Printables 260803): 2 gantry plates (93.9 × 135.7, NEMA17), carriage (93.9 × 122.7), short motor plate (93.9 × 110),
  tool plate (93.9 × 80.7), 4 end brackets, 2 links. Roles read from hole patterns, not yet confirmed by Allwin.

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
3. Gantry lofi v2 (2026-10-23, https://claude.ai/artifact/LQRCHp84mVaVaTB294fUjW). Allwin corrected v1: the gantry
   plates stand upright outside the 1000 rails (ACRO style), not flat on top. The file agrees: wheel holes 59.25 apart
   fit the top and bottom faces of a standing 2040, and the bar's end bolts to the plate as a 2040 on edge.
   Readings (unverified; they rest on catalogue wheel/spacer sizes):
   - the rails must come off the deck by at least ~24 so the bottom wheels clear (the parked "raised rails" is back);
   - the bar is a 2040 of ~602, cut between the plates' inner faces (neither the 700 nor a 560 fits);
   - the motors stand ~41 outside the frame, and the plates hang ~26 below the tabletop past its edge;
   - reach ~530 x 466 against A3's 450 x 330; the head, not the plates, sets it;
   - the stop blocks on the rail tops would catch the top wheels.
   Waits on Allwin: how the rails are lifted (ACRO end brackets or blocks), the table edge and wall clearance, and
   whether he has the wheels and spacers. Then the 3D inspector.

## Files

| Path | Role |
|---|---|
| `hardware/params.py` | Frame, deck, bar and gantry-plate constants. Note: the frame/bar block appears twice (around lines 44 and 170); clean that up before changing values. |
| `hardware/parts/frame.py`, `cross_bar.py`, `deck.py`, `assembly.py` | build123d models of the machine. `cross_bar.x_travel()`, `deflection()` give travel and sag. |
| `hardware/web/machine.html` | Older 3D view of the machine (https://claude.ai/artifact/2AN2q4qFQ4fbEECBUUztsq). |
| `hardware/gantry/` | Gantry parts and views. `acro_plates.py` reads the STL; `gantry_lofi.py` writes `hardware/web/lofi/gantry_lofi.html`. |
| `hardware/gantry/acrylic/` | The ACRO STL goes here. Git-ignored: the repo is public and the Printables licence isn't checked. |

## Inputs

- Drive: R04 Etch / Gantry (folder id 1LqnqajnVh5uIQSsz6jgPbedU7aNmEKlv). Allwin drops STLs and photos there.
  The agent downloads them with the Drive connector and commits them under `hardware/gantry/acrylic/`.

## How to work here

Same as the enclosure: show a lofi before modelling; ask before adding components; Allwin leads aesthetics; black
PETG for prints; mark guesses as unverified; one model drives the inspector so the view never drifts from the files.
Write any decision back here and in the R04 Handoff at room-close.
