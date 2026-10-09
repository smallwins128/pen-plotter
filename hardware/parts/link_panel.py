"""Bench-supply style panel for the PSU end of the power link: three voltage
rows (24 V, 12 V, 6 V), each label -> toggle -> 2-wire voltage display ->
4 mm banana jack, and a separate ground column with G1 and G2.

    python3 hardware/parts/link_panel.py          # both display sizes

Writes hardware/out/link_panel_psu_{056,036}.{stl,step} and
link_panel_mockup.png (true-scale front views, side by side).

    ┌───────────────────────────────────────┐
    │ 24V  [sw]  [ 24.1 ]  (O)    G1  (O)   │
    │ 12V  [sw]  [ 12.0 ]  (O)              │
    │  6V  [sw]  [  6.0 ]  (O)    G2  (O)   │
    └───────────────────────────────────────┘

A panel is a plate bigger than the hole cut in the box: the FLANGE rim sits on
the outside of the box wall and carries the screws, and a shallow BOSS on the
back drops into the cutout so the plate centres itself. Every component hole
is inside the boss.

ALL PART SIZES BELOW ARE TYPICAL, NOT MEASURED. Replace them from the specs
of the parts actually bought before printing.

Wiring notes, so they live next to the panel:
  - G1 is the Ender PSU 0 V; G2 is the 12 V / 6 V return. They are NOT joined
    in the PSU box -- only at the star point in the control box.
  - Switches are in the + line only, after the fuse: PSU -> fuse -> switch -> jack.
  - A 2-wire display is powered by the voltage it reads, so wire it after the
    switch: it then doubles as the "rail is on" lamp. Its - goes to that
    rail's own ground (G1 for 24 V, G2 for 12 V and 6 V).
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from build123d import Align, Axis, Box, BuildPart, Cylinder, Locations, Mode

DENSITY = 1.24e-3     # PLA, g/mm^3
LINEAR_STOCK = False

# Plate
PLATE_T = 3.0         # front plate thickness
FLANGE = 8.0          # rim past the box cutout, on every side
BOSS_H = 2.0          # back boss depth; roughly your box wall thickness
BOSS_CLEAR = 0.3      # boss is this much smaller than the cutout, per side
SCREW_D = 3.4         # M3 clearance, in the flange
MARGIN = 5.0          # cutout edge to nearest component
GAP = 3.0             # between neighbouring components in a row

# Displays: (bezel w, bezel h, cutout w, cutout h, digit height). Typical.
DISPLAYS = {
    "056": (48.0, 29.0, 45.5, 26.5, 14.2),   # 0.56", 3 digit, 2 wire
    "036": (30.0, 17.0, 28.0, 15.0, 9.1),    # 0.36", 3 digit, 2 wire, cased
}

JACK_HOLE = 8.0       # 4 mm banana panel jack
JACK_COLLAR = 14.0    # its front collar / nut, for spacing
TOGGLE_HOLE = 6.2     # mini bat toggle, 6 mm bushing
TOGGLE_W = 13.0       # its body, for spacing
LABEL = (16.0, 10.0)  # label pocket, fits 9 mm Dymo tape
LABEL_D = 0.6

RAILS = ["24V", "12V", "6V"]
GROUNDS = [("G1", 0), ("G2", 2)]   # (name, row it sits on)
RAIL_COLOUR = {"24V": "#c0392b", "12V": "#e67e22", "6V": "#f1c40f",
               "G1": "#1a1a1a", "G2": "#1a1a1a"}


def _layout(display):
    """Cutout size and component list in cutout coordinates (0,0 = bottom-left
    of the cutout). Items are (kind, x, y, name)."""
    bw, bh, _, _, _ = DISPLAYS[display]
    row_h = max(bh, JACK_COLLAR, LABEL[1]) + 5.0

    x = MARGIN
    x_label = x + LABEL[0] / 2;   x += LABEL[0] + GAP
    x_toggle = x + TOGGLE_W / 2;  x += TOGGLE_W + GAP
    x_disp = x + bw / 2;          x += bw + GAP + 1
    x_jack = x + JACK_COLLAR / 2; x += JACK_COLLAR + 2 * GAP
    x_glabel = x + LABEL[0] / 2;  x += LABEL[0] + GAP
    x_gjack = x + JACK_COLLAR / 2; x += JACK_COLLAR + MARGIN
    w = x
    h = 2 * MARGIN + len(RAILS) * row_h

    items = []
    for i, rail in enumerate(RAILS):
        y = h - MARGIN - row_h * (i + 0.5)
        items += [("label", x_label, y, rail), ("toggle", x_toggle, y, rail),
                  ("display", x_disp, y, rail), ("jack", x_jack, y, rail)]
    for name, row in GROUNDS:
        y = h - MARGIN - row_h * (row + 0.5)
        items += [("label", x_glabel, y, name), ("jack", x_gjack, y, name)]
    return w, h, items


def _screws(w, h):
    """Screw centres in the flange, plate-centred coordinates."""
    ex, ey = w / 2 + FLANGE / 2, h / 2 + FLANGE / 2
    return [(sx * ex, sy * ey) for sx in (-1, 1) for sy in (-1, 1)]


def build_panel(display="056"):
    """Front face at Z = PLATE_T, back of the boss at Z = -BOSS_H, centred in
    X/Y. Looking at the front, +X right, +Y up."""
    w, h, items = _layout(display)
    _, _, cw, ch, _ = DISPLAYS[display]
    cx, cy = w / 2, h / 2

    with BuildPart() as p:
        Box(w + 2 * FLANGE, h + 2 * FLANGE, PLATE_T,
            align=(Align.CENTER, Align.CENTER, Align.MIN))
        Box(w - 2 * BOSS_CLEAR, h - 2 * BOSS_CLEAR, BOSS_H,
            align=(Align.CENTER, Align.CENTER, Align.MAX))

        for kind, x, y, _ in items:
            with Locations((x - cx, y - cy, 0)):
                if kind == "display":
                    Box(cw, ch, 40, mode=Mode.SUBTRACT)
                elif kind == "jack":
                    Cylinder(JACK_HOLE / 2, 40, mode=Mode.SUBTRACT)
                elif kind == "toggle":
                    Cylinder(TOGGLE_HOLE / 2, 40, mode=Mode.SUBTRACT)
            if kind == "label":
                with Locations((x - cx, y - cy, PLATE_T)):
                    Box(*LABEL, 2 * LABEL_D, mode=Mode.SUBTRACT)

        with Locations(*[(x, y, 0) for x, y in _screws(w, h)]):
            Cylinder(SCREW_D / 2, 40, mode=Mode.SUBTRACT)
    return p.part


def build():
    return build_panel("056")


def draw_mockup(path, displays=("056", "036")):
    """True-scale front views with parts fitted, side by side on one grid."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

    sizes = [_layout(d)[:2] for d in displays]
    W = sum(w + 2 * FLANGE for w, _ in sizes) + 20 * (len(displays) - 1)
    H = max(h for _, h in sizes) + 2 * FLANGE
    fig, ax = plt.subplots(figsize=(W / 18, H / 18 + 1), dpi=130)

    ax.set_xlim(-5, W + 5)
    ax.set_ylim(-14, H + 5)
    ax.set_aspect("equal")
    ax.axis("off")
    scale = _pt_per_mm(ax, fig)

    ox = 0.0
    for d, (w, h) in zip(displays, sizes):
        _, _, items = _layout(d)
        bw, bh, _, _, digit = DISPLAYS[d]
        x0, y0 = ox + FLANGE, FLANGE

        ax.add_patch(FancyBboxPatch((ox, 0), w + 2 * FLANGE, h + 2 * FLANGE,
                                    boxstyle="round,pad=0,rounding_size=2",
                                    fc="#2b2d2f", ec="#111", lw=1.5))
        for sx, sy in _screws(w, h):
            ax.add_patch(Circle((x0 + w / 2 + sx, y0 + h / 2 + sy), 2.8,
                                fc="#b8b8b8", ec="#555"))
        for kind, x, y, name in items:
            x, y = x0 + x, y0 + y
            if kind == "label":
                ax.add_patch(Rectangle((x - LABEL[0] / 2, y - LABEL[1] / 2), *LABEL,
                                       fc="#e8e2cf", ec="none"))
                ax.text(x, y, name, ha="center", va="center", fontsize=7,
                        family="monospace", weight="bold", color="#222")
            elif kind == "toggle":
                ax.add_patch(Circle((x, y), 5.5, fc="#c9c9c9", ec="#777"))
                ax.plot([x, x], [y, y + 9], color="#e0e0e0", lw=3.5,
                        solid_capstyle="round")
            elif kind == "display":
                ax.add_patch(Rectangle((x - bw / 2, y - bh / 2), bw, bh,
                                       fc="#111", ec="#444"))
                volts = {"24V": "24.1", "12V": "12.0", "6V": " 6.0"}[name]
                ax.text(x, y, volts, ha="center", va="center", color="#ff3b2f",
                        family="DejaVu Sans", weight="bold",
                        fontsize=digit / 0.72 * 72 / 25.4 * scale)
            elif kind == "jack":
                ax.add_patch(Circle((x, y), JACK_COLLAR / 2, fc=RAIL_COLOUR[name],
                                    ec="#000"))
                ax.add_patch(Circle((x, y), 2.0, fc="#222", ec="#666"))
        ax.text(ox + (w + 2 * FLANGE) / 2, -6,
                f'{d[0]}.{d[1:]}" display — plate {w + 2 * FLANGE:.0f} x {h + 2 * FLANGE:.0f} mm,'
                f' box cutout {w:.0f} x {h:.0f} mm', ha="center", va="top", fontsize=9)
        ox += w + 2 * FLANGE + 20

    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _pt_per_mm(ax, fig):
    """Scale factor so text drawn in points comes out at its real size in mm."""
    fig.canvas.draw()
    x0, x1 = ax.get_xlim()
    px_per_mm = ax.get_window_extent().width / (x1 - x0)
    return px_per_mm / (fig.dpi / 25.4)


def main(argv):
    from build123d import export_step, export_stl

    out = pathlib.Path(__file__).resolve().parent.parent / "out"
    out.mkdir(exist_ok=True)
    for d in DISPLAYS:
        part = build_panel(d)
        name = f"link_panel_psu_{d}"
        export_step(part, str(out / f"{name}.step"))
        export_stl(part.rotate(Axis.X, 180), str(out / f"{name}.stl"))  # face-down
        w, h, _ = _layout(d)
        print(f"{name:20s} plate {w + 2 * FLANGE:.0f} x {h + 2 * FLANGE:.0f} mm   "
              f"cut the box {w:.0f} x {h:.0f} mm   {part.volume * DENSITY:.0f} g")
    draw_mockup(out / "link_panel_mockup.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
