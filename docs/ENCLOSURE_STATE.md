# Stainless enclosure — state of the world (2026-10-11)

Start here for the stainless boxes. `ENCLOSURE_HANDOFF.md` is the earlier brief (why plastic was
dropped, grounding, parts); this file is what is true now and how to keep working on it.

## What it is

Two stacked 1 mm 304 boxes, **control on top, power below**, each 450 W × 295 D inside
(control 110 H, power 170 H). Each box: a folded **body** (base, front, sides; top lips, back lips,
base back lip, front corner tabs) and a folded **lid** (top + back, return lips), plus a flat
**2 mm Al base plate** on 6 × M4 5 mm standoffs with a Ø6 grid (40 mm rows, alternate rows shifted 20).

- Fans + IEC on the left walls, original printed jack panels on the right walls (on their sides),
  GX16 1×6 rail on the control front (rectangular cutout, panel like the rest), USB-C + antenna
  panel on the control left wall.
- Every printed panel: 3 mm plate outside, 2 mm boss in the cutout (0.3 mm smaller per side),
  M3 countersunk screws + nyloc nuts.
- Lid fixings: 3 top + 3 back per box, M3 rivnuts set from outside (flange Ø8, measured), lid holes Ø10,
  M3 screw + **Ø16 penny washer**. Front corner tabs: 2 solid Ø3 rivets each, set cold.
- Stacking: 4 printed **locating feet** under the control box (Ø24 × 6 flange + Ø7.6 peg) drop into
  the power lid: Ø8 front-left locates, 8 × 11 slot front-right, Ø10 at the back. Power box keeps
  rubber feet.
- Power front: original stepped vents + **ETCH** mark top left (Orbitron Black, 18 mm cap, thickened
  0.5 mm, cut through; a black print behind embosses it 1.5 mm).
- Receiving panel (control right wall) moved **55 mm forward** so the saddle's window leaves its leg attached
  (60 would put a panel nut on a corner-tab rivet).

## Over-plates (added 2026-10-11, late)

Two stainless plates stand **16 mm off** the boxes on M3 standoffs: Allwin's sketch, built as one saddle + one band.
No colour (stainless only); 3D prints are the busy layer that goes on top later.

- **Saddle, 1.5 mm**: top over the control box (the laptop sits on it), a 40 mm visor with a 10 mm flange folded down
  (a bend, not a cut edge, where hands land), a 10 mm back flange, and two side plates shaped like a **7**: a band
  under the top, a nose over the front, a leg sweeping down and back that stops above the power box's side panels.
  Windows leave **10 mm of air round every port's printed plate** (USB/antenna, receiving panel); the control fan gets
  a slotted grille (50 % open). Fixed to the **control box only** (7 standoffs over the lid, 2 per side wall), so the
  control box still lifts off. The laptop gets ~0.7 mm of sag, a 10 kg lean ~3.4 mm and ~80 MPa (hand estimates; a
  1 mm saddle fails all three).
- **Band, 1 mm**: across the power box's front at 6 to 72 mm, wrapping both front corners; the left flange runs 82 mm
  back over the power fan (slotted, 45 % open), the right one 54 mm, stopping short of the PSU panel.
- **Corners**: 6 bends of 15°, 5 mm apart (bump bending) instead of a radius. All outline corners R5+, cut edges
  deburred + edge-rounded (no hems, no trim).
- **Holes added to the boxes**: control: 4 more top-lip rivnuts (+ lid clearance holes), 2 rivnuts in each side wall;
  power: 3 rivnuts in the front, 1 in the right wall. The lid-top screws become M3 x 15 male-female standoffs.
- **Open**: the Wi-Fi antenna on the USB/antenna panel. Pointing up, it hits the saddle's corner: it has to point out
  or down through the window, or become a short stub.

## Files

