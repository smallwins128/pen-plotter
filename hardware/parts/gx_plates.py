"""GX16 plates for the control box front: plain plates with GX16 holes, on the panel rules (panel_rules.py).

Three plates over the three steel openings (steppers ×3, servo ×1, endstops ×2). Socket positions, openings and
rivnuts come from the steel model (enclosure.GX_GROUPS / gx_openings / gx_plate), so plate and steel always agree.

    python3 hardware/parts/gx_plates.py      # writes hardware/out/gx_plates/*.stl + preview.png
"""
import pathlib
import sys

from build123d import export_stl
from shapely.geometry import box as sbox

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "sheet"))
import enclosure as E  # noqa: E402
import panel_rules as R  # noqa: E402
from fit_kit import FIT  # noqa: E402
from window_inserts import rounded  # noqa: E402

OUT = HERE.parent / "out" / "gx_plates"
OPEN_R = 3.0                                   # steel opening corner radius (as cut)


def plate(g):
    rect, riv = E.gx_openings()[g]
    opening = rounded(sbox(*rect), OPEN_R)
    outline = E.gx_plate(rect, g)
    holes = [(x, y, FIT["gx16"]) for x, y in E.GX_GROUPS[g]]
    bad = [c for c in R.check(outline, opening, riv) if not (c[2] and c[3])]
    if bad:
        raise SystemExit(f"{g}: rivnut relief too close to the plate edge or the lip: {bad}")
    return R.panel(outline, opening, riv, holes), outline


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import trimesh
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig = plt.figure(figsize=(15, 5), dpi=120)
    for i, g in enumerate(E.GX_GROUPS):
        p, outline = plate(g)
        export_stl(p, str(OUT / f"gx_plate_{g}.stl"))
        bb = p.bounding_box()
        print(f"gx_plate_{g}: {bb.size.X:.0f} x {bb.size.Y:.0f} x {bb.size.Z:.1f} mm, {p.volume / 1000:.1f} cm3")
        m = trimesh.load(OUT / f"gx_plate_{g}.stl")
        ax = fig.add_subplot(1, 3, i + 1, projection="3d")
        light = (m.face_normals @ [0.3, 0.6, 0.75] + 1.2) / 2.2
        ax.add_collection3d(Poly3DCollection(m.triangles, facecolors=[(0.2 + 0.5 * l,) * 3 for l in light], linewidths=0))
        lo, hi = m.bounds; c = (lo + hi) / 2; r = (hi - lo).max() / 2
        ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(c[2] - r, c[2] + r)
        ax.set_box_aspect((1, 1, 1)); ax.view_init(-55, -100); ax.set_axis_off(); ax.set_title(f"{g} (back: lip + reliefs)")
    fig.tight_layout(); fig.savefig(OUT / "preview.png")


if __name__ == "__main__":
    main()
