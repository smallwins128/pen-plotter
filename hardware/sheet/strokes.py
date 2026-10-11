#!/usr/bin/env python3
"""Brush strokes on the power box front: raised black printed ribs pushed through slots in the steel.

    python3 hardware/sheet/strokes.py        # writes hardware/out/strokes_preview.svg

Hand-drawn: three wave guides from the lower left toward the upper right, each broken
into short strokes (each prints on its own). Every stroke has a brush profile: a quick
swell from a fine tip, a broad belly, a long taper to the tail. Its height above the
steel follows the same breath: flush at both tips, highest in the belly.
Coordinates: front-face mm, x from the left edge, y up from the bottom edge.
"""
import math
import pathlib

from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

# wave guides (Catmull-Rom through these points), lowest first
GUIDES = [
    [(70, 24), (118, 23), (170, 40), (230, 67), (284, 83), (338, 90), (370, 89)],
    [(86, 50), (134, 54), (184, 76), (234, 99), (278, 111), (326, 115)],
    [(122, 82), (166, 96), (208, 111), (250, 123), (296, 127)],
    [(324, 126), (348, 132), (368, 134)],                          # a last flick toward the mark
]
# strokes: (guide, t0, t1, belly width, peak height, where the belly sits 0..1)
STROKES = [
    (0, 0.00, 0.42, 9.0, 5.0, 0.35),
    (0, 0.50, 0.97, 7.0, 4.0, 0.30),
    (1, 0.03, 0.45, 10.0, 5.5, 0.32),
    (1, 0.53, 0.95, 6.0, 3.5, 0.35),
    (2, 0.00, 0.48, 7.5, 4.5, 0.35),
    (2, 0.57, 1.00, 5.0, 3.0, 0.30),
    (3, 0.00, 1.00, 4.0, 2.5, 0.30),
]
# ETCH mark: Orbitron Black (SIL Open Font License), outlines grown for a heavier stroke, cut through the
# steel; a printed plate behind pushes the letters out MARK_PROUD. Outlines are stored in mark_etch.json
# (made by build_mark() from the font), so the generator needs no font file.
MARK_LEFT, MARK_TOP = 48.0, 128.0        # left edge and cap top, front-face mm (top left, wave set to its lower right)
MARK_CAP, MARK_BOLD, MARK_TRACK = 18.0, 0.5, 0.10
MARK_PROUD = 1.5
MARK_JSON = pathlib.Path(__file__).resolve().parent / "mark_etch.json"


# placement: the guides above are drawn at full size; the set is shrunk into the lower-left quadrant
SCALE, FROM, TO = 0.74, (69.0, 18.0), (175.0, 30.0)
W_SCALE, H_SCALE = 0.85, 0.9
TIP_W = 2.2          # slot width at the fine tips (the printed tip is 0.3 narrower)
CLEAR = 0.15         # print smaller than the slot, per side
FLANGE = 2.5         # printed flange past the slot, inside the steel
FLANGE_T = 1.2
MIN_WEB = 2 * FLANGE + 1.0   # slot to slot, so neighbouring flanges never touch


def _xf(pt):
    return (TO[0] + (pt[0] - FROM[0]) * SCALE, TO[1] + (pt[1] - FROM[1]) * SCALE)


