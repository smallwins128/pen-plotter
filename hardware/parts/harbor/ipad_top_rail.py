"""R05 Harbor: iPad top clip on the rail hook (2026-11-02, Allwin's option 4).

The thin top caps (ipad_sleeve.py v2-v4) hooked the slot that straddles the iPad's top edge, where the iPad covers the
board in front of the slot: no room for a flange, so nothing clamped the board. This one uses a printed rail HOOK
(skadis_rail.py, unchanged) in the first slot fully above the iPad: the hook's own flange and full lip hold the board.
A plate slides down the hook's rail and sits on the sleeve roof; below the hook it ends in a cap on the iPad's top
edge with a 3 mm lip over the bezel. The foot is notched behind so it passes the hook while sliding down.

    python3 ipad_top_rail.py      # checks, then out/harbor/ipad_top_rail.stl (print orientation)

World frame as ipad_sleeve.py (x along the board, y out, z up; iPad top edge z = 209.1, centre x = 10). The hook goes
in odd column x = 20 (10 right of the iPad's centre), slot floor 226, so the hook's bottom is at 220.
Print: upside down (sleeve roofs on the bed): groove walls vertical, lip grows off the front. No supports.
"""
import sys

from build123d import Pos, export_stl

from ipad_sleeve import IPAD, LIP_OVER, OUT, X0, ZB, board_piece, box, slot_floor_ok
from skadis_rail import BOARD, BOSS, CLR, FLANGE, NECK, PLATE_T, Y_BODY, hook, plate

HOOK_X, HOOK_FLOOR = 20.0, 226.0
ZH = HOOK_FLOOR - NECK["z"]                    # 220: hook bottom (local z = 0)
Z_IPAD = ZB + IPAD["h"]                        # 209.1
GAP = 0.5                                      # cap ceiling over the iPad's edge, seated
W = BOSS["w"]                                  # 18
Y_LIP0, Y_LIP1 = IPAD["t"] + GAP, IPAD["t"] + GAP + 1.6     # lip 8.0 - 9.6, as on the bottom clips
NOTCH = FLANGE["w"] / 2 + 1                    # plate() notches the foot +-6.5 for the hook's flange


def top_clip():
    """In the hook's local frame (hook bottom z = 0, slot column x = 0), as modelled: plate() puts the sleeve roof CLR
    above the rail's top, so seated the plate is CLR lower. The ceiling is set for the seated position."""
    z0 = Z_IPAD + GAP - ZH + CLR                                 # ceiling, as modelled
    z1 = FLANGE["h"] + CLR + BOSS["roof"]                        # roof top
    part = plate([0.0], W, z0, z1)
    part += box(-W / 2, W / 2, Y_BODY + PLATE_T - 0.1, Y_LIP1, z0, z1)              # front skin out to 9.6
    part += box(-W / 2, W / 2, Y_LIP0, Y_LIP1, z0 - LIP_OVER, z0 + 0.1)              # lip over the bezel
    for s in (-1, 1):                                            # fill behind the boss beside the notch (no overhang)
        part += box(*sorted((s * NOTCH, s * W / 2)), 0.0, 2.1, z0, z1)
    return part


def vol(a, b):
    try:
        return (a & b).volume
    except Exception:
        return 0.0


def main():
    import numpy as np, trimesh
    from trimesh.transformations import rotation_matrix
    ok = True
    ok &= slot_floor_ok(HOOK_X, HOOK_FLOOR)
    print(f"hook slot: column {HOOK_X:.0f}, floor {HOOK_FLOOR:.0f}: {'ok' if ok else 'NOT A SLOT'}")
    print(f"hook bottom {ZH:.1f}, iPad top {Z_IPAD:.1f}: flange clear of the iPad by {ZH - Z_IPAD:.1f} mm")
    ok &= ZH - Z_IPAD > 1
    w_hook = Pos(HOOK_X, 0, ZH) * hook()
    clip = Pos(HOOK_X, 0, ZH - CLR) * top_clip()                 # seated: roof on the rail
    board = board_piece(-20, 60, 195, 260)
    ipad = box(X0 - IPAD["w"] / 2, X0 + IPAD["w"] / 2, 0.0, IPAD["t"], ZB, Z_IPAD)
    print("seated:", *(f"vs {n} {vol(clip, o):.3f} mm3" for n, o in (("hook", w_hook), ("board", board), ("iPad", ipad))))
    ok &= max(vol(clip, w_hook), vol(clip, board), vol(clip, ipad)) < 0.01
    bb = clip.bounding_box()
    roof_gap = bb.max.Z - BOSS["roof"] - (ZH + FLANGE["h"])
    print(f"roof on the rail: gap {roof_gap:.2f} mm; ceiling over the iPad: "
          f"{(ZH - CLR + Z_IPAD + GAP - ZH + CLR) - Z_IPAD:.2f} mm")
    worst = max(max(vol(Pos(0, 0, dz) * clip, w_hook), vol(Pos(0, 0, dz) * clip, board), vol(Pos(0, 0, dz) * clip, ipad))
                for dz in [0.5 * i for i in range(1, 101)])
    print(f"slide down the rail from 50 mm above (0.5 mm steps): worst overlap {worst:.3f} mm3")
    ok &= worst < 0.05
    fwd = vol(Pos(0, 1, 0) * box(HOOK_X - 9, HOOK_X + 9, 0, IPAD["t"], Z_IPAD - 10, Z_IPAD), clip)
    up = vol(Pos(0, 0, 1) * ipad, clip)
    print(f"iPad held: 1 mm forward hits the lip {fwd:.1f} mm3, 1 mm up hits the cap {up:.1f} mm3")
    ok &= fwd > 1 and up > 1
    ok &= len(top_clip().solids()) == 1
    OUT.mkdir(parents=True, exist_ok=True)
    export_stl(top_clip(), str(OUT / "_trc.stl"))
    m = trimesh.load(str(OUT / "_trc.stl"))
    (OUT / "_trc.stl").unlink()
    m.apply_transform(rotation_matrix(np.radians(180), [1, 0, 0]))   # upside down
    m.apply_translation(-m.bounds[0])
    nz, zc = m.face_normals[:, 2], m.triangles_center[:, 2]
    over = m.area_faces[(nz < -0.71) & (zc > 0.2)].sum()
    print(f"print: {m.extents.round(1)} mm, {m.volume / 1000:.1f} cm3, down-facing area above the bed {over:.1f} mm2")
    ok &= over < 0.5
    m.export(str(OUT / "ipad_top_rail.stl"))
    print("ALL CHECKS PASS" if ok else "CHECKS FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
