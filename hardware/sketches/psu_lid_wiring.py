import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle

C = {"24": "#c0392b", "12": "#e67e22", "6": "#f1c40f", "G1": "#1a1a1a", "G2": "#7f8c8d"}
INK = {"24": "white", "12": "black", "6": "black", "G1": "white", "G2": "white"}
fig, ax = plt.subplots(figsize=(13, 10), dpi=120)
ax.set_xlim(0, 1320); ax.set_ylim(1000, -40); ax.set_aspect("equal"); ax.axis("off")

def box(x0, y0, x1, y1, t, fc, tc="white", fs=8, ls="-", ec="#222", r=10, z=2):
    ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0, boxstyle=f"round,pad=0,rounding_size={r}",
                                fc=fc, ec=ec, lw=1.2, ls=ls, zorder=z))
    if t:
        ax.text((x0 + x1) / 2, (y0 + y1) / 2, t, ha="center", va="center", color=tc, fontsize=fs,
                weight="bold", zorder=z + 1)

def guide(pts, w=24):
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color="#d8d2c4", lw=w, solid_capstyle="butt", solid_joinstyle="miter", zorder=1)

def wire(pts, k, lw=2.4, z=3):
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=C[k], lw=lw, solid_joinstyle="miter", solid_capstyle="round", zorder=z)

# lid, hinge, mains zone
box(20, 20, 1300, 930, "", "#efefec", ec="#555", r=40, z=0)
ax.plot([40, 1280], [958, 958], color="#1f4e79", lw=6)
ax.text(660, 982, "HINGE  -  24 / G1 / 12 / G2 come up from the PSUs", ha="center", color="#1f4e79",
        fontsize=9, weight="bold")
box(55, 610, 300, 925, "", "#f6e1dc", ec="#c0392b", ls="--", r=14, z=0)
ax.text(178, 632, "MAINS ZONE - no DC", ha="center", fontsize=8, color="#8e2b1f", weight="bold")
box(115, 720, 240, 830, "IEC\nswitch\n+ fuse", "#555")
ax.plot([178, 178], [830, 958], color="#8e44ad", lw=9, alpha=.45, zorder=1)

# fan, buck, panel
box(560, 50, 780, 270, "", "#3d6f8f"); ax.add_patch(Circle((670, 160), 95, fc="none", ec="white", zorder=3))
ax.text(670, 160, "12 V FAN", ha="center", va="center", color="white", fontsize=9, weight="bold", zorder=4)
box(810, 110, 970, 200, "BUCK\n12 > 6 V", "#1f5fa8")
box(860, 450, 1270, 920, "", "#2b2d2f")
ax.text(1065, 900, "PSU PANEL (back)", ha="center", color="#bbb", fontsize=8.5, weight="bold", zorder=4)
SW = {"24": 940, "12": 1050, "6": 1160}
for k, x in SW.items():
    box(x - 30, 520, x + 30, 590, f"{k} V\nSW", "#cfcfcf", tc="#222", fs=7.5, r=4, z=4)
JK = {"G1": 940, "G2": 1030, "24": 1110, "12": 1175, "6": 1240}
for k, x in JK.items():
    ax.add_patch(Circle((x, 830), 24, fc=C[k], ec="#111", zorder=4))
    ax.text(x, 830, k, ha="center", va="center", fontsize=7.5, weight="bold", color=INK[k], zorder=5)
ax.text(1100, 700, "on the panel back:\nSW out -> its jack + display red\nG1 jack -> 24 V display black\n"
        "G2 jack -> 12 V + 6 V display black", ha="center", va="center", color="#ccc", fontsize=7.5, zorder=4)

# hinge pass-throughs: the lid unplugs from the base
PT = [("G2", 545, "G2 a"), ("12", 600, "12"), ("24", 740, "24"), ("G2", 770, "G2 b"), ("G1", 800, "G1")]
for k, x, t in PT:
    box(x - 14, 860, x + 14, 900, t, C[k], tc=INK[k], fs=5.5, r=4, z=4)
ax.text(670, 914, "hinge pass-throughs (lid unplugs)", ha="center", fontsize=7, color="#444")

