"""Control box layout check: 3 TB6600 plates + the board plate on one DIN rail, against the box's keep-outs.

Top view: x across the box (−225 left wall … 225 right wall), z front/back (+147.5 front wall, −147.5 back).
Assumed (unverified) keep-outs: USB/antenna panel and banana panel parts reach 25 mm into the box; GX16 sockets +
plugged wires need 40 mm behind the front wall; wire bend zones 15 mm beside each terminal strip, 25 mm shared between
TB3 and the board. Heights assume the bought DIN clip's top face sits 7.5 above the rail.

    python3 hardware/parts/layout_control.py      # prints clearances, writes hardware/out/layout/control_layout.png
"""
import pathlib
import sys

from shapely.geometry import box as sbox

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "sheet"))
import enclosure as E  # noqa: E402

OUT = HERE.parent / "out" / "layout"
XW, ZF, ZB = E.W / 2, E.D / 2, -E.D / 2
REACH, GX_DEPTH, BEND, SHARED = 25.0, 40.0, 15.0, 25.0
TB = dict(wall=5.0, body=57.0, term=12.0, len=100.0, h=28.0)        # plate wall + driver body + terminals; plate length
BOARD = dict(pcb=(87.0, 126.0), term=3.0, usb=2.0, pwr=6.0, plate=(90.0, 130.0))
RAIL_Z, BOARD_DZ = -15.0, -10.0                                        # rail centre line; board centre behind the rail
PLATE_TOP, RAIL_H, CLIP_TOP = E.PLATE_Y[1], 7.5, 7.5                   # floor to base-plate top; rail; clip above rail


def keepouts():
    fz, fy = E.FAN["control"]
    k = {
        "fan": sbox(-XW, fz - 40, -XW + E.FAN_DEPTH + 5, fz + 40),
        "USB/antenna panel": sbox(-XW, -45 - 27, -XW + REACH, -45 + 27),
        "banana panel": sbox(XW - REACH, E.JACK_Z - 86, XW, E.JACK_Z + 86),
        "GX sockets + plugs": sbox(-205, ZF - GX_DEPTH, 30, ZF),
    }
    return k


