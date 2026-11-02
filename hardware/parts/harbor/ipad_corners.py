"""R05 Harbor: iPad sleeve v3, four corner plates on standard rail hooks (2026-11-02, Allwin's idea).

Goal: minimal frontal visibility, all four corners alike; a gap between the iPad and the board is fine. So four
standard rail hooks (skadis_rail.py, unchanged) hang behind the iPad's corners; each takes a plate that slides down the
hook's rail (as the tool plates do). The plates sit behind the iPad, which rests 9.15 mm off the board; only a thin
corner wrap shows: a 2 mm wall round the iPad's edge plus a 3 mm lip over the bezel, legs 36.8 long.

    BOTTOM L / R   wrap with a 3 mm ledge the iPad stands on; prints upright (ledge on the bed)
    TOP L / R      wrap with a 2 mm cap over the top corner; slides on last, over the iPad; prints upside down

Hooks: odd columns x = -100 and +100 (200 apart, same slot heights, so left and right are mirror images), slot floors
66 (bottom) and 186 (top), 120 apart in one column. Every hook and plate body sits behind the iPad.

Fit order: 4 hooks; bottom plates slide down their hooks; iPad onto the ledges, back against the plates; hold it
upright and slide the top plates down behind it until the caps land over its top corners. Off: reverse.

    python3 ipad_corners.py     # checks, then out/harbor/ipad_corner_*.stl (print orientation) and ipad_corners_bed.stl

Frame as ipad_sleeve.py: x along the board, y out of it (board front y = 0), z up; odd columns' slot floors at
-14 + 40 k. iPad 7th gen: 250.6 x 174.1 x 7.5 (Apple).
"""
import sys

from build123d import Plane, Pos, export_stl, mirror

from skadis_rail import BOSS, CLR, FLANGE, NECK, OUT, PLATE_T, Y_BODY, board_piece, box, hook, plate, prism_yz

IPAD = dict(w=250.6, h=174.1, t=7.5)
GAP = 0.5                                       # round the iPad's edges and over its face
X0 = 0.0
XL = X0 - IPAD["w"] / 2 - GAP                   # -125.8: left edge face
ZB = 36.0                                       # iPad's bottom edge (on the ledges)
ZC = ZB + IPAD["h"] + GAP                       # 210.6: cap ceiling
Y_PLATE = Y_BODY + PLATE_T                      # 8.85: plate front
Y_IPAD = Y_PLATE + 0.3                          # 9.15: iPad back (0.3 so the top plates slide behind it)
Y_LIP0 = Y_IPAD + IPAD["t"] + GAP               # 17.15: lip back
Y_LIP1 = Y_LIP0 + 1.6                           # 18.75: front of every wrap
WALL, LIP, LEDGE, CAP = 2.0, 3.0, 3.0, 2.0
HOOK_X = -100.0
FLOOR_B, FLOOR_T = 66.0, 186.0
LEG = (HOOK_X + BOSS["w"] / 2) - (XL - WALL)    # 36.8: plate and both legs end at the sleeve boss's outer side
XO, XE = XL - WALL, XL - WALL + LEG             # -127.8, -91.0
Z_ROOF = FLANGE["h"] + CLR + BOSS["roof"]        # sleeve roof top, hook-local
LEAD = 1.5


