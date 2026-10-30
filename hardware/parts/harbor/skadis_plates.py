"""R05 Harbor: generic plates for the SKÅDIS rail (2026-10-30). Nothing tool-shaped: each plate takes a family of tools.

    HOLE BAR  116  two rows of graded holes: small drivers drop in shaft-first, hex keys long-leg-first
    FORK BAR   76  three open-front slots 12 / 16 / 20: scissors blade-down, cutters and pliers jaws-down, handles on top
    CLIP BAR  116  three 34 mm tabs for tape measures: the tape's belt clip slides down over a 3.5 mm fin
    CUP        36  pens, markers, the line tester, a knife point-down
    TRAY       76  walled tray with a low front: tapes, utility knife, adapter
    SHELF     116  shallow shelf with a lip: remote, tapes, small boxes

    python3 skadis_plates.py      # writes out/harbor/plate_*.stl (+ .step)

Frame as in skadis_rail.py (x along the board, y out of it, z up, hook bottom z = 0). Every plate prints upright as
modelled, standing on its bottom edge: sleeves, foot and floors start on the bed. Shelves that sit higher are a thin
top plate on 45 deg ribs (light, and no supports; the plate bridges at most 37 mm between ribs).
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


def spread(segments, ds, gap=4.0):
    """Hole centres for diameters ds, filled into free x segments [(x0, x1)] left to right."""
    xs, i = [], 0
    for x0, x1 in segments:
        room = [d for d in ds[i:]]
        n = 0
        while n < len(room) and sum(room[:n + 1]) + gap * (n + 2) <= x1 - x0:
            n += 1
        if n == 0:
            continue
        pitch = (x1 - x0) / n
        xs += [x0 + pitch * (k + 0.5) for k in range(n)]
        i += n
    return list(zip(xs, ds[:len(xs)]))


def hole_bar():
    w, depth, top, t = 3 * 40 - GAP, 30.0, 44.0, 4.0
    ribs = sleeve_xs(w)
    part = plate(ribs, w, Z0, top) + rib_shelf(w, depth, top, t, ribs)
    edges = [-w / 2 + 2.4] + [x for r in ribs for x in (r - 1.2, r + 1.2)] + [w / 2 - 2.4]
    segs = [(edges[i], edges[i + 1]) for i in range(0, len(edges), 2)]
    rows = ((Y_F + 9.0, [3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 7.0]),          # hex keys, precision drivers
            (Y_F + 21.0, [6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0]))           # bigger drivers, the line tester
    for y, ds in rows:
        for x, d in spread(segs, ds):
            part -= Pos(x, y, top - t / 2) * Cylinder(d / 2 + 0.2, t + 2)
    return part


def fork_bar():
    """Scissors and cutters: three open-front slots in a thin shelf, a rib under every finger."""
    w, depth, top, t = 2 * 40 - GAP, 36.0, 44.0, 5.0
    widths = [12.0, 16.0, 20.0]
    fingers = (w - sum(widths)) / (len(widths) + 1)
    xs, x = [], -w / 2 + fingers
    for sw in widths:
        xs.append(x + sw / 2)
        x += sw + fingers
    ribs = [x - sw / 2 - fingers / 2 for x, sw in zip(xs, widths)][1:]          # under the inner fingers
    part = plate(sleeve_xs(w), w, Z0, top) + rib_shelf(w, depth, top, t, ribs, rib_w=min(4.0, fingers))
    for x, sw in zip(xs, widths):
        y0 = Y_F + 12.0
        part -= box(x - sw / 2, x + sw / 2, y0, Y_F + depth + 1, top - t - 1, top + 1)
        part -= Pos(x, y0, top - t / 2) * Cylinder(sw / 2, t + 2)
    return part


def clip_bar():
    """Tape measures: a fin parallel to the plate, joined at the bottom, open at the top. The tape's belt clip slides
    down into the gap behind the fin. Gap and fin are guesses until a clip is measured."""
    w, gap, fin, top = 3 * 40 - GAP, 3.0, 3.5, Z_ROOF + 4
    part = plate(sleeve_xs(w), w, Z0, top)
    for x in sleeve_xs(w):                                      # one 34 mm tab per tape, in front of each sleeve
        part += box(x - 17, x + 17, Y_F - 0.1, Y_F + gap + fin, Z0, Z0 + 4.0)                  # joins at the bottom
        part += box(x - 17, x + 17, Y_F + gap, Y_F + gap + fin, Z0, top)                       # the fin ("belt")
    part -= prism_yz([(Y_F + gap - 0.1, top + 0.1), (Y_F + gap + 1.5, top + 0.1), (Y_F + gap - 0.1, top - 1.6)],
                     -w, w)                                                                    # lead-in on its back
    return part


def cup():
    w, d, h = 1 * 40 - GAP, 32.0, 62.0
    part = plate(sleeve_xs(w), w, Z0, Z_ROOF + 2)
    part += box(-w / 2, w / 2, Y_BODY, Y_F + d, Z0, Z0 + h)      # own back wall above the plate
    part -= box(-w / 2 + WALL, w / 2 - WALL, Y_F, Y_F + d - WALL, Z0 + WALL, Z0 + h + 1)
    return part


def tray(w=2 * 40 - GAP, d=48.0, back=Z_ROOF + 2, front=26.0):
    part = plate(sleeve_xs(w), w, Z0, back)
    side = [(Y_F - 0.1, Z0), (Y_F + d, Z0), (Y_F + d, Z0 + front), (Y_F - 0.1, back)]   # sides slope to the front
    part += prism_yz(side, -w / 2, w / 2)
    inner = [(Y_F, Z0 + WALL), (Y_F + d - WALL, Z0 + WALL), (Y_F + d - WALL, Z0 + 200),
             (Y_F, Z0 + 200)]
    part -= prism_yz(inner, -w / 2 + WALL, w / 2 - WALL)
    part -= prism_yz([(Y_F + d - WALL - 0.1, Z0 + front), (Y_F + d + 1, Z0 + front), (Y_F + d + 1, Z0 + 200),
                      (Y_F + d - WALL - 0.1, Z0 + 200)], -w, w)
    return part


def shelf():
    return tray(w=3 * 40 - GAP, d=62.0, back=Z_ROOF + 2, front=10.0)


PLATES = {"hole_bar": hole_bar, "fork_bar": fork_bar, "clip_bar": clip_bar, "cup": cup, "tray": tray, "shelf": shelf}


def main():
    import trimesh
    OUT.mkdir(parents=True, exist_ok=True)
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
    export_stl(board_piece(-200, 80, -110, 75), str(OUT / "skadis_board_wall.stl"))   # for the inspector's wall view


if __name__ == "__main__":
    main()
