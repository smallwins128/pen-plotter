"""R05 Harbor: plates for the SKÅDIS rail (2026-10-30, v4 after Allwin's review). Simple shapes, light on filament.

    HOLES L   116  one row of 6 holes, Ø7-12 at 19.3 mm pitch: screwdrivers, files
    HOLES S   116  one row of 7 holes, Ø2.5-6 at 16.6 mm pitch: precision drivers, hex keys (long leg down)
    LEGS L/S   36  two holes side by side with a bridge: each handle of a cutter or pliers drops through its own
                   hole, the bridge sits in the V under the pivot; tools hang flat against the board
    SCISSORS   36  L/S: one slot along the board; scissors go in tip-down, the finger rings rest on the rim
    CLIP       24  one tape measure: its belt clip slides down behind a 3 mm fin
    ADAPTER    36  a bare sleeve plate with two M3 holes, to bolt onto a cup or tray you already have (bolt head
                   behind the plate, nut inside the cup)

    python3 skadis_plates.py      # writes out/harbor/plate_*.stl (+ .step)

Frame as in skadis_rail.py (x along the board, y out of it, z up, hook bottom z = 0). Every plate prints upright as
modelled, standing on its bottom edge: sleeves, foot and rings start on the bed, which is also the orientation the
loads want (rings and sleeves are loaded along their layers, not across them). The hole bars' shelves are a thin top
on 45 deg ribs at the ends and mid-way only. Handle sizes behind the hole pitch are estimates.
"""
import pathlib

from build123d import Cylinder, Pos, export_step, export_stl

from skadis_rail import CLR, FLANGE, GAP, OUT, PLATE_T, Y_BODY, BOSS, board_piece, box, plate, prism_yz, sleeve_xs

Y_F = Y_BODY + PLATE_T                   # plate front face
Z0 = 0.0                                 # plate bottom (foot), level with the hook's bottom
Z_ROOF = FLANGE["h"] + CLR + BOSS["roof"]  # top of the sleeve roofs; a plate is at least this tall
WALL = 2.0


def rib_shelf(w, depth, z_top, t, rib_xs, rib_w=2.4):
    """Shelf across the plate's front: a t-thick top plate at z_top, held by 45 deg ribs at rib_xs (plus both ends)
    that run from its front edge back down to the plate."""
    part = box(-w / 2, w / 2, Y_F - 0.1, Y_F + depth, z_top - t, z_top)
    rib = [(Y_F - 0.1, z_top - t + 0.1), (Y_F + depth, z_top - t + 0.1), (Y_F - 0.1, z_top - t - depth)]
    for x in sorted(set([-w / 2 + rib_w / 2, w / 2 - rib_w / 2] + list(rib_xs))):
        part += prism_yz(rib, x - rib_w / 2, x + rib_w / 2)
    return part


def hole_bar(w, ds, depth, hole_y, t=4.0, top=36.0):
    """One row of holes ds evenly across w, centred hole_y in front of the plate. Ribs only at the two ends and in
    the gap nearest the middle, so the shelf bridges about half its width (~55 mm on a 116 bar; the A1 bridges
    that cleanly in PLA)."""
    pitch = w / len(ds)
    xs = [-w / 2 + pitch * (i + 0.5) for i in range(len(ds))]
    gaps = [(xs[i] + xs[i + 1]) / 2 for i in range(len(xs) - 1)]
    part = plate(sleeve_xs(w), w, Z0, top) + rib_shelf(w, depth, top, t, [min(gaps, key=abs)])
    for x, d in zip(xs, ds):
        part -= Pos(x, Y_F + hole_y, top - t / 2) * Cylinder(d / 2 + 0.2, t + 2)
    return part


def holes_l():
    """Screwdrivers and files: 6 holes at 19.3 mm pitch on three hooks. A handle wider than ~19 mm needs the hole
    next to it left empty."""
    return hole_bar(3 * 40 - GAP, [7.0, 8.0, 9.0, 10.0, 11.0, 12.0], depth=28.0, hole_y=15.0)


def holes_s():
    return hole_bar(3 * 40 - GAP, [2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 6.0], depth=20.0, hole_y=11.0)


