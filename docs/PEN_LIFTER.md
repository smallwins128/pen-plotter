# Pen lifter

_Started 2026-10-14. Lofi layout agreed for inspection, nothing printed yet._

## The idea

The reference is a build Allwin shared (photos, not in the repo). On Etch's flat bed it works like this:

- **Flexure, not a slide.** A printed parallel-leaf flexure (two pairs of leaves, top and bottom) carries a
  shuttle straight up and down. The pen stays square to the paper, and there is nothing to bind or wear.
- **Pick face and pen plate.** The shuttle carries a pick face. Each pen is clamped by a grub screw into its own
  pen plate. Every plate has the same outline and hangs on the pick face by 4 × Ø6 magnets, and two 90° ridges in
  an L locate it in X and Z.
- **Servo lifts, never holds a stop.** The servo arm lifts the shuttle by a tab from below. At pen down the arm
  drops 1.2 mm clear of the tab, so the pen lands under its own weight plus the flexure, and the servo holds
  nothing. At pen up it holds only the flexure and the plate. There is no hard stop anywhere in its travel,
  which is the FINDINGS 7b rule.
- **Switch reads, never stops.** A microswitch reads pen up from a second tab. The tab meets the lever 0.5 mm
  before full lift, and the lever's over-travel takes the rest.
- **Docks.** A rail top and bottom catches the plate's flanges, with a lip on the carriage side. The head slides a
  plate in along X at pen-up height and backs off in −Y, which breaks the magnets. Pickup is the reverse.

The head bolts to the ACRO front plate's 31 mm M3 square if ACRO goes ahead. Otherwise only the mount bracket
changes.

## Numbers (estimates until the fit kit measures them)

| Quantity | Value | Source |
|---|---|---|
| Lift | 4 mm | chosen |
| Flexure leaves | 8 leaves, 10 wide × 40 long, 0.6 / 0.8 / 1.0 thick | coupon J picks |
| Flexure stiffness | 0.22 / 0.51 / 1.0 N/mm, i.e. 88 / 209 / 408 g at 4 mm | **estimate**, PETG E ≈ 2 GPa |
| Leaf strain at 4 mm | 0.45–0.75 % | estimate; PETG is comfortable under 1 % |
| Servo torque at 4 mm, 8 mm arm | 0.07–0.33 kg·cm, plus the plate and pen | estimate; an MG90S is rated ~1.8 kg·cm |

That last row is the point of the design: the old lift carried a ~400 g Ender carriage on a 30 mm crank and
needed ~1.2 kg·cm. Less torque means less servo current, and current is what resets the board.

## Fit kit coupons (hardware/parts/fit_kit.py, `python3 hardware/parts/fit_kit.py P`)

- **J flexure 0.6 / 0.8 / 1.0.** Stand it on the fixed block's foot on a kitchen scale and press the shuttle down.
  The reading just before the foot lands is the force at 4 mm. Pick the thinnest one that feels steady sideways.
- **K pick face + pen plate.** Press magnets in using coupon I's pocket size, N out on the face and S out on the
  plate. Check it seats with no rock, and hang weights to find the pull-off force.
- **L channel 0.2 / 0.3 / 0.4.** Slide the K plate's flange in. Pick the tightest that runs free by hand.

## Inspector

`hardware/web/parts_inspector.html` reads `pen_lifter.b64.txt`, which `python3 hardware/parts/pen_lifter.py`
writes. Published at https://claude.ai/artifact/2nnKKDM45tAEsGvKrvWk6a (private). To update it from a new chat,
run the generator, then publish the page with `files = {pen_lifter.b64.txt: ...}` and that URL (read it first).
The page is generic: point its `parts-data` meta at any bundle that `web_bundle.pack()` writes.

## Open

- ACRO or the current frame: only the mount bracket depends on it.
- Servo: MG90S-class (small current, the point of the design) or the MG996R already fitted.
- Pen capping in the dock, so parked pens don't dry out.
- Plate weight, i.e. the pen-down force: the flexure adds some and the plate sets the rest.
