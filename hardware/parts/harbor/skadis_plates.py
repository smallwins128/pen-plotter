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

from build123d import BuildPart, BuildSketch, Cylinder, Locations, Plane, Pos, Rectangle, export_step, export_stl, loft

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


def hole_bar(w, ds, depth, hole_y, t=4.0):
    """L profile: the hole shelf is the plate's bottom edge and prints flat on the bed (round holes, no bridging);
    the plate rises behind it only where the sleeves are, joined by a strip along the bottom. A 4 mm fillet runs
    along the whole joint and small ribs sit at the two ends; anything taller would block the handles. One row of holes ds evenly across w, centred hole_y out from the plate."""
    pitch = w / len(ds)
    xs = [-w / 2 + pitch * (i + 0.5) for i in range(len(ds))]
    part = plate(sleeve_xs(w), w, Z0, Z_ROOF, strip=t + 6.0)
    part += box(-w / 2, w / 2, Y_F - 0.1, Y_F + depth, Z0, Z0 + t)
    fil = [(Y_F - 0.1, Z0 + t - 0.1), (Y_F + 8.0, Z0 + t - 0.1), (Y_F - 0.1, Z0 + t + 6.0)]
    for x in (-w / 2, w / 2 - 2.4):
        part += prism_yz(fil, x, x + 2.4)
    part += prism_yz([(Y_F - 0.1, Z0 + t - 0.1), (Y_F + 4.0, Z0 + t - 0.1), (Y_F - 0.1, Z0 + t + 4.0)],
                     -w / 2, w / 2)                                  # 45 deg fillet along the whole joint, under the handles
    for x, d in zip(xs, ds):
        part -= Pos(x, Y_F + hole_y, Z0 + t / 2) * Cylinder(d / 2 + 0.2, t + 2)
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


def ring_plate(xs, w, holes, wall, h):
    """A ring on the bed in front of a trimmed plate: sleeve columns at xs, a 4 mm strip along the bottom."""
    return plate(xs, w, Z0, Z_ROOF, strip=4.0) + ring(w, holes, wall, h)


def legs(xs, w, hole, bridge, wall, h):
    """Cutters and pliers, flat against the board: two holes side by side (x) with a bridge between them. Each handle
    drops through its own hole and the bridge sits in the V under the pivot. hole = (along the board, out of it)."""
    hx, hy, b = hole[0], hole[1], bridge / 2
    return ring_plate(xs, w, [(-b - hx, -b, wall, wall + hy), (b, b + hx, wall, wall + hy)], wall, h)


def legs_l():
    """Pliers, needle-nose, crimpers, 6-8 inch cutters: 20 x 16 holes, 6 mm bridge. The ring is 52 wide, so it rides
    on two hooks (40 apart) and takes two hook spaces. 45 deg gussets on the ring's outer walls run up to the sleeve
    columns; the handles splay inward to the pivot, away from them."""
    hole, bridge, wall, h = (20.0, 16.0), 6.0, 3.0, 12.0
    part = legs([-20.0, 20.0], 52.0, hole, bridge, wall, h)                       # plate as wide as the ring
    x_out = bridge / 2 + hole[0]                                                  # inner face of the outer wall
    rise = min(hole[1] + 2 * wall, Z_ROOF - h)
    gus = [(Y_F - 0.1, Z0 + h - 0.1), (Y_F + rise, Z0 + h - 0.1), (Y_F - 0.1, Z0 + h + rise)]
    for x0 in (-x_out - wall, x_out):
        part += prism_yz(gus, x0, x0 + wall)
    return part


def legs_s():
    """Flush cutters and small pliers: 13 x 11 holes, 5 mm bridge; fits one hook space."""
    return legs([0.0], BOSS["w"], (13.0, 11.0), 5.0, 2.5, 10.0)


def scissors_l():
    """Scissors, tip-down, the finger rings rest on the rim: slot 26 x 9 along the board."""
    return ring_plate([0.0], BOSS["w"], [(-13.0, 13.0, 2.5, 11.5)], 2.5, 8.0)


def scissors_s():
    return ring_plate([0.0], BOSS["w"], [(-9.0, 9.0, 2.0, 9.0)], 2.0, 7.0)


