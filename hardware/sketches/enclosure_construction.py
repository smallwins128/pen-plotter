#!/usr/bin/env python3
"""Low-fidelity construction sketch for the two 1 mm stainless boxes.

    python3 hardware/sketches/enclosure_construction.py

Writes hardware/out/enclosure_construction.svg: how each box folds, where the
lips and corner tabs go, the bend reliefs, how a printed panel and the lid fix
on with rivnuts, how the lid's holes are offset from the body's, and how the
base plate stands off the floor. Schematic, not to scale; the numbers in the
labels are the design values.
"""
import math
import pathlib

OUT = pathlib.Path(__file__).resolve().parent.parent / "out" / "enclosure_construction.svg"

# ---- design values (shared with the DXF generator once it exists) ----------
T = 1.0                 # sheet, 304 stainless
R = 1.0                 # inner bend radius = 1 x t
K = 0.44                # K-factor, typical for stainless at R = t
BA = math.pi / 2 * (R + K * T)          # 90 deg bend allowance
BD = 2 * (R + T) - BA                   # 90 deg bend deduction
LIP = 15.0              # lid-seat and corner lips
RELIEF = 3.0            # round relief where two bend lines meet
HOLE_TO_BEND = 5.0      # nearest hole edge to a bend line
RIVNUT_M3_HOLE = 5.0    # MEASURE your rivnuts
RIVNUT_M4_HOLE = 6.0    # MEASURE your rivnuts
RIVNUT_FROM_WALL = 8.0  # rivnut centre from the inside face of the wall a lip folds off
LID_CLEAR = 0.5         # lid return lip to body wall, per side

INK, BLUE, RED, GREY, FILL = "#222", "#1f5fbf", "#c0392b", "#888", "#e9eef3"


def t(x, y, s, fs=10, c=INK, a="start", b=False):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{fs}" fill="{c}" text-anchor="{a}"'
            f'{" font-weight=\"bold\"" if b else ""}>{s}</text>')


