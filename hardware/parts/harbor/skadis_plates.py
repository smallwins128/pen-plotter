"""R05 Harbor: generic plates for the SKÅDIS rail (2026-10-30). Nothing tool-shaped: each plate takes a family of tools.

    HOLE BAR  116  two rows of graded holes: small drivers drop in shaft-first, hex keys long-leg-first
    SLOT BAR   76  open-front slots 6 / 10 / 14 / 18: caliper beam, scissors, spanner, anything with a waist
    CUP        36  pens, markers, the line tester, a knife point-down
    TRAY       76  walled tray with a low front: tapes, utility knife, adapter
    SHELF     116  shallow shelf with a lip: remote, tapes, small boxes

    python3 skadis_plates.py      # writes out/harbor/plate_*.stl (+ .step)

Frame as in skadis_rail.py (x along the board, y out of it, z up, hook bottom z = 0). Every plate prints upright as
modelled, standing on its bottom edge: sleeves, foot and floors start on the bed, and shelves that sit higher have a
45 deg underside, so nothing needs supports.
"""
import pathlib

from build123d import Cylinder, Pos, export_step, export_stl

from skadis_rail import CLR, FLANGE, GAP, OUT, PLATE_T, Y_BODY, BOSS, board_piece, box, plate, prism_yz, sleeve_xs

Y_F = Y_BODY + PLATE_T                   # plate front face
Z0 = -12.0                               # plate bottom (foot), below the hook
Z_ROOF = FLANGE["h"] + CLR + BOSS["roof"]  # top of the sleeve roofs; a plate is at least this tall
WALL = 2.0


def wedge_shelf(w, depth, z_top, t):
    """Shelf across the plate's front, flat top at z_top, t thick at the front and a 45 deg underside back to the
    plate, so it prints upright without supports."""
    prof = [(Y_F - 0.1, z_top), (Y_F + depth, z_top), (Y_F + depth, z_top - t), (Y_F - 0.1, z_top - t - depth)]
    return prism_yz(prof, -w / 2, w / 2)


def hole_bar():
    w, depth, top = 3 * 40 - GAP, 30.0, 44.0
    part = plate(sleeve_xs(w), w, Z0, top) + wedge_shelf(w, depth, top, 8.0)
    rows = ((Y_F + 9.0, [3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 7.0, 8.0]),     # hex keys, precision drivers
            (Y_F + 22.0, [5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0]))      # bigger drivers, the line tester
    for y, ds in rows:
        pitch = (w - 14) / (len(ds) - 1)
        for i, d in enumerate(ds):
            part -= Pos(-w / 2 + 7 + i * pitch, y, top - 30) * Cylinder(d / 2 + 0.2, 70)
    return part


def slot_bar():
    w, depth, top = 2 * 40 - GAP, 34.0, 44.0
    part = plate(sleeve_xs(w), w, Z0, top) + wedge_shelf(w, depth, top, 8.0)
    widths = [6.0, 10.0, 14.0, 18.0]
    pitch = w / len(widths)
    for i, sw in enumerate(widths):
        x = -w / 2 + pitch * (i + 0.5)
        y0 = Y_F + 10.0
        part -= box(x - sw / 2, x + sw / 2, y0, Y_F + depth + 1, top - 60, top + 1)
        part -= Pos(x, y0, top - 30) * Cylinder(sw / 2, 70)
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


PLATES = {"hole_bar": hole_bar, "slot_bar": slot_bar, "cup": cup, "tray": tray, "shelf": shelf}


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
