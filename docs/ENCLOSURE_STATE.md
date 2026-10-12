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
- Power front: original stepped vents only. ETCH mark removed for the cut (2026-10-12); Allwin will
  draw the front design himself.

## Files

| Path | Role |
|---|---|
| `hardware/sheet/enclosure.py` | **The single source.** Dimensions, flats, holes, folds, checks, DXF writer, and it writes the numbers into the inspector. `python3 hardware/sheet/enclosure.py` (`--report` = checks only). |
| `hardware/sheet/assembly_check.py` | Whole-assembly clearance: steel-to-steel gaps (≥ 2 mm unless a listed contact), lid fit, parts, fans, rivnuts, plate, feet, pegs. The generator refuses to write files on any clash. |
| `hardware/sheet/strokes.py` + `mark_etch.json` | ETCH mark outlines and the rejected brush strokes. **Unused** by the generator since 2026-10-12. |
| `hardware/sheet/pack.py` | Fabricator cover sheet PDF + zip: `python3 hardware/sheet/pack.py v4`. |
| `hardware/web/enclosure_inspector.html` | **The 3D renderer.** Reads the generator's `GEN` block (walls, panels, fans, plate, stack). |
| `hardware/cutfiles/2026-10-11 v3/` | Last released pack. **Superseded by the current model** (stacking holes, GX label text, fan/jack alignment) — issue v4 before sending. v1, v2 superseded. |

## Using the renderer in another chat

Published at https://claude.ai/artifact/DqabBr8QGaitg9eDwsvwex (private; v11). To change it:
1. Edit `enclosure.py` (or the inspector's drawing code), run `python3 hardware/sheet/enclosure.py` —
   it rewrites the `GEN` block in the inspector, so the 3D view always matches the cut files.
2. Republish: from a new chat, publish `hardware/web/enclosure_inspector.html` with
   `url = https://claude.ai/artifact/DqabBr8QGaitg9eDwsvwex` (read it first) to keep the same link.
3. Local check: Chromium headless shell + three@0.128.0 from npm (the CDN is blocked in the container);
   `camera` and `controls` are globals, so a script can set any view.

## Open before cutting

1. Issue cut pack v4 from the current model (`enclosure.py` then `pack.py v4`). — Claude
2. Fabricator confirms bend deduction for 1 mm 304 at R1 (files assume K 0.44, BD 1.74). — Allwin
3. Front design: Allwin draws it; plain panels (vents only) for now. Awaiting his final changes before v4.

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
  waves. Kept: clean steel, original vents, one bold mark (Orbitron Black). Offer one restrained idea,
  not a gallery; never fill a face.
