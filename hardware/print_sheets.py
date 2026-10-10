#!/usr/bin/env python3
"""Printable sheets for building the two boxes.

    python3 hardware/print_sheets.py

Writes hardware/out/panel_templates.pdf and hardware/out/wire_labels.pdf.

panel_templates.pdf -- one A4 page per panel at exactly 1:1. Print at 100 %
("actual size", never "fit to page"); each page carries a 100 mm ruler to
check. Tape the page to the lid, drill the corner screw holes, then cut the
solid rectangle. Pages are drawn as seen from OUTSIDE the lid, with the
machine end at the top and the hinge side marked.

wire_labels.pdf -- two of every label, one per wire end. Each strip carries
the name twice either side of a fold line: fold it round the wire as a flag,
or wrap it and tape over.
"""

import sys
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "parts"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle  # noqa: E402

import link_panel as lp  # noqa: E402

OUT = HERE / "out"
A4 = (210.0, 297.0)
MM = 1 / 25.4


def _page():
    """An A4 figure whose axes are millimetres, origin top-left, y down."""
    fig = plt.figure(figsize=(A4[0] * MM, A4[1] * MM))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, A4[0])
    ax.set_ylim(A4[1], 0)
    ax.axis("off")
    return fig, ax


def _ruler(ax, x, y):
    ax.plot([x, x + 100], [y, y], color="k", lw=1)
    for i in range(0, 101, 10):
        ax.plot([x + i, x + i], [y, y - (3 if i % 50 else 5)], color="k", lw=0.6)
    ax.text(x + 50, y + 4, "100 mm  -  measure this: if it is not 100 mm, reprint at 100 % / actual size",
            ha="center", va="top", fontsize=7)


# kind, title, hinge side ("left"/"right"), where it goes on the lid
TEMPLATES = [
    ("psu", "PSU box lid - PSU panel", "left",
     "Top-left of the PSU box lid: left edge against the hinge side, top edge at the machine end."),
    ("gx", "Control box lid - GX16 panel", "right",
     "Top-right of the control box lid: right edge against the hinge side, top edge at the machine end."),
    ("ctrl", "Control box lid - receiving jacks", "right",
     "Directly below the GX16 panel: right edges in line (hinge side), "
     "this plate's top edge 8 mm below the GX16 plate's bottom edge."),
]


def _template(pdf, kind, title, hinge, where):
    fig, ax = _page()
    w, h, items = lp._layout(kind)
    W, H = w + 2 * lp.FLANGE, h + 2 * lp.FLANGE
    x0, y0 = (A4[0] - W) / 2, 52.0           # plate top-left on the page
    cx, cy = x0 + W / 2, y0 + H / 2

    ax.text(A4[0] / 2, 12, title, ha="center", fontsize=13, weight="bold")
    ax.text(A4[0] / 2, 19, where, ha="center", fontsize=7.5, wrap=True)
    ax.text(A4[0] / 2, 25, "Viewed from OUTSIDE the lid.  Print at 100 % (actual size).",
            ha="center", fontsize=7.5, style="italic")

    # machine end arrow
    ax.annotate("", xy=(cx, y0 - 13), xytext=(cx, y0 - 3),
                arrowprops=dict(arrowstyle="-|>", lw=2, color="#1f4e79"))
    ax.text(cx, y0 - 16, "MACHINE END", ha="center", va="bottom", fontsize=9,
            weight="bold", color="#1f4e79")
    # hinge side bar
    hx = x0 - 8 if hinge == "left" else x0 + W + 8
    ax.plot([hx, hx], [y0, y0 + H], color="#1f4e79", lw=4)
    ax.text(hx + (-3 if hinge == "left" else 3), cy, "HINGE SIDE", rotation=90, va="center",
            ha="right" if hinge == "left" else "left", fontsize=9, weight="bold", color="#1f4e79")

    # plate outline (where the printed panel will sit)
    ax.add_patch(FancyBboxPatch((x0, y0), W, H, boxstyle=f"round,pad=0,rounding_size={lp.CORNER_R}",
                                fill=False, ec="#777", lw=0.8, ls="--"))
    ax.text(x0 + 2, y0 + H + 4, f"panel outline {W:.0f} x {H:.0f} mm (dashed, do not cut)",
            fontsize=7, color="#555", va="top")

    # ghost of the parts, so the orientation is obvious
    for k, x, y, name in items:
        px, py = x0 + lp.FLANGE + x, y0 + lp.FLANGE + (h - y)   # layout y is up; page y is down
        if k == "label":
            ax.add_patch(Rectangle((px - lp.LABEL[0] / 2, py - lp.LABEL[1] / 2), *lp.LABEL,
                                   fill=False, ec="#cfcfcf", lw=0.5))
            ax.text(px, py, name, ha="center", va="center", fontsize=5.5, color="#aaa")
        else:
            r = {"jack": lp.JACK_COLLAR / 2, "gx": lp.GX_NUT / 2, "toggle": 8.0}.get(k)
            if r:
                ax.add_patch(Circle((px, py), r, fill=False, ec="#cfcfcf", lw=0.5))
            if k == "display":
                ax.add_patch(Rectangle((px - lp.DISP_W / 2, py - lp.DISP_H / 2), lp.DISP_W, lp.DISP_H,
                                       fill=False, ec="#cfcfcf", lw=0.5))

    # the cut
    ax.add_patch(Rectangle((x0 + lp.FLANGE, y0 + lp.FLANGE), w, h, fill=False, ec="#c0392b", lw=1.6))
    ax.text(cx, y0 + lp.FLANGE + 3, f"CUT ON THIS LINE  -  {w:.0f} x {h:.0f} mm",
            ha="center", va="top", fontsize=8, weight="bold", color="#c0392b")

    # corner screws
    for sx, sy in lp._screws(w, h):
        px, py = cx + sx, cy - sy
        ax.add_patch(Circle((px, py), lp.SCREW_D / 2, fill=False, ec="k", lw=0.8))
        ax.plot([px - 4, px + 4], [py, py], color="k", lw=0.4)
        ax.plot([px, px], [py - 4, py + 4], color="k", lw=0.4)
    sxs = sorted({round(abs(sx) * 2, 1) for sx, _ in lp._screws(w, h)})[0]
    sys_ = sorted({round(abs(sy) * 2, 1) for _, sy in lp._screws(w, h)})[0]
    ax.text(x0 + W - 2, y0 + H + 4, f"4 x drill {lp.SCREW_D} mm (M3), {sxs:.0f} x {sys_:.0f} mm centres",
            fontsize=7, ha="right", va="top")

    _ruler(ax, (A4[0] - 100) / 2, A4[1] - 18)
    pdf.savefig(fig)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Wire labels: (section, [names]). Every name is printed twice (both ends).
