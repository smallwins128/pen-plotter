"""Draw grille options to scale on the fume extractor face as SVG data (run from the repo root; writes /tmp/claude-0/grille/grilles.json)."""
import math, sys, json
sys.path.insert(0, "hardware/parts/fume")
import fume as F
from shapely.geometry import Point, LineString, box, Polygon
from shapely.ops import unary_union
from shapely import affinity

C = Point(0, F.CY); DISC = C.buffer(F.GRILLE_D / 2, quad_segs=64)

def holes():
    return unary_union(F.grille_holes())

def slots(w=1.8, pitch=3.4, vertical=False):
    out = []
    n = int(F.GRILLE_D / pitch) + 2
    for k in range(-n, n + 1):
        y = F.CY + k * pitch
        seg = LineString([(-60, y), (60, y)]).intersection(DISC.buffer(-w / 2 - 0.5))
        if seg.is_empty or seg.length < 2: continue
        out.append(seg.buffer(w / 2, cap_style=1, quad_segs=8))
    g = unary_union(out)
    return affinity.rotate(g, 90, origin=(0, F.CY)) if vertical else g

def rings(w=2.0, pitch=4.0, spoke=2.0):
    out, r = [], 2.0 + w / 2
    while r + w / 2 <= F.GRILLE_D / 2:
        out.append(C.buffer(r + w / 2, quad_segs=64).difference(C.buffer(r - w / 2, quad_segs=64)))
        r += pitch
    g = unary_union(out)
    sp = unary_union([affinity.rotate(box(-spoke / 2, F.CY, spoke / 2, F.CY + 40), a, origin=(0, F.CY)) for a in (45, 135, 225, 315)])
    return g.difference(sp)

def hexes(af=6.0, wall=1.2):
    p = af + wall; out = []
    r = af / math.sqrt(3)              # circumradius of a hexagon with across-flats af
    dx, dy = p, p * math.sqrt(3) / 2
    n = int(F.GRILLE_D / dy) + 2
    for j in range(-n, n + 1):
        for i in range(-n, n + 1):
            x, y = (i + (j % 2) * 0.5) * dx, j * dy
            h = Polygon([(x + r * math.cos(math.radians(30 + 60 * k)), F.CY + y + r * math.sin(math.radians(30 + 60 * k))) for k in range(6)])
            if DISC.buffer(-0.8).contains(h): out.append(h)
    return unary_union(out)

def svg(geom):
    def ring_path(coords):
        return "M" + " L".join(f"{x:.2f},{F.H - y:.2f}" for x, y in coords) + " Z"
    polys = list(geom.geoms) if hasattr(geom, "geoms") else [geom]
    d = []
    for pg in polys:
        d.append(ring_path(pg.exterior.coords))
        d += [ring_path(i.coords) for i in pg.interiors]
    return " ".join(d)

opts = {
  "holes": ("Round holes (today)", holes()),
  "hslots": ("Horizontal slots", slots()),
  "vslots": ("Vertical slots", slots(vertical=True)),
  "rings": ("Concentric rings", rings()),
  "hex": ("Honeycomb", hexes()),
}
out = {}
for k, (name, g) in opts.items():
    n = len(g.geoms) if hasattr(g, "geoms") else 1
    out[k] = dict(name=name, open=round(100 * g.area / DISC.area), features=n, d=svg(g))
outline = svg(F.OUTLINE)
json.dump(dict(w=F.W, h=F.H, outline=outline, opts=out), open("/tmp/claude-0/grille/grilles.json", "w"))
for k, v in out.items(): print(k, v["name"], v["open"], "% open,", v["features"], "openings")
