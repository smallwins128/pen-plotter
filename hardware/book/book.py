"""Etch build book: IKEA-style 2D pages, one face per drawing, geometry from the generator (enclosure.py).

    python3 hardware/book/book.py      # writes hardware/book/build_book.html
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "sheet"))
import enclosure as E  # noqa: E402

PARTS = {p.name: p for p in E.build()}
INK, FAINT, ACC = "#111", "#b8b8b8", "#d33"
PW, PH = 297, 210                      # A4 landscape, mm


def f(x):
    return f"{x:.2f}".rstrip("0").rstrip(".")


class Svg:
    def __init__(self):
        self.s = []

    def add(self, t):
        self.s.append(t)
        return self

    def line(self, x0, y0, x1, y1, w=0.35, c=INK, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        return self.add(f'<line x1="{f(x0)}" y1="{f(y0)}" x2="{f(x1)}" y2="{f(y1)}" stroke="{c}" stroke-width="{w}"{d}/>')

    def rect(self, x, y, w, h, sw=0.35, c=INK, fill="none", dash=None, r=0):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        return self.add(f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="{f(r)}" stroke="{c}" stroke-width="{sw}" fill="{fill}"{d}/>')

    def circ(self, x, y, r, sw=0.35, c=INK, fill="none", dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        return self.add(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r)}" stroke="{c}" stroke-width="{sw}" fill="{fill}"{d}/>')

    def poly(self, pts, sw=0.35, c=INK, fill="none", close=True, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        tag = "polygon" if close else "polyline"
        return self.add(f'<{tag} points="{" ".join(f"{f(a)},{f(b)}" for a, b in pts)}" stroke="{c}" stroke-width="{sw}" fill="{fill}" stroke-linejoin="round"{d}/>')

    def text(self, x, y, s, size=4, anchor="start", weight=400, c=INK):
        return self.add(f'<text x="{f(x)}" y="{f(y)}" font-size="{f(size)}" text-anchor="{anchor}" font-weight="{weight}" fill="{c}">{s}</text>')

    def arrow(self, x0, y0, x1, y1, c=INK, w=0.5):
        import math
        a = math.atan2(y1 - y0, x1 - x0)
        h = 2.6
        p1 = (x1 - h * math.cos(a - 0.4), y1 - h * math.sin(a - 0.4))
        p2 = (x1 - h * math.cos(a + 0.4), y1 - h * math.sin(a + 0.4))
        self.line(x0, y0, x1, y1, w, c)
        return self.poly([(x1, y1), p1, p2], 0.2, c, c)

    def g(self, tx, ty, s, inner):
        return self.add(f'<g transform="translate({f(tx)} {f(ty)}) scale({f(s)})">{inner}</g>')

    def out(self):
        return "".join(self.s)


# ---------- part icons (drawn ~1:1 in mm, side view, origin = top-left of the icon box) ----------

def ico_screw_csk(L):
    s = Svg()
    s.poly([(0, 0), (6.4, 0), (4.6, 1.8), (1.8, 1.8)], 0.3, INK, "#fff")
    s.rect(1.8, 1.8, 2.8, L, 0.3, INK, "#fff")
    for i in range(int(L / 0.6)):
        s.line(1.8, 2.2 + i * 0.6, 4.6, 2.5 + i * 0.6, 0.12)
    return s.out(), 6.4, L + 1.8


def ico_screw_pan(L, d=3, head=5.5, hh=2.2):
    s = Svg()
    s.rect(0, 0, head, hh, 0.3, INK, "#fff", r=0.8)
    s.rect((head - d) / 2, hh, d, L, 0.3, INK, "#fff")
    for i in range(int(L / (d * 0.2))):
        y = hh + 0.4 + i * d * 0.2
        s.line((head - d) / 2, y, (head + d) / 2, y + d * 0.1, 0.12)
    return s.out(), head, L + hh


def ico_bolt_hex(L, d=6, head=10, hh=4):
    s = Svg()
    s.rect(0, 0, head, hh, 0.3, INK, "#fff")
    s.line(head / 3, 0, head / 3, hh, 0.2)
    s.line(2 * head / 3, 0, 2 * head / 3, hh, 0.2)
    s.rect((head - d) / 2, hh, d, L, 0.3, INK, "#fff")
    for i in range(int(L / 1.0)):
        y = hh + 0.5 + i * 1.0
        s.line((head - d) / 2, y, (head + d) / 2, y + 0.5, 0.12)
    return s.out(), head, L + hh


def ico_nut(w=10, h=5, nyloc=False):
    s = Svg()
    s.rect(0, 0, w, h, 0.3, INK, "#fff")
    s.line(w / 3, 0, w / 3, h, 0.2)
    s.line(2 * w / 3, 0, 2 * w / 3, h, 0.2)
    if nyloc:
        s.rect(w * 0.1, -h * 0.35, w * 0.8, h * 0.35, 0.3, INK, "#fff", r=0.6)
    return s.out(), w, h


def ico_washer(od=12, t=1.4, serrated=False):
    s = Svg()
    s.rect(0, 0, od, t, 0.3, INK, "#fff")
    if serrated:
        s.poly([(i * od / 8, t if i % 2 else 0) for i in range(9)], 0.2, close=False)
    return s.out(), od, t


def ico_standoff(L=5, w=7):
    s = Svg()
    s.rect(0, 0, w, L, 0.3, INK, "#fff")
    s.line(w / 2 - 2, 0, w / 2 - 2, L, 0.15, dash="0.6 0.4")
    s.line(w / 2 + 2, 0, w / 2 + 2, L, 0.15, dash="0.6 0.4")
    return s.out(), w, L


def ico_ring(d_hole=6.4, wire="#2a6"):
    s = Svg()
    s.circ(5, 5, 5, 0.3, INK, "#fff")
    s.circ(5, 5, d_hole / 2, 0.3)
    s.rect(9, 3, 7, 4, 0.3, INK, wire)
    s.line(16, 5, 24, 5, 1.2, wire)
    return s.out(), 24, 10


# ---------- page furniture ----------

def page(num, title, parts, body, notes=(), check=""):
    """parts: [(icon (svg, w, h), scale, qty, id)]; body: svg string for the drawing area (0..PW, 0..PH)."""
    s = Svg()
    s.rect(0, 0, PW, PH, 0, fill="#fff")
    s.text(10, 22, num, 16, weight=700)
    s.text(10, 30, title, 3.6, c="#555")
    # parts box
    x0, y0 = 10, 36
    cells = []
    for (svg, w, h), sc, qty, pid in parts:
        cells.append((svg, w * sc, h * sc, sc, qty, pid))
    bw = max(44, sum(max(c[1], 14) + 6 for c in cells) + 6)
    bh = max(c[2] for c in cells) + 18 if cells else 0
    if cells:
        s.rect(x0, y0, bw, bh, 0.4, r=2)
        x = x0 + 6
        for svg, w, h, sc, qty, pid in cells:
            cw = max(w, 14)
            s.g(x + (cw - w) / 2, y0 + 5 + (bh - 18 - h) / 2, sc, svg)
            s.text(x + cw / 2, y0 + bh - 7, f"{qty}x", 4.2, "middle", 700)
            s.text(x + cw / 2, y0 + bh - 2.5, pid, 2.6, "middle", c="#777")
            x += cw + 6
    s.add(body)
    for i, n in enumerate(notes):
        s.text(PW - 10, 16 + i * 5, n, 3, "end", c="#555")
    if check:
        ok_box(s, 10, PH - 14, check)
    return f'<svg class="page" viewBox="0 0 {PW} {PH}" xmlns="http://www.w3.org/2000/svg" font-family="Helvetica, Arial, sans-serif">{s.out()}</svg>'


def callout(s, x, y, r, cx, cy, cr):
    """Magnifier circle at (cx, cy) radius cr, linked to the spot (x, y) radius r."""
    s.circ(x, y, r, 0.4)
    import math
    a = math.atan2(cy - y, cx - x)
    s.line(x + r * math.cos(a), y + r * math.sin(a), cx - cr * math.cos(a), cy - cr * math.sin(a), 0.4)
    s.circ(cx, cy, cr, 0.5, fill="#fff")


def ok_box(s, x, y, text):
    s.rect(x, y, 6, 6, 0.4, r=1)
    s.poly([(x + 1.2, y + 3.2), (x + 2.6, y + 4.7), (x + 4.9, y + 1.3)], 0.6, close=False)
    s.text(x + 9, y + 4.8, text, 3.4)


def front_arrow(s, x, y, left):
    """'FRONT' arrow pointing left or right."""
    dx = -14 if left else 14
    s.arrow(x, y, x + dx, y, "#777", 0.4)
    s.text(x + dx / 2, y - 2, "FRONT", 2.6, "middle", c="#777")


# ---------- faces ----------

def wall_holes(kind, face):
    return [h for h in PARTS[f"{kind}_body"].holes if h["face"] == face]


def draw_left_wall(s, kind, ox, oy, sc, inside, hi=(), faint=False):
    """Left wall as a flat face. u = z (+ = front), v = height. inside=True: seen from inside (front on the left).
    (ox, oy) = page position of the wall's bottom-left corner. hi = notes to draw heavy; the rest is faint."""
    D, Hh = E.D, E.H[kind] + E.T
    sgn = -1 if inside else 1

    def P(u, v):
        return ox + (sgn * u + D / 2) * sc, oy - v * sc

    s.rect(ox, oy - Hh * sc, D * sc, Hh * sc, 0.5)
    fz, fy = E.FAN[kind]
    for h in wall_holes(kind, "left"):
        note = h["note"]
        strong = any(k in note for k in hi)
        c, w = (INK, 0.4) if strong else (FAINT, 0.25)
        if h["kind"] == "rect":
            u, v = h["uv"]; ww, hh = h["uvwh"]
            x0, y0 = P(u - sgn * ww / 2, v + hh / 2)
            s.rect(min(x0, P(u + sgn * ww / 2, 0)[0]), y0, ww * sc, hh * sc, w, c, r=3 * sc)
        elif h["kind"] == "circle":
            s.circ(*P(*h["uv"]), h["r"] * sc, w, c)
    # fan grille as one ring (the slots are many)
    strong = any("fan" in k for k in hi)
    c = INK if strong else FAINT
    for r in (12, 20, 28, 36):
        s.circ(*P(fz, fy), r * sc, 0.25, c, dash="1.5 0.8")
    return P


