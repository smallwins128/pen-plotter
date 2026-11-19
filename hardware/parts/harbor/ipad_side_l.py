"""R05 Harbor: iPad sleeve, LEFT side clip v2 (2026-11-02). Only this part gets printed; the v1 right side clip and
the two bottom clips are printed and hold.

v1's left clip had no purchase: its lug sat at the clip's top end and flush with its outer face, so nothing in front
of the board clamped it against the lip behind. v2 puts a flange round the slot like the rail hook's (skadis_rail.py):
the clip covers the board 3 mm past the slot's outer side, 3 mm above the slot's top, and from the slot's floor down
to the lip's bottom (6 mm). Inner side: the iPad's back covers the board 1.7 mm past the slot, so the flange stops
there. Its bottom is level with the lip's bottom, so it prints upright like the hook.

    LEFT SIDE v2   24 tall (z 160-184 above the board datum, i.e. 125-149 above the iPad's bottom edge),
                   12.7 wide seen from the front (9.7 wall outside the iPad's edge + 3 lip over the bezel).

    python3 ipad_side_l.py      # checks, then out/harbor/ipad_side_l_v2.stl (print orientation)

Frame, iPad and slot grid as ipad_sleeve.py. Lug: even column x = -120, slot 166-181 (v1's slot).
Print: upright as modelled (bottom end on the bed, lip on the bed too); the neck bridges 5.4 mm, as on the hook.
"""
import sys

from build123d import Pos, export_stl

from ipad_sleeve import (CLR, IPAD, LEAD, LIP_OVER, OUT, X0, XL, Y_FRONT, ZB, board_piece, bottom_l, box, lead_in,
                         lug, mirrored, outline, pocket, slot_floor_ok, LUGS)
from skadis_rail import BOARD

LUG_X, FLOOR = -120.0, 166.0
SLOT = (LUG_X - BOARD["slot_w"] / 2, LUG_X + BOARD["slot_w"] / 2, FLOOR, FLOOR + BOARD["slot_h"])
FLANGE_PAST = 3.0                                    # past the slot's outer side and top, as on the hook
Z0 = FLOOR - 6.0                                     # 160: level with the lip's bottom (prints on the bed)
Z1 = SLOT[3] + FLANGE_PAST                           # 184
XO = SLOT[0] - FLANGE_PAST                           # -125.5: outer face


def side_l_v2():
    part = outline([(XO, Z0), (XL + LIP_OVER, Z0), (XL + LIP_OVER, Z1), (XO, Z1)], {0: 1.5, 1: 1.5, 2: 1.5, 3: 1.5},
                   0.0, Y_FRONT)
    part -= pocket()
    part -= lead_in(XL, Z1, +1)
    part += lug(LUG_X, FLOOR)
    return part


def vol(a, b):
    try:
        return (a & b).volume
    except Exception:
        return 0.0


def flange(part):
    """How far the clip covers the board face (y = 0) past each side of the slot."""
    face = lambda x0, x1, z0, z1: box(x0, x1, -0.01, 0.3, z0, z1)
    out = {}
    for name, f, key in (("outer", face(SLOT[0] - 15, SLOT[0], SLOT[2], SLOT[3]), lambda b: SLOT[0] - b.min.X),
                         ("inner", face(SLOT[1], SLOT[1] + 15, SLOT[2], SLOT[3]), lambda b: b.max.X - SLOT[1]),
                         ("above", face(SLOT[0], SLOT[1], SLOT[3], SLOT[3] + 15), lambda b: b.max.Z - SLOT[3]),
                         ("below", face(SLOT[0], SLOT[1], SLOT[2] - 15, SLOT[2]), lambda b: SLOT[2] - b.min.Z)):
        try:
            out[name] = max(0.0, key((part & f).bounding_box()))
        except Exception:
            out[name] = 0.0
    return out


def main():
    import numpy as np, trimesh
    ok = slot_floor_ok(LUG_X, FLOOR)
    print(f"lug slot: column {LUG_X:.0f}, floor {FLOOR:.0f}: {'ok' if ok else 'NOT A SLOT'}")
    part = side_l_v2()
    board = board_piece(-150, -60, 140, 200)
    ipad = box(X0 - IPAD["w"] / 2, X0 + IPAD["w"] / 2, 0.0, IPAD["t"], ZB, ZB + IPAD["h"])
    v = vol(part, board), vol(part, ipad)
    print(f"seated: vs board {v[0]:.3f} mm3, vs iPad {v[1]:.3f} mm3")
    ok &= max(v) < 0.01
    path = [(12 - 0.5 * i, 6.5) for i in range(25)] + [(0.0, 6.5 - 0.5 * i) for i in range(14)]
    worst = max(vol(Pos(0, dy, dz) * part, board) for dy, dz in path)
    print(f"hang it: push in 6.5 mm high, then drop: worst overlap {worst:.3f} mm3")
    ok &= worst < 0.05
    bl = bottom_l()
    for x, zn in LUGS["bottom_l"]:
        bl += lug(x, zn)
    worst = max(vol(Pos(0, 0, dz) * ipad, part + bl) for dz in range(0, 230, 1))
    print(f"iPad drops in past it onto the bottom-left clip: worst overlap {worst:.3f} mm3")
    ok &= worst < 0.05
    fwd = vol(Pos(0, 1, 0) * box(XL + CLR, XL + 10, 0, IPAD["t"], Z0, Z1), part)
    print(f"iPad's left edge held: 1 mm forward hits the lip {fwd:.1f} mm3")
    ok &= fwd > 1
    f = flange(part)
    print("flange in front of the board round the slot (hook: 3 mm):", ", ".join(f"{k} {v:.1f}" for k, v in f.items()),
          "(inner limited by the iPad: 1.7)")
    ok &= f["outer"] >= 3 and f["above"] >= 3 and f["below"] >= 6 and f["inner"] >= 1.6
    ok &= len(part.solids()) == 1
    OUT.mkdir(parents=True, exist_ok=True)
    export_stl(part, str(OUT / "_sl.stl"))
    m = trimesh.load(str(OUT / "_sl.stl"))
    (OUT / "_sl.stl").unlink()
    m.apply_translation(-m.bounds[0])
    nz, zc = m.face_normals[:, 2], m.triangles_center[:, 2]
    over = m.area_faces[(nz < -0.71) & (zc > 1.2)].sum()
    print(f"print upright: {m.extents.round(1)} mm, {m.volume / 1000:.1f} cm3, down-facing {over:.1f} mm2 "
          f"(neck bridge: {4.4 * 5.4:.1f})")
    ok &= over < 4.4 * 5.4 + 0.5
    m.export(str(OUT / "ipad_side_l_v2.stl"))
    export_stl(part, str(OUT / "ipad_side_l_v2_assembly.stl"))
    print("ALL CHECKS PASS" if ok else "CHECKS FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