def slot_floor_ok(x, z):
    base = 6.0 if (int(x) // 20) % 2 == 0 else -14.0
    return abs((z - base) / 40 - round((z - base) / 40)) < 1e-6


def on_hook(z0w, z1w, floor):
    """Plate body (via skadis_rail.plate) on the hook at (HOOK_X, floor), world z0w..z1w, seated (the modelled roof
    sits CLR above the rail; seated it drops CLR)."""
    hb = floor - NECK["z"] - CLR
    cx, w = (XO + XE) / 2, XE - XO
    return Pos(cx, 0, hb) * plate([HOOK_X - cx], w, z0w - hb, z1w - hb)


def ipad_space():
    return box(XL, -XL, Y_PLATE + 0.01, Y_LIP0, ZB, ZC)


def bottom_l():
    z0, ztop = ZB - LEDGE, ZB - LEDGE + LEG
    part = on_hook(z0, FLOOR_B - NECK["z"] + Z_ROOF, FLOOR_B)
    part += box(XO, XE, Y_BODY, Y_LIP1, z0, ZB)                         # ledge
    part += box(XO, XL, Y_BODY, Y_LIP1, z0, ztop)                       # wall round the left edge
    part += box(XL - 0.01, XE, Y_LIP0, Y_LIP1, z0, ZB + LIP)             # lip over the bottom bezel
    part += box(XL - 0.01, XL + LIP, Y_LIP0, Y_LIP1, z0, ztop)           # lip over the side bezel
    part -= ipad_space()
    # lead-in at the side leg's top, on the lip's back face
    part -= prism_yz([(Y_LIP0 + 0.01, ztop + 0.01), (Y_LIP0 - LEAD, ztop + 0.01), (Y_LIP0 + 0.01, ztop - LEAD)],
                     XL - 0.02, XL + LIP + 0.02)
    return part


def top_l():
    z1, z0 = ZC + CAP, ZC + CAP - LEG
    hb = FLOOR_T - NECK["z"] - CLR
    part = on_hook(z0, z1, FLOOR_T)
    part += box(XO, XE, Y_BODY, Y_LIP1, ZC, z1)                         # cap over the top edge
    part += box(XO, XL, Y_BODY, Y_LIP1, z0, z1)                         # wall round the left edge
    part += box(XL - 0.01, XE, Y_LIP0, Y_LIP1, ZC - LIP, z1)             # lip over the top bezel
    part += box(XL - 0.01, XL + LIP, Y_LIP0, Y_LIP1, z0, z1)             # lip over the side bezel
    # printed upside down: fill the sleeve boss above its roof to the top, and behind it beside the flange notch
    xs = HOOK_X
    part += box(xs - BOSS["w"] / 2, xs + BOSS["w"] / 2, 2.0, Y_BODY + 0.1, hb + Z_ROOF - 0.1, z1)
    notch = FLANGE["w"] / 2 + 1
    for a, b in ((XO, xs - notch), (xs + notch, XE)):                    # solid back to the board beside the notch,
        part += box(a, b, 0.0, Y_BODY + 0.1, z0, z1)                        # so the foot never hangs upside down
    part -= ipad_space()
    return part


def mirrored(p):
    return mirror(p, Plane.YZ.offset(X0))


def vol(a, b):
    try:
        return (a & b).volume
    except Exception:
        return 0.0


def main():
    import numpy as np, trimesh
    from trimesh.transformations import rotation_matrix
    ok = True
    hooks = {}
    for side in (-1, 1):
        for fl in (FLOOR_B, FLOOR_T):
            x = side * -HOOK_X
            good = slot_floor_ok(x, fl)
            print(f"hook column {x:5.0f}, floor {fl:4.0f}: {'ok' if good else 'NOT A SLOT'}")
            ok &= good
            hooks[(side, fl)] = Pos(x, 0, fl - NECK["z"]) * hook()
    ps = {"bottom_l": bottom_l(), "top_l": top_l()}
    ps["bottom_r"], ps["top_r"] = mirrored(ps["bottom_l"]), mirrored(ps["top_l"])
    allhooks = sum(list(hooks.values())[1:], list(hooks.values())[0])
    board = board_piece(-150, 150, 20, 230)
    ipad = box(X0 - IPAD["w"] / 2, X0 + IPAD["w"] / 2, Y_IPAD, Y_IPAD + IPAD["t"], ZB, ZB + IPAD["h"])
    print("seated, overlaps (mm3):")
    names = list(ps)
    for n in names:
        v = (vol(ps[n], allhooks), vol(ps[n], board), vol(ps[n], ipad))
        print(f"  {n:9s} hooks {v[0]:.3f}  board {v[1]:.3f}  iPad {v[2]:.3f}")
        ok &= max(v) < 0.01
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if vol(ps[a], ps[b]) > 0.01:
                print("  FAIL", a, b)
                ok = False
    print("slide each plate down its hook from 60 mm above (0.5 mm steps); top plates with the iPad in:")
    for n in names:
        others = allhooks + board + (ipad if n.startswith("top") else box(0, 0.01, 0, 0.01, 0, 0.01))
        worst = max(vol(Pos(0, 0, 0.5 * i) * ps[n], others) for i in range(1, 121))
        print(f"  {n:9s} worst {worst:.3f}")
        ok &= worst < 0.05
    bottoms = ps["bottom_l"] + ps["bottom_r"]
    worst = max(vol(Pos(0, 0, dz) * ipad, bottoms + allhooks) for dz in range(1, 220))
    rest = vol(Pos(0, 0, -0.3) * ipad, bottoms)
    print(f"iPad drops onto the ledges from above: worst {worst:.3f}; 0.3 lower hits the ledges {rest:.1f}")
    ok &= worst < 0.05 and rest > 1
    allp = bottoms + ps["top_l"] + ps["top_r"]
    for label, mv in (("forward", Pos(0, 1, 0) * ipad), ("up", Pos(0, 0, 1) * ipad), ("left", Pos(-1, 0, 0) * ipad),
                      ("back", Pos(0, -1, 0) * ipad)):
        v = vol(mv, allp + allhooks)
        print(f"iPad held, 1 mm {label:7s}: {v:.1f} mm3")
        ok &= v > 1
    # what shows from the front: clip area outside the iPad's outline
    import shapely.geometry as sg
    from shapely.ops import unary_union
    vis = 0.0
    for n, p in ps.items():
        export_stl(p, str(OUT / "_c.stl"))
        m = trimesh.load(str(OUT / "_c.stl"))
        polys = [sg.Polygon(t[:, [0, 2]]) for t in m.triangles[np.abs(m.face_normals[:, 1]) > 0.5]]
        sil = unary_union([q for q in polys if q.area > 1e-9])
        out = sil.difference(sg.box(X0 - IPAD["w"] / 2, ZB, X0 + IPAD["w"] / 2, ZB + IPAD["h"]))
        vis += out.area
        ok &= len(p.solids()) == 1
    (OUT / "_c.stl").unlink()
    print(f"seen from the front outside the iPad: {vis:.0f} mm2 for all four (legs {LEG:.1f}, "
          f"side legs {WALL + LIP - GAP:.1f} wide incl. lip, bottom/top bars {LEDGE + LIP:.1f} / {CAP + LIP:.1f})")
    # print orientation: bottoms upright, tops upside down
    OUT.mkdir(parents=True, exist_ok=True)
    meshes = {}
    for n, p in ps.items():
        export_stl(p, str(OUT / "_c.stl"))
        m = trimesh.load(str(OUT / "_c.stl"))
        if n.startswith("top"):
            m.apply_transform(rotation_matrix(np.radians(180), [1, 0, 0]))
        m.apply_translation(-m.bounds[0])
        nz, zc = m.face_normals[:, 2], m.triangles_center[:, 2]
        over = m.area_faces[(nz < -0.71) & (zc > 0.3)].sum()
        allowed = 31.0 if n.startswith("bottom") else 1.0      # bottoms: sleeve roof bridge + groove mouth, as every plate
        print(f"print {n:9s} {m.extents.round(1)} mm, {m.volume / 1000:.1f} cm3, down-facing above the bed {over:.1f} mm2"
              f" (allowed {allowed:.0f})")
        ok &= over < allowed
        meshes[n] = m
        m.export(str(OUT / f"ipad_corner_{n}.stl"))
        export_stl(p, str(OUT / f"ipad_corner_{n}_assembly.stl"))
    (OUT / "_c.stl").unlink()
    export_stl(hook(), str(OUT / "_h.stl"))
    hm = trimesh.load(str(OUT / "_h.stl"))
    (OUT / "_h.stl").unlink()
    hm.apply_translation(-hm.bounds[0])
    for k, ((side, fl), h) in enumerate(hooks.items()):
        export_stl(h, str(OUT / f"ipad_corner_hook{k}_assembly.stl"))
    # bed: 4 plates + 3 hooks, A1 256 x 256
    placed, x = [], 10.0
    for n in ("bottom_l", "bottom_r", "top_l", "top_r"):
        m = meshes[n].copy()
        m.apply_translation([x, 10, 0])
        placed.append(m)
        x += m.extents[0] + 8
    for k in range(3):
        m = hm.copy()
        m.apply_translation([10 + k * (hm.extents[0] + 10), 60, 0])
        placed.append(m)
    bed = trimesh.util.concatenate(placed)
    print(f"bed: 4 plates + 3 hooks, {bed.extents[:2].round(0)} mm footprint, {bed.volume / 1000:.1f} cm3")
    ok &= bed.extents[0] < 250 and bed.extents[1] < 250
    bed.export(str(OUT / "ipad_corners_bed.stl"))
    print("ALL CHECKS PASS" if ok else "CHECKS FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
