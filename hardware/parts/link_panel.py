"""Bench-supply style panel for the PSU end of the power link: three voltage
rows (24 V, 12 V, 6 V), each label -> toggle -> 2-wire voltage display ->
4 mm banana jack, and a separate ground column with G1 and G2.

    python3 hardware/parts/link_panel.py

Writes hardware/out/link_panel_psu.{stl,step} and link_panel_mockup.png
(true-scale front view).

    ┌───────────────────────────────────────┐
    │ 24V  [sw]  [ 24.1 ]  (O)    G1  (O)   │
    │ 12V  [sw]  [ 12.0 ]  (O)              │
    │  6V  [sw]  [  6.0 ]  (O)    G2  (O)   │
    └───────────────────────────────────────┘

A panel is a plate bigger than the hole cut in the box: the FLANGE rim sits on
the outside of the box wall and carries the screws, and a shallow BOSS on the
back drops into the cutout so the plate centres itself. Every component hole
is inside the boss.

The display is the bare 0.36" 3-digit 2-wire voltmeter (2.5-30 V): a
22.70 x 10.42 x 7.5 mm display block on a PCB 30.40 mm across its mounting
ears (listing dimensions). The block pokes through a window; the ears sit
behind the panel on two M2 screws. Ear hole spacing is ESTIMATED from the
listing photo -- measure it. Jack and toggle sizes are still typical.

Spacing is set from what each part occupies BEHIND the panel (the display's
PCB ears, the jack and toggle nuts), plus GAP of clear space, so there is
room for a spanner and the wiring.

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

from build123d import (Align, Axis, Box, BuildPart, BuildSketch, Cylinder, Locations,
                       Mode, RectangleRounded, extrude)

DENSITY = 1.24e-3     # PLA, g/mm^3
LINEAR_STOCK = False

# Plate
PLATE_T = 3.0         # front plate thickness
FLANGE = 8.0          # rim past the box cutout, on every side
BOSS_H = 2.0          # back boss depth; roughly your box wall thickness
BOSS_CLEAR = 0.3      # boss is this much smaller than the cutout, per side
SCREW_D = 3.4         # M3 clearance, in the flange
CORNER_R = 5.0        # plate corner radius
MARGIN = 6.0          # cutout edge to nearest component
GAP = 6.0             # clear space between neighbouring components in a row
ROW_CLEAR = 8.0       # clear space between rows

# 0.36" bare voltmeter module, from the listing
DISP_W, DISP_H = 22.70, 10.42   # display block, pokes through the window
DISP_CLEAR = 0.3                # window clearance per side
DISP_PCB_W = 30.40              # across the mounting ears, behind the panel
DISP_PCB_H = 12.0               # PCB height behind the panel (estimate)
DISP_EAR_PITCH = 26.6           # ear hole centres (ESTIMATE -- measure)
DISP_SCREW_D = 2.2              # M2 clearance
DIGIT_H = 9.1                   # 0.36"

JACK_HOLE = 8.0       # 4 mm banana panel jack
JACK_COLLAR = 14.0    # its front collar / nut, for spacing
TOGGLE_HOLE = 6.2     # mini bat toggle, 6 mm bushing
TOGGLE_W = 13.0       # its body, for spacing
LABEL = (14.0, 10.0)  # label pocket, fits 9 mm Dymo tape
LABEL_D = 0.6

RAILS = ["24V", "12V", "6V"]
GROUNDS = ["G1", "G2"]
GROUP_GAP = 10.0      # extra space between the voltage rows and the grounds
RAIL_COLOUR = {"24V": "#c0392b", "12V": "#e67e22", "6V": "#f1c40f",
               "G1": "#1a1a1a", "G2": "#1a1a1a"}


def _layout():
    """Cutout size and component list in cutout coordinates (0,0 = bottom-left
    of the cutout). Items are (kind, x, y, name).

    Portrait: each voltage row runs jack -> label -> display -> toggle, left to
    right; the two ground jacks sit below in the jack column, after a gap."""
    row_h = max(DISP_PCB_H, JACK_COLLAR, TOGGLE_W, LABEL[1]) + ROW_CLEAR

    x = MARGIN
    x_jack = x + JACK_COLLAR / 2;  x += JACK_COLLAR + GAP
    x_label = x + LABEL[0] / 2;    x += LABEL[0] + GAP
    x_disp = x + DISP_PCB_W / 2;   x += DISP_PCB_W + GAP
    x_toggle = x + TOGGLE_W / 2;   x += TOGGLE_W + MARGIN
    w = x
    h = 2 * MARGIN + (len(RAILS) + len(GROUNDS)) * row_h + GROUP_GAP

    items = []
    y = h - MARGIN - row_h / 2
    for rail in RAILS:
        items += [("jack", x_jack, y, rail), ("label", x_label, y, rail),
                  ("display", x_disp, y, rail), ("toggle", x_toggle, y, rail)]
        y -= row_h
    y -= GROUP_GAP
    for name in GROUNDS:
        items += [("jack", x_jack, y, name), ("label", x_label, y, name)]
        y -= row_h
    return w, h, items


def _screws(w, h):
    """Screw centres in the flange, plate-centred coordinates."""
    ex, ey = w / 2 + FLANGE / 2, h / 2 + FLANGE / 2
    return [(sx * ex, sy * ey) for sx in (-1, 1) for sy in (-1, 1)]


def build_panel():
    """Front face at Z = PLATE_T, back of the boss at Z = -BOSS_H, centred in
    X/Y. Looking at the front, +X right, +Y up."""
    w, h, items = _layout()
    cx, cy = w / 2, h / 2

    with BuildPart() as p:
        with BuildSketch():
            RectangleRounded(w + 2 * FLANGE, h + 2 * FLANGE, CORNER_R)
        extrude(amount=PLATE_T)
        Box(w - 2 * BOSS_CLEAR, h - 2 * BOSS_CLEAR, BOSS_H,
            align=(Align.CENTER, Align.CENTER, Align.MAX))

        for kind, x, y, _ in items:
            with Locations((x - cx, y - cy, 0)):
                if kind == "display":
                    Box(DISP_W + 2 * DISP_CLEAR, DISP_H + 2 * DISP_CLEAR, 40,
                        mode=Mode.SUBTRACT)
                    with Locations((-DISP_EAR_PITCH / 2, 0), (DISP_EAR_PITCH / 2, 0)):
                        Cylinder(DISP_SCREW_D / 2, 40, mode=Mode.SUBTRACT)
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
    return build_panel()


def draw_mockup(path):
    """True-scale front view with parts fitted. Dashed outlines show what sits
    behind the panel, so the clear space between parts is visible."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

    w, h, items = _layout()
    W, H = w + 2 * FLANGE, h + 2 * FLANGE
    fig, ax = plt.subplots(figsize=(W / 14, H / 14 + 1), dpi=130)
    ax.set_xlim(-5, W + 5)
    ax.set_ylim(-14, H + 5)
    ax.set_aspect("equal")
    ax.axis("off")
    x0 = y0 = FLANGE
    behind = dict(fill=False, ec="#8a8f94", ls="--", lw=0.8)

    ax.add_patch(FancyBboxPatch((0, 0), W, H, boxstyle=f"round,pad=0,rounding_size={CORNER_R}",
                                fc="#2b2d2f", ec="#111", lw=1.5))
    ax.add_patch(Rectangle((x0, y0), w, h, fill=False, ec="#b0412e", ls=":", lw=0.8))
    for sx, sy in _screws(w, h):
        ax.add_patch(Circle((x0 + w / 2 + sx, y0 + h / 2 + sy), 2.8,
                            fc="#b8b8b8", ec="#555"))
    for kind, x, y, name in items:
        x, y = x0 + x, y0 + y
        if kind == "label":
            lw_, lh = LABEL
            ax.add_patch(Rectangle((x - lw_ / 2, y - lh / 2), lw_, lh,
                                   fc="#e8e2cf", ec="none"))
            ax.text(x, y, name, ha="center", va="center", fontsize=7,
                    family="monospace", weight="bold", color="#222")
        elif kind == "toggle":
            ax.add_patch(Rectangle((x - TOGGLE_W / 2, y - TOGGLE_W / 2),
                                   TOGGLE_W, TOGGLE_W, **behind))
            ax.add_patch(Circle((x, y), 4.5, fc="#c9c9c9", ec="#777"))
            ax.plot([x, x], [y, y + 8], color="#e0e0e0", lw=3,
                    solid_capstyle="round")
        elif kind == "display":
            ax.add_patch(Rectangle((x - DISP_PCB_W / 2, y - DISP_PCB_H / 2),
                                   DISP_PCB_W, DISP_PCB_H, **behind))
            ax.add_patch(Rectangle((x - DISP_W / 2, y - DISP_H / 2), DISP_W, DISP_H,
                                   fc="#111", ec="#444"))
            for ex in (-DISP_EAR_PITCH / 2, DISP_EAR_PITCH / 2):
                ax.add_patch(Circle((x + ex, y), 1.9, fc="#b8b8b8", ec="#555"))
            volts = {"24V": "24.1", "12V": "12.0", "6V": " 6.0"}[name]
            _digits(ax, volts.strip(), x, y)
        elif kind == "jack":
            ax.add_patch(Circle((x, y), JACK_COLLAR / 2, fc=RAIL_COLOUR[name], ec="#000"))
            ax.add_patch(Circle((x, y), 2.0, fc="#222", ec="#666"))
    ax.text(W / 2, -6, f'0.36" displays: plate {W:.0f} x {H:.0f} mm, box cutout '
            f'{w:.0f} x {h:.0f} mm.  Dashed = behind the panel.',
            ha="center", va="top", fontsize=9)
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _digits(ax, text, x, y):
    """Draw `text` centred at (x, y) with its digits exactly DIGIT_H mm tall."""
    from matplotlib.font_manager import FontProperties
    from matplotlib.patches import PathPatch
    from matplotlib.textpath import TextPath
    from matplotlib.transforms import Affine2D

    font = FontProperties(family="DejaVu Sans", weight="bold")
    ref = TextPath((0, 0), "0", size=1, prop=font).get_extents()
    tp = TextPath((0, 0), text, size=1, prop=font)
    ext = tp.get_extents()
    k = DIGIT_H / ref.height
    kx = min(k, 0.85 * DISP_W / ext.width)   # 7-segment digits are narrow
    t = (Affine2D().translate(-ext.x0 - ext.width / 2, -ref.y0 - ref.height / 2)
         .scale(kx, k).translate(x, y))
    ax.add_patch(PathPatch(t.transform_path(tp), fc="#ff3b2f", ec="none"))


def main(argv):
    from build123d import export_step, export_stl

    out = pathlib.Path(__file__).resolve().parent.parent / "out"
    out.mkdir(exist_ok=True)
    part = build_panel()
    export_step(part, str(out / "link_panel_psu.step"))
    export_stl(part.rotate(Axis.X, 180), str(out / "link_panel_psu.stl"))  # face-down
    w, h, _ = _layout()
    print(f"link_panel_psu  plate {w + 2 * FLANGE:.0f} x {h + 2 * FLANGE:.0f} mm   "
          f"cut the box {w:.0f} x {h:.0f} mm   {part.volume * DENSITY:.0f} g")
    draw_mockup(out / "link_panel_mockup.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
