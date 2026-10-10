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

CELL = (48.0, 11.0)   # one strip
COLS = 4


def _label_cell(ax, x, y, name):
    w, h = CELL
    ax.add_patch(Rectangle((x, y), w, h, fill=False, ec="#999", lw=0.4, ls=(0, (2, 2))))
    ax.plot([x + w / 2, x + w / 2], [y + 1.5, y + h - 1.5], color="#bbb", lw=0.4, ls=":")
    colour = next((c for k, c in lp.RAIL_COLOUR.items() if k in name), None)
    if colour:
        ax.add_patch(Rectangle((x, y), 2.2, h, fc=colour, ec="none"))
    for hx in (x + w / 4 + 1, x + 3 * w / 4):
        ax.text(hx, y + h / 2, name, ha="center", va="center", fontsize=7.5, weight="bold",
                family="DejaVu Sans Mono")


def _labels(path):
    entries = []
    for section, names in LABELS:
        entries.append(("section", section))
        for n in names:
            entries += [("label", n), ("label", n)]
    with PdfPages(path) as pdf:
        fig, ax = _page()
        ax.text(A4[0] / 2, 10, "Wire labels - two of each (one per end). Cut on the dashed lines. "
                "Fold on the dotted line as a flag, or wrap and tape.", ha="center", fontsize=7.5)
        x_l, y, col = 9.0, 16.0, 0
        for kind, val in entries:
            if kind == "section":
                if col:
                    y += CELL[1] + 1
                    col = 0
                if y + 6 + CELL[1] > A4[1] - 10:
                    pdf.savefig(fig); plt.close(fig)
                    fig, ax = _page(); y = 10.0
                ax.text(x_l, y + 4, val, fontsize=8, weight="bold", va="center")
                y += 7
                continue
            if y + CELL[1] > A4[1] - 10:
                pdf.savefig(fig); plt.close(fig)
                fig, ax = _page(); y, col = 10.0, 0
            _label_cell(ax, x_l + col * (CELL[0] + 0.5), y, val)
            col += 1
            if col == COLS:
                col = 0
                y += CELL[1] + 1
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