def draw_floor(s, kind, ox, oy, sc, hi=()):
    """Floor seen from above, front at the bottom. (ox, oy) = page centre."""
    W, D = E.W, E.D

    def P(x, z):
        return ox + x * sc, oy + z * sc

    s.rect(ox - W / 2 * sc, oy - D / 2 * sc, W * sc, D * sc, 0.5)
    for h in wall_holes(kind, "base"):
        strong = any(k in h["note"] for k in hi)
        if h["kind"] == "circle":
            s.circ(*P(*h["uv"]), max(h["r"], 1.6) * sc * 1.6, 0.35 if strong else 0.25, INK if strong else FAINT)
    return P


# ---------- pages ----------

def p_earth_stud():
    s = Svg()
    sc = 0.5
    ox, oy = 20, 182
    P = draw_left_wall(s, "power", ox, oy, sc, inside=True, hi=("earth stud",))
    s.text(ox, oy + 6, "Power box, left wall, seen from inside", 3, c="#777")
    front_arrow(s, ox + 20, oy - E.H["power"] * sc - 6, left=True)
    stud = next(h for h in wall_holes("power", "left") if "earth" in h["note"])
    x, y = P(*stud["uv"])
    s.circ(x, y, 3.25 * sc, 0.5, fill=ACC)
    # exploded stack, side view (wall vertical, outside on the left)
    cx, cy, cr = 236, 128, 46
    callout(s, x, y, 5, cx, cy, cr)
    k = 1.7                     # magnification
    wx = cx - 32
    s.rect(wx, cy - 30, 1.2 * k, 60, 0.4, INK, "#ddd")            # wall
    s.text(wx - 2, cy - 33, "outside", 2.6, "end", c="#777")
    s.text(wx + 4, cy - 33, "inside", 2.6, c="#777")
    s.rect(wx - 4 * k, cy - 5 * k, 4 * k, 10 * k, 0.35, INK, "#fff")  # bolt head
    s.rect(wx + 1.2 * k, cy - 3 * k, 36, 6 * k, 0.35, INK, "#fff")  # shank
    seq = [("washer", 1.2, 6.5), ("nut", 5, 5), ("ring", 1.0, 6), ("nut", 5, 5), ("ring", 1.0, 6), ("nut", 5, 5)]
    xx = wx + 1.2 * k + 3
    for i, (what, t, hh) in enumerate(seq):
        xx += 3.2
        if what == "ring":
            s.rect(xx, cy - hh * k, t * k, 2 * hh * k, 0.35, INK, "#3a7")
            s.line(xx + t * k / 2, cy - hh * k, xx + t * k / 2, cy - hh * k - 10, 1.0, "#3a7")
            s.text(xx + 1, cy - hh * k - 12, "IEC earth" if i == 2 else "PSU earths", 2.4, "middle", c="#3a7")
        else:
            s.rect(xx, cy - hh * k, t * k, 2 * hh * k, 0.35, INK, "#fff")
        xx += t * k
    s.text(cx, cy + cr - 8, "1 bolt · 1 serrated washer · 3 nuts", 2.6, "middle", c="#777")
    parts = [(ico_bolt_hex(20), 1.0, 1, "B09"), (ico_washer(12, 1.4, True), 1.0, 1, "B09"),
             (ico_nut(10, 5), 1.0, 3, "B09"), (ico_ring(), 0.9, 3, "B10")]
    return page("1.1", "Earth stud", parts, s.out(), ["⚠ scrape any film off under the serrated washer"], "Beep: stud ↔ bare steel")


