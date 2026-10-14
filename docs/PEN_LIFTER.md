# Pen lifter

_Started 2026-10-14. Lofi layout in the inspector, nothing printed yet._

## The idea

- **Two smooth rods, printed bushings.** Allwin's rods (Ø3.92 × 79, measured) stand 28 mm apart. They press
  snug into an 8 mm bottom ear, pass through the top ear, and jut 33 mm above it. The bushings are printed into
  the shuttle and run its full 32 mm height, so it can't rock. One rod gets a round bore, which locates the
  shuttle. The other gets a slot, which only stops it turning, so rods that aren't perfectly parallel can't bind
  it. LM4UU bearings were dropped: they're made for 4.00 mm shafts, and on 3.92 rods they'd have ~0.04 mm play
  per side, a couple of tenths of a millimetre at the pen tip.
- **Gravity puts the pen down.** No spring. The pen-down force is the weight of shuttle, bearings, pick face,
  plate and pen, about 50 g (estimate; weigh it). To press harder, add weight to the plate.
- **The servo only lifts.** An MG90S-size servo lies on its side above the top ear, between the rods. It
  turns a 3.5 mm toggle crank whose pin sits in a window on the shuttle:
  - at pen down (−30°) the pin hangs 1.1 mm clear of the window's top edge, so the servo holds nothing
    (FINDINGS 7b)
  - it meets the edge at −10° and lifts 4 mm by +80°
  - at pen up the pin is nearly over the shaft, so the weight it holds has only 0.6 mm of lever
- **Switch reads, never stops.** A microswitch sits over the window plate. The plate meets the lever 0.5 mm
  before full lift, and the lever's over-travel takes the rest.
- **Pick face, pen plate, docks.** Unchanged. Every pen gets a plate with the same outline: a grub-screw clamp,
  4 × Ø6 magnets, and two 90° ridges in an L. Docks catch the plate's flanges; the head slides a plate in along
  X at pen-up height and backs off in −Y.

The head is 48 mm wide, and the pen sits 41 mm from the carriage face. It bolts to the ACRO front plate's 31 mm
M3 square if ACRO goes ahead; otherwise only the bracket's back changes.

### How we got here (2026-10-14)

1. A horizontal parallel-leaf flexure pushed the pen ~85 mm out on four thin cantilevers. Dropped.
2. A vertical stack of printed loop springs was liked, but the spring force loads the servo at pen up.
3. A folded-beam suspension (frictionless, no play) made the head 114 mm wide. Dropped as too wide.
4. **Rods + gravity + lift-only servo (this).** Narrowest, proven, and no spring for the servo to fight.
   Then sized to Allwin's rods: 28 mm apart so the servo fits between them, printed bushings instead of LM4UU.

## Numbers (estimates until measured)

| Quantity | Value | Source |
|---|---|---|
| Lift | 4 mm | chosen |
| Moving weight = pen-down force | ~50 g | **estimate**: weigh shuttle + plate + pen |
| Servo torque, mid-lift peak | ~0.02 kg·cm | estimate: 0.5 N × 3.5 mm |
| Servo torque, pen up | ~0.003 kg·cm | estimate: 0.5 N × 0.6 mm |
| MG90S rating | ~1.8 kg·cm | catalogue |

The old lift carried a ~400 g Ender carriage on a 30 mm crank: about 1.2 kg·cm. Less torque means less servo
current, and current is what resets the board.

## Fit kit coupons (hardware/parts/fit_kit.py, `python3 hardware/parts/fit_kit.py P`)

- **J rod fits (for the Ø3.92 rods).** Bushing bores at 3.95 / 4.00 / 4.05 / 4.10, 12 deep: stand a rod upright,
  drop the coupon over it, and pick the tightest bore that slides down under its own weight with no rattle. Ear
  holes at 3.80 / 3.85 / 3.90: pick the tightest a rod presses into by hand and stays in.
- **K pick face + pen plate.** Press magnets in using coupon I's pocket size, N out on the face and S out on the
  plate. Check it seats with no rock, and hang weights to find the pull-off force.
- **L channel 0.2 / 0.3 / 0.4.** Slide the K plate's flange in. Pick the tightest that runs free by hand.

## To buy

- Rods: have them (2 × Ø3.92 × 79)
- 1 × MG90S (metal gear) servo
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
