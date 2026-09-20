# hardware

Parametric CAD for the machine's physical parts, as Python. Built with
[build123d](https://build123d.readthedocs.io/), which drives the OpenCASCADE
kernel — so these are real solids, not meshes, and export to STEP for anyone
downstream.

Models live here as code for the same reason the G-code conventions live in
`docs/`: so a change is a diff with a reason attached, rather than
`penlift_v4_FINAL.stl`.

## Use it

```sh
pip install -r hardware/requirements.txt

python3 hardware/make.py            # build every part -> hardware/out/
python3 hardware/make.py frame      # just one
python3 hardware/preview.py         # render PNGs to eyeball the result
python3 hardware/profiles.py        # print + plot the frame cross-section
python3 hardware/viewer.py          # build the interactive 3D viewer
python3 hardware/stock.py           # what to buy, and how to cut it
python3 hardware/stock.py 20x20     # just one profile
```

`hardware/out/viewer.html` is a self-contained page — open it in a browser to
orbit the model, toggle parts, and drive the cross bar through its X travel.
It carries no hard-coded dimensions; re-run `viewer.py` after changing
`params.py` and the numbers follow.

`hardware/out/` is generated and git-ignored.

Each part exports:

| File | For |
|---|---|
| `<name>.step` | Real CAD, a machinist, a fabricator. Solid geometry. |
| `<name>.stl` | Slicing and quick viewing. Mesh. |
| `<name>.png` | A shaded preview, from `preview.py`. |

## Layout

| | |
|---|---|
| **`params.py`** | Every shared dimension. Change a number here, not in a part. Values mirroring the root README's machine table are marked `[README]`. |
| **`profiles.py`** | The 20-series T-slot extrusion. `tslot_bar(length, w, h, axis)` is the building block for anything made of extrusion. |
| **`parts/case.py`** | The UN4020 electronics case, its contents, fans and panel connectors. |
| **`parts/deck.py`** | The steel base sheet, plus the plate-deflection maths behind it. |
| **`parts/frame.py`** | The outer 2040 frame. |
| **`parts/cross_bar.py`** | The moving 2020 gantry beam, plus its span/travel/deflection maths. |
| **`parts/assembly.py`** | Frame + cross bar in one coordinate system. |
| **`make.py`** | Builds and exports everything. Add new parts to `_parts()`. |
| **`preview.py`** | PNG renders. Sanity check, not a beauty shot. |
| **`viewer.py`** + **`web/`** | The two viewers. `_common.html` is the shared core; `machine.html` and `case.html` are the pages. `export_web.py` packs the geometry. |
| **`wiring.py`** | Routes the case harness, scores it, and searches for a better layout. |
| **`stock.py`** | Groups every cut list by profile and packs the pieces onto stock bars, kerf included. |

## Conventions

**Units** are mm, matching the machine's `G21`.

**Orientation** matches the root README: standing in front of the table, **+X
right, +Y away from you**, +Z up.

**Datum** is the centre of the frame's outer envelope in X and Y, with
**Z = 0 at the tabletop surface**. The frame no longer sits at Z = 0 — it
stands on the base deck, at `FRAME_BASE_Z` (= `DECK_T`). The writing surface,
the top of the deck, is at Z = `DECK_T`. Parts that
mount to the frame should be modelled in the same coordinate system so an
assembly is just a union.

Note this differs from the *drawing* datum in the root README, which is the
paper's bottom-left in Quadrant I. Machine geometry and drawing geometry are
separate coordinate systems on purpose.

## On the extrusion model

The 2040 cross-section in `profiles.py` is **accurate on the outside** —
envelope, corner chamfers, slot mouth width, slot depth, bore positions — and
**simplified on the inside**. Real vendor profiles differ in the exact shape of
the channel root and the web thickness.

It is right for fit, clearance, and layout. It is not a substitute for the
vendor drawing if you are machining against it, and the slot dimensions vary by
a few tenths between suppliers — **measure yours** before making anything that
has to slide in a slot.

The modelled section comes out at **491 mm² → 1.33 kg/m**, which is in the
right band for 20-series 2040 T-slot. Check it against your supplier's figure;
a large discrepancy means the section needs adjusting.

### The trap this hit

The channel tapers from `SLOT_INNER_W` back down to `SLOT_ROOT_W` at full
depth. That taper is not cosmetic — it is what leaves the diagonal webs joining
each corner of the section to the core. A straight full-width channel severs
them, and the "extrusion" becomes five floating slivers that still export
cleanly to STEP and STL and are silently nonsense.

`_assert_connected()` in `profiles.py` checks the section is one connected face
on every build, so this cannot come back quietly.

## Adding a part

1. New file in `parts/`, with a `build()` returning a solid or `Compound`.
2. Shared dimensions go in `params.py`, not hard-coded.
3. Register it in `make.py`'s `_parts()`.
4. `python3 hardware/make.py <name> && python3 hardware/preview.py <name>`, and
   look at the render.

## Placeholders that must be measured

Two numbers in `params.py` are guesses and are marked `TO CONFIRM`. Every Z
dimension above the frame depends on the first of them:

| | |
|---|---|
| `GANTRY_RISE` | Height from the top of the frame rails to the underside of the cross bar — i.e. the gantry plate and wheel stack. |
| `GANTRY_PLATE_LEN` | Plate footprint along X. Sets how much of the 1000 mm rail is lost to the plate, and therefore the X travel. |

## The base deck is not a flatness device

`parts/deck.py` models a steel sheet across the frame footprint, with the frame
bolted down on top of it. It must be **continuously supported by the tabletop**.
It cannot span the frame opening: `plate_sag()` puts a 1.5 mm sheet at ~13 mm of
sag over the 960 x 560 mm opening under nothing but its own weight, and holding
half a millimetre across that span would take roughly 8 mm of plate — 33 kg.

So the sheet inherits the tabletop's flatness rather than improving on it. What
it does buy is a hard, uniform, non-absorbent surface that will not dent under a
pen nor swell with humidity, protection for the tabletop, and — **only if the
steel is ferritic** — magnetic paper hold-down. 304 and 316 stainless are
austenitic and not meaningfully magnetic; 430 stainless or zinc-plated mild
steel is.

One assembly snag the model does not solve: with the sheet under the frame, the
screw heads land between sheet and tabletop and the machine rocks on them. An
M5 countersink wants ~2.5 mm of depth and a 1.5 mm sheet cannot give it. Either
relieve the tabletop under each head, or drop an opening-sized sheet into the
frame well instead and let the rails retain it.

## The electronics case

`parts/case.py` models a UN4020 hard carry case standing beside the machine.
It replaced an extrusion box when the plan changed; that part is gone rather
than left sitting around looking current.

It runs **closed**, which is why the two 80 mm fans are not optional. Three
TB6600 heatsinks hang fin-down in still air otherwise, and polypropylene
conducts about a thousandth of what aluminium does, so the shell will not help
them. Airflow needed is small — roughly 22–30 CFM of fan rating covers 50 W at
a 10 °C rise once derated for grille and filter — so 24 V axials off the
existing bus do the job and keep more mains out of the box.

### The lane

The lid is laid out around a clear channel down the middle. It is not spare
space — it is what makes the wiring short:

- **Drivers hard against the hinge edge**, so the heavy 24 V conductors cross
  the hinge and land immediately, without running the length of the lid.
- **Board opposite**, with its ports facing down into the lane.
- **Every panel connector drops into the lane**, ordered so each lands beside
  what it wires to: USB and endstops at the board end, each stepper connector
  opposite its own driver.

Nothing then has to route over the top of a driver or across the board.

The connectors are also the reason the lane has to exist at all. A panel-mount
GX16 hangs about 25 mm into the bay, and a TB6600 is 57 mm tall, so a connector
simply cannot sit above a driver. `check_layout()` counts connector bodies and
fans as bay-occupying parts for exactly this reason.

Airflow runs diagonally: intake low in the base at the cool end, exhaust in the
**lid** at the driver end, so the air leaving is the hottest air in the box.
That costs two conductors across the hinge, which is worth it.

### The wiring is routed, not eyeballed

`wiring.py` models every bundle in the lid — source, destination, conductor
count, kind — routes each as an L, and scores the result on four things:

| | |
|---|---|
| **obstruction** | a bundle crossing a component it doesn't belong to. The hard failure: you can't route through a TB6600. |
| **crossing** | two bundles crossing each other — a place something must lift over something else. |
| **separation** | mains or motor phase running alongside a signal bundle. |
| **length** | conductor-millimetres, with a tighter budget on lines that care. |

```sh
python3 hardware/wiring.py            # report the current layout
python3 hardware/wiring.py --search   # try board positions and connector orders
```

Geometry comes from `case.py`, so the analysis can't drift from the model, and
the routed paths are fed back into the viewer as 3D tubes — coloured by kind,
sized by conductor count. **The harness you see is the harness that was
scored**, not a drawing of one.

**Re-run the search after moving anything.**

It has already earned its keep. The first layout scored 20331 with two
obstructions; the current one scores 386 with none, and uses a fifth less wire.
What it found was that the *board position* was the problem, not the connector
order — moving the board from y −120 to y +60, up beside the drivers it talks
to, fixed most of it.

Three things it caught that eyeballing missed:

- **Connector bodies are obstacles.** A panel-mount GX16 hangs ~25 mm into the
  bay. Leaving them out of the model let routes pass straight through the lane.
- **A TB6600 has two terminal blocks.** Treating it as one point made every
  step/dir bundle look like it ran alongside its own motor phases.
- **The hinge is an edge, not a point** — power can cross anywhere along it.
- **A component is not a point either.** Three bundles all leaving the exact
  centre of one edge is what made the harness look like spaghetti — they left
  from the same place and overlapped for their whole first leg. Each attachment
  now gets its own terminal, spread along the face that points at its
  destination and ordered by where it's headed, so wires don't cross each other
  the moment they leave a part.
- **One run height is not a harness.** Every bundle shared a single Z, so
  sixteen runs sat in the same plane and overlapped wherever their paths
  agreed. The router has already proved nothing is in the way at any height
  along a route, so the bay depth is free: bundles now spread through a 34 mm
  band in lanes, sorted by kind, which is what you'd do with a real loom.
- **Ports face what they're wired to.** Pointing every terminal at the lid's
  lane made base parts route out of their far side and back through their own
  neighbours.
- **A router that can only turn one corner isn't a router.** Where two ends
  share a coordinate there's exactly one possible L, so anything sitting on it
  was reported as unroutable. Z-shaped detours let it go around, which is what
  a person would obviously do.

The base got the same treatment and needed it more: the servo PSU sat
diagonally opposite the IEC inlet, a 460 mm mains run that crossed both DC
rails. Mains are now clustered in one corner — inlet and both PSU inputs
together — and the 220 V stays out of the DC half entirely.

And one thing the *optimiser* got wrong before the objective was fixed: it
parked the servo PWM 274 mm away, because a single conductor scores cheap.
That line is single-ended and timing-critical, and `FINDINGS.md` §7 is a long
argument about the servo being marginal. USB is differential and doesn't care
about length; the servo does. They now have separate budgets.

### There is no 5 V rail

The Elecrow board regulates its own 5 V (500 mA) and 3.3 V (100 mA) from VMot,
so the external 5 V buck and bus would have fed nothing. Both are gone. The
only conversion left in the case is 24 V → 6.0 V for the servo, which is its
own supply for the reasons in `FINDINGS.md` §7.

Contents are stand-in blocks at real outside sizes. Not modelled: wiring, the
sub-plate the lid parts want to mount to, the switches, and the shell's moulded
detail.

## V-slot vs T-slot

`profiles.py` models a **T-slot** section. OpenBuilds gantry wheels need a
**V-slot** — a 45° groove the wheels run in. If the machine uses OpenBuilds
plates, the rails and the cross bar must both be V-slot extrusion; the wheels
have nothing to grip on the profile modelled here.

Envelope, slot positions, bore centres and fit are the same either way, so the
layout and cut lists hold. Only the wheel running surface is missing.