| Path | Role |
|---|---|
| `hardware/sheet/enclosure.py` | **The single source.** Dimensions, flats, holes, folds, checks, DXF writer, and it writes the numbers into the inspector. `python3 hardware/sheet/enclosure.py` (`--report` = checks only). |
| `hardware/sheet/assembly_check.py` | Whole-assembly clearance: steel-to-steel gaps (≥ 2 mm unless a listed contact), lid fit, parts, fans, rivnuts, plate, feet, pegs. The generator refuses to write files on any clash. |
| `hardware/sheet/strokes.py` + `mark_etch.json` | ETCH mark outlines (rebuild with `--build-mark <Orbitron-Black.ttf>`). Also holds the rejected brush-stroke design, unused. |
| `hardware/sheet/overplates.py` | The saddle + band: geometry, flats, standoff placement, their own checks (ports, webs, corner radii, fan grilles, clearances, laptop). `enclosure.py` builds and writes them; `python3 hardware/sheet/overplates.py` runs their checks alone. |
| `hardware/sheet/pack.py` | Fabricator cover sheet PDF + zip: `python3 hardware/sheet/pack.py v4`. |
| `hardware/web/enclosure_inspector.html` | **The 3D renderer.** Reads the generator's `GEN` block (walls, panels, fans, plate, stack, mark). |
| `hardware/cutfiles/2026-10-11 v3/` | Last released pack. **Superseded by the current model** (stacking holes, ETCH, GX label text) — issue v4 before sending. v1, v2 superseded. |

## Using the renderer in another chat

Published at https://claude.ai/artifact/DqabBr8QGaitg9eDwsvwex (private; v11). To change it:
1. Edit `enclosure.py` (or the inspector's drawing code), run `python3 hardware/sheet/enclosure.py` —
   it rewrites the `GEN` block in the inspector, so the 3D view always matches the cut files.
2. Republish: from a new chat, publish `hardware/web/enclosure_inspector.html` with
   `url = https://claude.ai/artifact/DqabBr8QGaitg9eDwsvwex` (read it first) to keep the same link.
3. Local check: Chromium headless shell + three@0.128.0 from npm (the CDN is blocked in the container);
   `camera` and `controls` are globals, so a script can set any view.

## Open before cutting

1. Issue cut pack v4 from the current model (`enclosure.py` then `pack.py v4`): now 8 DXFs with the saddle + band. — Claude,
   after Allwin settles the antenna.
2. Fabricator confirms bend deduction for 1 mm 304 at R1 (files assume K 0.44, BD 1.74). — Allwin
3. Fabricator confirms 5 mm between bump bends (1 and 1.5 mm 304) and that they deburr + edge-round. — Allwin
4. Antenna vs the saddle: point it out through the window, or a stub antenna. — Allwin

Still unmeasured: M4 rivnut hole (Ø6 assumed). Placeholder interior layout (drivers, PSUs) is soft:
one warning remains (GX rail parts 1.5 mm from driver D1) — move the driver when wiring.

## Learnings (process)

- **Check everything, not just steel.** v2 shipped with a fan through the base plate because only folds
  were checked. Now one gate checks parts, fasteners, fits and fold gaps before any DXF is written.
- **Design for bend tolerance (±0.5 per bend).** Flanges that must not touch: ≥ 2 mm (designed 2.5).
  Lid over body: 1.0 per side. Lap joints: 0.5 shy, closed by rivets. Locating features: one hole,
  one slot, the rest clearance.
- **One model.** The inspector drifted (round GX holes, wrong USB height) while it kept its own
  numbers. Everything it draws now comes from the generator.
- **Mutation-test the checks:** break a value on purpose and confirm the gate fails.

## Learnings (working with Allwin on this)

- Short, crisp messages. Discuss before building; show a preview before wiring anything in.
- Ask before adding components. "Tell, don't do" when he asks a question.
- Aesthetics: he leads. Rejected: full-face inlay/marquetry, corner emblems, hex-hole fades, brush-stroke
  waves, clip-on corner armour, orange cheeks / colour (he can't get colour), a zig-zag routed round the ports.
  Kept: clean steel, original vents, one bold mark (Orbitron Black), and his own sketch for the over-plates
  (space-cabin / hard-case references: shells standing off the box, windows, smooth bent curves).
- Lo-fi sketches before building worked well; sketch his drawings back to confirm the reading.