def catmull(pts, n=400):
    """Centripetal-ish Catmull-Rom through pts, returned as a dense polyline."""
    P = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    seg = len(pts) - 1
    for i in range(seg):
        p0, p1, p2, p3 = P[i], P[i + 1], P[i + 2], P[i + 3]
        for k in range(n // seg):
            t = k / (n // seg)
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    out.append(pts[-1])
    return out


def _resample(line, t0, t1, n):
    L = line.length
    return [line.interpolate(L * (t0 + (t1 - t0) * i / (n - 1))).coords[0] for i in range(n)]


def profile(t, belly):
    """0..1 brush breath: fine at both tips, swelling quickly to a belly at `belly`, long taper after."""
    if t <= belly:
        a = t / belly
        return math.sin(a * math.pi / 2) ** 0.8
    a = (t - belly) / (1 - belly)
    return math.cos(a * math.pi / 2) ** 1.3


def strokes():
    """Each stroke: centreline samples (x, y, slot width, height above the steel) and its slot outline."""
    out = []
    for gi, t0, t1, wmax, hmax, belly in STROKES:
        line = LineString(catmull([_xf(q) for q in GUIDES[gi]]))
        wmax, hmax = TIP_W + (wmax - TIP_W) * W_SCALE, hmax * H_SCALE
        n = max(40, int(line.length * (t1 - t0) / 1.5))
        c = _resample(line, t0, t1, n)
        samples = []
        for i, (x, y) in enumerate(c):
            t = i / (n - 1)
            p = profile(t, belly)
            samples.append((x, y, TIP_W + (wmax - TIP_W) * p, hmax * p))
        out.append(dict(samples=samples, outline=outline(samples), length=LineString(c).length))
    return out


def outline(samples, shrink=0.0):
    """Slot outline: offset the centreline by half the local width each side, round tips."""
    left, right = [], []
    for i, (x, y, w, _) in enumerate(samples):
        a = samples[max(0, i - 1)]; b = samples[min(len(samples) - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy) or 1
        nx, ny = -dy / L, dx / L
        r = w / 2 - shrink
        left.append((x + nx * r, y + ny * r)); right.append((x - nx * r, y - ny * r))
    body = Polygon(left + right[::-1]).buffer(0)
    tips = [LineString([samples[0][:2], samples[0][:2]]).buffer(samples[0][2] / 2 - shrink, 16),
            LineString([samples[-1][:2], samples[-1][:2]]).buffer(samples[-1][2] / 2 - shrink, 16)]
    g = unary_union([body] + [t for t in tips if not t.is_empty])
    return g.simplify(0.05)


def build_mark(font_path, text="ETCH"):
    """Flatten the font's outlines, grow them by MARK_BOLD with square corners, place them, save to MARK_JSON."""
    import json
    from fontTools.pens.basePen import BasePen
    from fontTools.ttLib import TTFont
    from shapely.geometry import Polygon as Pg

    class Flat(BasePen):
        def __init__(self, gs):
            super().__init__(gs); self.contours, self.cur = [], []
        def _moveTo(self, p): self.cur = [p]
        def _lineTo(self, p): self.cur.append(p)
        def _curveToOne(self, p1, p2, p3):
            p0 = self.cur[-1]
            for i in range(1, 13):
                t = i / 12; u = 1 - t
                self.cur.append(tuple(u ** 3 * p0[k] + 3 * u * u * t * p1[k] + 3 * u * t * t * p2[k] + t ** 3 * p3[k] for k in (0, 1)))
        def _closePath(self):
            if len(self.cur) > 2: self.contours.append(self.cur)
            self.cur = []

    f = TTFont(font_path); gs = f.getGlyphSet(); cmap = f.getBestCmap(); upm = f["head"].unitsPerEm
    pen = Flat(gs); gs[cmap[ord("H")]].draw(pen)
    cap = max(y for c in pen.contours for _, y in c); k = MARK_CAP / cap
    glyphs, x = [], 0.0
    for ch in text:
        pen = Flat(gs); gs[cmap[ord(ch)]].draw(pen)
        g = None
        for c in pen.contours:
            pg = Pg([(x + px * k, py * k) for px, py in c]).buffer(0)
            g = pg if g is None else g.symmetric_difference(pg)
        glyphs.append(g.buffer(MARK_BOLD, join_style=2, mitre_limit=3))
        x += (gs[cmap[ord(ch)]].width + MARK_TRACK * upm) * k
    left = min(g.bounds[0] for g in glyphs)
    dx, dy = MARK_LEFT - left, MARK_TOP - MARK_CAP
    out = []
    for g in glyphs:
        for poly in getattr(g, "geoms", [g]):
            out.append(dict(shell=[(round(px + dx, 3), round(py + dy, 3)) for px, py in poly.exterior.coords],
                            holes=[[(round(px + dx, 3), round(py + dy, 3)) for px, py in r.coords] for r in poly.interiors]))
    MARK_JSON.write_text(json.dumps(dict(font="Orbitron Black (SIL OFL)", text=text, cap=MARK_CAP, bold=MARK_BOLD, polys=out)))
    print("wrote", MARK_JSON)


def mark():
    """Slot polygons for the mark (front-face mm)."""
    import json
    d = json.loads(MARK_JSON.read_text())
    return [Polygon(q["shell"], q["holes"]) for q in d["polys"]]


def report():
    s = strokes()
    slots = [d["outline"] for d in s]
    web = min(slots[i].distance(slots[j]) for i in range(len(slots)) for j in range(i + 1, len(slots)))
    m = mark()
    mw = min(m[i].distance(m[j]) for i in range(len(m)) for j in range(i + 1, len(m)))
    ms = min(a.distance(b) for a in m for b in slots)
    mb = unary_union(m).bounds
    print(f"mark {mb[2] - mb[0]:.0f} x {mb[3] - mb[1]:.0f} mm at x {mb[0]:.0f}-{mb[2]:.0f}, y {mb[1]:.0f}-{mb[3]:.0f}; webs {mw:.2f} (need 1.5); to strokes {ms:.1f}")
    print(f"strokes span x {min(d['outline'].bounds[0] for d in s):.0f}-{max(d['outline'].bounds[2] for d in s):.0f}, y {min(d['outline'].bounds[1] for d in s):.0f}-{max(d['outline'].bounds[3] for d in s):.0f}")
    print(f"{len(s)} strokes, lengths {', '.join(f'{d['length']:.0f}' for d in s)} mm; closest slots {web:.1f} mm (need {MIN_WEB})")
    for d in s:
        b = d["outline"].buffer(FLANGE).bounds
        print(f"  print footprint {b[2] - b[0]:.0f} x {b[3] - b[1]:.0f} mm, peak {max(q[3] for q in d['samples']):.1f} mm proud")
    return s


def preview(path):
    W, H, s = 452, 171, report()
    def P(poly):
        return " ".join(f"{x:.2f},{H - y:.2f}" for x, y in poly.exterior.coords)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-10 -10 {W + 20} {H + 20}" width="{(W + 20) * 3}" height="{(H + 20) * 3}">',
           f'<rect x="-10" y="-10" width="{W + 20}" height="{H + 20}" fill="#2a2d31"/>',
           f'<rect x="0" y="0" width="{W}" height="{H}" fill="#c9cdd1"/>',
           f'<rect x="0" y="0" width="{W}" height="15" fill="#b3b8bd"/>']
    for x in (8.5, W - 8.5):
        for y in (0.3 * H, 0.7 * H):
            out.append(f'<circle cx="{x}" cy="{H - y}" r="2.8" fill="#9aa0a6"/>')
    for d in s:
        out.append(f'<polygon points="{P(d["outline"].buffer(FLANGE))}" fill="none" stroke="#7a7f85" stroke-width="0.25" stroke-dasharray="1.5 1"/>')
    for d in s:   # shade the slot by height: darker where it stands proud
        smp = d["samples"]
        for i in range(len(smp) - 1):
            seg = Polygon(outline(smp[i:i + 2]).exterior.coords)
            h = smp[i][3]
            g = int(70 - 14 * h)
            out.append(f'<polygon points="{P(seg)}" fill="rgb({g},{g + 2},{g + 5})" stroke="none"/>')
    for g in mark():
        out.append(f'<polygon points="{P(g)}" fill="#1c1e21" stroke="#6a6e73" stroke-width="0.3"/>')
    out.append("</svg>")
    path.write_text("\n".join(out))
    print("wrote", path)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2 and sys.argv[1] == "--build-mark":
        build_mark(sys.argv[2])
    preview(pathlib.Path(__file__).resolve().parent.parent / "out" / "strokes_preview.svg")