def clip():
    """One tape measure: a fin parallel to the plate, joined at the bottom, open at the top; the tape's belt clip
    slides down into the gap behind it. Gap and fin are guesses until a clip is measured."""
    w, gap, fin, top = 24.0, 3.0, 3.0, Z_ROOF + 4                 # just wider than the sleeve boss
    part = plate([0.0], BOSS["w"], Z0, top, strip=4.0)
    part += box(-w / 2, w / 2, Y_F - 0.1, Y_F + gap + fin, Z0, Z0 + 4.0)                     # joins at the bottom
    part += box(-w / 2, w / 2, Y_F + gap, Y_F + gap + fin, Z0, top)                          # the fin ("belt")
    part -= prism_yz([(Y_F + gap - 0.1, top + 0.1), (Y_F + gap + 1.5, top + 0.1), (Y_F + gap - 0.1, top - 1.6)],
                     -w, w)                                                                  # lead-in on its back
    return part


def frustum(x0, y0, x1, y1, z0, z1):
    """Ruled solid from a rectangle x0 half-width (along the board) by y span y0 = (y_a, y_b) at z0 to x1 by y1 at z1.
    Give both spans the same y_a to keep the back wall vertical."""
    with BuildPart() as p:
        for z, hx, (ya, yb) in ((z0, x0, y0), (z1, x1, y1)):
            with BuildSketch(Plane.XY.offset(z)):
                with Locations((0, (ya + yb) / 2)):
                    Rectangle(2 * hx, yb - ya)
        loft()
    return p.part


def plier_cup():
    """Pliers and crimpers, head down (Allwin's reference photo, 2026-10-31): a cup with an open bottom and sloped
    walls. The head drops through the 54 x 26 opening and the handles wedge against the walls as they spread, so one
    size takes the ferrule crimper (head ~50, handle ends ~80 apart), the teal crimper (~32 / ~60) and needle-nose
    (~18 / ~61); sizes measured off the photo, +-3 mm. Two hooks; the cup's back wall is the plate."""
    w, h, t = 2 * 40 - GAP, 25.0, 2.0
    bot, top = (27.0, 26.0), (36.0, 40.0)                 # inner half-width along the board, inner depth
    part = plate([-20.0, 20.0], w, Z0, Z_ROOF, strip=4.0)
    part += frustum(bot[0] + t, (Y_BODY, Y_F + bot[1] + t), top[0] + t, (Y_BODY, Y_F + top[1] + t), Z0, Z0 + h)   # own back wall
    k = 1.0 / h                                           # extend the inner cut 1 mm past both ends, same slope
    ib = [bot[0] - (top[0] - bot[0]) * k, bot[1] - (top[1] - bot[1]) * k]
    it = [top[0] + (top[0] - bot[0]) * k, top[1] + (top[1] - bot[1]) * k]
    part -= frustum(ib[0], (Y_F, Y_F + ib[1]), it[0], (Y_F, Y_F + it[1]), Z0 - 1, Z0 + h + 1)
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
          "scissors_s": scissors_s, "clip": clip, "adapter": adapter, "plier_cup": plier_cup}


# One print job (Bambu A1, 256 x 256). Everything upright as modelled. The A1 slings its bed along Y, so each plate is
# turned to put its thin wall along Y (it then can't whip back and forth); hooks are small and squat, left as they are.
BED, MARGIN, SPACE = 256.0, 8.0, 6.0
JOB = [("holes_l", 1), ("holes_s", 1), ("legs_s", 2), ("scissors_l", 1), ("scissors_s", 2), ("clip", 1)]   # large rings
CUPS = 4                                                  # -> plier cups, their own job (bed_plier_cups)
SPARE_HOOKS = 2
SLEEVES = {"holes_l": [-40.0, 0.0, 40.0], "holes_s": [-40.0, 0.0, 40.0], "legs_l": [-20.0, 20.0], "legs_s": [0.0],
           "scissors_l": [0.0], "scissors_s": [0.0], "clip": [0.0], "adapter": [0.0], "plier_cup": [-20.0, 20.0]}
HOOKS = {k: len(v) for k, v in SLEEVES.items()}


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
    write_bed("bed_plier_cups", [("plier_cup", meshes["plier_cup"].copy().apply_transform(turn)) for _ in range(CUPS)]
              + [("hook", h.copy()) for _ in range(HOOKS["plier_cup"] * CUPS)])
    write_bed("bed_fit_test", [("fit_strip", strip.copy().apply_transform(turn))] + [("hook", h.copy()) for _ in range(3)])


if __name__ == "__main__":
    main()