def sub(s, x, y, ch):
    s.circ(x, y, 3.2, 0.4)
    s.text(x, y + 1.3, ch, 3.6, "middle", 700)


def p_base_plate():
    s = Svg()
    sc = 0.22
    pl = PARTS["power_base_plate"]
    for i, (ox, with_plate) in enumerate(((72, False), (180, True))):
        oy = 140
        P = draw_floor(s, "power", ox, oy, sc, hi=("standoff",))
        sub(s, ox - E.W / 2 * sc, oy - E.D / 2 * sc - 7, "ab"[i])
        s.text(ox, oy + E.D / 2 * sc + 5, "FRONT", 2.4, "middle", c="#777")
        if with_plate:
            s.poly([(ox + x * sc, oy + z * sc) for x, z in pl.outline().exterior.coords[:-1]], 0.5, fill="#f4f4f4")
            for h in pl.holes:
                x, z = h["c"]
                st = "standoff" in (h.get("note") or "")
                s.circ(ox + x * sc, oy + z * sc, (2.6 if st else h["r"] * sc), 0.4 if st else 0.2, INK if st else FAINT, "#fff" if st else "none")
        else:
            for h in wall_holes("power", "base"):
                if "standoff" in h["note"]:
                    s.circ(*P(*h["uv"]), 2.6, 0.5, fill=ACC)
    s.text(72 - E.W / 2 * sc, 140 + E.D / 2 * sc + 11, "Power box floor, from above", 2.8, c="#777")
    # side stack
    cx, cy = 262, 140
    k = 2.4
    s.text(cx, 78, "each of 6", 2.8, "middle", c="#777")
    s.rect(cx - 16, cy, 32, 1.2 * k, 0.4, INK, "#ddd")
    s.text(cx + 17, cy + 3, "floor", 2.4, c="#777")
    s.rect(cx - 3.5 * k / 2, cy - 5 * k, 3.5 * k, 5 * k, 0.4, INK, "#fff")
    s.text(cx + 6, cy - 5 * k / 2 + 1, "a", 3, weight=700)
    py = cy - 5 * k - 2 * k - 8
    s.rect(cx - 16, py, 32, 2 * k, 0.4, INK, "#f4f4f4")
    s.text(cx + 17, py + 3.5, "plate", 2.4, c="#777")
    s.text(cx - 19, py + 3.5, "b", 3, "end", 700)
    svg, w, h = ico_screw_pan(8, 4, 7, 2.8)
    m = k / 1.6
    yb = cy + 1.2 * k + 7
    s.add(f'<g transform="translate({f(cx - w * m / 2)} {f(yb + h * m)}) scale({f(m)} {f(-m)})">{svg}</g>')
    s.arrow(cx, yb + 1, cx, cy + 1.2 * k + 1, "#777", 0.4)
    yt = py - 8 - h * m
    s.g(cx - w * m / 2, yt, m, svg)
    s.arrow(cx, yt + h * m + 0.5, cx, py - 1, "#777", 0.4)
    parts = [(ico_standoff(5, 7), 1.6, 6, "B26"), (ico_screw_pan(8, 4, 7, 2.8), 1.3, 12, "B27")]
    return page("1.2", "Base plate", parts, s.out(), ["🚫 gate: plate material (B25)", "⚠ screw length unverified"],
                "Plate doesn't rock · no head below the rubber feet")


