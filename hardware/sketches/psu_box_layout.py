import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle

# Coordinates traced from the photo (pixels, 1500 x 2000), y down. Not to scale in mm.
fig, ax = plt.subplots(figsize=(9.5, 12.5), dpi=120)
ax.set_xlim(40, 1460); ax.set_ylim(2010, 20); ax.set_aspect("equal"); ax.axis("off")

def box(x0, y0, x1, y1, label, fc, ec="#222", tc="white", fs=8.5, r=8, ls="-"):
    ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0, boxstyle=f"round,pad=0,rounding_size={r}",
                                fc=fc, ec=ec, lw=1.2, ls=ls))
    ax.text((x0 + x1) / 2, (y0 + y1) / 2, label, ha="center", va="center", color=tc, fontsize=fs,
            weight="bold", wrap=True)

# shells
box(80, 80, 1400, 990, "", "#efefec", ec="#555", r=40)
box(80, 1040, 1400, 1960, "", "#efefec", ec="#555", r=40)
ax.text(110, 115, "LID  (panel side, faces up when closed)", fontsize=10, weight="bold", color="#333")
ax.text(110, 1940, "BASE", fontsize=10, weight="bold", color="#333")
ax.plot([120, 1360], [1015, 1015], color="#1f4e79", lw=6)
ax.text(1380, 1015, "hinge", color="#1f4e79", fontsize=9, va="center", weight="bold")

# lid parts
box(300, 445, 490, 535, "BUCK 24>6 V\n(with display)", "#1f5fa8")
box(665, 305, 885, 545, "", "#3d6f8f")
ax.add_patch(Circle((775, 425), 95, fc="none", ec="white", lw=1)); ax.text(775, 425, "12 V FAN\n80 mm", ha="center", va="center", color="white", fontsize=8.5, weight="bold")
box(318, 628, 410, 745, "small\nlever\nblock", "#e0e0e0", tc="#222", fs=7.5)
box(520, 595, 625, 745, "large\nlever\nblock", "#f0a35e", tc="#222", fs=7.5)
box(218, 815, 345, 925, "IEC\nswitch\n+ fuse", "#555")
box(845, 595, 1265, 970, "", "#2b2d2f")
ax.text(1055, 625, "PSU PANEL", ha="center", color="white", fontsize=9, weight="bold")
for i in range(3):
    ax.add_patch(Rectangle((1060 + i * 60, 640), 46, 60, fc="#c9c9c9", ec="#777"))
ax.text(1150, 720, "3 toggles", ha="center", color="#ddd", fontsize=7)
ax.add_patch(Rectangle((1070, 745), 140, 50, fc="#0b0b0b", ec="#444")); ax.text(1140, 770, "displays", ha="center", va="center", color="#ff4b3f", fontsize=7.5)
for i, c in enumerate(["#1f5fa8", "#1f5fa8", "#c0392b", "#c0392b", "#c0392b"]):
    ax.add_patch(Circle((915 + i * 75 + (40 if i > 1 else 0), 905), 20, fc=c, ec="#111"))
ax.text(1055, 950, "5 binding posts (2 blue, 3 red)", ha="center", color="#ddd", fontsize=7)
box(200, 320, 300, 360, "clip", "#444", fs=6.5, r=4)
box(190, 600, 260, 720, "clip", "#444", fs=6.5, r=4)

# base parts
box(245, 1145, 350, 1300, "MAINS\nlever\nsplitter", "#9aa0a6", tc="#111", fs=7.5)
box(715, 1130, 1285, 1450, "LRS-350-24\n24 V  14.6 A", "#b7bcc1", tc="#111", fs=10)
box(600, 1465, 1150, 1800, "2nd PSU\n(12 V?)", "#c9cdd1", tc="#111", fs=10)
ax.text(735, 1290, "+V +V -V -V  FG N L", fontsize=6.5, color="#333", rotation=90, va="center")
box(495, 1215, 610, 1305, "printed\npart", "#444", fs=6.5, r=30)
box(375, 1610, 505, 1680, "printed\npart", "#444", fs=6.5, r=30)

# proposed bundles
ax.plot([280, 280, 300], [925, 1015, 1145], color="#8e44ad", lw=7, alpha=.55, solid_capstyle="round")
ax.text(175, 1015, "A: MAINS\nL / N / PE", color="#6c3483", fontsize=8, weight="bold", ha="center", va="center",
        bbox=dict(fc="white", ec="#8e44ad", pad=2))
ax.plot([1000, 1000], [975, 1130], color="#e67e22", lw=7, alpha=.65, solid_capstyle="round")
ax.text(1000, 1075, "B: DC  24V / G1 / 12V / G2", color="#a04f00", fontsize=8, weight="bold", ha="center",
        va="center", bbox=dict(fc="white", ec="#e67e22", pad=2))
ax.text(750, 2000, "Traced from your photo. Positions approximate, not to scale. Purple and orange = proposed hinge bundles.",
        ha="center", fontsize=8, color="#555")
fig.savefig(str(__import__("pathlib").Path(__file__).resolve().parents[1] / "out" / "psu_box_layout_sketch.png"), bbox_inches="tight", facecolor="white")
