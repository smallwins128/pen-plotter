# Pen lifter

_Started 2026-10-14. Lofi layout in the inspector, nothing printed yet._

## The idea

Allwin's pen guide and holder (`hardware/ref/pen_guide/`, as downloaded; the source isn't recorded) with Etch's
swappable magnetic pen plate in place of the holder's pen clamp. It works the same way as the AxiDraw lift:
gravity down, the servo only lifts, a stock horn under a tab.

- **Guide (fixed).** 40 × 70 × 28 mm, bolted flat to the carriage. 4 M3 holes on the ACRO 31 mm square are added
  to its base. Its two end walls hold Allwin's rods (Ø3.92 × 79, measured) 30 mm apart and 23 mm out from the
  carriage. The rods press into the end walls and jut 9 mm out of the top.
- **Holder (moving).** Two 5 mm wings, 40 mm apart, ride the rods: a round bore on one rod and a slot on the
  other, so it can't bind. The guide gives it ~9 mm of free travel. The pen uses 4, leaving 3 mm below pen down
  and 2.2 mm above pen up. The wings carry the pick face, where the original holder had its 14 mm square pen
  clamp.
- **Gravity puts the pen down.** No spring. The pen-down force is the holder, pick face, plate and pen, about
  45 g (estimate; weigh it).
- **A 9 g servo only lifts.** An SG90 or MG90S sits in the guide's open-sided pocket. Its tabs screw to the
  guide's side face (the original's two Ø1.8 pilot holes, 28 mm apart), and the body sticks out of the side
  about 13 mm. Its stock horn points out from the carriage and sits 1.5 mm under a tab on the holder at pen down
  (AxiDraw recommends 1–2 mm), so the servo holds nothing. About 41° of turn lifts the pen 4 mm.
- **Switch reads, never stops.** A microswitch on the guide's side reads a tab on the holder's upper wing. The
  tab meets the lever 0.5 mm before full lift, and the lever's over-travel takes the rest.
- **Pick face, pen plate, docks.** Every pen gets a plate with the same outline: a grub-screw clamp, 4 × Ø6
  magnets, and two 90° ridges in an L. Docks catch the plate's flanges; the head slides a plate in along X at
  pen-up height and backs off in −Y.

The head is 40 mm wide plus the servo sticking out 13 mm. The pen sits 47 mm from the carriage face; the
original holder put it 37 mm out, and the magnetic interface costs the other 10.

### How we got here (2026-10-14)

1. A horizontal parallel-leaf flexure pushed the pen ~85 mm out on four thin cantilevers. Dropped.
2. A vertical stack of printed loop springs was liked, but the spring force loads the servo at pen up.
3. A folded-beam suspension (frictionless, no play) made the head 114 mm wide. Dropped as too wide.
4. Fixed rods, a shuttle on printed bushings, and a toggle crank, then a swappable MG90S/MG996R bay. The bay
   above the rod tips made the head ~170 mm tall.
5. AxiDraw-style: moving rods through a fixed block, a stock horn under a lip, and one 9 g servo.
6. **Allwin's guide + holder (this).** Fixed rods in a guide, the holder on the rods, and a 9 g servo in the
   guide's pocket; the holder carries the magnetic pick face. The re-draw matches the downloaded STLs (the
   inspector's "Reference" layer overlays them).

## Numbers (estimates until measured)

| Quantity | Value | Source |
|---|---|---|
| Lift | 4 mm | chosen |
| Moving weight = pen-down force | ~45 g | **estimate**: holder, pick face, plate, pen. Weigh it |
| Servo torque while lifting | ~0.04 kg·cm | estimate: 0.45 N × 8 mm horn |
| 9 g servo rating | ~1.6–1.8 kg·cm | catalogue |
| Horn gap at pen down | 1.5 mm | AxiDraw forum: 1–2 mm |

The old lift carried a ~400 g Ender carriage on a 30 mm crank: about 1.2 kg·cm. Less torque means less servo
current, and current is what resets the board.

## Fit kit coupons (hardware/parts/fit_kit.py, `python3 hardware/parts/fit_kit.py P`)

- **J rod fits (for the Ø3.92 rods).** Bores at 3.95 / 4.00 / 4.05 / 4.10, 12 deep, for the holder's wings: hold
  the coupon level, drop a rod into each, and pick the tightest it slides through under its own weight with no
  rattle. Press holes at 3.80 / 3.85 / 3.90 for the guide's end walls: pick the tightest a rod presses into by
  hand and stays in. (The original STLs use 4.3 in the holder and 4.2 in the guide: loose on 3.92 rods.)
- **K pick face + pen plate.** Press magnets in using coupon I's pocket size, N out on the face and S out on the
  plate. Check it seats with no rock, and hang weights to find the pull-off force.
- **L channel 0.2 / 0.3 / 0.4.** Slide the K plate's flange in. Pick the tightest that runs free by hand.

## To buy

- Rods: have them (2 × Ø3.92 × 79)
- Servo: a 9 g SG90 or MG90S (have an MG90S? measure it; the cradle is sized from catalogue figures)
- 1 × mini microswitch with lever

## Inspector

`hardware/web/parts_inspector.html` reads `pen_lifter.b64.txt`, which `python3 hardware/parts/pen_lifter.py`
writes. Published at https://claude.ai/artifact/2nnKKDM45tAEsGvKrvWk6a (private). To update it from a new chat,
run the generator, then publish the page with `files = {pen_lifter.b64.txt: ...}` and that URL (read it first).
The page is generic: point its `parts-data` meta at any bundle that `web_bundle.pack()` writes.

## Open

- ACRO or the current frame: only the guide's mounting holes depend on it.
- Pen capping in the dock, so parked pens don't dry out.
- Whether ~50 g is enough pen pressure for each pen type; add weight to the plate if not.
