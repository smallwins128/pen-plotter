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
python3 hardware/profiles.py        # print + plot the 2040 cross-section
```

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
| **`parts/frame.py`** | The outer 2040 frame. |
| **`make.py`** | Builds and exports everything. Add new parts to `_parts()`. |
| **`preview.py`** | PNG renders. Sanity check, not a beauty shot. |

## Conventions

**Units** are mm, matching the machine's `G21`.

**Orientation** matches the root README: standing in front of the table, **+X
right, +Y away from you**, +Z up.

**Datum** for the frame is the centre of its outer envelope in X and Y, with
**Z = 0 at the tabletop surface** (the underside of the rails). Parts that
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
