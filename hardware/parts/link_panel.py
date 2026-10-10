"""Bench-supply style panel for the PSU end of the power link: three voltage
rows (24 V, 12 V, 6 V), each label -> toggle -> 2-wire voltage display ->
4 mm banana jack, and a separate ground column with G1 and G2.

    python3 hardware/parts/link_panel.py

Writes hardware/out/link_panel_{psu,ctrl}.{stl,step} and link_panel_mockup.png
(true-scale front views of both). "ctrl" is the receiving panel on the
control box: the same five jacks in the same order, with labels, nothing else.

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
listing photo -- measure it. Jack sizes are from its datasheet; the
toggle size is still typical.

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

import math

from build123d import (Align, Axis, Box, BuildPart, BuildSketch, Cone, Cylinder, Locations,
                       Mode, RectangleRounded, extrude)

DENSITY = 1.24e-3     # PLA, g/mm^3
LINEAR_STOCK = False

# Plate
PLATE_T = 3.0         # front plate thickness
FLANGE = 10.0         # rim past the box cutout, on every side
BOSS_H = 2.0          # back boss depth; roughly your box wall thickness
BOSS_CLEAR = 0.3      # boss is this much smaller than the cutout, per side
SCREW_D = 3.4         # M3 clearance, in the flange
CSK_D = 6.4           # countersink at the face: M3 countersunk head is 6.0
                      # (DIN 7991 / ISO 10642, 90 deg); 6.4 lets it sit just flush
CSK_ANGLE = 90.0
SCREW_INSET = 6.0     # screw centre in from both plate edges
CORNER_R = SCREW_INSET  # corner arc concentric with the screw: even wall all round
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

# 4 mm banana binding post, Sharvi Technologies datasheet: M12 x 0.75 body,
# drill 12 +/- 0.1, front cap 14.5 dia x 2 proud, 23.5 long overall.
JACK_HOLE = 12.2      # 12.0 drill + allowance for printed holes running small
JACK_COLLAR = 14.5    # front cap
JACK_NUT = 18.0       # M12 fine nut behind the panel, across corners, for spacing
# KN3(A)-101 SPST ON-OFF toggle, Sharvi Technologies datasheet: M12 x 0.75
# bushing, panel hole 12.2 with an anti-rotation key slot 1.9 wide reaching
# 0.9 past the hole edge, body 28 x 16 x 17 deep (+7 for screw terminals),
# lever 17.5 tall, throwing 30 deg across the 28 mm side.
TOGGLE_HOLE = 12.2
TOGGLE_KEY = (1.9, 0.9)   # key slot width, depth past the hole edge
TOGGLE_BODY = (28.0, 16.0)  # (along the lever throw, across it)
TOGGLE_NUT = 18.0     # M12 fine nut across corners
TOGGLE_THROW = "horizontal"   # "vertical": flick up/down; "horizontal": left/right
LABEL = (14.0, 10.0)  # label pocket, fits 9 mm Dymo tape
LABEL_D = 0.6

# GX16 aviation panel sockets for the machine cables, on the control box.
# Every pin count uses the same 16 mm shell, so the hole is the same; the pin
# count keys them (a 5-pin plug will not mate a 3-pin socket). The three
# steppers are all GX16-5 and CAN be swapped, so their labels matter.
GX_HOLE = 16.2        # GX16 panel hole (16 mm thread)
GX_NUT = 22.0         # rear nut / front flange, for spacing
GX_PITCH = 30.0       # centre to centre: leaves ~10 mm finger room round a plug's coupling ring
GX_ROWS = [[("X1", "GX16-5"), ("X2", "GX16-5"), ("Y", "GX16-5")],          # steppers
           [("XLIM", "GX16-3"), ("YLIM", "GX16-3"), ("PEN", "GX16-4")]]   # endstops, servo

RAILS = ["24V", "12V", "6V"]
GROUNDS = ["G1", "G2"]
GROUP_GAP = 10.0      # extra space between the voltage rows and the grounds
RAIL_COLOUR = {"24V": "#c0392b", "12V": "#e67e22", "6V": "#f1c40f",
               "G1": "#1a1a1a", "G2": "#1a1a1a"}


def _toggle_footprint():
    """(width, height) the toggle takes up behind the panel, as mounted."""
    along, across = TOGGLE_BODY
    w, h = (across, along) if TOGGLE_THROW == "vertical" else (along, across)
    return max(w, TOGGLE_NUT), max(h, TOGGLE_NUT)


def _layout_gx():
    """GX16 panel: one row per cable group, each socket with its label below."""
    cols = max(len(r) for r in GX_ROWS)
    row_h = GX_NUT + LABEL_GAP_GX + LABEL[1] + ROW_CLEAR
    w = 2 * MARGIN + cols * GX_PITCH
    h = 2 * MARGIN + len(GX_ROWS) * row_h - ROW_CLEAR
    items = []
    top = h - MARGIN
    for r, row in enumerate(GX_ROWS):
        y_gx = top - r * row_h - GX_NUT / 2
        for c, (name, _) in enumerate(row):
            x = MARGIN + GX_PITCH * (c + 0.5)
            items += [("gx", x, y_gx, name),
                      ("label", x, y_gx - GX_NUT / 2 - LABEL_GAP_GX - LABEL[1] / 2, name)]
    return w, h, items


LABEL_GAP_GX = 3.0    # GX16 flange to its label pocket


def _layout(kind="psu"):
    """Cutout size and component list in cutout coordinates (0,0 = bottom-left
    of the cutout). Items are (kind, x, y, name).

    Portrait: each voltage row runs jack -> label -> display -> toggle, left to
    right; the two ground jacks sit below in the jack column, after a gap.
    The "ctrl" panel (receiving end) is labels then jacks, left to right, on
    the same row pitch, so each rail sits at the same height on both panels."""
    if kind == "gx":
        return _layout_gx()
    tw, th = _toggle_footprint()
    row_h = max(DISP_PCB_H, JACK_NUT, th, LABEL[1]) + ROW_CLEAR

    x = MARGIN
    if kind == "psu":
        x_jack = x + JACK_NUT / 2;     x += JACK_NUT + GAP
        x_label = x + LABEL[0] / 2;    x += LABEL[0] + GAP
        x_disp = x + DISP_PCB_W / 2;   x += DISP_PCB_W + GAP
        x_toggle = x + tw / 2;         x += tw
    else:   # receiving panel: labels on the left, jacks on the right
        x_label = x + LABEL[0] / 2;    x += LABEL[0] + GAP
        x_jack = x + JACK_NUT / 2;     x += JACK_NUT
    w = x + MARGIN
    h = 2 * MARGIN + (len(RAILS) + len(GROUNDS)) * row_h + GROUP_GAP

    items = []
    y = h - MARGIN - row_h / 2
    for rail in RAILS:
        items += [("jack", x_jack, y, rail), ("label", x_label, y, rail)]
        if kind == "psu":
            items += [("display", x_disp, y, rail), ("toggle", x_toggle, y, rail)]
        y -= row_h
    y -= GROUP_GAP
    for name in GROUNDS:
        items += [("jack", x_jack, y, name), ("label", x_label, y, name)]
        y -= row_h
    return w, h, items


def _screws(w, h):
    """Screw centres in the flange, plate-centred coordinates."""
    ex, ey = w / 2 + FLANGE - SCREW_INSET, h / 2 + FLANGE - SCREW_INSET
    return [(sx * ex, sy * ey) for sx in (-1, 1) for sy in (-1, 1)]


def build_panel(kind="psu"):
    """Front face at Z = PLATE_T, back of the boss at Z = -BOSS_H, centred in
    X/Y. Looking at the front, +X right, +Y up."""
    w, h, items = _layout(kind)
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
                elif kind == "gx":
                    Cylinder(GX_HOLE / 2, 40, mode=Mode.SUBTRACT)
                elif kind == "jack":
                    Cylinder(JACK_HOLE / 2, 40, mode=Mode.SUBTRACT)
                elif kind == "toggle":
                    Cylinder(TOGGLE_HOLE / 2, 40, mode=Mode.SUBTRACT)
                    # key slot on the throw axis: above the hole for an
                    # up/down switch, to its left for a left/right one
                    kw, kd = TOGGLE_KEY
                    r = TOGGLE_HOLE / 2
                    if TOGGLE_THROW == "vertical":
                        with Locations((0, r + kd / 2 - 0.5)):
                            Box(kw, kd + 1.0, 40, mode=Mode.SUBTRACT)
                    else:
                        with Locations((-(r + kd / 2 - 0.5), 0)):
                            Box(kd + 1.0, kw, 40, mode=Mode.SUBTRACT)
            if kind == "label":
                with Locations((x - cx, y - cy, PLATE_T)):
                    Box(*LABEL, 2 * LABEL_D, mode=Mode.SUBTRACT)

        with Locations(*[(x, y, 0) for x, y in _screws(w, h)]):
            Cylinder(SCREW_D / 2, 40, mode=Mode.SUBTRACT)
        # 90 deg cone from CSK_D at the front face down to the clearance hole,
        # carried 1 mm above the face so the cut is clean
        csk_depth = (CSK_D - SCREW_D) / 2 / math.tan(math.radians(CSK_ANGLE / 2))
        over = 1.0
        with Locations(*[(x, y, PLATE_T - csk_depth) for x, y in _screws(w, h)]):
            Cone(SCREW_D / 2, CSK_D / 2 + over, csk_depth + over,
                 align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
    return p.part


def build():
    return build_panel()


def draw_mockup(path, kinds=("psu", "ctrl", "gx")):
    """True-scale front views of both panels, side by side, with parts fitted.
    Dashed outlines show what sits behind the panel, so the clear space between
    parts is visible."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

    sizes = [_layout(k)[:2] for k in kinds]
    SEP = 25.0
    TW = sum(w + 2 * FLANGE for w, _ in sizes) + SEP * (len(kinds) - 1)
    TH = max(h for _, h in sizes) + 2 * FLANGE
    fig, ax = plt.subplots(figsize=(TW / 14, TH / 14 + 1.5), dpi=130)
    ax.set_xlim(-5, TW + 5)
    ax.set_ylim(-22, TH + 5)
    ax.set_aspect("equal")
    ax.axis("off")
    behind = dict(fill=False, ec="#8a8f94", ls="--", lw=0.8)
    titles = {"psu": "PSU box (sending)", "ctrl": "Control box (receiving)",
              "gx": "Control box GX16 (machine)"}

    ox = 0.0
    for kind in kinds:
        ox = _draw_panel(ax, kind, ox, behind, titles[kind]) + SEP
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _draw_panel(ax, kind, ox, behind, title):
    """One panel's front view with its left edge at x = ox. Returns its right edge."""
    from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

    w, h, items = _layout(kind)
    W, H = w + 2 * FLANGE, h + 2 * FLANGE
    x0, y0 = ox + FLANGE, FLANGE

    ax.add_patch(FancyBboxPatch((ox, 0), W, H, boxstyle=f"round,pad=0,rounding_size={CORNER_R}",
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
            along, across = TOGGLE_BODY
            bw_, bh_ = (across, along) if TOGGLE_THROW == "vertical" else (along, across)
            ax.add_patch(Rectangle((x - bw_ / 2, y - bh_ / 2), bw_, bh_, **behind))
            ax.add_patch(Circle((x, y), 8.0, fc="#c9c9c9", ec="#777"))   # front nut
            ax.add_patch(Circle((x, y), 6.0, fc="#b0b0b0", ec="#777"))   # bushing
            dx, dy = (0, 9) if TOGGLE_THROW == "vertical" else (9, 0)
            ax.plot([x, x + dx], [y, y + dy], color="#111", lw=5,
                    solid_capstyle="round")                            # black lever
        elif kind == "display":
            ax.add_patch(Rectangle((x - DISP_PCB_W / 2, y - DISP_PCB_H / 2),
                                   DISP_PCB_W, DISP_PCB_H, **behind))
            ax.add_patch(Rectangle((x - DISP_W / 2, y - DISP_H / 2), DISP_W, DISP_H,
                                   fc="#111", ec="#444"))
            for ex in (-DISP_EAR_PITCH / 2, DISP_EAR_PITCH / 2):
                ax.add_patch(Circle((x + ex, y), 1.9, fc="#b8b8b8", ec="#555"))
            volts = {"24V": "24.1", "12V": "12.0", "6V": " 6.0"}[name]
            _digits(ax, volts.strip(), x, y)
        elif kind == "gx":
            ax.add_patch(Circle((x, y), GX_NUT / 2, fc="#9a9ea3", ec="#555"))   # knurled flange
            ax.add_patch(Circle((x, y), 8.0, fc="#c9ccd0", ec="#666"))         # shell
            ax.add_patch(Circle((x, y), 6.0, fc="#1b1b1b", ec="#444"))         # insert
            import math as _m
            n = {nm: int(t[-1]) for row in GX_ROWS for nm, t in row}[name]
            for i in range(n):
                a = 2 * _m.pi * i / n + _m.pi / 2
                ax.add_patch(Circle((x + 3.4 * _m.cos(a), y + 3.4 * _m.sin(a)), 0.7, fc="#d4af37", ec="none"))
        elif kind == "jack":
            ax.add_patch(Circle((x, y), JACK_COLLAR / 2, fc=RAIL_COLOUR[name], ec="#000"))
            ax.add_patch(Circle((x, y), 2.0, fc="#222", ec="#666"))
    ax.text(ox + W / 2, -5, f"{title}\nplate {W:.0f} x {H:.0f} mm\n"
            f"box cutout {w:.0f} x {h:.0f} mm", ha="center", va="top", fontsize=8.5)
    return ox + W


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


# ---------------------------------------------------------------------------
# Lid layouts: where each panel, fan and the IEC inlet sit on the two lids
# ---------------------------------------------------------------------------

LID_AREA = (200.0, 350.0)   # usable flat area on each lid top, w x h (measured)
FAN = 80.0                  # 8080 fan: 80 x 80, 76 mm hole, M4 at 71.5 mm
FAN_HOLE, FAN_SCREW_PITCH = 76.0, 71.5
IEC = (32.0, 55.0)          # fused + switched inlet module already fitted (approx)

# (name, kind, x, y) with x, y the top-left of the outline, measured from the
# top-left of the lid area. "panel:<kind>" uses the plate size from _layout.
# The two boxes sit hinge to hinge: the control box hinge is its right edge,
# the PSU box hinge its left edge. Board and drivers live in the control box
# BASE, panels on the LID, so wires cross the hinge in two separate bundles:
#   motor bundle  - top-right corner, dropping straight from behind the GX16
#                   panel's stepper row
#   power+signal  - mid hinge, beside the receiving jacks; the GX16 bottom row
#                   (endstops, PEN) sits just above it
# All connectors are in one column on the hinge edge, GX16 at the machine end.
# The fan and the PEN socket's 6 V take power from the jacks on the lid.
HINGE_CROSSINGS = {
    "Control box (left)": [("motor bundle", 15.0, 95.0), ("power + signal", 160.0, 260.0)],
}

LIDS = {
    "Control box (left)": [
        ("GX16 panel", "panel:gx", 78.0, 0.0),            # top right: machine end, hinge edge
        ("Receiving jacks", "panel:ctrl", 130.0, 118.0),  # directly below, beside the mid crossing
        ("12 V fan", "fan", 20.0, 200.0),
    ],
    "PSU box (right)": [
        ("PSU panel", "panel:psu", 0.0, 0.0),            # top left: faces the control box
        ("12 V fan", "fan", 110.0, 195.0),
        ("IEC inlet (fitted)", "iec", 15.0, 285.0),
    ],
}


def _outline(kind):
    if kind.startswith("panel:"):
        w, h, _ = _layout(kind.split(":")[1])
        return w + 2 * FLANGE, h + 2 * FLANGE
    return {"fan": (FAN, FAN), "iec": IEC, "keepout": (70.0, 100.0)}[kind]


def check_lids(min_gap=5.0):
    """Every outline inside the lid area and at least min_gap from its neighbours."""
    problems = []
    for lid, things in LIDS.items():
        boxes = []
        for name, kind, x, y in things:
            w, h = _outline(kind)
            if x < 0 or y < 0 or x + w > LID_AREA[0] or y + h > LID_AREA[1]:
                problems.append(f"{lid}: {name} runs off the lid area")
            boxes.append((name, x, y, x + w, y + h))
        for i, a in enumerate(boxes):
            for b in boxes[i + 1:]:
                gx = max(a[1], b[1]) - min(a[3], b[3])
                gy = max(a[2], b[2]) - min(a[4], b[4])
                if max(gx, gy) < min_gap:
                    problems.append(f"{lid}: {a[0]} and {b[0]} are {max(gx, gy):.1f} mm apart")
    return problems


def draw_lids(path):
    """Both lid tops to scale, as seen from above, plotter side at the top."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

    LW, LH = LID_AREA
    SEP = 60.0
    fig, ax = plt.subplots(figsize=(9, 8.5), dpi=130)
    ax.set_xlim(-10, 2 * LW + SEP + 10)
    ax.set_ylim(LH + 42, -25)
    ax.set_aspect("equal")
    ax.axis("off")
    fills = {"panel": "#2b2d2f", "fan": "#3d6f8f", "iec": "#7a7a7a", "keepout": "none"}
    for i, (lid, things) in enumerate(LIDS.items()):
        ox = i * (LW + SEP)
        ax.add_patch(Rectangle((ox, 0), LW, LH, fc="#f2f3f1", ec="#444", lw=1.2, ls="--"))
        ax.text(ox + LW / 2, -8, f"{lid}  ({LW:.0f} x {LH:.0f} mm usable)", ha="center", fontsize=9)
        for name, kind, x, y in things:
            w, h = _outline(kind)
            base = kind.split(":")[0]
            if base == "panel":
                ax.add_patch(FancyBboxPatch((ox + x, y), w, h, boxstyle=f"round,pad=0,rounding_size={CORNER_R}",
                                            fc=fills[base], ec="#111"))
            elif base == "keepout":
                ax.add_patch(Rectangle((ox + x, y), w, h, fc="#f6d9d3", ec="#c0392b", ls="--",
                                       hatch="//", lw=1))
            else:
                ax.add_patch(Rectangle((ox + x, y), w, h, fc=fills[base], ec="#111", alpha=.85))
            if base == "fan":
                cx, cy = ox + x + w / 2, y + h / 2
                ax.add_patch(Circle((cx, cy), FAN_HOLE / 2, fc="none", ec="white", lw=1))
                for sx in (-1, 1):
                    for sy in (-1, 1):
                        ax.add_patch(Circle((cx + sx * FAN_SCREW_PITCH / 2, cy + sy * FAN_SCREW_PITCH / 2),
                                            2.2, fc="white", ec="none"))
            if base == "keepout":
                ax.text(ox + x + w / 2, y + h / 2, name, ha="center", va="center",
                        color="#8e2b1f", fontsize=7, weight="bold",
                        bbox=dict(fc="#f6d9d3", ec="none", pad=1.5))
                continue
            if base == "iec":   # too narrow to hold its label
                ax.text(ox + x + w + 4, y + h / 2, f"{name}\n{w:.0f} x {h:.0f}", ha="left",
                        va="center", color="#333", fontsize=7.5, weight="bold")
            else:
                ax.text(ox + x + w / 2, y + h / 2, f"{name}\n{w:.0f} x {h:.0f}", ha="center",
                        va="center", color="white", fontsize=7.5, weight="bold")
    # hinge edges: right edge of the control box, left edge of the PSU box
    for hx in (LW, LW + SEP):
        ax.plot([hx, hx], [0, LH], color="#1f4e79", lw=3, solid_capstyle="butt")
    ax.text(LW + 3, LH + 8, "hinge", color="#1f4e79", fontsize=7.5, ha="left")
    ax.text(LW + SEP - 3, LH + 8, "hinge", color="#1f4e79", fontsize=7.5, ha="right")
    key = []
    for lid_i, (lid, things) in enumerate(LIDS.items()):
        for name, y0, y1 in HINGE_CROSSINGS.get(lid, []):
            hx = lid_i * (LW + SEP) + LW
            ax.plot([hx, hx], [y0, y1], color="#e67e22", lw=8, solid_capstyle="butt", alpha=.9)
            key.append(name)
            ax.text(hx + 11, (y0 + y1) / 2, str(len(key)), ha="center", va="center", fontsize=8,
                    color="white", weight="bold",
                    bbox=dict(boxstyle="circle,pad=0.3", fc="#e67e22", ec="none"))
    ax.text(0, LH + 32, "Hinge crossings (orange):  " +
            "    ".join(f"{i + 1} = {n}" for i, n in enumerate(key)) +
            ".  Board and drivers are in the control box base.", fontsize=8, color="#a04f00")
    jy = 140.0   # receiving jacks' upper rows, clear of the crossing markers
    ax.annotate("", xy=(LW + 6, jy), xytext=(LW + SEP - 6, jy),
                arrowprops=dict(arrowstyle="<->", color="#c0392b", lw=1.5))
    ax.text(LW + SEP / 2, jy - 6, "jumper\ncable", ha="center", va="bottom", fontsize=7.5, color="#c0392b")
    ax.text(LW + SEP / 2, LH + 18, "plotter side at the top.  IEC position is approximate (from photo).",
            ha="center", fontsize=8, color="#555")
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main(argv):
    from build123d import export_step, export_stl

    out = pathlib.Path(__file__).resolve().parent.parent / "out"
    out.mkdir(exist_ok=True)
    for kind in ("psu", "ctrl", "gx"):
        part = build_panel(kind)
        name = f"link_panel_{kind}"
        export_step(part, str(out / f"{name}.step"))
        export_stl(part.rotate(Axis.X, 180), str(out / f"{name}.stl"))  # face-down
        w, h, _ = _layout(kind)
        print(f"{name:15s} plate {w + 2 * FLANGE:.0f} x {h + 2 * FLANGE:.0f} mm   "
              f"cut the box {w:.0f} x {h:.0f} mm   {part.volume * DENSITY:.0f} g")
    draw_mockup(out / "link_panel_mockup.png")
    draw_lids(out / "lid_layout.png")
    for problem in check_lids():
        print("LID LAYOUT:", problem)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
