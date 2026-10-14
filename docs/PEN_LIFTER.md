# Pen lifter

_Started 2026-10-14. Lofi layout agreed for inspection, nothing printed yet._

## The idea

The reference is a build Allwin shared (photos, not in the repo). On Etch's flat bed it works like this:

- **A loop spring in line with the lift.** Three printed oval loops are stacked on top of the shuttle, joined
  only at their middles, under a shelf on the bracket. Lifting the pen squashes them by 4 mm; they spring back
  and put the pen on the paper. The shuttle runs in a printed vertical guide on the bracket, which keeps the pen
  about 37 mm from the carriage face.
  (A first draft used horizontal parallel leaves. That pushed the pen ~85 mm out on four thin cantilevers, and
  the spring did not act along the lift. Dropped.)
- **Pick face and pen plate.** The shuttle carries a pick face. Each pen is clamped by a grub screw into its own
  pen plate. Every plate has the same outline and hangs on the pick face by 4 × Ø6 magnets, and two 90° ridges in
  an L locate it in X and Z.
- **Servo lifts, never holds a stop.** The servo arm lifts the shuttle by a tab from below. At pen down the arm
  drops 1.2 mm clear of the tab, so the pen lands on the spring and its own weight, and the servo holds
  nothing. At pen up it holds only the squashed spring and the plate. There is no hard stop anywhere in its travel,
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
| Spring | 3 loops, 40 long × 8 high × 8 deep, 0.6 / 0.8 / 1.0 thick, 30 mm free height | coupon J picks |
| Force at 4 mm squash | 0.6: 30–115 g · 0.8: 70–270 g · 1.0: 130–530 g | **estimate**, PETG E ≈ 2 GPa; loop ends somewhere between pinned and fixed, hence the range |
| Loop strain at 4 mm | 0.2–0.4 % | estimate; PETG is comfortable under 1 % |
| Servo torque at 4 mm, 8 mm arm | up to ~0.4 kg·cm with 1.0 loops, plus the plate and pen | estimate; an MG90S is rated ~1.8 kg·cm |
| Pen-down force | plate + pen + shuttle weight; add preload by lowering the shelf | to tune on paper |

The servo torque row is the point of the design: the old lift carried a ~400 g Ender carriage on a 30 mm crank and
needed ~1.2 kg·cm. Less torque means less servo current, and current is what resets the board.

## Fit kit coupons (hardware/parts/fit_kit.py, `python3 hardware/parts/fit_kit.py P`)

- **J spring 0.6 / 0.8 / 1.0.** Stand it on a kitchen scale and press the top bar down. The reading just before
  the bar lands on its two stop posts is the force at 4 mm of squash. It should spring straight back.
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
- Plate weight, i.e. the pen-down force: the spring adds preload if the shelf is lowered, and the plate sets the rest.