def ring(w, holes, wall, h):
    """Ring standing on the bed in front of the plate: outer box around holes [(x0, x1, y0, y1)] (y from the plate's
    front face), walls `wall` thick, `h` tall."""
    x0 = min(hx0 for hx0, _, _, _ in holes) - wall
    x1 = max(hx1 for _, hx1, _, _ in holes) + wall
    y1 = max(hy1 for _, _, _, hy1 in holes) + wall
    part = box(x0, x1, Y_F - 0.1, Y_F + y1, Z0, Z0 + h)
    for hx0, hx1, hy0, hy1 in holes:
        part -= box(hx0, hx1, Y_F + hy0, Y_F + hy1, Z0 - 1, Z0 + h + 1)
    return part


def legs(hole=(16.0, 14.0), bridge=6.0, wall=2.5, h=12.0):
    """Cutters and pliers, flat against the board: two holes side by side (x) with a bridge between them. Each handle
    drops through its own hole and the bridge sits in the V under the pivot. hole = (along the board, out of it)."""
    w = 1 * 40 - GAP
    part = plate(sleeve_xs(w), w, Z0, Z_ROOF + 2)
    hx, hy = hole
    x_in = bridge / 2
    return part + ring(w, [(-x_in - hx, -x_in, wall, wall + hy), (x_in, x_in + hx, wall, wall + hy)], wall, h)


def legs_l():
    """Big pliers and cutters. The ring is 42 wide, wider than the 36 plate: don't hang two of these on neighbouring
    hooks (next to anything else it clears by 1 mm)."""
    return legs((16.0, 14.0), 5.0, 2.5, 12.0)


def legs_s():
    """Small cutters and pliers: fits within the 36 mm plate."""
    return legs((12.0, 11.0), 5.0, 2.5, 10.0)


def scissors(slot=(26.0, 9.0), wall=2.5, h=8.0):
    """Scissors: one slot along the board, thin walls; tip-down, the finger rings rest on the rim."""
    w = 1 * 40 - GAP
    part = plate(sleeve_xs(w), w, Z0, Z_ROOF + 2)
    sx, sy = slot
    return part + ring(w, [(-sx / 2, sx / 2, wall, wall + sy)], wall, h)


def scissors_l():
    return scissors((26.0, 9.0), 2.5, 8.0)


def scissors_s():
    return scissors((18.0, 7.0), 2.0, 7.0)


def clip():
    """One tape measure: a fin parallel to the plate, joined at the bottom, open at the top; the tape's belt clip
    slides down into the gap behind it. Gap and fin are guesses until a clip is measured."""
    w, gap, fin, top = 24.0, 3.0, 3.0, Z_ROOF + 4                 # just wider than the sleeve boss
    part = plate(sleeve_xs(w), w, Z0, top)
    part += box(-w / 2, w / 2, Y_F - 0.1, Y_F + gap + fin, Z0, Z0 + 4.0)                     # joins at the bottom
    part += box(-w / 2, w / 2, Y_F + gap, Y_F + gap + fin, Z0, top)                          # the fin ("belt")
    part -= prism_yz([(Y_F + gap - 0.1, top + 0.1), (Y_F + gap + 1.5, top + 0.1), (Y_F + gap - 0.1, top - 1.6)],
                     -w, w)                                                                  # lead-in on its back
    return part


def adapter():
    """Bare sleeve plate for a bought cup or tray: two M3 clearance holes beside the sleeve. The bolt head sits in the
    gap behind the plate (4.4 mm deep), the nut inside the cup."""
    w = 1 * 40 - GAP
    part = plate(sleeve_xs(w), w, Z0, Z_ROOF + 2)
    for x in (-13.0, 13.0):
        part -= Pos(x, Y_F - PLATE_T / 2, 18.0) * Cylinder(1.7, PLATE_T + 2, rotation=(90, 0, 0))
    return part


PLATES = {"holes_l": holes_l, "holes_s": holes_s, "legs_l": legs_l, "legs_s": legs_s, "scissors_l": scissors_l,
          "scissors_s": scissors_s, "clip": clip, "adapter": adapter}