def rect(x, y, w, h, fill=FILL, stroke=INK, sw=1.2, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>'


def line(x1, y1, x2, y2, c=INK, sw=1.2, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{c}" stroke-width="{sw}"{d}/>'


def circ(x, y, r, fill="#fff", c=INK, sw=1.2):
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{fill}" stroke="{c}" stroke-width="{sw}"/>'


def poly(pts, fill=FILL, c=INK, sw=1.2):
    return f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" fill="{fill}" stroke="{c}" stroke-width="{sw}"/>'


def bend(x1, y1, x2, y2):
    return line(x1, y1, x2, y2, BLUE, 1.2, "6 4")


def panel_title(x, y, n, s):
    return t(x, y, f"{n}  {s}", 13, b=True)


def body_blank(ox, oy):
    """Flat blank of the body: base + front + two sides, lips, tabs, reliefs."""
    o = [panel_title(ox, oy - 12, "A", "Body blank — base, front, both sides (one piece)")]
    W, D, H, L = 220, 150, 70, 16          # schematic sizes
    bx, by = ox + H + L, oy + H + L        # base top-left
    # base
    o.append(rect(bx, by, W, D))
    o.append(t(bx + W / 2, by + D / 2, "BASE", 12, a="middle", b=True))
    o.append(t(bx + W / 2, by + D / 2 + 15, "6 standoff holes · feet", 9, GREY, "middle"))
    # front wall (below), its top lip further below
    o.append(rect(bx, by + D, W, H)); o.append(t(bx + W / 2, by + D + H / 2 + 4, "FRONT", 11, a="middle", b=True))
    o.append(rect(bx, by + D + H, W, L, "#dfe8f5")); o.append(t(bx + W / 2, by + D + H + 11, "top lip 15 — lid rests on it", 8, a="middle"))
    # left / right walls with top lips (outer) and back lips (top edge of drawing)
    for side, sx in (("LEFT", bx - H), ("RIGHT", bx + W)):
        o.append(rect(sx, by, H, D))
        o.append(t(sx + H / 2, by + D / 2, side, 11, a="middle", b=True))
        lx = sx - L if side == "LEFT" else sx + H
        o.append(rect(lx, by, L, D, "#dfe8f5"))
        o.append(t(lx + L / 2, by + D / 2 - 30, "top", 7, a="middle")); o.append(t(lx + L / 2, by + D / 2 - 21, "lip", 7, a="middle"))
        # back lip on each side wall (folds inward, lid back screws to it)
        o.append(rect(sx, by - L, H, L, "#dfe8f5")); o.append(t(sx + H / 2, by - 5, "back lip", 7, a="middle"))
        # front corner tab: laps inside the front wall
        tx = sx
        o.append(poly([(tx, by + D), (tx + H, by + D), (tx + H - 4, by + D + L), (tx + 4, by + D + L)], "#f6e3c8"))
        o.append(t(tx + H / 2, by + D + 11, "corner tab", 7, a="middle"))
        for k in (0.3, 0.7):
            o.append(circ(tx + H * k, by + D + 8, 2.2))
    # base back lip
    o.append(rect(bx, by - L, W, L, "#dfe8f5")); o.append(t(bx + W / 2, by - 5, "back lip — lid back screws to it", 8, a="middle"))
    # bend lines
    o += [bend(bx, by, bx + W, by), bend(bx, by + D, bx + W, by + D), bend(bx, by, bx, by + D), bend(bx + W, by, bx + W, by + D),
          bend(bx, by + D + H, bx + W, by + D + H), bend(bx - H, by, bx - H, by + D), bend(bx + W + H, by, bx + W + H, by + D),
          bend(bx - H, by, bx, by), bend(bx + W, by, bx + W + H, by), bend(bx - H, by + D, bx, by + D), bend(bx + W, by + D, bx + W + H, by + D)]
    # corner reliefs where two bend lines meet
    for cx, cy in [(bx, by), (bx + W, by), (bx, by + D), (bx + W, by + D), (bx - H, by), (bx + W + H, by),
                   (bx - H, by + D), (bx + W + H, by + D), (bx, by + D + H), (bx + W, by + D + H)]:
        o.append(circ(cx, cy, 3.2, "#fff", RED, 1.4))
    o.append(t(ox, by + D + H + L + 30, "blue dashed = bend line · red circle = Ø3 relief, cut where two bends meet so the corner can't tear or crash", 9, GREY))
    o.append(t(ox, by + D + H + L + 44, "the back is open: the lid (top + back) closes it", 9, GREY))
    return "".join(o)


def lid_blank(ox, oy):
    o = [panel_title(ox, oy - 12, "B", "Lid blank — top + back (one piece)")]
    W, D, H, L = 220, 150, 70, 14
    x, y = ox + L, oy + L
    o.append(rect(x, y, W, D)); o.append(t(x + W / 2, y + D / 2, "TOP", 12, a="middle", b=True))
    o.append(t(x + W / 2, y + D / 2 + 15, "no vents · laptop sits here", 9, GREY, "middle"))
    o.append(rect(x, y + D, W, H)); o.append(t(x + W / 2, y + D + H / 2, "BACK", 11, a="middle", b=True))
    o.append(t(x + W / 2, y + D + H / 2 + 14, "flow-field vents", 9, GREY, "middle"))
    # return lips down over the outside of the side walls, and over the front lip
    for lx in (x - L, x + W):
        o.append(rect(lx, y, L, D, "#dfe8f5")); o.append(rect(lx, y + D, L, H, "#dfe8f5"))
    o.append(rect(x, y - L, W, L, "#dfe8f5")); o.append(t(x + W / 2, y - 4, "front return lip", 8, a="middle"))
    o.append(t(x - L - 4, y + D / 2, "return lip", 8, a="end"))
    o += [bend(x, y, x + W, y), bend(x, y, x, y + D + H), bend(x + W, y, x + W, y + D + H), bend(x, y + D, x + W, y + D)]
    for cx, cy in [(x, y), (x + W, y), (x, y + D), (x + W, y + D)]:
        o.append(circ(cx, cy, 3.2, "#fff", RED, 1.4))
    # screw holes: top over the side + front lips, back over the side back lips + base back lip
    for k in range(3):
        o.append(circ(x + 10, y + 25 + k * 50, 2.2)); o.append(circ(x + W - 10, y + 25 + k * 50, 2.2))
        o.append(circ(x + 40 + k * 70, y + 10, 2.2))
    for k in range(2):
        o.append(circ(x + 10, y + D + 20 + k * 30, 2.2)); o.append(circ(x + W - 10, y + D + 20 + k * 30, 2.2))
        o.append(circ(x + 70 + k * 80, y + D + H - 10, 2.2))
    o.append(t(ox, y + D + H + 26, "the lips stiffen the lid (an open L flaps) and locate it; screws land in rivnuts in the body's lips", 9, GREY))
    return "".join(o)


def corner_detail(ox, oy):
    """Plan view of a front corner: side-wall tab lapping inside the front wall."""
    o = [panel_title(ox, oy - 12, "C", "Front corner, from above")]
    s = 4.0
    fx, fy = ox + 20, oy + 120              # outside corner
    o.append(rect(fx, fy - T * s * 3, 200, T * s * 3, "#cfd8e3"))  # front wall (drawn thick for legibility)
    o.append(t(fx + 140, fy + 16, "front wall", 10))
    o.append(rect(fx, fy - 110, T * s * 3, 110 - T * s * 3, "#cfd8e3"))  # side wall
    o.append(t(fx + 18, fy - 90, "side wall", 10))
    # tab, inside the front wall
    o.append(rect(fx + T * s * 3, fy - T * s * 6, 70, T * s * 3, "#f6e3c8"))
    o.append(t(fx + 80, fy - 30, "tab folded off the side wall, laps inside the front", 9))
    for k in (0.35, 0.8):
        cx = fx + T * s * 3 + 70 * k
        o.append(line(cx, fy - T * s * 6 - 6, cx, fy + 6, RED, 1.6))
    o.append(t(fx + 60, fy + 34, "2 x M3 rivnut in the tab, screw from outside", 9, RED))
    o.append(t(fx + 60, fy + 47, "(or 2 x blind rivet / a TIG tack — the shop's choice)", 9, GREY))
    o.append(circ(fx + T * s * 3, fy - T * s * 3, 5, "#fff", RED, 1.4))
    o.append(t(fx - 4, fy + 34, "relief", 9, RED))
    return "".join(o)


def lid_section(ox, oy):
    """Section across the top of a side wall with the lid on."""
    o = [panel_title(ox, oy - 12, "D", "Lid on a side wall — section, and the hole offset")]
    s = 6.0
    wx, top = ox + 120, oy + 30
    th = T * s
    # side wall (vertical), inward lip at the top
    o.append(rect(wx, top, th, 150, "#cfd8e3"))
    o.append(rect(wx - LIP * s / 1.5, top, LIP * s / 1.5 + th, th, "#cfd8e3"))
    o.append(t(wx + th + 6, top + 120, "side wall", 10))
    o.append(t(wx - LIP * s / 1.5, top + th + 14, f"top lip {LIP:.0f}", 9))
    # rivnut from BELOW (flange under the lip, so the lid sits flat)
    rx = wx - RIVNUT_FROM_WALL * s / 1.5
    o.append(rect(rx - 9, top + th, 18, 4, "#a0a7b0"))
    o.append(rect(rx - 6, top + th + 4, 12, 34, "#a0a7b0"))
    o.append(t(rx - 64, top + 66, "M3 rivnut, set from below", 9, RED))
    o.append(t(rx - 64, top + 79, "body hangs ~9 mm: keep 12 mm clear", 9, GREY))
    # lid: top sheet on the lip, return lip outside the wall
    lt = top - th
    o.append(rect(wx - 140, lt, 140 + th + LID_CLEAR * s + th, th, "#f6e3c8"))
    o.append(rect(wx + th + LID_CLEAR * s, lt, th, 70, "#f6e3c8"))
    o.append(t(wx + th + LID_CLEAR * s + th + 6, lt + 50, "lid return lip", 9))
    o.append(t(wx + th + LID_CLEAR * s + th + 6, lt + 63, f"{LID_CLEAR} clear to the wall", 9, GREY))
    # screw
    o.append(rect(rx - 7, lt - 6, 14, 6, "#555")); o.append(rect(rx - 2.5, lt, 5, th + th + 30, "#555"))
    # offset dimension
    off_lid = T + LID_CLEAR + T + RIVNUT_FROM_WALL
    y = top + 190
    o.append(line(rx, top + 160, rx, y + 4, GREY, 0.8, "2 2"))
    o.append(line(wx + th + LID_CLEAR * s + th, lt + 75, wx + th + LID_CLEAR * s + th, y + 4, GREY, 0.8, "2 2"))
    o.append(line(rx, y, wx + th + LID_CLEAR * s + th, y, RED, 1.2))
    o.append(t(rx - 4, y + 16, f"lid hole from the lid's outer edge = t + {LID_CLEAR} + t + {RIVNUT_FROM_WALL:.0f} = {off_lid:.1f}", 9, RED))
    o.append(t(rx - 4, y + 29, f"rivnut from the body's outer face = t + {RIVNUT_FROM_WALL:.0f} = {T + RIVNUT_FROM_WALL:.1f} · lid outer = body outer + 2 x {T + LID_CLEAR:.1f}", 9, GREY))
    return "".join(o)


def panel_section(ox, oy):
    """A printed panel on a wall cutout, fixed into rivnuts."""
    o = [panel_title(ox, oy - 12, "E", "Printed panel on a wall — section")]
    s = 5.0
    wx = ox + 150
    th = T * s
    o.append(rect(wx, oy + 10, th, 40, "#cfd8e3")); o.append(rect(wx, oy + 130, th, 40, "#cfd8e3"))
    o.append(t(wx + th + 6, oy + 30, "wall (1 mm)", 9))
    # panel outside: plate + boss into the cutout
    o.append(rect(wx - 15, oy + 30, 15, 120, "#fff3c4"))
    o.append(rect(wx, oy + 52, 2 * s, 76, "#fff3c4"))
    o.append(t(wx - 120, oy + 92, "printed panel (as printed)", 9))
    o.append(t(wx - 120, oy + 105, "boss 2 mm: 1 mm pokes inside, harmless", 9, GREY))
    # countersunk screw into rivnut set from INSIDE
    for yy in (oy + 38, oy + 142):
        o.append(rect(wx - 15, yy - 2.5, 15 + th + 26, 5, "#555"))
        o.append(rect(wx + th, yy - 7, 4, 14, "#a0a7b0")); o.append(rect(wx + th + 4, yy - 5, 22, 10, "#a0a7b0"))
    o.append(t(wx + th + 34, oy + 150, "M3 rivnut set from INSIDE: its flange is", 9, RED))
    o.append(t(wx + th + 34, oy + 163, "behind the wall, so the panel sits flush", 9, RED))
    o.append(t(wx - 120, oy + 190, f"cutout = panel boss + 0.3/side · rivnut hole Ø{RIVNUT_M3_HOLE} at the panel's screw centres", 9, GREY))
    return "".join(o)


def base_section(ox, oy):
    o = [panel_title(ox, oy - 12, "F", "Base plate on the floor — section")]
    s = 4.0
    fy = oy + 120
    o.append(rect(ox + 10, fy, 330, T * s, "#cfd8e3")); o.append(t(ox + 345, fy + 6, "floor 1 mm", 9))
    o.append(rect(ox + 10, fy - 5 * s - 2 * s, 330, 2 * s, "#e3e8d8")); o.append(t(ox + 345, fy - 22, "base plate 2 mm", 9))
    for cx in (ox + 40, ox + 300):
        o.append(rect(cx - 6, fy - 5 * s, 12, 5 * s, "#a0a7b0"))
        o.append(rect(cx - 2.5, fy - 5 * s - 2 * s - 3, 5, 5 * s + 2 * s + T * s + 10, "#555"))
    o.append(t(ox + 40, fy + 30, "M4 standoff 5 mm, screws through the floor", 9, a="middle"))
    # grid hole with a rivnut and a printed anchor
    for k in range(4):
        hx = ox + 90 + k * 50
        o.append(rect(hx - 5, fy - 5 * s - 2 * s, 10, 2 * s, "#fff", GREY))
    o.append(rect(ox + 185, fy - 5 * s - 2 * s - 40, 50, 40, "#fff3c4")); o.append(t(ox + 210, fy - 5 * s - 2 * s - 18, "anchor", 9, a="middle"))
    o.append(rect(ox + 187, fy - 5 * s - 2 * s - 2, 6, 2 * s + 12, "#a0a7b0"))
    o.append(t(ox + 90, fy - 70, f"grid: Ø{RIVNUT_M4_HOLE} holes, 40 mm rows, every other row shifted 20", 9))
    o.append(t(ox + 90, fy - 57, "M4 rivnut where a part needs it, plain hole elsewhere", 9))
    return "".join(o)


def rules(ox, oy):
    rows = [("sheet", f"{T:.0f} mm 304 stainless"), ("inner bend radius", f"{R:.0f} mm (= t)"),
            ("K-factor", f"{K} (the shop's number wins)"),
            ("bend allowance / deduction", f"{BA:.2f} / {BD:.2f} mm per 90° bend"),
            ("lips", f"{LIP:.0f} mm (≥ 8 needed by the brake)"), ("bend relief", f"Ø{RELIEF:.0f} where two bends meet"),
            ("hole to bend line", f"≥ {HOLE_TO_BEND:.0f} mm, edge to bend"),
            ("rivnut to the wall it folds off", f"≥ {RIVNUT_FROM_WALL:.0f} mm (clears the bend + rivnut body)"),
            ("M3 / M4 rivnut hole", f"Ø{RIVNUT_M3_HOLE} / Ø{RIVNUT_M4_HOLE} — MEASURE yours"),
            ("lid to body", f"{LID_CLEAR} mm per side inside the lid's return lips")]
    o = [panel_title(ox, oy - 12, "G", "Rules every cut file follows")]
    for i, (a, b) in enumerate(rows):
        o.append(t(ox, oy + 14 + i * 17, a, 10, GREY)); o.append(t(ox + 210, oy + 14 + i * 17, b, 10))
    o.append(t(ox, oy + 14 + len(rows) * 17 + 10, "Hand the shop the FOLDED drawing; they unfold with their own tooling.", 10, b=True))
    return "".join(o)


def main():
    parts = [body_blank(30, 60), lid_blank(530, 60), corner_detail(30, 470), lid_section(400, 470),
             panel_section(30, 790), base_section(400, 790), rules(30, 1060)]
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="900" height="1330" font-family="Helvetica, Arial, sans-serif">'
           f'<rect width="100%" height="100%" fill="#fff"/>'
           f'{t(30, 30, "Enclosure construction — 1 mm stainless, two boxes (low fidelity, not to scale)", 16, b=True)}'
           f'{"".join(parts)}</svg>')
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(svg)
    print(OUT)


if __name__ == "__main__":
    main()
