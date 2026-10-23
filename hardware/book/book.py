"""Etch build book: IKEA-style 2D pages, one face per drawing, a few lines of text per step.

Geometry comes from the generator (enclosure.py: walls, holes, panels), the control layout (layout_control.py) and the
printed parts' own STLs (outlines traced from hardware/out/), so the pages match the steel and the prints.
Run the part scripts first so the STLs exist (gx_plates.py, din_mounts.py, window_meccano.py, bend_jig.py).

    python3 hardware/book/book.py      # writes hardware/book/build_book.html
"""
import math
import pathlib
import sys
from html import escape

HERE = pathlib.Path(__file__).resolve().parent
OUTDIR = HERE.parent / "out"
sys.path.insert(0, str(HERE.parent / "sheet"))
sys.path.insert(0, str(HERE.parent / "parts"))
import enclosure as E  # noqa: E402
import layout_control as LC  # noqa: E402

PARTS = {p.name: p for p in E.build()}
PANELS = {k: {q["key"]: q for q in PARTS[f"{k}_body"].panels} for k in ("control", "power")}
INK, FAINT, MID, ACC = "#111", "#c4c4c4", "#777", "#d33"
WIRE = dict(L="#8a5a2b", N="#2b62c4", PE="#2f9a4a", P24="#d33", P12="#e07b00", P6="#a5c", G="#111", SIG="#2a8fbf")
PW, PH = 297, 210                      # A4 landscape, mm
TX = 168                               # text column left edge

F = lambda x: f"{x:.2f}".rstrip("0").rstrip(".")  # noqa: E731


# ============================================================================
# SVG primitives
# ============================================================================
class Svg:
    def __init__(self):
        self.s = []

    def add(self, t):
        self.s.append(t)
        return self

    @staticmethod
    def _d(dash):
        return f' stroke-dasharray="{dash}"' if dash else ""

    def line(self, x0, y0, x1, y1, w=0.35, c=INK, dash=None, cap="butt"):
        return self.add(f'<line x1="{F(x0)}" y1="{F(y0)}" x2="{F(x1)}" y2="{F(y1)}" stroke="{c}" stroke-width="{F(w)}" stroke-linecap="{cap}"{self._d(dash)}/>')

    def rect(self, x, y, w, h, sw=0.35, c=INK, fill="none", dash=None, r=0):
        x, w = (x + w, -w) if w < 0 else (x, w)
        y, h = (y + h, -h) if h < 0 else (y, h)
        return self.add(f'<rect x="{F(x)}" y="{F(y)}" width="{F(w)}" height="{F(h)}" rx="{F(r)}" stroke="{c}" stroke-width="{F(sw)}" fill="{fill}"{self._d(dash)}/>')

    def circ(self, x, y, r, sw=0.35, c=INK, fill="none", dash=None):
        return self.add(f'<circle cx="{F(x)}" cy="{F(y)}" r="{F(r)}" stroke="{c}" stroke-width="{F(sw)}" fill="{fill}"{self._d(dash)}/>')

    def poly(self, pts, sw=0.35, c=INK, fill="none", close=True, dash=None):
        tag = "polygon" if close else "polyline"
        return self.add(f'<{tag} points="{" ".join(f"{F(a)},{F(b)}" for a, b in pts)}" stroke="{c}" stroke-width="{F(sw)}" fill="{fill}" stroke-linejoin="round"{self._d(dash)}/>')

    def path(self, d, sw=0.35, c=INK, fill="none", rule="evenodd", dash=None):
        return self.add(f'<path d="{d}" stroke="{c}" stroke-width="{F(sw)}" fill="{fill}" fill-rule="{rule}" stroke-linejoin="round"{self._d(dash)}/>')

    def text(self, x, y, s, size=3.2, anchor="start", weight=400, c=INK, rot=0):
        tr = f' transform="rotate({F(rot)} {F(x)} {F(y)})"' if rot else ""
        return self.add(f'<text x="{F(x)}" y="{F(y)}" font-size="{F(size)}" text-anchor="{anchor}" font-weight="{weight}" fill="{c}"{tr}>{escape(s)}</text>')

    def arrow(self, x0, y0, x1, y1, c=MID, w=0.45):
        a = math.atan2(y1 - y0, x1 - x0)
        h = 2.4
        self.line(x0, y0, x1, y1, w, c)
        return self.poly([(x1, y1), (x1 - h * math.cos(a - .4), y1 - h * math.sin(a - .4)),
                          (x1 - h * math.cos(a + .4), y1 - h * math.sin(a + .4))], .2, c, c)

    def g(self, tx, ty, s, inner, sy=None):
        sy = s if sy is None else sy
        return self.add(f'<g transform="translate({F(tx)} {F(ty)}) scale({F(s)} {F(sy)})">{inner}</g>')

    def out(self):
        return "".join(self.s)


def wire(s, pts, kind, w=0.8, label=None, at=0):
    """A coloured wire along pts; PE gets the yellow stripe."""
    c = WIRE[kind]
    s.poly(pts, w, c, close=False)
    if kind == "PE":
        s.poly(pts, w * .45, "#e8d02a", close=False, dash="1.4 1.4")
    if label:
        (x0, y0), (x1, y1) = pts[at], pts[at + 1]
        s.text((x0 + x1) / 2, (y0 + y1) / 2 - 1.2, label, 2.3, "middle", c=MID)


def sub(s, x, y, ch):
    s.circ(x, y, 3, .4, fill="#fff")
    s.text(x, y + 1.2, ch, 3.3, "middle", 700)


def callout(s, x, y, r, cx, cy, cr):
    s.circ(x, y, r, .4)
    a = math.atan2(cy - y, cx - x)
    s.line(x + r * math.cos(a), y + r * math.sin(a), cx - cr * math.cos(a), cy - cr * math.sin(a), .4)
    s.circ(cx, cy, cr, .5, fill="#fff")


def front_arrow(s, x, y, left, label="FRONT"):
    dx = -14 if left else 14
    s.arrow(x, y, x + dx, y, MID, .4)
    s.text(x + dx / 2, y - 1.8, label, 2.4, "middle", c=MID)


def caption(s, x, y, t):
    s.text(x, y, t, 2.6, c=MID)


def box(s, x, y, w, h, label="", sub_="", fill="#fff", dash=None, size=2.8, c=INK):
    s.rect(x, y, w, h, .4, c, fill, dash, r=1)
    if label:
        s.text(x + w / 2, y + h / 2 + (0 if sub_ else size * .35), label, size, "middle", 700, c)
    if sub_:
        s.text(x + w / 2, y + h / 2 + size * 1.1, sub_, size * .78, "middle", c=MID)


def term(s, x, y, name, side="r", c=INK):
    """A terminal dot with its name on the inner side."""
    s.circ(x, y, .9, .3, INK, "#fff")
    if side == "r":
        s.text(x - 1.8, y + .9, name, 2.2, "end", c=c)
    else:
        s.text(x + 1.8, y + .9, name, 2.2, c=c)
    return (x, y)


# ============================================================================
# icons (≈ 1:1 mm, side view; origin top-left). Each returns (svg, w, h)
# ============================================================================
def _thread(s, x0, x1, y0, L, p=.6):
    for i in range(int(L / p) - 1):
        s.line(x0, y0 + .3 + i * p, x1, y0 + .3 + i * p + p / 2, .12)


def i_csk(L, d=3, head=6):
    s = Svg()
    hh = (head - d) / 2
    s.poly([(0, 0), (head, 0), (head - hh, hh), (hh, hh)], .3, INK, "#fff")
    s.rect(hh, hh, d, L - hh, .3, INK, "#fff")
    _thread(s, hh, hh + d, hh, L - hh)
    return s.out(), head, L


def i_pan(L, d=3, head=5.5, hh=2):
    s = Svg()
    s.rect(0, 0, head, hh, .3, INK, "#fff", r=.8)
    s.rect((head - d) / 2, hh, d, L, .3, INK, "#fff")
    _thread(s, (head - d) / 2, (head + d) / 2, hh, L, d * .2)
    return s.out(), head, L + hh


def i_button(L, d=3, head=5.7, hh=1.65):
    s = Svg()
    s.path(f"M0 {hh} Q0 0 {head / 2} 0 Q{head} 0 {head} {hh} Z", .3, INK, "#fff")
    s.rect((head - d) / 2, hh, d, L, .3, INK, "#fff")
    _thread(s, (head - d) / 2, (head + d) / 2, hh, L, d * .2)
    return s.out(), head, L + hh


def i_hex(L, d=6, head=10, hh=4):
    s = Svg()
    s.rect(0, 0, head, hh, .3, INK, "#fff")
    s.line(head / 3, 0, head / 3, hh, .2)
    s.line(2 * head / 3, 0, 2 * head / 3, hh, .2)
    s.rect((head - d) / 2, hh, d, L, .3, INK, "#fff")
    _thread(s, (head - d) / 2, (head + d) / 2, hh, L, d * .17)
    return s.out(), head, L + hh


def i_nut(w=5.5, h=2.4, nyloc=False):
    s = Svg()
    if nyloc:
        s.rect(w * .12, 0, w * .76, h * .45, .3, INK, "#eee", r=.4)
    y = h * .45 if nyloc else 0
    s.rect(0, y, w, h, .3, INK, "#fff")
    s.line(w / 3, y, w / 3, y + h, .2)
    s.line(2 * w / 3, y, 2 * w / 3, y + h, .2)
    return s.out(), w, y + h


def i_washer(od=7, t=.6, serrated=False, fill="#fff"):
    s = Svg()
    s.rect(0, 0, od, max(t, .6), .3, INK, fill)
    if serrated:
        s.poly([(i * od / 8, t if i % 2 else 0) for i in range(9)], .2, close=False)
    return s.out(), od, max(t, .6)


def i_rivnut(d=5, L=10, fl=8, ft=1):
    s = Svg()
    s.rect(0, 0, fl, ft, .3, INK, "#fff")
    s.rect((fl - d) / 2, ft, d, L - ft, .3, INK, "#fff")
    for i in range(4):
        s.line((fl - d) / 2 + .2, ft + 1 + i * 1.6, (fl + d) / 2 - .2, ft + 1.6 + i * 1.6, .15)
    return s.out(), fl, L


def i_rivet(d=3.2, L=8, head=5.6):
    s = Svg()
    s.path(f"M0 1.6 Q0 0 {head / 2} 0 Q{head} 0 {head} 1.6 Z", .3, INK, "#fff")
    s.rect((head - d) / 2, 1.6, d, L, .3, INK, "#fff")
    return s.out(), head, L + 1.6


def i_standoff(L=5, w=7):
    s = Svg()
    s.poly([(0, 0), (w, 0), (w, L), (0, L)], .3, INK, "#fff")
    s.line(w / 3, 0, w / 3, L, .2)
    s.line(2 * w / 3, 0, 2 * w / 3, L, .2)
    return s.out(), w, L


def i_insert(d=4.3, L=4):
    s = Svg()
    s.rect(0, 0, d, L, .3, INK, "#e9d48a")
    for i in range(3):
        s.line(0, .6 + i * 1.3, d, 1.2 + i * 1.3, .2)
    return s.out(), d, L


def i_ring(hole=4, c="#2b62c4"):
    s = Svg()
    s.circ(4, 4, 4, .3, INK, "#fff")
    s.circ(4, 4, hole / 2, .3)
    s.rect(7.5, 2.4, 6, 3.2, .3, INK, c)
    s.line(13.5, 4, 19, 4, 1, c)
    return s.out(), 19, 8


def i_spade(c="#8a5a2b"):
    s = Svg()
    s.rect(0, 1, 7, 4, .3, INK, "#fff", r=.6)
    s.rect(7, .4, 6, 5.2, .3, INK, c)
    s.line(13, 3, 18, 3, 1, c)
    return s.out(), 18, 6


def i_ferrule(c="#2b62c4"):
    s = Svg()
    s.rect(0, 1.2, 8, 1.6, .3, INK, "#ddd")
    s.poly([(8, 0), (14, .6), (14, 3.4), (8, 4)], .3, INK, c)
    return s.out(), 14, 4


def i_wago():
    s = Svg()
    s.rect(0, 2, 18, 8, .3, INK, "#f2f2f2", r=1)
    for i in range(3):
        s.rect(1 + i * 6, 0, 4, 4, .3, INK, "#f2a33a", r=.6)
    return s.out(), 18, 10


def i_label(t, w=None, h=8, fill="#fff", size=2.4):
    w = w or max(10, len(t) * size * .55 + 4)
    s = Svg()
    s.rect(0, 0, w, h, .3, INK, fill, r=1)
    s.text(w / 2, h / 2 + size * .35, t, size, "middle", 700)
    return s.out(), w, h


def i_round(d, fill="#fff", inner=None, inner_fill="none"):
    s = Svg()
    s.circ(d / 2, d / 2, d / 2, .3, INK, fill)
    if inner:
        s.circ(d / 2, d / 2, inner / 2, .3, INK, inner_fill)
    return s.out(), d, d


def i_clip():
    s = Svg()
    s.rect(0, 0, 25, 7, .3, INK, "#fff", r=1)
    s.circ(5, 3.5, 1.7, .3)
    s.circ(20, 3.5, 1.7, .3)
    s.path("M2 7 L2 10 L6 10 M23 7 L23 10 L19 10", .3)
    return s.out(), 25, 10


def i_gx(pins):
    s = Svg()
    s.circ(8, 8, 8, .3, INK, "#fff")
    s.circ(8, 8, 5.6, .3)
    for i in range(pins):
        a = 2 * math.pi * i / pins - math.pi / 2
        s.circ(8 + 3.4 * math.cos(a), 8 + 3.4 * math.sin(a), .7, .2, INK, INK)
    return s.out(), 16, 16


def i_meter():
    s = Svg()
    s.rect(0, 0, 12, 18, .3, INK, "#f5d33a", r=1.5)
    s.rect(2, 2, 8, 5, .3, INK, "#dfe8d8")
    s.circ(6, 12, 2.6, .3, INK, "#fff")
    return s.out(), 12, 18


