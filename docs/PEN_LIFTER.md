# Pen lifter

_Started 2026-10-14. Lofi layout in the inspector, nothing printed yet._

## The idea

Modelled on the AxiDraw pen lift (gravity down, servo only lifts, stock horn under a lip, moving rods through a
fixed block), with Etch's swappable magnetic pen plate added.

- **Moving rods, fixed block.** The moving stage is a pen carrier at the bottom and a bridge at the top, joined by
  Allwin's two rods (Ø3.92 × 79, measured, 28 mm apart). The rods press into the carrier and the bridge. They
  slide through a 25 mm fixed block on the bracket: a round bore on one rod locates the stage, and a slot on the
  other only stops it turning, so rods that aren't perfectly parallel can't bind it. A gravity-only stage must
  never bind.
- **Gravity puts the pen down.** No spring. The pen-down force is the stage's weight, about 70 g (estimate; weigh
  it). Add weight to a plate for pens that need more, or a light spring for ballpoints, as AxiDraw's brushless
  kit does.
- **A 9 g servo only lifts.** An SG90 or MG90S (same body, one cradle) lies on top of the block between the rods,
  shaft facing out. Its stock single-arm horn sits 1.5 mm under a lip that hangs down from the bridge at pen
  down (AxiDraw recommends 1–2 mm), so the servo holds nothing. Turning about 32° lifts the stage 4 mm. The MG996R
  is out: it doesn't fit, and its ~2.5 A start-up spike is what the board can't take.
- **Switch reads, never stops.** A microswitch over the bridge, between the rods. The bridge meets its lever
  0.5 mm before full lift, and the lever's over-travel takes the rest.
- **Pick face, pen plate, docks.** Every pen gets a plate with the same outline: a grub-screw clamp, 4 × Ø6
  magnets, and two 90° ridges in an L. Docks catch the plate's flanges; the head slides a plate in along X at
  pen-up height and backs off in −Y.

The head is 44 mm wide and its top stands ~140 mm above the paper. The pen sits 41 mm from the carriage face. It
bolts to the ACRO front plate's 31 mm M3 square if ACRO goes ahead; otherwise only the bracket's back changes.

### How we got here (2026-10-14)

1. A horizontal parallel-leaf flexure pushed the pen ~85 mm out on four thin cantilevers. Dropped.
2. A vertical stack of printed loop springs was liked, but the spring force loads the servo at pen up.
3. A folded-beam suspension (frictionless, no play) made the head 114 mm wide. Dropped as too wide.
4. Fixed rods, a shuttle on printed bushings, and a toggle crank, then a swappable MG90S/MG996R bay. The bay
   above the rod tips made the head ~170 mm tall.
5. **AxiDraw-style (this).** Moving rods through a fixed block, a stock horn under a lip, and one 9 g servo.
   Compact again, and the servo sits where AxiDraw puts it.

## Numbers (estimates until measured)

| Quantity | Value | Source |
|---|---|---|
| Lift | 4 mm | chosen |
| Moving weight = pen-down force | ~70 g | **estimate**: carrier, rods (~15 g), bridge, plate, pen. Weigh it |
| Servo torque while lifting | ~0.07 kg·cm | estimate: 0.7 N × 10 mm horn |
| 9 g servo rating | ~1.6–1.8 kg·cm | catalogue |
| Horn gap at pen down | 1.5 mm | AxiDraw forum: 1–2 mm |

The old lift carried a ~400 g Ender carriage on a 30 mm crank: about 1.2 kg·cm. Less torque means less servo
current, and current is what resets the board.

## Fit kit coupons (hardware/parts/fit_kit.py, `python3 hardware/parts/fit_kit.py P`)

- **J rod fits (for the Ø3.92 rods).** Block bores at 3.95 / 4.00 / 4.05 / 4.10, 12 deep: hold the coupon level,
  drop a rod into each, and pick the tightest it slides through under its own weight with no rattle. Press holes
  at 3.80 / 3.85 / 3.90 for the carrier and bridge: pick the tightest a rod presses into by hand and stays in.
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

- ACRO or the current frame: only the bracket's back depends on it.
- Pen capping in the dock, so parked pens don't dry out.
- Whether ~50 g is enough pen pressure for each pen type; add weight to the plate if not.