# One print job (Bambu A1, 256 x 256). Everything upright as modelled. The A1 slings its bed along Y, so each plate is
# turned to put its thin wall along Y (it then can't whip back and forth); hooks are small and squat, left as they are.
BED, MARGIN, SPACE = 256.0, 8.0, 6.0
JOB = [("holes_l", 1), ("holes_s", 1), ("legs_l", 2), ("legs_s", 2), ("scissors_l", 1), ("scissors_s", 2), ("clip", 1)]
SPARE_HOOKS = 2
HOOKS = {"holes_l": 3, "holes_s": 3, "legs_l": 1, "legs_s": 1, "scissors_l": 1, "scissors_s": 1, "clip": 1, "adapter": 1}


def pack(items):
    """Column packer: items [(name, mesh)] already on the bed at the origin; tallest-in-Y first, columns left to
    right. Returns the placed meshes or raises if the bed is full."""
    items = sorted(items, key=lambda it: -it[1].extents[1])
    placed, x, y, col_w = [], MARGIN, MARGIN, 0.0
    for name, m in items:
        dx, dy = m.extents[:2]
        if y + dy > BED - MARGIN:
            x, y, col_w = x + col_w + SPACE, MARGIN, 0.0
        if x + dx > BED - MARGIN:
            raise RuntimeError(f"bed full at {name}")
        placed.append((name, m.copy().apply_translation([x - m.bounds[0][0], y - m.bounds[0][1], -m.bounds[0][2]])))
        y, col_w = y + dy + SPACE, max(col_w, dx)
    return placed


def write_bed(name, items):
    import trimesh
    placed = pack(items)
    scene = trimesh.Scene()
    for i, (n, m) in enumerate(placed):
        scene.add_geometry(m, node_name=f"{n}_{i}", geom_name=f"{n}_{i}")
    trimesh.util.concatenate([m for _, m in placed]).export(str(OUT / f"{name}.stl"))
    try:
        scene.export(str(OUT / f"{name}.3mf"))
    except Exception as e:                                  # 3MF needs extra packages; the STL is enough
        print(f"  ({name}.3mf skipped: {e})")
    lo = min(m.bounds[0][0] for _, m in placed), min(m.bounds[0][1] for _, m in placed)
    hi = max(m.bounds[1][0] for _, m in placed), max(m.bounds[1][1] for _, m in placed)
    print(f"{name}: {len(placed)} parts, uses {hi[0] - lo[0]:.0f} x {hi[1] - lo[1]:.0f} of {BED:.0f} x {BED:.0f},"
          f" {sum(m.volume for _, m in placed) / 1000 * 1.24:.0f} g PLA solid")
    return placed


def main():
    import numpy as np, trimesh
    from trimesh.transformations import rotation_matrix
    from skadis_rail import fit_strip, hook
    OUT.mkdir(parents=True, exist_ok=True)
    meshes = {}
    for name, fn in PLATES.items():
        part = fn()
        bb = part.bounding_box()
        print(f"plate_{name}: {bb.size.X:.0f} x {bb.size.Y:.0f} x {bb.size.Z:.0f} mm, volume {part.volume / 1000:.1f} cm3,"
              f" about {part.volume / 1000 * 1.24:.0f} g PLA solid")
        export_stl(part, str(OUT / f"plate_{name}.stl"))
        export_step(part, str(OUT / f"plate_{name}.step"))
        m = trimesh.load(str(OUT / f"plate_{name}.stl"))
        m.apply_translation(-m.bounds[0])                                     # upright, bottom edge on the bed
        m.export(str(OUT / f"plate_{name}_print.stl"))
        meshes[name] = m
    export_stl(board_piece(-200, 80, -190, 75), str(OUT / "skadis_board_wall.stl"))   # for the inspector's wall view

    export_stl(hook(), str(OUT / "_hook.stl"))
    export_stl(fit_strip(), str(OUT / "_strip.stl"))
    h, strip = trimesh.load(str(OUT / "_hook.stl")), trimesh.load(str(OUT / "_strip.stl"))
    turn = rotation_matrix(np.radians(90), [0, 0, 1])
    items = []
    for name, n in JOB:
        for _ in range(n):
            items.append((name, meshes[name].copy().apply_transform(turn)))
    n_hooks = sum(HOOKS[name] * n for name, n in JOB) + SPARE_HOOKS
    items += [("hook", h.copy()) for _ in range(n_hooks)]
    write_bed("bed_harbor_skadis", items)
    write_bed("bed_fit_test", [("fit_strip", strip.copy().apply_transform(turn))] + [("hook", h.copy()) for _ in range(3)])


if __name__ == "__main__":
    main()
