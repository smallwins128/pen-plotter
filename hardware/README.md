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
| **`parts/deck.py`** | The steel base sheet, plus the plate-deflection maths behind it. |
| **`parts/frame.py`** | The outer 2040 frame. |
| **`parts/cross_bar.py`** | The moving 2020 gantry beam, plus its span/travel/deflection maths. |
| **`parts/assembly.py`** | Frame + cross bar in one coordinate system. |
| **`make.py`** | Builds and exports everything. Add new parts to `_parts()`. |
| **`preview.py`** | PNG renders. Sanity check, not a beauty shot. |
| **`viewer.py`** + **`web/`** | The interactive 3D viewer. `export_web.py` packs the geometry. |
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

## V-slot vs T-slot

`profiles.py` models a **T-slot** section. OpenBuilds gantry wheels need a
**V-slot** — a 45° groove the wheels run in. If the machine uses OpenBuilds
plates, the rails and the cross bar must both be V-slot extrusion; the wheels
have nothing to grip on the profile modelled here.

Envelope, slot positions, bore centres and fit are the same either way, so the
layout and cut lists hold. Only the wheel running surface is missing.