def i_fan():
    s = Svg()
    s.rect(0, 0, 20, 20, .3, INK, "#fff", r=1.5)
    s.circ(10, 10, 9, .25)
    s.circ(10, 10, 3, .25)
    for i in range(4):
        s.circ(2.2 + 15.6 * (i % 2), 2.2 + 15.6 * (i // 2), .9, .2)
    return s.out(), 20, 20


def i_rail(L=40):
    s = Svg()
    s.rect(0, 0, L, 7, .3, INK, "#dfe3e6")
    for i in range(int(L / 10)):
        s.rect(3 + i * 10, 2.3, 5, 2.4, .2, INK, "#fff", r=1)
    return s.out(), L, 7


def i_lead(c="#d33"):
    s = Svg()
    s.rect(0, 0, 5, 9, .3, INK, c, r=1)
    s.path("M2.5 9 C 4 20, 22 20, 24 9", 1.1, c)
    s.rect(21.5, 0, 5, 9, .3, INK, c, r=1)
    return s.out(), 26.5, 17


# ============================================================================
# page furniture
# ============================================================================
def wrap(t, n):
    out, line = [], ""
    for w in t.split():
        if len(line) + len(w) + 1 > n and line:
            out.append(line)
            line = w
        else:
            line = f"{line} {w}".strip()
    return out + [line] if line else out


def ok_box(s, x, y, text):
    s.rect(x, y, 5.5, 5.5, .4, r=1)
    s.poly([(x + 1.1, y + 3), (x + 2.4, y + 4.3), (x + 4.5, y + 1.2)], .6, close=False)
    s.text(x + 8, y + 4.3, text, 3.1, weight=600)


def page(num, title, parts, body, steps=(), notes=(), check="", stage=""):
    """parts: [(icon, scale, qty, id)]; body: drawing svg; steps: numbered text lines; notes: ⚠/🚫 lines."""
    s = Svg()
    s.rect(0, 0, PW, PH, 0, fill="#fff")
    if stage:
        s.text(10, 9, stage.upper(), 2.3, c=MID, weight=600)
    s.text(10, 23, num, 15, weight=700)
    s.text(10 + len(num) * 8.6 + 3, 22.5, title, 4.4, weight=600)
    # parts box, wrapped at 150 mm: icon, quantity, spec (2 lines max), ID
    if parts:
        cells = []
        for pt in parts:
            (svg, w, h), sc, qty, pid = pt[:4]
            spec = pt[4] if len(pt) > 4 and pt[4] else NAMES.get(pid, "")
            lines = wrap(spec, 15)[:2]
            cw = max(w * sc, 21, max((len(x) for x in lines), default=0) * 1.25)
            cells.append((svg, w * sc, h * sc, sc, qty, pid, lines, cw))
        rows, row, rw = [], [], 6
        for c in cells:
            if rw + c[7] + 5 > 150 and row:
                rows.append(row)
                row, rw = [], 6
            row.append(c)
            rw += c[7] + 5
        rows.append(row)
        x0, y = 10, 29
        bw = max(sum(c[7] + 5 for c in r) for r in rows) + 6
        heights = [max(c[2] for c in r) + 21 for r in rows]
        s.rect(x0, y, bw, sum(heights) + 2, .4, r=2)
        for r, rh in zip(rows, heights):
            x = x0 + 6
            for svg, w, h, sc, qty, pid, lines, cw in r:
                s.g(x + (cw - w) / 2, y + 3 + (rh - 21 - h) / 2, sc, svg)
                yb = y + rh - 12.5
                s.text(x + cw / 2, yb, f"{qty}x" if isinstance(qty, int) else qty, 3.4, "middle", 700)
                for j, ln in enumerate(lines):
                    s.text(x + cw / 2, yb + 3.4 + j * 2.8, ln, 2.3, "middle", c="#333")
                s.text(x + cw / 2, y + rh - 1.6, pid, 2.0, "middle", c=MID)
                x += cw + 5
            y += rh
        box_bottom = y + 2
    else:
        box_bottom = 0
    # text column
    y = 14
    for i, st in enumerate(steps):
        lines = wrap(st, 62)
        s.text(TX, y, f"{i + 1}", 3.1, weight=700)
        for j, ln in enumerate(lines):
            s.text(TX + 5, y + j * 4.1, ln, 3.1)
        y += len(lines) * 4.1 + 1.6
    for n in notes:
        for j, ln in enumerate(wrap(n, 66)):
            s.text(TX, y + 1 + j * 3.7, ln, 2.8, c="#a33" if n.startswith(("⚠", "🚫")) else MID)
        y += len(wrap(n, 66)) * 3.7 + 1
    top, bot = 50.0, PH - 15.0
    if box_bottom + 3 > top:                     # parts box grew: shrink the drawing into the space left, anchored bottom-left
        k = (bot - box_bottom - 3) / (bot - top)
        s.add(f'<g transform="translate(10 {F(bot)}) scale({F(k)}) translate(-10 {F(-bot)})">{body}</g>')
    else:
        s.add(body)
    if check:
        ok_box(s, 10, PH - 12, check)
    s.text(PW - 10, PH - 6, num, 2.6, "end", c=MID)
    return f'<svg class="page" id="p{num.replace(".", "-")}" viewBox="0 0 {PW} {PH}" xmlns="http://www.w3.org/2000/svg" font-family="Helvetica, Arial, sans-serif">{s.out()}</svg>'


# ============================================================================
# faces from the generator
# ============================================================================
SGN = {("front", True): 1, ("front", False): -1, ("left", True): 1, ("left", False): -1,
       ("right", True): -1, ("right", False): 1, ("back", True): -1, ("back", False): 1}


def holes(kind, face):
    return [h for h in PARTS[f"{kind}_body"].holes if h["face"] == face]


def face_w(face):
    return E.W if face in ("front", "back") else E.D


def wall(s, kind, face, ox, oy, sc, outside=True, hi=(), all_ink=False, lw=.5):
    """A wall as a flat face, (ox, oy) = page position of its bottom-left corner. hi: note keywords drawn heavy.
    Returns P(u, v) -> page point."""
    Wf, Hh = face_w(face), E.H[kind] + E.T
    sg = SGN[(face, outside)]

    def P(u, v):
        return ox + (sg * u + Wf / 2) * sc, oy - v * sc

    s.rect(ox, oy - Hh * sc, Wf * sc, Hh * sc, lw, fill="#fff")

    def style(note):
        strong = all_ink or any(k in note for k in hi)
        return (INK, .4) if strong else (FAINT, .25)

    for h in holes(kind, face):
        c, w = style(h["note"])
        if h["kind"] == "rect":
            (u, v), (ww, hh) = h["uv"], h["uvwh"]
            x0, y0 = P(u - ww / 2, v + hh / 2)
            x1, y1 = P(u + ww / 2, v - hh / 2)
            s.rect(min(x0, x1), y0, abs(x1 - x0), y1 - y0, w, c, r=3 * sc)
        elif h["kind"] == "circle" and "uv" in h:
            s.circ(*P(*h["uv"]), h["r"] * sc, w, c)
        elif h["kind"] == "poly":
            s.poly([P(a, b) for a, b in h["uvpts"]], w, c)
        elif h["kind"] == "slot":
            (u, v), (L, wd, a) = h["uv"], h["uvslot"]
            hl = L / 2 - wd / 2
            p0, p1 = P(u - hl * math.cos(a), v - hl * math.sin(a)), P(u + hl * math.cos(a), v + hl * math.sin(a))
            s.line(*p0, *p1, wd * sc, c, cap="round")
            s.line(*p0, *p1, max(wd * sc - 2 * w, .05), "#fff", cap="round")
    if face == "left":
        fz, fy = E.FAN[kind]
        c, _ = style("fan")
        for r in (12, 20, 28, 36):
            s.circ(*P(fz, fy), r * sc, .25, c, dash="1.4 .8")
    return P


def floor(s, kind, cx, cy, sc, hi=(), plate=False, plate_hi=None):
    """Floor from above, front at the bottom. (cx, cy) = page centre. Returns P(x, z)."""
    W, D = E.W, E.D

    def P(x, z):
        return cx + x * sc, cy + z * sc

    s.rect(cx - W / 2 * sc, cy - D / 2 * sc, W * sc, D * sc, .5, fill="#fff")
    for h in holes(kind, "base"):
        strong = any(k in h["note"] for k in hi)
        s.circ(*P(*h["uv"]), 2.25 * sc, .3 if strong else .2, INK if strong else FAINT)
    if plate:
        pl = PARTS[f"{kind}_base_plate"]
        s.poly([P(x, z) for x, z in pl.outline().exterior.coords[:-1]], .45, fill="#f6f6f4")
        for h in pl.holes:
            x, z = h["c"]
            st = "standoff" in (h.get("note") or "")
            hl = plate_hi and plate_hi(x, z)
            s.circ(*P(x, z), h["r"] * sc, .35 if (st or hl) else .2, INK if (st or hl) else FAINT, "#fff")
    return P


def stl_outline(path, keep=lambda poly: True):
    """Outline of a printed part seen along its z axis: union of the projected triangles (shapely)."""
    import trimesh
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    m = trimesh.load(path)
    tris = [Polygon(t[:, :2]) for t in m.triangles if abs(m.face_normals[0][2]) >= 0]
    u = unary_union([t.buffer(0.01) for t in tris if t.area > 1e-6]).buffer(-0.01)
    return u


def draw_shape(s, geom, T, sw=.4, c=INK, fill="#fff"):
    """shapely (Multi)Polygon through T(x, y) -> page, holes kept."""
    polys = getattr(geom, "geoms", [geom])
    for g in polys:
        d = ""
        for ring in [g.exterior, *g.interiors]:
            pts = [T(x, y) for x, y in ring.coords]
            d += "M" + " L".join(f"{F(a)} {F(b)}" for a, b in pts) + " Z "
        s.path(d, sw, c, fill)


_CACHE = {}
NAMES = {r.split("\t")[0]: r.split("\t")[1] for f in ("bom.tsv", "prints.tsv") if (HERE / f).exists()
         for r in (HERE / f).read_text().strip().splitlines()[1:]}


def part_outline(rel):
    if rel not in _CACHE:
        p = OUTDIR / rel
        _CACHE[rel] = stl_outline(p) if p.exists() else None
    return _CACHE[rel]


# ============================================================================
# shared icons / numbers
# ============================================================================
CSK6 = (i_csk(6), 2.0)
M3_10 = (i_pan(10), 1.6)
NYLOC3 = (i_nut(5.5, 2.4, True), 2.0)
WASH3 = (i_washer(7, .6), 2.0)
RIVNUT3 = (i_rivnut(), 1.6)
RIVET = (i_rivet(), 1.6)


def P_(icon_scale, qty, pid, spec=None):
    (icon, sc) = icon_scale
    return (icon, sc, qty, pid, spec)


S0, S1, S2, S3, S4 = ("Stage 0 · Before you start", "Stage 1 · Power box", "Stage 2 · Control box",
                      "Stage 3 · Close up", "Stage 4 · Power-on")


# ============================================================================
# pages: front matter
# ============================================================================
def p_cover():
    s = Svg()
    sc = .42
    ox = (PW - E.W * sc) / 2
    oy_p = 186
    wall(s, "power", "front", ox, oy_p, sc, True, all_ink=True)
    hp = (E.H["power"] + E.T) * sc
    wall(s, "control", "front", ox, oy_p - hp - 2.5, sc, True, all_ink=True)
    gx = part_outline("gx_plates/gx_plate_steppers.stl")
    for g in ("steppers", "servo", "endstops"):
        o = part_outline(f"gx_plates/gx_plate_{g}.stl")
        if o is not None:
            draw_shape(s, o, lambda x, y, oy=oy_p - hp - 2.5: (ox + (x + E.W / 2) * sc, oy - y * sc), .35, INK, "rgba(0,0,0,.06)")
        for u, v in E.GX_GROUPS[g]:
            s.circ(ox + (u + E.W / 2) * sc, oy_p - hp - 2.5 - v * sc, 8 * sc, .35)
    del gx
    s.text(10, 40, "Etch", 26, weight=800)
    s.text(10, 52, "Build book · pen plotter enclosure", 5, c=MID)
    s.text(10, 62, "One complete A3 artwork. Built once, in the case.", 3.4)
    s.text(PW - 10, 40, "Power box below · control box on top", 2.8, "end", c=MID)
    s.text(PW - 10, 45, "450 × 295 inside · 1.2 mm 304 stainless", 2.8, "end", c=MID)
    return f'<svg class="page" id="cover" viewBox="0 0 {PW} {PH}" xmlns="http://www.w3.org/2000/svg" font-family="Helvetica, Arial, sans-serif">{s.out()}</svg>'


def p_legend():
    s = Svg()
    y = 60
    items = [
        ("parts", "Parts box: what this step uses, how many, and its BOM or Prints ID (Bxx, Pxx)."),
        ("ink", "Black lines: what you work on in this step. Grey lines: the rest of the face, for orientation."),
        ("red", "Red: where to put it."),
        ("front", "FRONT arrow: which way the box's front faces in the drawing."),
        ("sub", "a, b: sub-steps, in order."),
        ("check", "Check: do not start the next page until this passes."),
        ("warn", "⚠ unverified: a guess or an unmeasured number. Measure first."),
        ("gate", "🚫 gate: a decision is needed before this step."),
    ]
    for key, t in items:
        x = 30
        if key == "parts":
            s.rect(x - 8, y - 6, 16, 9, .4, r=1.5)
            s.text(x, y + 1, "4x", 3.2, "middle", 700)
        elif key == "ink":
            s.line(x - 8, y - 2.5, x + 8, y - 2.5, .45)
            s.line(x - 8, y + 1, x + 8, y + 1, .3, FAINT)
        elif key == "red":
            s.circ(x, y - 1, 2.6, .4, fill=ACC)
        elif key == "front":
            front_arrow(s, x + 7, y, True)
        elif key == "sub":
            sub(s, x, y - 1, "a")
        elif key == "check":
            ok_box(s, x - 3, y - 4, "")
        s.text(48, y, t, 3.4)
        y += 13
    steps = ["Build top to bottom, once, inside the case.",
             "Before each session, read the next two pages and buy or print anything missing (BOM and Prints at the back).",
             "The Etch Build Book doc is the master: if a page and the doc disagree, the doc wins and this page gets redrawn."]
    return page("How to read", "", [], s.out(), steps, stage="")


def p_rules():
    s = Svg()
    rules = [("Unplugged means unplugged.", "The IEC lead is out of the wall and in sight before a hand goes into the power box."),
             ("Ferrule every stranded wire under a screw.", "Never tin a wire with solder under a screw: it creeps and loosens."),
             ("Brown = live, blue = neutral, green/yellow = earth.", "Never use green/yellow for anything else."),
             ("Earth first, earth last.", "Fitted first, removed last, and longer than L and N so it pulls tight last."),
             ("DC 0 V never touches earth.", "G1 and G2 stay off the box metal; the laptop's USB already earths 0 V."),
             ("Shroud every mains terminal", "before the first power-on."),
             ("Never plug or unplug a motor with 24 V on.", "A TB6600 whose motor is pulled live often dies.")]
    y = 112
    for i, (a, b) in enumerate(rules):
        s.circ(17, y - 1.2, 4, .5, ACC if i < 6 else INK, "#fff")
        s.text(17, y + .1, str(i + 1), 3.6, "middle", 700)
        s.text(26, y, a, 3.8, weight=700)
        s.text(26, y + 5, b, 3.2, c="#444")
        y += 12.5
    tools = [(i_meter(), 1.6, 1, "B60", "multimeter, beep + 0.01 V"), (i_label("rivnut tool", 26, 9), 1.0, 1, "B61", "rivnut tool, M3 + M4"),
             (i_label("ferrule crimper", 30, 9), 1.0, 1, "B62", "ferrule crimper 0.25–6 mm²"), (i_label("ring crimper", 26, 9), 1.0, 1, "B63", "crimper, insulated rings"),
             (i_label("labels", 16, 9), 1.0, 1, "B64", "wire labels")]
    steps = ["Lay out the tools in the parts box before starting.",
             "Label every wire at both ends as you cut it.",
             "Also on the bench: stripper, screwdrivers, 2.5 / 3 mm hex keys, 5.5 / 7 / 10 mm spanners, iron with a heat-set tip."]
    return page("0.1", "Tools and mains rules", tools, s.out(), steps, stage=S0)


# ============================================================================
# stage 0: rivnuts and rivets
# ============================================================================
def lid_lip_points():
    """Lid fixing rivnuts on the body lips: top view (x, z) for the 3 top lips, back view (x, v) for the 3 back lips."""
    top = [h["uv"] for h in PARTS["control_lid"].holes if h["face"] == "top" and "clears rivnut" in h["note"]]
    back = [h["uv"] for h in PARTS["control_lid"].holes if h["face"] == "back" and "clears rivnut" in h["note"]]
    return top, back


def rivnut_section(s, cx, cy, k=3.0):
    """Rivnut set in the sheet, section, with the tool pulling."""
    s.rect(cx - 16, cy, 11, 1.2 * k, .4, INK, "#ddd")
    s.rect(cx + 5, cy, 11, 1.2 * k, .4, INK, "#ddd")
    s.rect(cx - 4 * k / 2 - 1.5, cy - 1 * k, 4 * k + 3, 1 * k, .4, INK, "#fff")      # flange on the outside face
    s.poly([(cx - 2.5 * k / 2, cy), (cx + 2.5 * k / 2, cy), (cx + 3.2 * k / 2, cy + 3 * k), (cx - 3.2 * k / 2, cy + 3 * k)], .4, INK, "#fff")
    s.rect(cx - 2.2 * k / 2, cy + 3 * k, 2.2 * k, 3 * k, .4, INK, "#fff")
    s.text(cx + 18, cy + 2.5, "steel", 2.3, c=MID)
    s.text(cx + 10, cy - 4, "flange outside", 2.3, c=MID)
    s.text(cx + 10, cy + 3 * k + 2, "bulge inside", 2.3, c=MID)


def p_rivnuts(kind):
    s = Svg()
    sc = .27
    hi = ("rivnut",)
    # front, left, right faces (outside) in a row, lips below
    W, D, Hh = E.W, E.D, E.H[kind] + E.T
    y0 = 128 if kind == "control" else 140
    hi = ("rivnut (5mm)",)
    wall(s, kind, "front", 10, y0, sc, True, hi)
    caption(s, 10, y0 + 5, "front, outside")
    wall(s, kind, "left", 10 + W * sc + 6, y0, sc * .9, True, hi)
    caption(s, 10 + W * sc + 6, y0 + 5, "left, outside")
    if kind == "power":
        wall(s, kind, "right", 10 + W * sc + D * sc * .9 + 12, y0, sc * .9, True, hi)
        caption(s, 10 + W * sc + D * sc * .9 + 12, y0 + 5, "right: banana panel uses screws, no rivnuts")
    for face, ox, scf in (("front", 10, sc), ("left", 10 + W * sc + 6, sc * .9)):
        sg = SGN[(face, True)]
        for h in holes(kind, face):
            if "rivnut" in h["note"] and "accessory" not in h["note"] and "uv" in h:
                u, v = h["uv"]
                s.circ(ox + (sg * u + face_w(face) / 2) * scf, y0 - v * scf, 1.3, .3, INK, ACC)
    # lips: top view + back view
    top, back = lid_lip_points()
    tx, ty, ts = 22, 166, .12
    s.rect(tx, ty - D * ts / 2, W * ts, D * ts, .45, fill="#fff")
    for x, z in top:
        s.circ(tx + (x + W / 2) * ts, ty + z * ts, 1.3, .3, INK, ACC)
    caption(s, tx, ty + D * ts / 2 + 4.5, "top lips, from above")
    s.text(tx + W * ts / 2, ty + D * ts / 2 - 1, "FRONT", 1.9, "middle", c=MID)
    bx = tx + W * ts + 14
    s.rect(bx, ty - Hh * ts / 2 - 4, W * ts, Hh * ts, .45, fill="#fff")
    for x, v in back:
        s.circ(bx + (-x + W / 2) * ts, ty - Hh * ts / 2 - 4 + (Hh - v) * ts, 1.3, .3, INK, ACC)
    caption(s, bx, ty + D * ts / 2 + 4.5, "back lips, from behind")
    rivnut_section(s, 236, 166)
    n_face = sum(1 for f in ("front", "left") for h in holes(kind, f) if "rivnut" in h["note"] and "accessory" not in h["note"])
    n = n_face + len(top) + len(back)
    steps = [f"Set {n} M3 rivnuts in the {kind} box: {n_face} in the walls (red) and 6 in the lips for the lid.",
             "Flange on the outside, bulge on the inside. Squeeze the tool until it stops; don't over-pull.",
             "Leave the Ø5 accessory holes empty for now." if kind == "power" else "The 4 lid-top accessory holes stay empty for now."]
    return page(f"0.2{'a' if kind == 'control' else 'b'}", f"Rivnuts · {kind} box", [P_(RIVNUT3, n, "B29", "M3 rivnut, Ø5 hole, flange Ø8")], s.out(), steps,
                ["Total both boxes: 39. Buy 50."], "Each takes an M3 screw by hand and doesn't spin", S0)


def p_rivets():
    s = Svg()
    sc = .3
    wall(s, "power", "front", 10, 120, sc, True, ("rivet",))
    caption(s, 10, 125, "front corners, outside (both boxes)")
    for h in holes("power", "front"):
        pass
    # rivet positions are on the corner tabs: show by callout at the two front corners
    for side in (-1, 1):
        x = 10 + (side * (E.W / 2 - 6) + E.W / 2) * sc
        for v in (40, 130)[:2]:
            s.circ(x, 120 - v * sc, 1.4, .3, INK, ACC)
    # section: tab behind the front wall, rivet through both
    cx, cy = 230, 110
    k = 3
    s.rect(cx - 20, cy - 2 * k, 40, 1.2 * k, .4, INK, "#ddd")
    s.text(cx + 22, cy - 2 * k + 2.5, "front wall", 2.3, c=MID)
    s.rect(cx - 20, cy - 2 * k + 1.2 * k + .6, 40, 1.2 * k, .4, INK, "#eee")
    s.text(cx + 22, cy + 1.5, "side tab", 2.3, c=MID)
    s.path(f"M{cx - 2.8 * k / 2} {cy - 2 * k} Q{cx - 2.8 * k / 2} {cy - 2 * k - 1.6 * k} {cx} {cy - 2 * k - 1.6 * k} "
           f"Q{cx + 2.8 * k / 2} {cy - 2 * k - 1.6 * k} {cx + 2.8 * k / 2} {cy - 2 * k} Z", .4, INK, "#fff")
    s.rect(cx - 3.2 * k / 2, cy - 2 * k, 3.2 * k, 3 * k + .6, .4, INK, "#fff")
    s.path(f"M{cx - 3.2 * k / 2} {cy + k + .6} Q{cx - 4.5 * k / 2} {cy + k + 3} {cx} {cy + k + 3.2} Q{cx + 4.5 * k / 2} {cy + k + 3} {cx + 3.2 * k / 2} {cy + k + .6} Z", .4, INK, "#fff")
    s.text(cx, cy + k + 9, "peened over inside", 2.3, "middle", c=MID)
    s.text(cx, cy - 2 * k - 1.6 * k - 3, "dome head outside, on a dolly", 2.3, "middle", c=MID)
    steps = ["8 solid Ø3.2 rivets: 2 per front corner tab, 2 tabs per box, 2 boxes.",
             "Squeeze the tab against the front wall with a clamp first; the gap closes by the rivet, not the hammer.",
             "Dome head outside on a dolly. Peen the tail over from inside with light blows."]
    return page("0.3", "Corner rivets", [P_(RIVET, 8, "B30", "solid rivet Ø3.2, dome head")], s.out(), steps,
                ["Rivet positions drawn approximately: use the holes in the steel."], "Tab tight against the wall, no rocking", S0)


# ============================================================================
# stage 1: power box
# ============================================================================
def p_earth_stud():
    s = Svg()
    sc = .5
    ox, oy = 12, 190
    P = wall(s, "power", "left", ox, oy, sc, outside=False, hi=("earth stud",))
    caption(s, ox, oy + 5, "Power box, left wall, from inside")
    front_arrow(s, ox + 20, oy - (E.H["power"] + E.T) * sc - 5, left=True)
    stud = next(h for h in holes("power", "left") if "earth" in h["note"])
    x, y = P(*stud["uv"])
    s.circ(x, y, 3.25 * sc + .4, .5, fill=ACC)
    cx, cy, cr = 238, 138, 44
    callout(s, x, y, 5, cx, cy, cr)
    k = 1.7
    wx = cx - 32
    s.rect(wx, cy - 28, 1.2 * k, 56, .4, INK, "#ddd")
    s.text(wx - 2, cy - 31, "outside", 2.4, "end", c=MID)
    s.text(wx + 4, cy - 31, "inside", 2.4, c=MID)
    s.rect(wx - 4 * k, cy - 5 * k, 4 * k, 10 * k, .35, INK, "#fff")
    s.rect(wx + 1.2 * k, cy - 3 * k, 36, 6 * k, .35, INK, "#fff")
    seq = [("washer", 1.2, 6.5), ("nut", 5, 5), ("ring", 1, 6), ("nut", 5, 5), ("ring", 1, 6), ("nut", 5, 5)]
    xx = wx + 1.2 * k + 3
    for i, (what, t, hh) in enumerate(seq):
        xx += 3.2
        if what == "ring":
            s.rect(xx, cy - hh * k, t * k, 2 * hh * k, .35, INK, WIRE["PE"])
            wire(s, [(xx + t * k / 2, cy - hh * k), (xx + t * k / 2, cy - hh * k - 9)], "PE", 1)
            s.text(xx + 1, cy - hh * k - 11, "IEC earth" if i == 2 else "PSU earths", 2.3, "middle", c=WIRE["PE"])
        else:
            s.rect(xx, cy - hh * k, t * k, 2 * hh * k, .35, INK, "#fff")
        xx += t * k
    parts = [(i_hex(30), .8, 1, "B09", "M6 × 30 hex bolt, A2"), (i_washer(12, 1.4, True), 1.0, 2, "B09", "M6 serrated washer"), (i_nut(10, 5), 1.0, 3, "B09", "M6 nut"),
             (i_ring(6.4, WIRE["PE"]), 1.0, 3, "B10", "M6 ring, 0.5–1.5 mm²")]
    steps = ["M6 bolt through the Ø6.5 hole low on the left wall, head outside.",
             "Inside: serrated washer, nut. Tighten hard: this is the bond to the box.",
             "The IEC earth ring goes on next with its own nut (1.5). PSU earth rings go above it under a third nut."]
    return page("1.1", "Earth stud", parts, s.out(), steps, ["⚠ scrape any film off under the serrated washer"],
                "Beep: stud ↔ bare steel anywhere on the body", S1)


def standoff_stack(s, cx, cy, k=2.4):
    s.text(cx, cy - 58, "each of 6", 2.6, "middle", c=MID)
    s.rect(cx - 16, cy, 32, 1.2 * k, .4, INK, "#ddd")
    s.text(cx + 17, cy + 3, "floor", 2.3, c=MID)
    s.rect(cx - 3.5 * k / 2, cy - 5 * k, 3.5 * k, 5 * k, .4, INK, "#fff")
    s.text(cx + 6, cy - 5 * k / 2 + 1, "a", 3, weight=700)
    py = cy - 5 * k - 2 * k - 8
    s.rect(cx - 16, py, 32, 2 * k, .4, INK, "#f6f6f4")
    s.text(cx + 17, py + 3.5, "plate", 2.3, c=MID)
    s.text(cx - 19, py + 3.5, "b", 3, "end", 700)
    svg, w, h = i_pan(8, 4, 7, 2.8)
    m = k / 1.6
    yb = cy + 1.2 * k + 7
    s.g(cx - w * m / 2, yb + h * m, m, svg, -m)
    s.arrow(cx, yb + 1, cx, cy + 1.2 * k + 1)
    yt = py - 8 - h * m
    s.g(cx - w * m / 2, yt, m, svg)
    s.arrow(cx, yt + h * m + .5, cx, py - 1)


def p_base_plate(kind, num, stage):
    s = Svg()
    sc = .22
    for i, (ox, with_plate) in enumerate(((68, False), (178, True))):
        oy = 140
        P = floor(s, kind, ox, oy, sc, hi=("standoff",), plate=with_plate)
        sub(s, ox - E.W / 2 * sc, oy - E.D / 2 * sc - 7, "ab"[i])
        s.text(ox, oy + E.D / 2 * sc + 4.5, "FRONT", 2.3, "middle", c=MID)
        if not with_plate:
            for h in holes(kind, "base"):
                if "standoff" in h["note"]:
                    s.circ(*P(*h["uv"]), 2.4, .5, fill=ACC)
    caption(s, 68 - E.W / 2 * sc, 140 + E.D / 2 * sc + 10, f"{kind.capitalize()} box floor, from above")
    standoff_stack(s, 262, 140)
    parts = [(i_standoff(5, 7), 1.6, 6, "B26", "M4 standoff 5 mm F–F"), (i_pan(8, 4, 7, 2.8), 1.3, 12, "B27", "M4 × 8 pan ⚠"), (i_label("plate", 18, 10, "#f6f6f4"), 1, 1, "B25", "base plate 440 × 285")]
    steps = ["a  Six M4 standoffs onto the floor, screwed from underneath.",
             "b  Plate on top, six more screws." + (" Set the PSU-bracket M4 rivnuts first (1.3)." if kind == "power" else
                                                    " Prepare the rail fixings first (2.2): easier with the plate on the bench.")]
    return page(num, f"Base plate · {kind} box", parts, s.out(), steps,
                ["Plates: 2 mm mild steel, already cut", "Standoffs stay 5 mm: 6 mm or more hits the window rivnut and PSU panel screws"],
                "Plate doesn't rock · no screw head below the feet", stage)


PSU24 = (-165.0, -50.0, -107.5, 107.5)          # assembly_check placeholders (x0, x1, z0, z1), lying flat, 30 tall
PSU12 = (-40.0, 75.0, -107.5, 107.5)


def p_psus():
    s = Svg()
    sc = .3
    cx, cy = 95, 150
    P = floor(s, "power", cx, cy, sc, plate=True)
    s.text(cx, cy + E.D / 2 * sc + 4.5, "FRONT", 2.3, "middle", c=MID)
    for (x0, x1, z0, z1), name, sub_ in ((PSU24, "24 V", "LRS-350-24"), (PSU12, "12 V", "model ⚠")):
        a, b = P(x0, z0), P(x1, z1)
        box(s, a[0], a[1], b[0] - a[0], b[1] - a[1], name, sub_, "rgba(255,255,255,.85)", size=3.4)
        s.rect(a[0] + 1, a[1] + 1, b[0] - a[0] - 2, 5, .3, INK, "#ddd")         # terminal strip at the back
    bx0, bz0 = P(95, -60)
    box(s, bx0, bz0, 50 * sc, 26 * sc, "buck", "", "#fff", size=2.4)
    # keep-out behind the IEC panel (stop button, module)
    ip = PANELS["power"]["iec"]
    k0, k1 = P(-E.W / 2, -ip["u"] - 45), P(-E.W / 2 + 52, -ip["u"] + 45)
    s.rect(k0[0], k0[1], k1[0] - k0[0], k1[1] - k0[1], .3, ACC, "rgba(221,51,51,.08)", "1.2 .8")
    s.text(k0[0] + 1, k1[1] + 3, "keep clear: stop button + IEC", 2.1, c=ACC)
    s.text(P(-E.W / 2, 0)[0] - 2, P(0, 0)[1], "IEC wall", 2.3, "end", c=MID, rot=-90)
    # bracket detail
    dx, dy = 248, 120
    box(s, dx - 22, dy - 6, 44, 12, "PSU", "", "#fff")
    for sgn in (-1, 1):
        s.poly([(dx + sgn * 22, dy + 6), (dx + sgn * 30, dy + 6), (dx + sgn * 30, dy + 9), (dx + sgn * 20, dy + 9)], .4, INK, "#eee")
        s.circ(dx + sgn * 26, dy + 7.5, .9, .3)
    s.rect(dx - 34, dy + 9, 68, 2, .4, INK, "#f6f6f4")
    caption(s, dx - 34, dy + 16, "printed bracket (P03) each side, M4 into a plate rivnut")
    parts = [(i_label("24 V PSU", 26, 10), 1, 1, "B13", "LRS-350-24"), (i_label("12 V PSU", 26, 10), 1, 1, "B14", "12 V PSU ⚠ model"), (i_label("buck", 14, 8), 1, 1, "B15", "buck 12 → 6 V"),
             (i_label("bracket", 20, 8, "#eee"), 1, "2 sets", "P03", "PSU bracket"), (i_rivnut(6, 11, 9, 1.2), 1.3, 8, "B28", "M4 rivnut, Ø6 hole"), (i_pan(8, 4, 7, 2.8), 1.1, 8, "B31", "M4 × 8 ⚠ datasheet")]
    steps = ["Read both PSU labels. Write the 12 V model and its rated current in the doc (Open questions 2).",
             "Read the buck's chip: LM2596 (2–3 A) or XL4015 (5 A).",
             "Stand the PSUs on the plate as drawn, terminal strips facing back. Mark the bracket holes on the grid, set M4 rivnuts, bolt down.",
             "Keep the red zone clear: the stop button reaches about 51 mm in behind the IEC panel."]
    return page("1.3", "PSUs and buck", parts, s.out(), steps,
                ["⚠ positions are the model's placeholders · P03 not modelled yet", "⚠ PSU screw depth: check the datasheet"],
                "IEC module, stop button and fan clear the PSUs", S1)


def p_iec_panel():
    s = Svg()
    sc = .5
    ox, oy = 12, 190
    P = wall(s, "power", "left", ox, oy, sc, outside=True, hi=("IEC",))
    caption(s, ox, oy + 5, "Power box, left wall, from outside")
    front_arrow(s, ox + E.D * sc - 22, oy - (E.H["power"] + E.T) * sc - 5, left=False)
    pan = PANELS["power"]["iec"]
    pw, ph = pan["plate"]
    px, py = 238, 128
    s.rect(px - pw / 2 * sc, py - ph / 2 * sc, pw * sc, ph * sc, .5, fill="#fff", r=5 * sc)
    # placeholder layout of the contents: module, 2 LEDs, stop
    s.rect(px - 50 * sc, py - 15 * sc, 50 * sc, 30 * sc, .35, INK, "#fff", r=1)
    s.rect(px - 44 * sc, py - 8 * sc, 22 * sc, 16 * sc, .3)
    s.circ(px + 14 * sc, py - 14 * sc, 6 * sc, .35, INK, "#fff")
    s.circ(px + 14 * sc, py + 14 * sc, 6 * sc, .35, INK, "#fff")
    s.circ(px + 14 * sc, py - 14 * sc, 3 * sc, .2, INK, WIRE["PE"])
    s.circ(px + 14 * sc, py + 14 * sc, 3 * sc, .2, INK, WIRE["PE"])
    s.circ(px + 50 * sc, py, 14.8 * sc, .35, INK, ACC)
    for h in holes("power", "left"):
        if "IEC" in h["note"] and h["kind"] == "circle":
            u, v = h["uv"]
            q = (px + (u - pan["u"]) * sc, py - (v - pan["v"]) * sc)
            s.circ(*q, 3.2 * sc, .4)
            s.circ(*q, 1.7 * sc, .3)
    cx, cy = P(pan["u"], pan["v"])
    s.arrow(px - pw / 2 * sc - 3, py, cx + 70 * sc, cy)
    caption(s, px - pw / 2 * sc, py + ph / 2 * sc + 5, "P01 · layout of the parts on it ⚠ not final")
    iec = ("<rect width='20' height='12' rx='1' fill='#fff' stroke='#111' stroke-width='.3'/>"
           "<rect x='3' y='3' width='9' height='6' fill='none' stroke='#111' stroke-width='.3'/><rect x='14' y='3' width='4' height='6' fill='#d33' stroke='#111' stroke-width='.3'/>", 20, 12)
    parts = [P_(CSK6, 4, "B42", "M3 × 6 countersunk"), (iec, 1, 1, "B01", "IEC C14 3-in-1"), (i_round(5, "#fff"), 1.6, "1+2", "B02", "fuse 5×20 T3.15 A"),
             (i_round(12, "#fff", 6, WIRE["PE"]), 1, 2, "B04", "LED 12 mm, 12–24 V"), (i_round(16, ACC), 1, 1, "B03", "stop LA38-11ZS Ø22"), (i_label("C + D", 16, 9, "#eee"), 1, 1, "P02", "fit coupons C + D")]
    steps = ["Print the fit coupons C and D first (P02). Pick the IEC frame that snaps in firmly; note the LED and stop hole sizes.",
             "Measure the module's tabs (4.8 or 6.3 mm) and the stop button's AC rating before buying spades.",
             "Into the panel: IEC module (snaps into the 1.5 mm thin zone), 2 LEDs, stop button. Fuse T3.15 A in the drawer.",
             "Panel onto the wall, lip into the opening, 4 countersunk M3 into the rivnuts."]
    return page("1.4", "IEC panel", parts, s.out(), steps, ["⚠ P01 not modelled yet: drawn from the steel and the parts list"],
                "Lip seats · heads flush · stop latches and twists out", S1)


def mains_diagram(s, y0=78, earth=True, live=True):
    """Power-box mains schematic: IEC → stop NC → Wago → two PSUs; earth via the stud."""
    # IEC module
    box(s, 14, y0, 34, 46, "IEC", "inlet · fuse · DP switch")
    l_ = term(s, 48, y0 + 12, "L", "r")
    n_ = term(s, 48, y0 + 24, "N", "r")
    e_ = term(s, 48, y0 + 38, "⏚", "r")
    # stop button
    box(s, 70, y0 - 2, 24, 18, "STOP", "NC", "#fff")
    st_in = term(s, 70, y0 + 12, "", "l")
    st_out = term(s, 94, y0 + 12, "", "r")
    # wagos
    box(s, 112, y0 + 4, 18, 14, "Wago", "L")
    box(s, 112, y0 + 22, 18, 14, "Wago", "N")
    # PSUs
    box(s, 196, y0 - 8, 56, 32, "24 V PSU", "LRS-350-24")
    box(s, 196, y0 + 40, 56, 32, "12 V PSU", "")
    p24 = {k: term(s, 196, y0 - 8 + 8 + i * 8, k, "l") for i, k in enumerate(("L", "N", "FG"))}
    p12 = {k: term(s, 196, y0 + 40 + 8 + i * 8, k, "l") for i, k in enumerate(("L", "N", "FG"))}
    # stud
    sx, sy = 95, y0 + 92
    s.circ(sx, sy, 3.5, .4, INK, "#fff")
    s.circ(sx, sy, 1.4, .3, INK, INK)
    s.text(sx, sy + 8, "earth stud (1.1)", 2.4, "middle", c=MID)
    if live:
        wire(s, [l_, st_in], "L")
        wire(s, [st_out, (112, y0 + 12)], "L")
        wire(s, [(130, y0 + 9), (160, y0 + 9), (160, p24["L"][1]), p24["L"]], "L")
        wire(s, [(130, y0 + 13), (165, y0 + 13), (165, p12["L"][1]), p12["L"]], "L")
        wire(s, [n_, (60, y0 + 24), (60, y0 + 30), (112, y0 + 30)], "N")
        wire(s, [(130, y0 + 27), (172, y0 + 27), (172, p24["N"][1]), p24["N"]], "N")
        wire(s, [(130, y0 + 31), (177, y0 + 31), (177, p12["N"][1]), p12["N"]], "N")
    if earth:
        wire(s, [e_, (56, y0 + 38), (56, sy), (sx - 3.5, sy)], "PE", .9, "1st ring", 1)
        wire(s, [(sx + 3.5, sy - 1), (184, sy - 1), (184, p24["FG"][1]), p24["FG"]], "PE", .9)
        wire(s, [(sx + 3.5, sy + 1), (188, sy + 1), (188, p12["FG"][1]), p12["FG"]], "PE", .9)
    for k, c in (("L", "brown = L"), ("N", "blue = N"), ("PE", "green/yellow = earth")):
        pass


def p_mains(part):
    s = Svg()
    if part == "a":
        mains_diagram(s, earth=True, live=False)
        steps = ["Unplugged. Earth first: IEC earth tab → the stud, on the first ring, own nut.",
                 "Stud → FG of the 24 V PSU, and stud → FG of the 12 V PSU: one wire each, on the second ring stack.",
                 "Leave each earth wire a little longer than L and N will be, so it pulls tight last."]
        parts = [(i_spade(WIRE["PE"]), 1.2, 1, "B07", "spade ⚠ 4.8 / 6.3"), (i_ring(6.4, WIRE["PE"]), 1.1, 3, "B10", "M6 ring, 0.5–1.5 mm²"), (i_ferrule(WIRE["PE"]), 1.4, 2, "B08", "ferrule 1.0 mm²"),
                 (i_label("G/Y 1.0 mm²", 26, 7, "#e9f4e9"), 1, "1 m", "B05", "H05V-K 1.0 mm² G/Y")]
        return page("1.5a", "Mains wiring · earth", parts, s.out(), steps, [], "Beep: IEC earth pin ↔ stud ↔ both PSU cases ↔ body", S1)
    mains_diagram(s, earth=True, live=True)
    steps = ["Live: IEC switched L → stop button NC → Wago L → L of each PSU.",
             "Neutral: IEC switched N → Wago N → N of each PSU.",
             "Ferrules on every end under a screw; spades on the IEC tabs. Shroud the IEC tabs and both PSU input strips.",
             "Tie the mains bundle to the left half of the plate, away from where DC will run."]
    parts = [(i_spade(WIRE["L"]), 1.2, 4, "B07", "spade ⚠ 4.8 / 6.3"), (i_wago(), 1, 2, "B06", "Wago 221-413"), (i_ferrule(WIRE["L"]), 1.4, 8, "B08", "ferrule 1.0 mm²"),
             (i_label("brown + blue 1.0 mm²", 36, 7, "#f3ece4"), 1, "1 m ea", "B05", "H05V-K 1.0 mm²"), (i_label("shrouds", 18, 7), 1, 1, "B11", "terminal shrouds")]
    return page("1.5b", "Mains wiring · live and neutral", parts, s.out(), steps,
                ["⚠ the stop button breaks L only: the IEC rocker is the double-pole switch"],
                "No beep L↔earth or N↔earth, rocker on and off", S1)


def p_first_power():
    s = Svg()
    box(s, 30, 80, 60, 34, "24 V PSU", "LED on")
    box(s, 30, 128, 60, 34, "12 V PSU", "LED on")
    for y, v, c in ((97, "24.0 V", WIRE["P24"]), (145, "12.x V", WIRE["P12"])):
        term(s, 90, y - 4, "+V", "r", c)
        term(s, 90, y + 4, "−V", "r")
        s.g(118, y - 13, 1.4, i_meter()[0])
        s.line(90, y - 4, 118, y - 6, .6, c)
        s.line(90, y + 4, 118, y + 4, .6, INK)
        s.text(140, y + 1, v, 4.2, weight=700)
    s.circ(220, 120, 16, .6, INK, ACC)
    s.text(220, 145, "press: both dark", 2.8, "middle")
    s.text(220, 150, "twist: both back", 2.8, "middle")
    steps = ["Nothing on the DC side. Lid off, hands clear. Plug in, rocker on.",
             "Rocker lights; both PSU LEDs on. Meter 24 V and 12 V at the outputs. Trim the 24 V to 24.0 V.",
             "Press the stop: both go dark. Twist to release: both back.",
             "Rocker off, unplug. Wait for the PSU LEDs to fade before touching anything."]
    return page("1.6", "First mains power-on", [(i_meter(), 1.6, 1, "B60", "multimeter")], s.out(), steps, [],
                "24.0 V and 12 V present · stop cuts both", S1)


def p_dc(part):
    s = Svg()
    if part == "a":
        box(s, 14, 88, 40, 44, "12 V PSU", "")
        pp = term(s, 54, 96, "+V", "r", WIRE["P12"])
        pn = term(s, 54, 106, "−V", "r")
        lp = term(s, 54, 116, "+V", "r", WIRE["P12"])
        ln = term(s, 54, 126, "−V", "r")
        box(s, 84, 78, 34, 30, "splitter +12", "1 in / 3 out")
        box(s, 84, 116, 34, 30, "splitter G2", "1 in / 3 out")
        wire(s, [pp, (84, 96)], "P12", .8)
        wire(s, [pn, (70, 106), (70, 137), (84, 137)], "G", .8)
        outs_p = [(118, 84), (118, 93), (118, 102)]
        outs_g = [(118, 122), (118, 131), (118, 140)]
        box(s, 168, 76, 34, 16, "buck", "12 → 6 V")
        box(s, 168, 100, 34, 14, "fan", "80 mm 12 V")
        box(s, 228, 76, 44, 16, "12 V toggle", "PSU panel")
        box(s, 228, 128, 44, 14, "G2 jack", "PSU panel")
        box(s, 168, 150, 34, 14, "12 V LED", "IEC panel")
        wire(s, [outs_p[0], (140, 84), (140, 82), (168, 82)], "P12", .7)
        wire(s, [outs_p[1], (146, 93), (146, 104), (168, 104)], "P12", .7)
        wire(s, [outs_p[2], (152, 102), (152, 70), (220, 70), (220, 84), (228, 84)], "P12", .7)
        wire(s, [outs_g[0], (158, 122), (158, 88), (168, 88)], "G", .6)
        wire(s, [outs_g[1], (162, 131), (162, 110), (168, 110)], "G", .6)
        wire(s, [outs_g[2], (215, 140), (215, 135), (228, 135)], "G", .6)
        wire(s, [lp, (62, 116), (62, 154), (168, 154)], "P12", .5)
        wire(s, [ln, (66, 126), (66, 160), (168, 160)], "G", .5)
        s.text(56, 172, "LED from the PSU's spare +V / −V screws ⚠ check it has two pairs", 2.4, c=MID)
        s.text(185, 97, "set 6.0 V first", 2.2, "middle", c=ACC)
        steps = ["12 V PSU +V → splitter +12 → buck IN+, fan +, the 12 V toggle.",
                 "12 V PSU −V → splitter G2 → buck IN−, fan −, the G2 jack. One 0 V wire to the buck: its IN− and OUT− are the same copper.",
                 "12 V LED straight off the PSU's second +V / −V pair.",
                 "Meter on the buck's output, nothing connected: set 6.0 V."]
        parts = [(i_label("PCT 2×6", 20, 9), 1, 1, "B16", "PCT 2×6 splitter"), (i_label("0.75 mm²", 20, 7, "#fde8cc"), 1, "3 m ea", "B18", "0.75 mm² silicone"),
                 (i_ferrule(WIRE["P12"]), 1.4, 12, "B08", "ferrule 0.75 mm²")]
        return page("1.7a", "DC · 12 V and 6 V", parts, s.out(), steps, ["⚠ wire size: confirm against the 12 V PSU's label"],
                    "Buck reads 6.0 V unloaded", S1)
    box(s, 14, 76, 50, 34, "24 V PSU", "LRS-350-24")
    p_, n_ = term(s, 64, 86, "+V", "r", WIRE["P24"]), term(s, 64, 100, "−V", "r")
    box(s, 140, 62, 46, 20, "PSU panel", "24 V toggle")
    box(s, 140, 116, 46, 16, "G1 jack", "PSU panel")
    box(s, 140, 90, 46, 16, "24 V LED", "IEC panel")
    wire(s, [p_, (110, 86), (110, 70), (140, 70)], "P24", 1.2, "1.5 mm²", 1)
    l2 = term(s, 64, 93, "+V", "r", WIRE["P24"])
    wire(s, [l2, (120, 93), (120, 96), (140, 96)], "P24", .6)
    wire(s, [n_, (100, 100), (100, 124), (140, 124)], "G", 1.2, "1.5 mm²", 1)
    l3 = term(s, 64, 107, "−V", "r")
    wire(s, [l3, (92, 107), (92, 114), (126, 114), (126, 101), (140, 101)], "G", .6)
    s.rect(206, 70, 70, 46, .4, ACC, "rgba(221,51,51,.05)", "1.2 .8", r=2)
    s.text(241, 82, "G1 and G2", 3.4, "middle", 700, ACC)
    s.text(241, 89, "are NOT joined", 3.4, "middle", 700, ACC)
    s.text(241, 96, "in this box", 3.4, "middle", 700, ACC)
    s.text(241, 106, "star point: Open questions 4", 2.4, "middle", c=MID)
    steps = ["24 V PSU +V → the 24 V toggle. −V → the G1 jack.",
             "24 V LED off the PSU's second +V / −V pair.",
             "1.5 mm² throughout on 24 V and G1: 16 AWG is too thin."]
    parts = [(i_label("1.5 mm² red + black", 34, 7, "#f9dede"), 1, "3 m ea", "B17", "1.5 mm² (not 16 AWG)"), (i_ferrule(WIRE["P24"]), 1.4, 6, "B08", "ferrule 1.5 mm²")]
    return page("1.7b", "DC · 24 V", parts, s.out(), steps, [], "Unplugged: G1↔G2 open · G1, G2 ↔ stud open", S1)


def fan_page(kind, num, stage):
    s = Svg()
    sc = .5
    ox, oy = 12, 190 if kind == "power" else 178
    P = wall(s, kind, "left", ox, oy, sc, outside=True, hi=("fan",))
    caption(s, ox, oy + 5, f"{kind.capitalize()} box, left wall, from outside")
    front_arrow(s, ox + E.D * sc - 22, oy - (E.H[kind] + E.T) * sc - 5, left=False)
    fz, fy = E.FAN[kind]
    for h in holes(kind, "left"):
        if "fan screw" in h["note"]:
            s.circ(*P(*h["uv"]), 1.5, .4, fill=ACC)
    # stack
    cx, cy = 236, 132
    k = 1.6
    s.rect(cx - 30, cy - 30, 1.2 * k, 60, .4, INK, "#ddd")
    s.text(cx - 32, cy - 33, "outside", 2.3, "end", c=MID)
    s.rect(cx - 30 + 1.2 * k + 2, cy - 30, 25 * k * .6, 60, .4, INK, "#fff")
    s.text(cx - 30 + 1.2 * k + 2 + 7.5, cy + 2, "fan", 2.8, "middle", 700)
    for yy in (-22, 22):
        s.rect(cx - 30 - 3.2, cy + yy - 3.5, 3.2, 7, .35, INK, "#fff")
        s.rect(cx - 30, cy + yy - 2, 22 + 1.2 * k + 6, 4, .35, INK, "#fff")
        s.rect(cx - 30 + 1.2 * k + 2 + 25 * k * .6 + .5, cy + yy - 3.5, .8, 7, .3, INK, "#fff")
        s.rect(cx - 30 + 1.2 * k + 2 + 25 * k * .6 + 1.5, cy + yy - 3, 3, 6, .35, INK, "#eee")
    parts = [(i_fan(), 1.2, 1, "B20", "fan 80 × 80 × 25, 12 V"), (i_pan(35, 4, 7, 2.8), .8, 4, "B21", "M4 × 35 pan"), (i_washer(9, .8), 1.6, 4, "B21", "M4 washer"), (i_nut(7, 3.2, True), 1.6, 4, "B21", "M4 nyloc")]
    steps = ["Fan inside, against the grille. Airflow direction: see Open questions 6 (arrow on the fan's side).",
             "M4 × 35 from outside, washer and nyloc inside. Snug, don't crush the fan frame.",
             "Lead: + to 12 V, − to G2 (" + ("1.7a)." if kind == "power" else "2.8).")]
    return page(num, f"Fan · {kind} box", parts, s.out(), steps, [], "Blades turn freely by hand", stage)


def panel_page(kind, key, num, title, stage, steps, notes, check, parts, screws=True):
    """Banana panel (printed, have) on the right wall, through Ø3.4 steel holes."""
    s = Svg()
    sc = .5
    ox, oy = 12, 190 if kind == "power" else 178
    P = wall(s, kind, "right", ox, oy, sc, outside=True, hi=("panel",))
    caption(s, ox, oy + 5, f"{kind.capitalize()} box, right wall, from outside")
    front_arrow(s, ox + 22, oy - (E.H[kind] + E.T) * sc - 5, left=True)
    pan = PANELS[kind][key]
    pw, ph = pan["plate"]
    px, py = 236, 128
    s.rect(px - pw / 2 * sc, py - ph / 2 * sc, pw * sc, ph * sc, .5, fill="#fff", r=4 * sc)
    rows = 3 if key == "psu" else 1
    labels = [["24 V", "G1"], ["12 V", "G2"], ["6 V", ""]] if key == "psu" else [["24 V", "G1", "12 V", "6 V", "G2"]]
    for r in range(rows):
        yy = py + (r - (rows - 1) / 2) * 38 * sc
        n = len(labels[r])
        for i, lab in enumerate(labels[r]):
            if not lab:
                continue
            xx = px + (i - (n - 1) / 2) * (24 if key != "psu" else 40) * sc
            col = {"24 V": WIRE["P24"], "12 V": WIRE["P12"], "6 V": WIRE["P6"]}.get(lab, INK)
            s.circ(xx, yy, 7.2 * sc, .4, INK, col)
            s.text(xx, yy + 7.2 * sc + 3, lab, 2.2, "middle")
        if key == "psu":
            s.rect(px + 30 * sc, yy - 6 * sc, 22 * sc, 11 * sc, .35, INK, "#222")
            s.circ(px + 66 * sc, yy, 6 * sc, .35, INK, "#fff")
    for u, v in ((pan["u"] - pan["screw"][0], pan["v"] - pan["screw"][1] + pan["screw"][1] * 0),):
        pass
    for h in holes(kind, "right"):
        if "panel screw" in h["note"]:
            u, v = h["uv"]
            s.circ(px + -(u - pan["u"]) * sc, py - (v - pan["v"]) * sc, 1.7 * sc + .3, .4)
    cx, cy = P(pan["u"], pan["v"])
    s.arrow(px - pw / 2 * sc - 3, py, cx + pan["cut"][0] / 2 * sc + 2, cy)
    caption(s, px - pw / 2 * sc, py + ph / 2 * sc + 6, "jack layout drawn schematically: follow the printed panel")
    return page(num, title, parts, s.out(), steps, notes, check, stage)


def p_psu_panel(part):
    if part == "a":
        s = Svg()
        rails = [("24 V", "P24", "PSU 24 V +V"), ("12 V", "P12", "splitter +12"), ("6 V", "P6", "buck OUT+")]
        for i, (name, w, src) in enumerate(rails):
            y = 76 + i * 34
            box(s, 14, y, 40, 16, src, "")
            box(s, 84, y - 2, 30, 20, "toggle", name)
            box(s, 146, y - 6, 34, 12, "voltmeter", "red after toggle")
            s.circ(220, y + 8, 6, .5, INK, WIRE[w])
            s.text(220, y + 20, f"{name} jack", 2.4, "middle")
            wire(s, [(54, y + 8), (84, y + 8)], w, 1.1 if w == "P24" else .8)
            wire(s, [(114, y + 8), (214, y + 8)], w, 1.1 if w == "P24" else .8)
            wire(s, [(130, y + 8), (130, y), (146, y)], w, .5)
            g = "G1" if w == "P24" else "G2"
            wire(s, [(180, y), (240, y), (240, y + 14)], "G", .5)
            s.text(243, y + 15, f"{g} (black lead)", 2.2, c=MID)
        steps = ["Each rail: source → toggle → jack.",
                 "Voltmeter red lead after the toggle (it doubles as the rail-on light); black lead to that rail's own ground.",
                 "Rings on the jack studs: blue (1.5–2.5) for 24 V and G1, red (0.5–1.5) for 12 V, 6 V, G2."]
        parts = [(i_ring(4, "#2b62c4"), 1.1, 10, "B19", "M4 ring, blue 1.5–2.5"), (i_ring(4, "#d33"), 1.1, 20, "B19", "M4 ring, red 0.5–1.5")]
        return page("1.9a", "PSU panel · wiring", parts, s.out(), steps, [], "", S1)
    steps = ["Wire the panel on the bench first (1.9a), leaving 15 cm of slack into the box.",
             "Panel onto the right wall: M3 × 10 from outside through the Ø3.4 holes, washer and nyloc inside."]
    parts = [P_(M3_10, 4, "B23", "M3 × 10 pan"), P_(WASH3, 4, "B23", "M3 washer"), P_(NYLOC3, 4, "B23", "M3 nyloc"), (i_label("PSU panel", 22, 9, "#eee"), 1, "have", "P05", "PSU panel")]
    return panel_page("power", "psu", "1.9b", "PSU panel · mount", S1, steps, [],
                      "Powered: each toggle shows its volts · stop: all dark", parts)


# ============================================================================
# stage 2: control box
# ============================================================================
RAIL_A = dict(x0=-171.5, x1=31.7, z=-2.5, fix=[(-140.0, -2.5), (-20.0, -2.5)])
RAIL_B = dict(x=131.0, z0=-135.0, z1=68.2, fix=[(131.0, -117.0), (131.0, 47.0)])


def p_rails():
    s = Svg()
    sc = .36
    cx, cy = 105, 135
    fix = RAIL_A["fix"]
    P = floor(s, "control", cx, cy, sc, plate=True, plate_hi=lambda x, z: any(abs(x - a) < 1 and abs(z - b) < 1 for a, b in fix))
    s.text(cx, cy + E.D / 2 * sc + 4.5, "FRONT", 2.3, "middle", c=MID)
    a0, a1 = P(RAIL_A["x0"], RAIL_A["z"] - 17.5), P(RAIL_A["x1"], RAIL_A["z"] + 17.5)
    s.rect(a0[0], a0[1], a1[0] - a0[0], a1[1] - a0[1], .4, INK, "rgba(170,180,187,.55)")
    s.text((a0[0] + a1[0]) / 2, a0[1] - 1.5, "rail A", 2.6, "middle", 700)
    b0, b1 = P(RAIL_B["x"] - 17.5, RAIL_B["z0"]), P(RAIL_B["x"] + 17.5, RAIL_B["z1"])
    s.rect(b0[0], b0[1], b1[0] - b0[0], b1[1] - b0[1], .4, INK, "rgba(170,180,187,.55)")
    s.text(b1[0] + 1.5, (b0[1] + b1[1]) / 2, "rail B", 2.6, weight=700)
    for x, z in fix:
        s.circ(*P(x, z), 1.6, .4, fill=ACC)
    for x, z in RAIL_B["fix"]:
        s.circ(*P(x, z), 1.6, .4, ACC, "#fff")
        s.line(P(x, z)[0] - 1.6, P(x, z)[1], P(x, z)[0] + 1.6, P(x, z)[1], .3, ACC)
        s.line(P(x, z)[0], P(x, z)[1] - 1.6, P(x, z)[0], P(x, z)[1] + 1.6, .3, ACC)
    s.circ(232, 96, 1.6, .4, fill=ACC)
    s.text(236, 97, "M4 rivnut in a grid hole", 2.4)
    s.circ(232, 103, 1.6, .4, ACC, "#fff")
    s.line(230.4, 103, 233.6, 103, .3, ACC)
    s.line(232, 101.4, 232, 104.6, .3, ACC)
    s.text(236, 104, "drill Ø4.5, M4 + nyloc", 2.4)
    parts = [(i_rail(40), 1, 2, "B34", "TS35 rail, 8 in"), (i_rivnut(6, 11, 9, 1.2), 1.2, 2, "B28", "M4 rivnut, Ø6 hole"), (i_pan(10, 4, 7, 2.8), 1.1, 4, "B40", "M4 × 10 pan"),
             (i_nut(7, 3.2, True), 1.6, 2, "B40", "M4 nyloc")]
    steps = ["Rail A (drivers): along the box on grid row z −2.5. M4 rivnuts in the grid holes at x −140 and −20.",
             "Rail B (board): front to back at x 131. Drill Ø4.5 at z −117 and +47; M4 bolt, nyloc under the plate.",
             "Lay each rail on the plate and mark through its slots before setting or drilling anything."]
    return page("2.2", "DIN rails", parts, s.out(), steps, ["⚠ rail slots must land on these holes: mark first",
                                                            "Moves rail A 12.5 mm forward of the layout check: still 51 mm clear of the GX zone"],
                "Both rails flat; don't move when pushed", S2)


def p_plate(which):
    s = Svg()
    rel = "din_mounts/tb6600_plate.stl" if which == "tb" else "din_mounts/board_plate.stl"
    o = part_outline(rel)
    sc = 1.0 if which == "tb" else .85
    cx, cy = 92, 135
    if o is not None:
        (x0, y0, x1, y1) = o.bounds
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        draw_shape(s, o, lambda x, y: (cx + (x - mx) * sc, cy - (y - my) * sc), .45, INK, "#f4f4f2")
    caption(s, cx - 50, 196, "printed plate, from above (traced from its STL)")
    # exploded side view: clip under, plate, part on top
    ex = 228
    s.g(ex - 25, 168, 2, i_clip()[0])
    s.text(ex + 28, 176, "DIN clip", 2.4, c=MID)
    s.arrow(ex, 162, ex, 152)
    s.rect(ex - 30, 140, 60, 8, .45, INK, "#f4f4f2")
    s.text(ex + 32, 145, "plate", 2.4, c=MID)
    for dx in (-20, 20):
        s.g(ex + dx - 2.15, 141, 1, i_insert()[0])
    if which == "tb":
        box(s, ex - 28, 108, 56, 18, "TB6600", "")
        s.arrow(ex, 128, ex, 138)
        parts = [(i_label("TB6600", 20, 9), 1, 3, "B32", "TB6600 driver"), (i_clip(), 1, 3, "B35", "DIN clip 25 × 69"), (i_insert(), 2, 6, "B37", "M3 × 4 insert, OD 4.3"), (i_csk(8), 1.6, 6, "B36", "M3 × 8 flat head ⚠"),
                 (i_pan(10), 1.4, 6, "B39", "M3 × 10 pan"), (i_nut(5.5, 2.4), 1.6, 6, "B39", "M3 nut")]
        steps = ["Print 3 TB6600 plates at the corrected 89 mm hole pitch (P07).",
                 "Melt the M3 inserts into the clip bosses. Clip under each plate, countersink on the rail side, M3 flat heads.",
                 "Driver onto its plate: M3 × 10 + nut through both flanges."]
        return page("2.3a", "Driver plates", parts, s.out(), steps, [], "Each plate snaps onto a rail offcut and releases", S2)
    box(s, ex - 28, 112, 56, 14, "FluidNC board", "")
    s.arrow(ex, 128, ex, 138)
    parts = [(i_label("board", 16, 9), 1, 1, "B33", "FluidNC board"), (i_clip(), 1, 2, "B35", "DIN clip 25 × 69"), (i_insert(), 2, 8, "B37", "M3 × 4 insert, OD 4.3"), (i_csk(8), 1.6, 4, "B36", "M3 × 8 flat head ⚠"),
             (i_pan(6), 1.6, 4, "B38", "M3 × 6 pan")]
    steps = ["Print the board plate with the rotated clips (P08).",
             "Inserts into the clip bosses and the 4 board bosses. Clips under, M3 flat heads.",
             "Board on with 4 × M3 × 6: USB to the back, driver signals left, I/O right, power to the front."]
    return page("2.3b", "Board plate", parts, s.out(), steps, ["⚠ board hole spacing 78 × 118: best-effort measurement"],
                "PCB sits flat, nothing touches underneath", S2)


def p_layout():
    s = Svg()
    sc = .4
    cx, cy = 115, 128
    P = floor(s, "control", cx, cy, sc, plate=True)
    s.text(cx, cy + E.D / 2 * sc + 4.5, "FRONT · GX sockets", 2.3, "middle", c=MID)
    sp = (LC.XW - LC.REACH) - max(g.bounds[2] for g in LC.parts().values())
    lay = LC.parts(sp / 2)
    dz = RAIL_A["z"] - LC.RAIL_Z
    a0, a1 = P(RAIL_A["x0"], RAIL_A["z"] - 17.5), P(RAIL_A["x1"], RAIL_A["z"] + 17.5)
    s.rect(a0[0], a0[1], a1[0] - a0[0], a1[1] - a0[1], .3, MID, "rgba(170,180,187,.4)")
    b0, b1 = P(RAIL_B["x"] - 17.5, RAIL_B["z0"]), P(RAIL_B["x"] + 17.5, RAIL_B["z1"])
    s.rect(b0[0], b0[1], b1[0] - b0[0], b1[1] - b0[1], .3, MID, "rgba(170,180,187,.4)")
    for n, g in lay.items():
        if n.startswith("_"):
            continue
        x0, z0, x1, z1 = g.bounds
        if n.startswith("TB"):
            z0, z1 = z0 + dz, z1 + dz
        q0, q1 = P(x0, z0), P(x1, z1)
        box(s, q0[0], q0[1], q1[0] - q0[0], q1[1] - q0[1], n if n != "board" else "board", "", "rgba(255,255,255,.9)", size=3)
        if n.startswith("TB"):
            t0 = P(x1 - 12, z0 + 10)
            s.rect(t0[0], t0[1], 12 * sc, (z1 - z0 - 20) * sc, .3, INK, "#cfe8d6")
    for k, g in LC.keepouts().items():
        x0, z0, x1, z1 = g.bounds
        q0, q1 = P(x0, z0), P(x1, z1)
        s.rect(q0[0], q0[1], q1[0] - q0[0], q1[1] - q0[1], .25, ACC, "rgba(221,51,51,.06)", "1 .8")
    s.text(P(-E.W / 2, 0)[0] - 2, P(0, 0)[1], "USB + fan wall", 2.2, "end", c=MID, rot=-90)
    s.text(P(E.W / 2, 0)[0] + 4, P(0, 0)[1], "banana panel wall", 2.2, "middle", c=MID, rot=90)
    steps = ["Snap the three TB6600 plates onto rail A, 89 mm apart: about 7.5 mm spare at each end.",
             "Board plate onto rail B.",
             "Red dashed: keep-outs for the fan, panels and GX plugs. Nothing goes in them."]
    return page("2.4", "Plates onto the rails", [], s.out(), steps,
                ["⚠ the model warns: driver TB1 sits 1.5 mm from the GX sockets; nudge right if tight"],
                "About 51 mm clear above the drivers to the lid", S2)


def gx_plate_draw(s, g, ox, oy, sc, explode=0.0):
    o = part_outline(f"gx_plates/gx_plate_{g}.stl")
    if o is not None:
        draw_shape(s, o, lambda x, y: (ox + (x + E.W / 2) * sc, oy - y * sc - explode), .45, INK, "#f4f4f2")
    for u, v in E.GX_GROUPS[g]:
        s.circ(ox + (u + E.W / 2) * sc, oy - v * sc - explode, 8 * sc, .4, INK, "#fff")
        s.circ(ox + (u + E.W / 2) * sc, oy - v * sc - explode, 5.6 * sc, .3)


def p_gx(part):
    s = Svg()
    if part == "a":
        sc = .9
        x = 16
        for g in ("steppers", "servo", "endstops"):
            rect, riv = E.gx_openings()[g]
            o = part_outline(f"gx_plates/gx_plate_{g}.stl")
            x0, y0, x1, y1 = o.bounds if o is not None else (rect[0] - 12, rect[1] - 12, rect[2] + 12, rect[3] + 12)
            ox = x - (x0 + E.W / 2) * sc
            gx_plate_draw(s, g, ox, 170 + y0 * sc, sc)
            pins = {"steppers": "GX16-5", "servo": "GX16-4", "endstops": "GX16-3"}[g]
            caption(s, x, 182, f"{g} · {pins} × {len(E.GX_GROUPS[g])}")
            x += (x1 - x0) * sc + 14
        steps = ["Print the three GX plates (P09).",
                 "Sockets into the plates from the front, nut behind, tight. The nut seat stops them turning.",
                 "Solder the socket tails now, on the bench (pin schedule 2.9b). Then the plates go on."]
        parts = [(i_gx(5), 1, 3, "B41", "GX16-5 socket"), (i_gx(4), 1, 1, "B41", "GX16-4 socket"), (i_gx(3), 1, 2, "B41", "GX16-3 socket"), (i_label("GX plates", 22, 9, "#eee"), 1, 3, "P09", "GX plates")]
        return page("2.5a", "GX sockets into the plates", parts, s.out(), steps,
                    ["Different pin counts on purpose: nothing mates the wrong socket"], "Each plug mates and locks", S2)
    sc = .52
    ox, oy = 26, 188
    wall(s, "control", "front", ox, oy, sc, True, hi=("GX",))
    caption(s, ox, oy + 5, "Control box front, from outside")
    for g in ("steppers", "servo", "endstops"):
        gx_plate_draw(s, g, ox, oy, sc, explode=0)
        for u, v in E.gx_openings()[g][1]:
            s.circ(ox + (u + E.W / 2) * sc, oy - v * sc, 1.1, .3, INK, ACC)
    steps = ["Feed the tails in through the openings first.",
             "Plate on, lip into the opening, countersunk M3 × 6 into the rivnuts (red): 3 + 2 + 2."]
    return page("2.5b", "GX plates onto the front", [P_(CSK6, 7, "B42", "M3 × 6 countersunk")], s.out(), steps, [],
                "Backshells tighten without fouling each other", S2)


def p_receiving():
    steps = ["Rings on the 5 posts first (2.8), then the panel on.",
             "M3 × 10 from outside through the Ø3.4 holes, washer and nyloc inside."]
    parts = [P_(M3_10, 4, "B23", "M3 × 10 pan"), P_(WASH3, 4, "B23", "M3 washer"), P_(NYLOC3, 4, "B23", "M3 nyloc"), (i_label("receiving", 24, 9, "#eee"), 1, "have", "P06", "receiving panel")]
    return panel_page("control", "receiving", "2.6", "Receiving panel", S2, steps,
                      ["⚠ post order drawn as 24 V, G1, 12 V, 6 V, G2: follow your printed panel's labels"], "Posts don't spin", parts)


def p_usb():
    s = Svg()
    sc = .55
    ox, oy = 12, 178
    P = wall(s, "control", "left", ox, oy, sc, True, hi=("USB",))
    caption(s, ox, oy + 5, "Control box, left wall, from outside")
    front_arrow(s, ox + E.D * sc - 22, oy - (E.H["control"] + E.T) * sc - 5, left=False)
    pan = PANELS["control"]["usb_ant"]
    pw, ph = pan["plate"]
    px, py = 236, 120
    s.rect(px - pw / 2 * sc, py - ph / 2 * sc, pw * sc, ph * sc, .5, INK, "#fff", "1.4 .8", r=4 * sc)
    s.rect(px - 20 * sc, py - 5 * sc, 12 * sc, 7 * sc, .35, INK, "#fff", r=1)
    s.circ(px + 18 * sc, py, 3.25 * sc + .4, .35)
    s.text(px, py + ph / 2 * sc + 5, "P10 · not modelled", 2.4, "middle", c=MID)
    for h in holes("control", "left"):
        if "USB" in h["note"] and h["kind"] == "circle":
            s.circ(*P(*h["uv"]), 1.2, .3, INK, ACC)
    cx, cy = P(pan["u"], pan["v"])
    s.arrow(px - pw / 2 * sc - 3, py, cx + 42 * sc, cy)
    steps = ["Decide the USB-C pass-through (B43) and whether the pendant socket goes in now (recommended: later).",
             "Short USB lead from the panel to the board, along the board's back edge.",
             "Panel on: countersunk M3 × 6 into the 4 rivnuts."]
    return page("2.7", "USB / antenna panel", [(i_label("USB-C", 16, 8), 1, 1, "B43", "USB-C pass-through 🚫"), P_(CSK6, 4, "B42", "M3 × 6 countersunk"), (i_label("panel", 16, 9, "#eee"), 1, 1, "P10", "USB panel")],
                s.out(), steps, ["🚫 gate: USB-C part (B43) · pendant now or later"], "Laptop sees the board over the panel", S2)


def p_power_wiring(part):
    s = Svg()
    if part == "a":
        box(s, 12, 60, 30, 82, "receiving", "panel")
        posts = {k: term(s, 42, 70 + i * 16, k, "r", WIRE.get({"24 V": "P24", "12 V": "P12", "6 V": "P6"}.get(k, "G")))
                 for i, k in enumerate(("24 V", "G1", "12 V", "6 V", "G2"))}
        for i in range(3):
            box(s, 100 + i * 46, 60, 38, 26, f"TB{i + 1}", "VCC · GND")
            wire(s, [posts["24 V"], (70 + i * 3, 70), (70 + i * 3, 54), (119 + i * 46 - 4, 54), (119 + i * 46 - 4, 60)], "P24", 1)
            wire(s, [posts["G1"], (80 + i * 3, 86), (80 + i * 3, 96), (119 + i * 46 + 4, 96), (119 + i * 46 + 4, 86)], "G", 1)
        box(s, 100, 110, 60, 26, "board", "VIN · GND")
        wire(s, [(70, 70), (66, 70), (66, 120), (100, 120)], "P24", 1)
        wire(s, [(80, 86), (76, 86), (76, 128), (100, 128)], "G", 1)
        box(s, 200, 106, 40, 18, "fan", "control box")
        wire(s, [posts["12 V"], (90, 102), (90, 104), (196, 104), (196, 112), (200, 112)], "P12", .7)
        wire(s, [posts["G2"], (94, 134), (94, 146), (196, 146), (196, 119), (200, 119)], "G", .6)
        steps = ["24 V post → VCC of each TB6600 and the board's VIN, 1.5 mm². G1 post → each GND. One wire per terminal; no daisy chains.",
                 "12 V post → control fan +, G2 → fan −.",
                 "Before powering: read the board's 5 V regulator. A linear 7805 will cook on 24 V."]
        parts = [(i_label("1.5 mm²", 18, 7, "#f9dede"), 1, "", "B17", "1.5 mm² red + black"), (i_ring(4, "#2b62c4"), 1.1, 2, "B19", "M4 ring, blue 1.5–2.5"), (i_ferrule(), 1.4, 10, "B08", "ferrule 1.5 mm²")]
        return page("2.8a", "Power wiring · duct 1", parts, s.out(), steps, ["⚠ board regulator unverified (Open questions 11)"],
                    "24 V ↔ G1 not a short · G1 ↔ body open", S2)
    box(s, 12, 76, 30, 50, "receiving", "panel")
    p6, g2 = term(s, 42, 90, "6 V", "r", WIRE["P6"]), term(s, 42, 108, "G2", "r")
    s.g(150, 76, 3, i_gx(4)[0])
    s.text(174, 130, "servo socket, from behind", 2.4, "middle", c=MID)
    pin = lambda i: (174 + 3.4 * 3 * math.cos(2 * math.pi * i / 4 - math.pi / 2), 100 + 3.4 * 3 * math.sin(2 * math.pi * i / 4 - math.pi / 2))  # noqa: E731
    for i in range(4):
        s.text(pin(i)[0] + 3, pin(i)[1] - 2, str(i + 1), 2.6, weight=700)
    wire(s, [p6, (120, 90), (120, pin(0)[1]), pin(0)], "P6", .8, "pin 1 · 6 V", 1)
    wire(s, [g2, (130, 108), (130, pin(1)[1] + 6), (pin(1)[0], pin(1)[1] + 6), pin(1)], "G", .8)
    s.text(196, pin(1)[1], "pin 2 · G2", 2.4)
    s.text(196, pin(2)[1] + 6, "pin 3 · PWM from board (2.9a)", 2.4)
    s.text(196, pin(3)[1] - 6, "pin 4 · spare", 2.4, c=MID)
    s.rect(40, 150, 210, 18, .4, ACC, "rgba(221,51,51,.05)", "1.2 .8", r=2)
    s.text(46, 158, "Star point (Open questions 4): proposal is one short link G2 post → G1 post on this panel.", 2.8, c=ACC)
    s.text(46, 163, "Needs your OK before it goes in.", 2.8, c=ACC)
    steps = ["6 V post → servo socket pin 1. G2 post → pin 2.",
             "The board's PWM goes to pin 3 (2.9a). Pin 4 spare.",
             "Fit the 2200 µF at the servo end, not here (B49)."]
    return page("2.8b", "Power wiring · servo supply", [(i_ring(4, "#d33"), 1.1, 2, "B19", "M4 ring, red 0.5–1.5")], s.out(), steps,
                [], "6 V post ↔ pin 1 beeps · pin 1 ↔ pin 2 open", S2)


def p_signals(part):
    s = Svg()
    if part == "a":
        box(s, 14, 60, 50, 110, "FluidNC", "board")
        sig = ["X1 step", "X1 dir", "X2 step", "X2 dir", "Y step", "Y dir", "enable", "PWM (servo)", "X endstop", "Y endstop"]
        for i, n in enumerate(sig):
            y = 68 + i * 10
            term(s, 64, y, n, "r", WIRE["SIG"])
        for i in range(3):
            box(s, 160, 60 + i * 30, 48, 24, f"TB{i + 1}", "PUL · DIR · ENA")
            for j in range(2):
                wire(s, [(64, 68 + (i * 2 + j) * 10), (100 + i * 6 + j * 2, 68 + (i * 2 + j) * 10), (100 + i * 6 + j * 2, 66 + i * 30 + j * 6), (160, 66 + i * 30 + j * 6)], "SIG", .5)
            wire(s, [(64, 128), (130 + i * 3, 128), (130 + i * 3, 78 + i * 30), (160, 78 + i * 30)], "SIG", .4)
        s.text(160, 160, "PWM → servo socket pin 3", 2.6)
        s.text(160, 166, "endstops → GX16-3 sockets (2.9b)", 2.6)
        wire(s, [(64, 138), (150, 138), (150, 158), (158, 158)], "SIG", .5)
        steps = ["Step, dir and enable from the board's external-driver header to each TB6600.",
                 "Follow the board's pinout for PUL+ vs PUL− (common anode or cathode). Check each driver's silkscreen: clones reorder terminals.",
                 "0.25–0.5 mm², labelled both ends. Bend with the jig sleeves (P11); guides (P15) along duct 2."]
        parts = [(i_label("signal wire", 24, 7, "#dcecf4"), 1, "set", "B45", "0.25–0.5 mm²"), (i_round(16, "#fff", 4), 1, "4/4/2", "P11", "sleeves Ø16/24/40"), (i_ferrule("#ccc"), 1.4, 20, "B08", "ferrule 0.25–0.5 bare")]
        return page("2.9a", "Signals · board to drivers", parts, s.out(), steps,
                    ["⚠ board output type and TB6600 terminal order unverified (Open questions 12)"], "", S2)
    for i, (name, pins, rows) in enumerate((("GX16-5 · steppers", 5, ["A+", "A−", "B+", "B−", "screen → G1"]),
                                             ("GX16-4 · servo", 4, ["6 V", "G2", "PWM", "spare"]),
                                             ("GX16-3 · endstops", 3, ["signal", "return", "screen (box end)"]))):
        cx, cy = 50 + i * 85, 112
        s.circ(cx, cy, 22, .5, INK, "#fff")
        s.circ(cx, cy, 16, .3)
        for j in range(pins):
            a = 2 * math.pi * j / pins - math.pi / 2
            px, py = cx + 10 * math.cos(a), cy + 10 * math.sin(a)
            s.circ(px, py, 2, .3, INK, "#fff")
            s.text(px, py + 1.1, str(j + 1), 2.6, "middle", 700)
        s.rect(cx - 2, cy - 23, 4, 3, .3, INK, "#111")
        s.text(cx, cy + 30, name, 3, "middle", 700)
        for j, r in enumerate(rows):
            s.text(cx - 20, cy + 37 + j * 4.4, f"{j + 1}  {r}", 2.8)
    s.text(12, 82, "Seen from the solder side (behind the plate) ⚠ check the numbers moulded on your sockets", 2.6, c=MID)
    steps = ["Motors: A+ A− B+ B− on pins 1–4; the cable screen on pin 5 → G1. Never earth a screen through the shell.",
             "Find coil pairs with the meter: continuity = same coil. Don't trust Ender colours.",
             "Endstops: screen at the box end only."]
    return page("2.9b", "Signals · socket pins", [(i_gx(5), 1, 3, "B41", "GX16-5 plug"), (i_label("4-core screened", 30, 7), 1, "10 m", "B46", "4-core screened"),
                                                   (i_label("2-pair screened", 30, 7), 1, "4 m", "B47", "2-pair screened")], s.out(), steps, [],
                "Continuity table ticked: every pin to its terminal", S2)


def p_dip():
    s = Svg()
    for i in range(3):
        x = 22 + i * 88
        box(s, x, 70, 70, 50, f"TB{i + 1}", "")
        s.rect(x + 12, 100, 46, 12, .4, INK, "#e33")
        for j in range(6):
            s.rect(x + 14 + j * 7.2, 102, 5, 8, .3, INK, "#fff")
            s.rect(x + 14 + j * 7.2, 102 if j < 3 else 106, 5, 4, .3, INK, "#111")
            s.text(x + 16.5 + j * 7.2, 117, f"{j + 1}", 2.2, "middle")
        s.text(x + 35, 130, "SW1–3: microstep · SW4–6: current", 2.2, "middle", c=MID)
    steps = ["Current: the Ender 42-34 is about 0.84 A per phase. Use the nearest setting not above it; check whether the driver's table is peak or RMS.",
             "Microstep: the same on all three, and it must match steps/mm in the FluidNC config.",
             "Write the setting on each driver with a marker."]
    return page("2.11", "Driver switches", [], s.out(), steps, ["⚠ switch positions drawn are an example, not the setting"],
                "Same on all three · written on each", S2)


# ============================================================================
# stage 3
# ============================================================================
def p_windows():
    s = Svg()
    sc = .3
    yp, yc = 182, 106
    wall(s, "control", "front", 10, yc, sc, True, hi=("window",))
    wall(s, "power", "front", 10, yp, sc, True, hi=("window",))
    caption(s, 10, yc + 4.5, "control front, outside")
    caption(s, 10, yp + 4.5, "power front, outside")
    for kind, oy, slots in (("control", yc, ["control"]), ("power", yp, ["power_left", "power_right"])):
        for sl in slots:
            o = part_outline(f"window_meccano/meccano_{sl}.stl")
            if o is not None:
                draw_shape(s, o, lambda x, y, oy=oy: (10 + (x + E.W / 2) * sc, oy - y * sc), .35, INK, "rgba(240,240,236,.9)")
    o = part_outline("window_meccano/window_meccano.stl")
    if o is not None:
        (x0, y0, x1, y1) = o.bounds
        draw_shape(s, o, lambda x, y: (232 + (x - (x0 + x1) / 2) * .55, 130 - (y - (y0 + y1) / 2) * .55), .4, INK, "#f4f4f2")
        caption(s, 232 - (x1 - x0) * .275, 130 + (y1 - y0) * .275 + 5, "172 × 79, 12.7 mm Meccano pitch")
    steps = ["Print three Meccano window panels (P12): one per window slot file.",
             "Lip into the opening, 4 countersunk M3 × 6 into the rivnuts."]
    return page("3.1", "Window panels", [P_(CSK6, 12, "B42", "M3 × 6 countersunk"), (i_label("Meccano", 22, 9, "#eee"), 1, 3, "P12", "Meccano panel 172 × 79")], s.out(), steps, [],
                "Panels flat, heads flush", S3)


def p_lids():
    s = Svg()
    ts = .3
    lw, ld = 456.8, 300.8
    cx, cy = 85, 128
    s.rect(cx - lw / 2 * ts, cy - ld / 2 * ts, lw * ts, ld * ts, .5, fill="#fff")
    for h in PARTS["control_lid"].holes:
        if h["face"] == "top" and "uv" in h:
            x, z = h["uv"]
            strong = "clears rivnut" in h["note"]
            s.circ(cx + x * ts, cy + z * ts, h["r"] * ts + (.6 if strong else 0), .4 if strong else .25, INK if strong else FAINT, ACC if strong else "none")
    s.text(cx, cy + ld / 2 * ts + 4.5, "FRONT", 2.3, "middle", c=MID)
    caption(s, cx - lw / 2 * ts, cy + ld / 2 * ts + 10, "lid top, from above")
    ts = .25
    bx, by_, bh = 162, 150, (E.H["control"] + 2.4)
    s.rect(bx, by_ - bh * ts, lw * ts, bh * ts, .5, fill="#fff")
    for h in PARTS["control_lid"].holes:
        if h["face"] == "back" and "clears rivnut" in h["note"]:
            x, v = h["uv"]
            s.circ(bx + (-x + lw / 2) * ts, by_ - v * ts, h["r"] * ts + .6, .4, INK, ACC)
    caption(s, bx, by_ + 5, "lid back, from behind")
    # screw stack
    sx, sy = 236, 70
    s.g(sx - 2.85 * 1.6, sy, 1.6, i_button(8)[0])
    s.rect(sx - 8, sy + 16, 16, 1.6, .35, INK, "#eee")
    s.text(sx + 10, sy + 17.5, "printed washer", 2.2, c=MID)
    s.rect(sx - 14, sy + 18.4, 9, 2, .35, INK, "#ddd")
    s.rect(sx + 5, sy + 18.4, 9, 2, .35, INK, "#ddd")
    s.text(sx + 16, sy + 20.5, "lid (Ø10)", 2.2, c=MID)
    s.text(sx - 26, sy + 5, "", 2)
    steps = ["Power lid first. Ease the snug fit before forcing it (Open questions 13).",
             "6 screws per lid: 3 on top, 3 at the back. Button head M3 over a printed washer; the Ø10 holes clear the rivnut flanges.",
             "Same for the control lid."]
    return page("3.2", "Lids", [(i_button(8), 1.6, 12, "B51", "M3 × 8 button ⚠"), (i_round(15, "#eee", 3.4), .9, 14, "P13", "washer Ø15")], s.out(), steps,
                ["⚠ screw length · P13 not modelled yet"], "Lid seats without bowing the walls · no wire pinched", S3)


def p_stack():
    s = Svg()
    sc = .27
    ox, oy = 12, 186
    hp = (E.H["power"] + E.T) * sc
    wall(s, "power", "front", ox, oy, sc, True)
    wall(s, "control", "front", ox, oy - hp - 10, sc, True)
    for x, _ in E.FEET_XZ[::2]:
        fx = ox + (x + E.W / 2) * sc
        s.rect(fx - 3.6, oy - hp - 10 + .2, 7.2, 1.8, .35, INK, "#eee")
        s.rect(fx - 1.1, oy - hp - 8.2, 2.2, 3, .35, INK, "#eee")
        s.arrow(fx, oy - hp - 4, fx, oy - hp - .8)
    caption(s, ox, oy + 4.5, "front view: control box onto the power lid")
    # peg holes on power lid
    ts = .22
    cx, cy = 232, 110
    s.rect(cx - 456.8 / 2 * ts, cy - 300.8 / 2 * ts, 456.8 * ts, 300.8 * ts, .5, fill="#fff")
    for (x, z), how in E.PEG_HOLES.items():
        px, py = cx + x * ts, cy + z * ts
        if how == "slot":
            s.rect(px - 5.5 * ts * 2, py - 4 * ts * 2, 11 * ts * 2, 8 * ts * 2, .4, INK, ACC, r=1)
        else:
            s.circ(px, py, (4 if how == "round" else 5) * ts * 2, .4, INK, ACC if how == "round" else "#fff")
    s.text(cx, cy + 300.8 / 2 * ts + 4, "FRONT", 2.2, "middle", c=MID)
    caption(s, cx - 456.8 / 2 * ts, cy + 300.8 / 2 * ts + 9, "power lid top: hole, slot, 2 clearance")
    parts = [(i_label("foot", 14, 7, "#eee"), 1, 4, "P14", "foot Ø24 × 6 + peg"), (i_lead(WIRE["P24"]), 1, 5, "B53", "4 mm banana lead")]
    steps = ["Push the 4 printed feet into the control box's base holes.",
             "Lower the control box onto the power lid: the front-left peg finds the round hole, the front-right the slot.",
             "Banana leads, post to post, colour-matched: 24 V, G1, 12 V, 6 V, G2."]
    return page("3.3", "Stack", parts, s.out(), steps, ["⚠ P14 not modelled yet"], "Control box sits square, no rocking", S3)


def p_board_top():
    s = Svg()
    ts = .38
    lw, ld = 456.8, 300.8
    cx, cy = 120, 128
    s.rect(cx - lw / 2 * ts, cy - ld / 2 * ts, lw * ts, ld * ts, .5, fill="#fff")
    for x, z in E.ACC_LID:
        s.circ(cx + x * ts, cy + z * ts, 2.5 * ts + .5, .4, INK, ACC)
    s.rect(cx - 200 * ts, cy - 125 * ts, 400 * ts, 250 * ts, .45, INK, "rgba(200,170,120,.18)", "2 1")
    s.text(cx, cy, "board ≥ 40 cm wide", 3.2, "middle", 700)
    s.text(cx, cy + ld / 2 * ts + 4.5, "FRONT", 2.3, "middle", c=MID)
    steps = ["A board at least 40 cm wide: on a 38 cm board the lid's corner holes sit only 5 mm in from its edges.",
             "Or pads under it. M3 rivnuts in the 4 corner holes if you want it fixed."]
    return page("3.4", "Laptop board", [(i_label("board", 18, 9, "#efe4d2"), 1, 1, "B54", "board ≥ 40 cm")], s.out(), steps, ["Later: not on the path to the first A3"], "", S3)


# ============================================================================
# stage 4
# ============================================================================
def p_checks(part):
    s = Svg()
    if part == "a":
        pts = [("IEC earth pin", 30), ("stud", 70), ("24 V PSU case", 110), ("12 V PSU case", 150), ("power body", 190), ("power lid", 230)]
        for n, x in pts:
            s.circ(x, 100, 4, .45, INK, "#fff")
            s.text(x, 110, n, 2.5, "middle")
        wire(s, [(34, 100), (66, 100)], "PE", .9)
        for a, b in zip(pts[1:], pts[2:]):
            s.path(f"M{a[1]} 96 Q{(a[1] + b[1]) / 2} 82 {b[1]} 96", .5, WIRE["PE"])
        s.text(150, 76, "all beep", 3.4, "middle", 700, WIRE["PE"])
        for n, x in (("G1", 80), ("G2", 120), ("24 V", 160)):
            s.circ(x, 150, 4, .45, INK, "#fff")
            s.text(x, 160, n, 2.6, "middle")
        s.circ(220, 150, 4, .45, INK, "#fff")
        s.text(220, 160, "earth", 2.6, "middle")
        s.path("M84 150 Q150 132 216 150", .5, ACC, dash="1.4 1")
        s.path("M124 150 Q170 138 216 150", .5, ACC, dash="1.4 1")
        s.text(150, 130, "open: no beep", 3.4, "middle", 700, ACC)
        steps = ["Unplugged. Earth: IEC earth pin → stud, both PSU cases, power body, both lids, control body. All beep.",
                 "Isolation: G1 and G2 to earth: open. 24 V to G1: not a short.",
                 "Power box alone, banana leads out, mains on: every jack at its voltage."]
        return page("4.1", "Checks before motors", [(i_meter(), 1.6, 1, "B60", "multimeter")], s.out(), steps,
                    ["Lids beep only if the bond leads go in (Open questions 5)"], "All three pass", S4)
    seq = [("USB in", "board boots"), ("banana leads", ""), ("24 V toggle", "TB LEDs on"), ("6 V toggle", "servo unplugged: 6.0 V on pins 1–2"),
           ("one motor", "toggles off to plug; jog 10 mm"), ("endstops", "press each by hand: status shows it"), ("servo", "pen up/down × 5, no reset"),
           ("10 min run", "drivers warm, fans spin")]
    for i, (a, b) in enumerate(seq):
        x, y = 22 + (i % 4) * 68, 84 + (i // 4) * 52
        s.circ(x, y, 5, .5, INK, "#fff")
        s.text(x, y + 1.6, str(i + 1), 4, "middle", 700)
        s.text(x + 8, y + 1.4, a, 3.4, weight=700)
        for j, ln in enumerate(wrap(b, 26)):
            s.text(x + 8, y + 7 + j * 3.8, ln, 2.7, c="#444")
        if i % 4 < 3:
            s.arrow(x + 50, y, x + 60, y)
    steps = ["Up: USB first, then the toggles. Down: toggles off, then USB.",
             "Motors one at a time. If X1 and X2 fight, swap one coil pair on one motor.",
             "Endstops before the first homing."]
    return page("4.2", "First power-up", [], s.out(), steps, ["Never plug or unplug a motor with 24 V on"], "Then Stage 5: the first A3", S4)


# ============================================================================
# back matter: BOM and prints (from the doc's tables)
# ============================================================================
BOM = HERE / "bom.tsv"
PRINTS = HERE / "prints.tsv"


def table_pages(path, title, cols, widths, per=24, num="BOM"):
    rows = [ln.split("\t") for ln in path.read_text().strip().splitlines()[1:]]
    pages = []
    for k in range(0, len(rows), per):
        s = Svg()
        y = 60
        x = 10
        for c, w in zip(cols, widths):
            s.text(x, y, c, 2.8, weight=700)
            x += w
        s.line(10, y + 2, PW - 10, y + 2, .4)
        for i, r in enumerate(rows[k:k + per]):
            y += 5.6
            if i % 2:
                s.rect(10, y - 4, PW - 20, 5.6, 0, fill="#f4f4f2")
            x = 10
            for c, w in zip(r, widths):
                s.text(x, y, c[: int(w / 1.45)], 2.7)
                x += w
        n = f"{num} {k // per + 1}"
        pages.append(page(n, "", [], s.out(), [f"Master copy: the Etch Build Book doc. Status here is as of {TODAY}."]))
    return pages


TODAY = "2026-10-22"

PAGES = [p_cover, p_legend, p_rules, lambda: p_rivnuts("control"), lambda: p_rivnuts("power"), p_rivets,
         p_earth_stud, lambda: p_base_plate("power", "1.2", S1), p_psus, p_iec_panel, lambda: p_mains("a"), lambda: p_mains("b"),
         p_first_power, lambda: p_dc("a"), lambda: p_dc("b"), lambda: fan_page("power", "1.8", S1), lambda: p_psu_panel("a"),
         lambda: p_psu_panel("b"),
         lambda: p_base_plate("control", "2.1", S2), p_rails, lambda: p_plate("tb"), lambda: p_plate("board"), p_layout,
         lambda: p_gx("a"), lambda: p_gx("b"), p_receiving, p_usb, lambda: p_power_wiring("a"), lambda: p_power_wiring("b"),
         lambda: p_signals("a"), lambda: p_signals("b"), lambda: fan_page("control", "2.10", S2), p_dip,
         p_windows, p_lids, p_stack, p_board_top, lambda: p_checks("a"), lambda: p_checks("b")]


def html():
    pages = [p() for p in PAGES]
    if BOM.exists():
        pages += table_pages(BOM, "BOM", ["ID", "Item", "Spec", "Qty", "Step", "Status"], [12, 44, 120, 22, 40, 30], num="BOM")
    if PRINTS.exists():
        pages += table_pages(PRINTS, "Prints", ["ID", "Part", "Script → STL", "Qty", "Step", "Status"], [12, 60, 110, 18, 30, 30], num="Prints")
    body = "\n".join(pages)
    return f"""<title>Etch Build Book</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
/* layout: a stack of A4-landscape pages on a desk-grey ground */
:root{{--desk:#e6e6e2;--paper:#fff;--shadow:rgba(0,0,0,.22)}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{--desk:#262624;--shadow:rgba(0,0,0,.6);color-scheme:dark}}}}
:root[data-theme="dark"]{{--desk:#262624;--shadow:rgba(0,0,0,.6);color-scheme:dark}}
body{{background:var(--desk);padding-block:16px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}}
.page{{display:block;width:100%;max-width:1100px;margin:0 auto 16px;background:var(--paper);box-shadow:0 1px 4px var(--shadow)}}
</style>
{body}
"""


if __name__ == "__main__":
    out = HERE / "build_book.html"
    out.write_text(html())
    print("wrote", out, len(PAGES), "drawn pages")
