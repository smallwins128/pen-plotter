"""Meccano window panel: a plain plate over any of the three front windows (all 143 × 50, R5, 4 M3 rivnuts 7 mm out),
on the panel rules (3 mm plate, countersunk M3, rivnut flange reliefs, 2 mm lip into the opening), with the area over
the opening drilled on the Meccano grid (Ø4.1 holes on a 12.7 mm pitch) so switches, LEDs and brackets bolt on later.

    python3 hardware/parts/window_meccano.py     # writes hardware/out/window_meccano/window_meccano.stl
"""
import math
import pathlib
import sys

from build123d import export_stl
from shapely.geometry import Point

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "sheet"))
import enclosure as E  # noqa: E402
import panel_rules as R  # noqa: E402

OUT = HERE.parent / "out" / "window_meccano"
PITCH, HOLE = 12.7, 4.1          # Meccano: ½" pitch, 5/32" holes
EDGE = 14.5                      # plate edge beyond the opening (the old bezel band + rim): keeps 15 mm off the box edges
HOLE_CLEAR = 1.0                 # web between a hole and the lip


def panel():
    opening, screws = E.ctrl_window()
    cx, cy = opening.centroid.x, opening.centroid.y
    opening = opening.buffer(0)          # centred frame
    from shapely.affinity import translate
    opening = translate(opening, -cx, -cy)
    screws = [(x - cx, y - cy) for x, y in screws]
    outline = opening.buffer(EDGE, join_style=1, quad_segs=12)
    bad = [c for c in R.check(outline, opening, screws) if not (c[2] and c[3])]
    if bad:
        raise SystemExit(f"rivnut relief too close to the edge or the lip: {bad}")
    usable = opening.buffer(-(R.LIP_GAP + R.LIP_W + HOLE_CLEAR + HOLE / 2), join_style=2)
    x0, y0, x1, y1 = usable.bounds
    nx, ny = int((x1 - x0) // PITCH) + 1, int((y1 - y0) // PITCH) + 1
    ox, oy = -(nx - 1) * PITCH / 2, -(ny - 1) * PITCH / 2
    holes = [(ox + i * PITCH, oy + j * PITCH, HOLE) for i in range(nx) for j in range(ny)
             if usable.contains(Point(ox + i * PITCH, oy + j * PITCH))]
    return R.panel(outline, opening, screws, holes), outline, (nx, ny, len(holes))


def slot_meshes(stl):
    """The panel placed on each window for the inspector: wall frame u, v (window centre), w out of the steel."""
    import numpy as np
    import trimesh
    m = trimesh.load(stl)
    wins = {"control": E.ctrl_window()[0]}
    wins["power_left"], wins["power_right"] = (w[0] for w in E.window_panes())
    for k, poly in wins.items():
        c = poly.centroid
        mm = m.copy()
        mm.vertices = np.column_stack([mm.vertices[:, 0] + c.x, mm.vertices[:, 1] + c.y, R.PLATE_T - mm.vertices[:, 2]])
        mm.invert()                                       # the w flip mirrors the mesh; keep normals outward
        mm.export(OUT / f"meccano_{k}.stl")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    p, outline, (nx, ny, n) = panel()
    export_stl(p, str(OUT / "window_meccano.stl"))
    slot_meshes(OUT / "window_meccano.stl")
    bb = p.bounding_box()
    print(f"window_meccano: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm, {n} Meccano holes ({nx} x {ny}), {p.volume / 1000:.1f} cm3")


if __name__ == "__main__":
    main()