def p_iec_panel():
    s = Svg()
    sc = 0.5
    ox, oy = 20, 182
    P = draw_left_wall(s, "power", ox, oy, sc, inside=False, hi=("IEC",))
    s.text(ox, oy + 6, "Power box, left wall, from outside", 3, c="#777")
    front_arrow(s, ox + E.D * sc - 20, oy - E.H["power"] * sc - 6, left=False)
    pan = next(q for q in PARTS["power_body"].panels if q["key"] == "iec")
    pw, ph = pan["plate"]
    # panel drawn exploded to the right
    px, py = 238, 118
    s.rect(px - pw / 2 * sc, py - ph / 2 * sc, pw * sc, ph * sc, 0.5, fill="#fff", r=5 * sc)
    cw, ch = pan["cut"]
    s.rect(px - (cw / 2 - 2.3) * sc, py - (ch / 2 - 2.3) * sc, (cw - 4.6) * sc, (ch - 4.6) * sc, 0.25, FAINT, dash="1 0.6", r=3 * sc)
    s.text(px, py + 2, "P01", 3.2, "middle", 700, "#aaa")
    for h in wall_holes("power", "left"):
        if "rivnut" in h["note"] and "IEC" in h["note"]:
            u, v = h["uv"]
            s.circ(px + (u - pan["u"]) * sc, py - (v - pan["v"]) * sc, 3.2 * sc, 0.4)
            s.circ(px + (u - pan["u"]) * sc, py - (v - pan["v"]) * sc, 1.7 * sc, 0.3)
    cx, cy = P(pan["u"], pan["v"])
    s.arrow(px - pw / 2 * sc - 3, py, cx + cw / 2 * sc + 2, cy, "#777", 0.4)
    # contents of the panel (layout to model): module, 2 LEDs, stop
    s.text(px, py + ph / 2 * sc + 8, "IEC module · 2 LEDs · stop button go in first", 2.6, "middle", c="#777")
    iec = ("<rect width='20' height='12' rx='1' fill='#fff' stroke='#111' stroke-width='.3'/>"
           "<rect x='3' y='3' width='14' height='6' fill='none' stroke='#111' stroke-width='.3'/>", 20, 12)
    led = ("<circle cx='6' cy='6' r='6' fill='#fff' stroke='#111' stroke-width='.3'/><circle cx='6' cy='6' r='3' fill='#3a7'/>", 12, 12)
    stop = ("<circle cx='8' cy='8' r='8' fill='#d33' stroke='#111' stroke-width='.3'/>", 16, 16)
    parts = [(ico_screw_csk(6), 2.0, 4, "B42"), (iec, 1.0, 1, "B01"), (led, 1.0, 2, "B04"), (stop, 1.0, 1, "B03")]
    return page("1.4", "IEC panel", parts, s.out(), ["⚠ panel P01 not modelled yet: drawn blank", "lip goes into the opening"], "Lip seats · screw heads flush")


PAGES = [p_earth_stud, p_base_plate, p_iec_panel]


def html():
    pages = "\n".join(p() for p in PAGES)
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
{pages}
"""


if __name__ == "__main__":
    out = HERE / "build_book.html"
    out.write_text(html())
    print("wrote", out)
