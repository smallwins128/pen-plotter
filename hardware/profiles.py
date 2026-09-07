"""Parametric 20-series T-slot extrusion.

`tslot_bar()` returns a length of extrusion as a solid, centred on the origin
and running along the axis you ask for. Everything else in `parts/` builds on
this, so it is worth it being right.

Fidelity note: the cross-section is accurate on the outside (envelope,
chamfers, slot openings, slot depth, bore positions) and simplified on the
inside -- real vendor profiles have slightly different internal webs and a
rounded channel root. It is right for fit, clearance and layout; it is not a
substitute for the vendor drawing if you are machining against it.
"""

import math
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from build123d import (
    BuildPart,
    BuildSketch,
    Mode,
    Plane,
    Polygon,
    Circle,
    Rectangle,
    chamfer,
    extrude,
    Locations,
)

from params import (
    BORE_D,
    CELL,
    PROFILE_CHAMFER,
    SLOT_DEPTH,
    SLOT_FLARE_D,
    SLOT_INNER_W,
    SLOT_LIP_D,
    SLOT_MOUTH_W,
    SLOT_ROOT_W,
)


def _rotate(pts, degrees):
    """Rotate a list of (x, y) about the origin."""
    a = math.radians(degrees)
    c, s = math.cos(a), math.sin(a)
    return [(x * c - y * s, x * s + y * c) for x, y in pts]


def _translate(pts, dx, dy):
    return [(x + dx, y + dy) for x, y in pts]


def _slot_outline():
    """One T-slot, opening towards +Y, mouth on the line y = 0.

    Widens from the mouth to SLOT_INNER_W, then tapers back to SLOT_ROOT_W at
    full depth. That closing taper is load-bearing: it is what leaves the
    diagonal webs tying each corner of the section to the middle.

    Overshoots the face by a little so the boolean cut is clean rather than
    leaving a zero-thickness skin.
    """
    mouth = SLOT_MOUTH_W / 2.0
    inner = SLOT_INNER_W / 2.0
    root = SLOT_ROOT_W / 2.0
    over = 0.5           # overshoot past the outer face

    return [
        (-mouth, over),
        (-mouth, -SLOT_LIP_D),
        (-inner, -SLOT_FLARE_D),
        (-root, -SLOT_DEPTH),
        (root, -SLOT_DEPTH),
        (inner, -SLOT_FLARE_D),
        (mouth, -SLOT_LIP_D),
        (mouth, over),
    ]


def _cell_centres(extent):
    """Centres of the 20 mm cells across an extent, measured from the middle."""
    n = int(round(extent / CELL))
    return [(-extent / 2.0) + CELL * (i + 0.5) for i in range(n)]


def _slot_placements(w, h):
    """(points, ) for every slot in a w x h profile, in sketch coordinates."""
    base = _slot_outline()
    placements = []

    # The two faces normal to Y: one slot per cell across the width.
    for xc in _cell_centres(w):
        placements.append(_translate(base, xc, h / 2.0))                  # +Y
        placements.append(_translate(_rotate(base, 180), xc, -h / 2.0))   # -Y

    # The two faces normal to X: one slot per cell up the height.
    for yc in _cell_centres(h):
        placements.append(_translate(_rotate(base, -90), w / 2.0, yc))    # +X
        placements.append(_translate(_rotate(base, 90), -w / 2.0, yc))    # -X

    return placements


def _section(w, h, plane):
    """Draw the cross-section on `plane` and return it as a standalone Sketch.

    build123d resolves its builder context by walking call frames, so a sketch
    opened inside a helper does not register with a BuildPart in the caller.
    Hand the returned sketch to `extrude` explicitly instead.
    """
    with BuildSketch(plane) as sk:
        Rectangle(w, h)
        chamfer(sk.vertices(), length=PROFILE_CHAMFER)

        for pts in _slot_placements(w, h):
            Polygon(*pts, align=None, mode=Mode.SUBTRACT)

        for xc in _cell_centres(w):
            for yc in _cell_centres(h):
                with Locations((xc, yc)):
                    Circle(BORE_D / 2.0, mode=Mode.SUBTRACT)

    return sk.sketch


