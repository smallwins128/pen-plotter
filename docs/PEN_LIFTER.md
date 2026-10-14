# Pen lifter

_Started 2026-10-14. Lofi layout in the inspector, nothing printed yet._

## The idea

- **Two smooth rods, rolling bearings.** The shuttle rides two vertical Ø4 rods, 20 mm apart, inside its own
  32 mm width. Four LM4UU linear ball bearings carry it, two per rod and 6 mm apart. Rolling means next to no
  friction, and two bearings per rod mean it can't rock. The rods are clamped in a bottom and a top ear on the
  bracket.
- **Gravity puts the pen down.** No spring. The pen-down force is the weight of shuttle, bearings, pick face,
  plate and pen, about 50 g (estimate; weigh it). To press harder, add weight to the plate.
- **The servo only lifts.** An MG90S-size servo lies on its side above the top ear, inside the head's width. It
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

The head is 44 mm wide, and the pen sits 37 mm from the carriage face. It bolts to the ACRO front plate's 31 mm
M3 square if ACRO goes ahead; otherwise only the bracket's back changes.

### How we got here (2026-10-14)

1. A horizontal parallel-leaf flexure pushed the pen ~85 mm out on four thin cantilevers. Dropped.
2. A vertical stack of printed loop springs was liked, but the spring force loads the servo at pen up.
3. A folded-beam suspension (frictionless, no play) made the head 114 mm wide. Dropped as too wide.
4. **Rods + gravity + lift-only servo (this).** Narrowest, proven, and no spring for the servo to fight.

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

- **J rod + bearing.** LM4UU bores at 7.9 / 8.0 / 8.1: pick the tightest a bearing goes into by thumb without
  cracking. Ø4 rod holes at 3.9 / 4.0 / 4.1: pick the tightest a rod slides through by hand.
- **K pick face + pen plate.** Press magnets in using coupon I's pocket size, N out on the face and S out on the
  plate. Check it seats with no rock, and hang weights to find the pull-off force.
- **L channel 0.2 / 0.3 / 0.4.** Slide the K plate's flange in. Pick the tightest that runs free by hand.

## To buy

- 2 × Ø4 mm smooth rod, ~50 mm (cut from a longer length)
- 4 × LM4UU linear bearings
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