def parts(shift=0.0):
    out, x = {}, -XW + REACH + shift
    for i in range(3):
        z0, z1 = RAIL_Z - TB["len"] / 2, RAIL_Z + TB["len"] / 2
        out[f"TB{i + 1}"] = sbox(x, z0, x + TB["wall"] + TB["body"] + TB["term"], z1)
        x += TB["wall"] + TB["body"] + TB["term"] + (BEND if i < 2 else SHARED)
    w = BOARD["pcb"][0] + 2 * BOARD["term"]
    bz = RAIL_Z + BOARD_DZ
    out["board"] = sbox(x, bz - BOARD["pcb"][1] / 2 - BOARD["usb"], x + w, bz + BOARD["pcb"][1] / 2 + BOARD["pwr"])
    out["_io_bend"] = sbox(x + w, bz - 50, x + w + BEND, bz + 50)
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ko = keepouts()
    p0 = parts()
    right = max(g.bounds[2] for g in p0.values())
    spare = (XW - REACH) - right
    p = parts(shift=spare / 2)                                         # centre the row between the side keep-outs
    print(f"row length {right - (-XW + REACH):.0f} of {2 * (XW - REACH):.0f} mm between the side keep-outs -> {spare / 2:.1f} mm spare each side")
    worst = []
    for n, g in p.items():
        for kn, kg in ko.items():
            d = g.distance(kg)
            worst.append((d, n, kn))
            if d < 0.01:
                print(f"  CLASH {n} x {kn}")
    for d, n, kn in sorted(worst)[:6]:
        print(f"  {n:9s} to {kn:20s} {d:6.1f} mm")
    fz0 = min(g.bounds[1] for n, g in p.items() if not n.startswith("_"))
    fz1 = max(g.bounds[3] for n, g in p.items() if not n.startswith("_"))
    print(f"back free (to the back edge) {fz0 - ZB:.0f} mm, front free (to the GX zone) {(ZF - GX_DEPTH) - fz1:.0f} mm")
    clip_top = PLATE_TOP + RAIL_H + CLIP_TOP
    tb_top, board_top = clip_top + 8 + TB["h"], clip_top + 12 + 1.6 + 15
    print(f"heights above the floor: TB6600 top {tb_top:.0f}, board top {board_top:.0f}; inside height {E.H['control']:.0f} -> {E.H['control'] - tb_top:.0f} mm free above")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(11, 7.6), dpi=110)
    ax.add_patch(plt.Rectangle((-XW, ZB), 2 * XW, E.D, fill=False, lw=2, ec="#333"))
    for n, g in ko.items():
        x0, z0, x1, z1 = g.bounds
        ax.add_patch(plt.Rectangle((x0, z0), x1 - x0, z1 - z0, fc="#e7b7a8", ec="#b0533a", alpha=.6, hatch="//"))
        ax.text((x0 + x1) / 2, (z0 + z1) / 2, n, ha="center", va="center", fontsize=7, rotation=90 if x1 - x0 < 40 else 0)
    # two 8-inch rails: A under the drivers (full 203), B under the board (cut to 120); bought clips 25 x 69
    clips = [p[f"TB{i + 1}"].bounds[0] + TB["wall"] + TB["body"] / 2 for i in range(3)]
    bcx = (p["board"].bounds[0] + p["board"].bounds[2]) / 2
    clips += [bcx - 30, bcx + 30]
    ra = (clips[0] - 12.5, clips[0] - 12.5 + 203.2)
    rb = (bcx - 60, bcx + 60)
    for (x0, x1), lab in ((ra, "rail A: full 8 in (203)"), (rb, "rail B: 8 in cut to 120")):
        ax.add_patch(plt.Rectangle((x0, RAIL_Z - 17.5), x1 - x0, 35, fc="#aab4bb", ec="#6d7780", zorder=1))
        ax.add_patch(plt.Rectangle((x0, RAIL_Z - 17.5), x1 - x0, 35, fc="none", ec="#3d464d", lw=1, ls=":", zorder=6))
        ax.text((x0 + x1) / 2, RAIL_Z - 88, lab + f"  (x {x0:.0f} to {x1:.0f})", ha="center", fontsize=7.5, color="#3d464d", zorder=6)
    screws = [(clips[0] + clips[1]) / 2, (clips[1] + clips[2]) / 2, bcx, rb[1] - 8]
    print("rail A", [round(v, 1) for v in ra], "rail B", [round(v, 1) for v in rb])
    print("clip centres", [round(c, 1) for c in clips], "rail screws", [round(v, 1) for v in screws])
    CLIPS, SCREWS = clips, screws
    for n, g in p.items():
        x0, z0, x1, z1 = g.bounds
        if n == "_io_bend":
            ax.add_patch(plt.Rectangle((x0, z0), x1 - x0, z1 - z0, fc="none", ec="#2a7", ls="--")); continue
        ax.add_patch(plt.Rectangle((x0, z0), x1 - x0, z1 - z0, fc="#77c1ef" if n == "board" else "#5aa0d0", ec="#1c2328"))
        if n.startswith("TB"):
            ax.add_patch(plt.Rectangle((x1 - TB["term"], z0 + 10), TB["term"], z1 - z0 - 20, fc="#6fc28a", ec="#1c2328"))
        ax.text((x0 + x1) / 2, (z0 + z1) / 2, n, ha="center", va="center", fontsize=9, weight="bold")
    for cx in CLIPS:
        ax.add_patch(plt.Rectangle((cx - 12.5, RAIL_Z - 34.5), 25, 69, fc="none", ec="#d22", lw=1.2, ls="--", zorder=7))
    for sx in SCREWS:
        ax.add_patch(plt.Circle((sx, RAIL_Z), 3, fc="#222", zorder=8))
    ax.text(0, ZF + 10, "FRONT (GX sockets) - you stand here", ha="center", fontsize=8); ax.text(0, ZB - 8, "BACK", ha="center", fontsize=8)
    ax.set_xlim(-XW - 15, XW + 15); ax.set_ylim(ZF + 14, ZB - 18);   # front at the bottom: seen from above, standing at the front
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_title(f"Control box top view: two 8-inch rails at z {RAIL_Z:g} (red dashed = DIN clips, black dots = rail screws); {spare / 2:.0f} mm spare each side", fontsize=9.5)
    fig.tight_layout(); fig.savefig(OUT / "control_layout.png")


if __name__ == "__main__":
    main()