# ---------------------------------------------------------------------------

LABELS = [
    ("Jumper cable, box to box", ["LINK 24V", "LINK 12V", "LINK 6V", "LINK G1", "LINK G2"]),
    ("PSU box, behind the PSU panel", [
        "24V PSU>FUSE", "24V SW>JACK", "12V PSU>FUSE", "12V SW>JACK",
        "6V PSU>FUSE", "6V SW>JACK", "G1 PSU>JACK", "G2 PSU>JACK", "FAN +12V", "FAN GND"]),
    ("Control box, hinge crossing 1: motors", [
        f"{m} {p}" for m in ("X1", "X2", "Y") for p in ("A+", "A-", "B+", "B-", "SHLD")]),
    ("Control box, hinge crossing 2: power + signal", [
        "24V", "G1", "G2", "12V", "XLIM SIG", "XLIM GND", "YLIM SIG", "YLIM GND", "PEN SIG"]),
    ("Control box lid, stays on the lid", ["PEN +6V", "PEN GND", "FAN +12V", "FAN GND"]),
    ("Control box base, drivers", [
        f"{m} {s}" for m in ("X1", "X2", "Y") for s in ("STEP", "DIR", "EN", "24V", "GND")]),
    ("Spare, write your own", [""] * 8),
]

# Label colours, matched on whole words in the name, first match wins. Power
# rails match the jack colours; each motor axis has its own colour, used on its
# phase wires and its driver wiring alike.
LABEL_COLOURS = [
    ("G1", "#1a1a1a"), ("G2", "#1a1a1a"), ("GND", "#1a1a1a"),
    ("24V", "#c0392b"), ("12V", "#e67e22"), ("+12V", "#e67e22"), ("6V", "#f1c40f"), ("+6V", "#f1c40f"),
    ("X1", "#1f5fa8"), ("X2", "#2e8b57"), ("Y", "#7d3c98"),
    ("XLIM", "#aed6f1"), ("YLIM", "#d7bde2"), ("PEN", "#f5b7b1"),
    ("FAN", "#d5d8dc"),
]
BLANK = "#ffffff"


def _colour(name):
    words = name.replace(">", " ").split()
    # the axis decides a motor/driver wire's colour, the rail decides the rest
    for key, c in LABEL_COLOURS[7:]:
        if words and words[0] == key and key in ("X1", "X2", "Y"):
            return c
    for key, c in LABEL_COLOURS:
        if key in words:
            return c
    return BLANK


def _ink(hex_bg):
    """Black or white, whichever contrasts more with the background (WCAG)."""
    def lin(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (int(hex_bg[i:i + 2], 16) for i in (1, 3, 5))
    L = 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)
    return "#000000" if (L + 0.05) / 0.05 >= 1.05 / (L + 0.05) else "#ffffff"


