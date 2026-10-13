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
- Power front (2026-10-12): vent rows at 145/136/42, two acrylic windows split by a slanted bar (`WIN` in
  `enclosure.py`: 330 span, 40 tall, 40°, R3, 20 mm steel between 9 mm PETG bezels; 3 mm acrylic outside under the bezel;
  4 M3 screws per window from inside into heat-set inserts), 3 Ø5 accessory holes at 30 mm.
- Control front (2026-10-12): no GX holes in the steel. Three plain openings (`GX_GROUPS`, 6 mm play round each Ø22
  nut) with M3 rivnuts; printed GX plates carry the sockets (nut seat stops turning) and screw on from the front.
  Inspector shows the chamfered plates. Small trapezium window (`CTRL_WIN`: 96 × 40, left end 40°, right end square).
- Control lid top: no window (removed 2026-10-12); 4 corner accessory holes only.
- Accessory holes: plain Ø5 (M3 rivnut set later, or a printed plug). Control lid top: 4 corners. GX16 rail centred.
- Body flats are mirrored left-right (`mirror_x`): the shop reads the drawing from the inside face and folds UP,
  which mirrors the design frame. Found 2026-10-12 by `fold.py`; v1–v3 body DXFs would have folded mirrored.

## Files

| Path | Role |
|---|---|
| `hardware/sheet/enclosure.py` | **The single source.** Dimensions, flats, holes, folds, checks, DXF writer, and it writes the numbers into the inspector. `python3 hardware/sheet/enclosure.py` (`--report` = checks only). |
| `hardware/sheet/assembly_check.py` | Whole-assembly clearance: steel-to-steel gaps (≥ 2 mm unless a listed contact), lid fit, parts, fans, rivnuts, plate, feet, pegs. The generator refuses to write files on any clash. |
| `hardware/sheet/strokes.py` + `mark_etch.json` | ETCH mark outlines and the rejected brush strokes. **Unused** by the generator since 2026-10-12. |
| `hardware/sheet/fold.py` | Folds the DXFs as the shop will (real R1 bends, from the files alone), checks hole positions (no mirroring), sizes, self-collision, whole-assembly overlap, and lid/tab fit for shop radii R0.6–R2.5. Writes `out/fold/assembly.glb` + STLs for Blender. Run by `enclosure.py`; needs `pip install trimesh manifold3d mapbox_earcut scipy`. |
| `hardware/sheet/pack.py` | Fabricator cover sheet PDF + zip: `python3 hardware/sheet/pack.py v4`. |
| `hardware/web/enclosure_inspector.html` | **The 3D renderer.** Reads the generator's `GEN` block (walls, panels, fans, plate, stack). |
| `hardware/cutfiles/2026-10-12 v4/` | **Released pack** (6 steel/Al parts + 3 acrylic, cover PDF, zip), shared with the vendor via Drive (R04 Outputs). v1–v3 superseded (v3 bodies folded mirrored). |

## Using the renderer in another chat

Published at https://claude.ai/artifact/DqabBr8QGaitg9eDwsvwex (private; v11). To change it:
1. Edit `enclosure.py` (or the inspector's drawing code), run `python3 hardware/sheet/enclosure.py` —
   it rewrites the `GEN` block in the inspector, so the 3D view always matches the cut files.
2. Republish: from a new chat, publish `hardware/web/enclosure_inspector.html` with
   `url = https://claude.ai/artifact/DqabBr8QGaitg9eDwsvwex` (read it first) to keep the same link.
3. Local check: Chromium headless shell + three@0.128.0 from npm (the CDN is blocked in the container);
   `camera` and `controls` are globals, so a script can set any view.

## Status (2026-10-12)

- Steel cut pack v4 sent to the vendor. Base plates: Allwin will get them in **1 mm 304 or 2 mm mild steel, not aluminium**
  (model still assumes 2 mm; 1 mm SS over 205 × 255 standoff spans will flex under the PSUs; mild steel needs plating or paint).
- Next: the 3D printed parts.

## Mains panel (power box left wall, printed 150 × 85 over the 130 × 65 cut) — parts chosen 2026-10-13

- 3-in-1 IEC C14 module (inlet + 5×20 fuse + lit rocker), snap-in, flange 50 × 30, cutout ~47.5 × 27.5 (confirm by
  coupon); clips want a 1–2 mm panel, so the print thins to 1.5 mm round it. Check the rocker is double-pole; fit a
  slow-blow T3.15–T4 A fuse.
- 2 × 12 mm 12–24 V green metal LEDs (Ø12 holes), stacked: one on 24 V, one on 12 V.
- LA38-11ZS latching stop: Ø22 hole, Ø29.6 head, 50.7 deep behind the face, block 42 × 29.5; NC contact in series with
  mains after the switch. Check its AC rating covers both supplies (~2–2.5 A at 230 V). Depth may touch the 24 V PSU
  placeholder (~60 mm from the wall): re-check when the PSUs are placed.
- Lofi: https://claude.ai/artifact/ALg9yatCVH13EWULpcy4EN

## Later (parked)

- Window lighting: status colours (12 V WS2811 strip, data from a spare FluidNC pin via a level shifter: idle /
  plotting / alarm). Own branch off the 12 V splitter, not the servo buck's input; check the 12 V PSU's rating
  first (est. load ~2.3 A with servo stall). Strip clips go in the bezel prints.
- Spare 6x capabilities, ports later if needed: 3 more motor outputs (one more GX16 in a reprinted plate), 6 spare
  inputs (feed hold / start / reset buttons, probe, lid switch), 2 × 3 A MOSFET outputs (window LEDs), microSD
  (extension to a printed panel). Steel stays as is; a bigger USB cutout (~110 × 30) was offered and skipped.
- Bezel and GX plate prints (Allwin will split the long ones); nut seat for GX sockets once nut sizes are in.

## Open questions: M5Dial pendant (logged 2026-10-12)

- Power the M5Dial from 12 V (it takes 6–36 V DC), not the board's 5 V. Only TX/RX come from the board.
- Socket: GX16 on the USB panel (cutout now 80 × 30, plate 100 × 50, centred z = -45). Pin count: GX16-7 proposed,
  so it cannot mate the servo's GX16-4. Undecided.
- Elecrow FluidDial RJ12 protection module (diodes + series resistors) between board and socket: recommended.
- 6x expansion-socket pinout for TX/RX: not verified.
- Pendant box (lofi https://claude.ai/artifact/9ojddVq95ED7KYcvP6qGKG): 1 mm 304 top 90 × 110 with a 34 mm bent lip
  holding a GX16, 3 mm Al base, 4 × M3 35 mm standoffs. Needs the M5Dial body diameter (48 is a placeholder) and its
  back fixing points before it goes in the model.

## Open before cutting

1. ~~Issue cut pack v4~~ done 2026-10-12.
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
- **Fold the files, not the model.** Every check passed on the model while the body DXFs folded mirrored. Now `fold.py` folds the DXFs and compares.
- **Every bend end needs a relief** (checked; mutation-tested by removing the reliefs).
- **Mutation-test the checks:** break a value on purpose and confirm the gate fails.

## Learnings (working with Allwin on this)

- Short, crisp messages. Discuss before building; show a preview before wiring anything in.
- Ask before adding components. "Tell, don't do" when he asks a question.
- Aesthetics: he leads. Rejected: full-face inlay/marquetry, corner emblems, hex-hole fades, brush-stroke
  waves. Kept: clean steel, original vents, one bold mark (Orbitron Black). Offer one restrained idea,
  not a gallery; never fill a face.