def _assert_connected(sketch, w, h):
    """The section must be one connected face.

    If a slot is cut too deep or its root too wide, the four corners of the
    section detach from the core and the "extrusion" becomes five floating
    slivers -- which still exports happily to STEP and STL, and is silently
    nonsense. Cheap to check, so check it every time.
    """
    n = len(sketch.faces())
    if n != 1:
        raise ValueError(
            f"{w:g}x{h:g} section came out as {n} disconnected regions, not 1. "
            "The slot geometry in params.py has severed the corner webs -- "
            "reduce SLOT_DEPTH, SLOT_INNER_W or SLOT_ROOT_W."
        )


def tslot_sketch(w, h, plane=Plane.XY):
    """The 2D cross-section on its own, for area checks and DXF export."""
    sketch = _section(w, h, plane)
    _assert_connected(sketch, w, h)
    return sketch


def tslot_bar(length, w, h, axis="Z"):
    """A length of w x h extrusion running along `axis`, centred on the origin.

    The profile's `w` lies in the table plane and `h` runs along Z for the X
    and Y axes, which is what a flat frame wants. The section is drawn on the
    target plane rather than being modelled once and rotated, so the slots stay
    square to the world axes.
    """
    plane = {"X": Plane.YZ, "Y": Plane.XZ, "Z": Plane.XY}[axis.upper()]
    section = _section(w, h, plane)
    _assert_connected(section, w, h)

    with BuildPart() as bar:
        extrude(to_extrude=section, amount=length / 2.0, both=True)

    return bar.part


def section_area(w, h):
    """Cross-sectional area of the modelled profile, mm^2."""
    return tslot_sketch(w, h).area


def section_polylines(w, h, samples=900):
    """The section as closed (x, y) polylines: outer boundary first, then bores.

    For plotting and quick checks. Sampled by wire parameter, so curves come out
    smooth and straight runs are over-sampled but harmless.
    """
    face = tslot_sketch(w, h).faces()[0]
    wires = [face.outer_wire()] + list(face.inner_wires())

    lines = []
    for wire in wires:
        pts = [(p.X, p.Y) for p in (wire @ (i / samples) for i in range(samples + 1))]
        lines.append(pts)
    return lines


if __name__ == "__main__":
    import pathlib

    from params import PROFILE_H, PROFILE_W, ALUMINIUM_DENSITY

    out = pathlib.Path(__file__).resolve().parent / "out"
    out.mkdir(parents=True, exist_ok=True)

    area = section_area(PROFILE_W, PROFILE_H)
    print(f"{PROFILE_W:g} x {PROFILE_H:g} section")
    print(f"  area        {area:.1f} mm^2")
    print(f"  linear mass {area * ALUMINIUM_DENSITY:.3f} kg/m (aluminium)")

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    lines = section_polylines(PROFILE_W, PROFILE_H)
    fig, ax = plt.subplots(figsize=(4, 7), dpi=160)
    ax.fill(*zip(*lines[0]), facecolor="#b8c0c8", edgecolor="#2f3640", linewidth=1.1)
    for bore in lines[1:]:
        ax.fill(*zip(*bore), facecolor="white", edgecolor="#2f3640", linewidth=1.1)
    ax.set_aspect("equal")
    ax.set_xlabel("mm")
    ax.set_title(f"{PROFILE_W:g} x {PROFILE_H:g} section  ({area:.0f} mm²)", fontsize=10)
    ax.grid(True, linewidth=0.3, alpha=0.4)
    fig.tight_layout()

    png = out / f"profile_{PROFILE_W:g}x{PROFILE_H:g}.png"
    fig.savefig(png, facecolor="white")
    print(f"  wrote       {png.relative_to(out.parent.parent)}")