# panel pass-throughs: the panel unplugs from the lid
PP = [("6", 520), ("12", 590), ("24", 650), ("G2", 710), ("G1", 770)]
for k, y in PP:
    box(812, y - 14, 850, y + 14, k, C[k], tc=INK[k], fs=6.5, r=4, z=5)
ax.text(831, 795, "panel\npass-\nthroughs", ha="center", va="top", fontsize=6.5, color="#444")

# PCT 2x6 under the fan: G2 splitter left, 12 V splitter right
box(520, 600, 730, 700, "", "#f4f4f2", ec="#888", r=6)
box(527, 607, 623, 693, "", C["G2"], ec="#333", r=5, z=3)
box(627, 607, 723, 693, "", C["12"], ec="#333", r=5, z=3)
ax.text(575, 650, "G2\n1 > 3", ha="center", va="center", fontsize=8, weight="bold", color="white", zorder=5)
ax.text(675, 650, "12 V\n1 > 3", ha="center", va="center", fontsize=8, weight="bold", zorder=5)
ax.text(625, 712, "PCT 2x6", ha="center", va="top", fontsize=7.5, color="#444")

# guides
guide([(572, 860), (572, 700)], w=70)
guide([(620, 600), (620, 270)], w=60)
guide([(540, 600), (540, 35), (880, 35), (880, 110)], w=14)
guide([(700, 590), (812, 590)], w=46)
guide([(790, 570), (790, 210)], w=14)
guide([(845, 200), (845, 506)], w=14)
guide([(770, 860), (770, 640)], w=70)

# hinge -> PCT inputs
wire([(545, 860), (545, 693)], "G2")
wire([(600, 860), (600, 760), (660, 760), (660, 693)], "12")
# PCT outs: fan (straight up), buck (around the fan), 12 V to the panel
wire([(600, 607), (600, 270)], "G2")                                        # fan -
wire([(640, 607), (640, 270)], "12")                                        # fan +
wire([(540, 607), (540, 35), (880, 35), (880, 110)], "G2")                  # buck in -
wire([(680, 607), (680, 570), (790, 570), (790, 210), (815, 210), (815, 200)], "12")  # buck in +
wire([(715, 607), (715, 590), (812, 590)], "12")                            # 12 V -> panel
# buck out + -> panel
wire([(845, 200), (845, 506)], "6")
# hinge -> panel pass-throughs
wire([(740, 860), (740, 650), (812, 650)], "24")
wire([(770, 860), (770, 710), (812, 710)], "G2")
wire([(800, 860), (800, 770), (812, 770)], "G1")
# panel side: pass-throughs -> switches and ground jacks (over the top of the switches)
wire([(850, 520), (856, 520), (856, 480), (1160, 480), (1160, 520)], "6")
wire([(850, 590), (866, 590), (866, 495), (1050, 495), (1050, 520)], "12")
wire([(850, 650), (876, 650), (876, 510), (940, 510), (940, 520)], "24")
wire([(850, 710), (1030, 710), (1030, 806)], "G2")
wire([(850, 770), (940, 770), (940, 806)], "G1")

# legend
lx, ly = 45, 60
for i, (k, t) in enumerate([("24", "24 V"), ("12", "12 V"), ("6", "6 V"), ("G1", "G1  24 V return"),
                            ("G2", "G2  12 V + 6 V return")]):
    ax.plot([lx, lx + 40], [ly + i * 22, ly + i * 22], color=C[k], lw=4)
    ax.text(lx + 50, ly + i * 22, t, va="center", fontsize=8)
ax.plot([lx, lx + 40], [ly + 115, ly + 115], color="#d8d2c4", lw=12)
ax.text(lx + 50, ly + 115, "printed wire guide", va="center", fontsize=8)
ax.text(660, -20, "PSU box lid - DC wiring (sketch, not to scale)", ha="center", fontsize=11, weight="bold",
        va="top")
fig.savefig(str(__import__("pathlib").Path(__file__).resolve().parents[1] / "out" / "psu_lid_wiring.png"), bbox_inches="tight", facecolor="white")
