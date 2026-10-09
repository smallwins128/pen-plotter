"""Bench-supply style panels for the power link between the two boxes: five
binding posts (24 V, 12 V, 6 V, G1, G2) on each box, plus switches, a rail
selector and an analog meter on the PSU box.

    python3 hardware/parts/link_panel.py

Writes hardware/out/link_panel_{psu,ctrl}.{stl,step} and link_panel_layout.png.

A panel is a plate bigger than the hole cut in the box: the FLANGE rim sits on
the outside of the box wall and carries the screws, and a shallow BOSS on the
back drops into the cutout so the plate centres itself. Every component hole
is inside the boss, so components mount through plate + boss and their bodies
pass through the box cutout. Each post, switch and the selector has a shallow
LABEL pocket under it, sized for 12 mm Dymo tape or a printed paper label.

Hole sizes are typical, not measured. Check them against the parts you buy.

The STL is exported face-down, ready to print: the bed gives the front its
finish, and the label pockets print as open recesses with no bridging.

Wiring notes, so they live next to the panel:
  - G1 is the Ender PSU 0 V; G2 is the 12 V / 6 V return. They are NOT joined
    in the PSU box -- only at the star point in the control box.
  - Switches are in the + line only, after the fuse: PSU -> fuse -> switch -> post.
  - The selector is 2-pole: it switches the meter across each rail AND that
    rail's own ground, because G1 and G2 are separate inside the PSU box.
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from build123d import (
    Align,
    Axis,
    Box,
    BuildPart,
    Cylinder,
    Locations,
    Mode,
    Pos,
)

DENSITY = 1.24e-3     # PLA, g/mm^3
LINEAR_STOCK = False

# Plate
PLATE_T = 3.0         # front plate thickness
FLANGE = 10.0         # rim past the box cutout, on every side
BOSS_H = 2.0          # back boss depth; roughly your box wall thickness
BOSS_CLEAR = 0.3      # boss is this much smaller than the cutout, per side
SCREW_D = 3.4         # M3 clearance, in the flange
MARGIN = 6.0          # cutout edge to nearest component

# Component holes -- typical sizes, measure yours
HOLE = {
    "post": 8.0,        # 4 mm binding post
    "toggle": 12.2,     # full-size bat toggle, 15/32" bushing
    "selector": 9.8,    # rotary switch, 3/8" bushing
    "meter": 52.0,      # round 2" analog panel meter body
}

PITCH = 22.0          # column spacing for posts and switches
ROW = 20.5            # component row height
LABEL = (20.0, 13.0)  # label pocket, w x h
LABEL_D = 0.6         # pocket depth
LABEL_GAP = 3.5       # component row to label pocket
METER_AREA = 70.0     # width given to the meter on the PSU panel

POSTS = ["24V", "12V", "6V", "G1", "G2"]
SWITCHES = ["24V", "12V", "6V"]   # over the first three posts


def _layout(kind):
    """Cutout size and component list, in cutout coordinates (0,0 = bottom-left
    of the cutout). Returns (w, h, [(part, x, y, label), ...])."""
    lab_h = LABEL[1]
    post_lab_y = MARGIN + lab_h / 2
    post_y = post_lab_y + lab_h / 2 + LABEL_GAP + ROW / 2
    x0 = MARGIN + (METER_AREA if kind == "psu" else 0)
    cols = [x0 + PITCH / 2 + i * PITCH for i in range(len(POSTS))]

    items = [("post", x, post_y, name) for x, name in zip(cols, POSTS)]
    top = post_y + ROW / 2

    if kind == "psu":
        sw_lab_y = top + LABEL_GAP + lab_h / 2
        sw_y = sw_lab_y + lab_h / 2 + LABEL_GAP + ROW / 2
        items += [("toggle", x, sw_y, name) for x, name in zip(cols, SWITCHES)]
        items.append(("selector", (cols[3] + cols[4]) / 2, sw_y, "METER"))
        top = sw_y + ROW / 2
        h = top + MARGIN
        items.append(("meter", MARGIN + METER_AREA / 2, h / 2, None))
    else:
        h = top + MARGIN

    w = cols[-1] + PITCH / 2 + MARGIN
    return w, h, items


def _label_y(y):
    return y - ROW / 2 - LABEL_GAP - LABEL[1] / 2


def _screws(w, h):
    """Screw centres in the flange, plate-centred coordinates."""
    W, H = w + 2 * FLANGE, h + 2 * FLANGE
    ex, ey = W / 2 - FLANGE / 2, H / 2 - FLANGE / 2
    pts = [(sx * ex, sy * ey) for sx in (-1, 1) for sy in (-1, 1)]
    if W > 150:
        pts += [(0, ey), (0, -ey)]
    return pts


def build_panel(kind):
    """Front face at Z = PLATE_T, back of the boss at Z = -BOSS_H, centred in
    X/Y. Looking at the front, +X right, +Y up."""
    w, h, items = _layout(kind)
    W, H = w + 2 * FLANGE, h + 2 * FLANGE
    cx, cy = w / 2, h / 2   # cutout coords -> plate-centred

    with BuildPart() as p:
        Box(W, H, PLATE_T, align=(Align.CENTER, Align.CENTER, Align.MIN))
        Box(w - 2 * BOSS_CLEAR, h - 2 * BOSS_CLEAR, BOSS_H,
            align=(Align.CENTER, Align.CENTER, Align.MAX))

        for part, x, y, label in items:
            with Locations((x - cx, y - cy, 0)):
                Cylinder(HOLE[part] / 2, 40, mode=Mode.SUBTRACT)
            if label:
                with Locations((x - cx, _label_y(y) - cy, PLATE_T)):
                    Box(*LABEL, 2 * LABEL_D, mode=Mode.SUBTRACT)

        with Locations(*[(x, y, 0) for x, y in _screws(w, h)]):
            Cylinder(SCREW_D / 2, 40, mode=Mode.SUBTRACT)
    return p.part


def build():
    return build_panel("psu")


def draw_layout(path):
    """Front-view drawing of both panels, with the cutout to make in the box."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle

    fig, axes = plt.subplots(2, 1, figsize=(11, 10), dpi=120,
                             gridspec_kw={"height_ratios": [1.6, 1]})
    for ax, kind, title in zip(axes, ["psu", "ctrl"], ["PSU box", "Control box"]):
        w, h, items = _layout(kind)
        W, H = w + 2 * FLANGE, h + 2 * FLANGE
        ax.add_patch(Rectangle((-FLANGE, -FLANGE), W, H, fc="#d9d4c7", ec="k", lw=1.2))
        ax.add_patch(Rectangle((0, 0), w, h, fill=False, ec="#b0412e", ls="--", lw=1))
        ax.text(w - 1, h - 1.5, f"box cutout {w:.0f} x {h:.0f}", ha="right", va="top",
                color="#b0412e", fontsize=8)
        for x, y in _screws(w, h):
            ax.add_patch(Circle((x + w / 2, y + h / 2), SCREW_D / 2, fc="white", ec="k"))
        colours = {"24V": "#c0392b", "12V": "#e67e22", "6V": "#f1c40f",
                   "G1": "#222222", "G2": "#222222", "METER": "#555555"}
        for part, x, y, label in items:
            ax.add_patch(Circle((x, y), HOLE[part] / 2, fc="white", ec="k"))
            if part == "post":
                ax.add_patch(Circle((x, y), 6.5, fill=False, ec=colours[label], lw=2.5))
            if part == "meter":
                ax.text(x, y, "0-30 V\nmeter", ha="center", va="center", fontsize=9)
            if label:
                ly = _label_y(y)
                ax.add_patch(Rectangle((x - LABEL[0] / 2, ly - LABEL[1] / 2), *LABEL,
                                       fc="white", ec="#888", lw=0.8))
                ax.text(x, ly, label, ha="center", va="center", fontsize=8,
                        family="monospace", weight="bold")
        ax.set_xlim(-FLANGE - 3, w + FLANGE + 3)
        ax.set_ylim(-FLANGE - 3, h + FLANGE + 3)
        ax.set_aspect("equal")
        ax.set_title(f"{title}: plate {W:.0f} x {H:.0f} mm, {PLATE_T:.0f} mm thick "
                     f"+ {BOSS_H:.0f} mm boss", fontsize=10)
        ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main(argv):
    from build123d import export_step, export_stl

    out = pathlib.Path(__file__).resolve().parent.parent / "out"
    out.mkdir(exist_ok=True)
    for kind in ("psu", "ctrl"):
        part = build_panel(kind)
        name = f"link_panel_{kind}"
        export_step(part, str(out / f"{name}.step"))
        export_stl(part.rotate(Axis.X, 180), str(out / f"{name}.stl"))
        w, h, _ = _layout(kind)
        bb = part.bounding_box()
        print(f"{name:16s} plate {bb.size.X:.0f} x {bb.size.Y:.0f} mm   "
              f"cut the box {w:.0f} x {h:.0f} mm   {part.volume * DENSITY:.0f} g")
    draw_layout(out / "link_panel_layout.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