STRIP = (62.0, 11.0)   # one wire label: name twice, fold line between


def _strip(ax, x, y, name, w=STRIP[0], h=STRIP[1], fold=True, size=8.0):
    bg = _colour(name)
    ink = _ink(bg)
    ax.add_patch(Rectangle((x, y), w, h, fc=bg, ec="#666", lw=0.4, ls=(0, (2, 2))))
    if fold:
        ax.plot([x + w / 2, x + w / 2], [y + 1.2, y + h - 1.2], color=ink, lw=0.4, ls=":", alpha=.6)
        centres = (x + w / 4, x + 3 * w / 4)
    else:
        centres = (x + w / 2,)
    for cx in centres:
        ax.text(cx, y + h / 2, name, ha="center", va="center", fontsize=size, weight="bold",
                family="DejaVu Sans Mono", color=ink)


def _labels(path):
    """Wire labels, one row per wire: both copies (one per end) side by side,
    so a row can be cut off as that wire is fitted. Then a page of labels for
    the panels' label pockets."""
    row_h, gap = STRIP[1] + 2.0, 6.0
    x1 = (A4[0] - 2 * STRIP[0] - gap) / 2
    x2 = x1 + STRIP[0] + gap
    with PdfPages(path) as pdf:
        fig, ax = _page()
        ax.text(A4[0] / 2, 9, "Wire labels: one row per wire, one copy for each end. "
                "Cut on the dashed lines; fold on the dotted line as a flag, or wrap and tape.",
                ha="center", fontsize=7)
        y = 15.0
        for section, names in LABELS:
            if y + 7 + row_h > A4[1] - 10:
                pdf.savefig(fig); plt.close(fig)
                fig, ax = _page(); y = 10.0
            ax.text(x1, y + 3.5, section, fontsize=8, weight="bold", va="center")
            y += 7
            for n in names:
                if y + row_h > A4[1] - 10:
                    pdf.savefig(fig); plt.close(fig)
                    fig, ax = _page(); y = 10.0
                _strip(ax, x1, y, n)
                _strip(ax, x2, y, n)
                ax.text(x2 + STRIP[0] + 3, y + STRIP[1] / 2, "end A | end B", fontsize=5,
                        color="#999", va="center")
                y += row_h
            y += 2
        pdf.savefig(fig)
        plt.close(fig)
        _panel_labels(pdf)


# Labels for the panels' label pockets (lp.LABEL, 14 x 10 mm), printed a little
# undersize so they drop in. Order follows each panel, top to bottom.
PANEL_LABELS = [
    ("PSU box panel", ["24V", "12V", "6V", "G1", "G2"]),
    ("Control box receiving panel", ["24V", "12V", "6V", "G1", "G2"]),
    ("Control box GX16 panel", ["X1", "X2", "Y", "XLIM", "YLIM", "PEN"]),
    ("Spares", ["24V", "12V", "6V", "G1", "G2"]),
    ("Spares", ["X1", "X2", "Y", "XLIM", "YLIM", "PEN"]),
]
POCKET_CLEAR = 0.3   # per side


def _panel_labels(pdf):
    fig, ax = _page()
    lw_, lh = lp.LABEL[0] - 2 * POCKET_CLEAR, lp.LABEL[1] - 2 * POCKET_CLEAR
    ax.text(A4[0] / 2, 12, "Panel labels", ha="center", fontsize=13, weight="bold")
    ax.text(A4[0] / 2, 19, f"Each one is {lw_:.1f} x {lh:.1f} mm to drop into the "
            f"{lp.LABEL[0]:.0f} x {lp.LABEL[1]:.0f} mm pockets. Print at 100 % (actual size). "
            "Cut on the dashed lines; a dab of glue or double-sided tape holds them.",
            ha="center", fontsize=7)
    y = 30.0
    for section, names in PANEL_LABELS:
        ax.text(15, y, section, fontsize=8.5, weight="bold", va="top")
        y += 6
        for i, n in enumerate(names):
            _strip(ax, 15 + i * (lw_ + 4), y, n, w=lw_, h=lh, fold=False, size=9.5)
        y += lh + 10
    _ruler(ax, (A4[0] - 100) / 2, A4[1] - 18)
    pdf.savefig(fig)
    plt.close(fig)


def main():
    OUT.mkdir(exist_ok=True)
    with PdfPages(OUT / "panel_templates.pdf") as pdf:
        for t in TEMPLATES:
            _template(pdf, *t)
    _labels(OUT / "wire_labels.pdf")
    print(f"wrote {OUT / 'panel_templates.pdf'}")
    print(f"wrote {OUT / 'wire_labels.pdf'}")


if __name__ == "__main__":
    main()
