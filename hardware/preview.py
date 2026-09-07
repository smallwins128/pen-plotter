#!/usr/bin/env python3
"""Render a PNG preview of a part, so you can eyeball a model without CAD.

    python3 hardware/preview.py           # every part
    python3 hardware/preview.py frame

Writes hardware/out/<name>.png. This is a sanity check, not a pretty render --
flat shading, no shadows. Its job is to let you catch "that hole is on the
wrong face" in one glance.
"""

import sys
import pathlib

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402
import trimesh  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "parts"))

from build123d import export_stl  # noqa: E402

OUT = HERE / "out"

# Viewing direction, degrees. Matches how you stand at the machine: looking
# down and from the front-left, so +X runs right and +Y away from you.
ELEV, AZIM = 28, -58

FACE_RGB = np.array([0.62, 0.66, 0.70])   # anodised-aluminium grey
LIGHT = np.array([0.4, -0.7, 0.6])


def _shaded_colours(mesh):
    """Flat lambertian shading from face normals."""
    light = LIGHT / np.linalg.norm(LIGHT)
    intensity = mesh.face_normals @ light
    intensity = 0.35 + 0.65 * np.clip(intensity, 0.0, 1.0)
    return np.clip(FACE_RGB[None, :] * intensity[:, None], 0, 1)


def render(name, part, path=None):
    OUT.mkdir(parents=True, exist_ok=True)
    path = path or OUT / f"{name}.png"

    stl = OUT / f"{name}.stl"
    if not stl.exists():
        export_stl(part, str(stl))
    mesh = trimesh.load(str(stl))

    fig = plt.figure(figsize=(11, 7), dpi=130)
    ax = fig.add_subplot(111, projection="3d")

    tris = mesh.vertices[mesh.faces]
    ax.add_collection3d(
        Poly3DCollection(
            tris,
            facecolors=_shaded_colours(mesh),
            edgecolors="none",
            linewidths=0,
        )
    )

    # Equal aspect: matplotlib will not do it for us on a 3D axis. Set the
    # limits to the real bounds and the box aspect to the real proportions,
    # rather than a cube -- otherwise a flat part like the frame renders as a
    # postage stamp floating in empty space.
    lo, hi = mesh.bounds
    size = np.maximum(hi - lo, 1e-6)
    pad = size.max() * 0.02
    ax.set_xlim(lo[0] - pad, hi[0] + pad)
    ax.set_ylim(lo[1] - pad, hi[1] + pad)
    ax.set_zlim(lo[2] - pad, hi[2] + pad)
    ax.set_box_aspect(size / size.max())
    ax.view_init(elev=ELEV, azim=AZIM)
    ax.set_axis_off()

    ax.set_title(
        f"{name}   {size[0]:.0f} x {size[1]:.0f} x {size[2]:.0f} mm",
        fontsize=11,
        color="#333333",
    )
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def main(argv):
    import make

    parts = make._parts()
    wanted = argv or list(parts)
    for name in wanted:
        if name not in parts:
            print(f"unknown part: {name}", file=sys.stderr)
            return 1
        build, _ = parts[name]
        path = render(name, build())
        print(f"wrote {path.relative_to(HERE.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
