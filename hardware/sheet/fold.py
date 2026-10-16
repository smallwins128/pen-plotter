"""Fold the cut files the way the shop will, and check the folded parts against the design.

Reads each DXF in out/sheet (what the laser cuts), splits it at the Bend Center lines, and bends
every flange 90 deg toward the viewer of the drawing ("UP") about inner radius R, with the flat
lengths from the bend allowance. Nothing is taken from the design model except T, R, K: the
folded shape comes from the DXF alone. Then:

  - the folded part is placed by a proper rotation (no mirroring) that best fits the design;
  - every hole centre is compared with where the design wants it (catches mirrored flats);
  - outer dimensions are compared with the design;
  - flanges of one part must not touch each other (fold collisions);
  - the whole assembly (bodies, lids, plates, stacked) must not intersect.

Writes out/fold/<part>.stl and out/fold/assembly.glb (one node per part, for Blender).

    python3 hardware/sheet/fold.py
"""
import json
import math
import pathlib
import sys

import numpy as np
import trimesh
from shapely.geometry import LineString, Point, Polygon, box as sbox
from shapely.ops import polygonize, unary_union

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import enclosure as E            # noqa: E402  (T, R, K, BA and the design, for comparison only)

SRC = E.OUT
DST = HERE.parent / "out" / "fold"
T, R, BA = E.T, E.R, E.BA
STRIPS = 9                       # strips per bend zone


# ---------------------------------------------------------------- DXF -> flat polygon + bends
def read_flat(path):
    ents = E.read_dxf(path)
    f = lambda e, c: float(e[c][0])
    segs, circles, bends = [], [], []
    for e in ents:
        lay = e.get("8", [""])[0]
        if e["type"] == "LINE" and lay == "Visible":
            segs.append(LineString([(f(e, "10"), f(e, "20")), (f(e, "11"), f(e, "21"))]))
        elif e["type"] == "ARC" and lay == "Visible":
            cx, cy, r, a0, a1 = f(e, "10"), f(e, "20"), f(e, "40"), math.radians(f(e, "50")), math.radians(f(e, "51"))
            sweep = (a1 - a0) % (2 * math.pi) or 2 * math.pi
            n = max(4, int(sweep / (math.pi / 16)))
            segs.append(LineString([(cx + r * math.cos(a0 + sweep * i / n), cy + r * math.sin(a0 + sweep * i / n)) for i in range(n + 1)]))
        elif e["type"] == "CIRCLE" and lay == "Visible":
            circles.append(((f(e, "10"), f(e, "20")), f(e, "40")))
        elif e["type"] == "LINE" and lay == "Bend Center":
            bends.append(((f(e, "10"), f(e, "20")), (f(e, "11"), f(e, "21"))))
    # snap endpoints so arcs and lines close
    merged = unary_union([LineString([(round(x, 3), round(y, 3)) for x, y in s.coords]) for s in segs])
    rings = sorted(polygonize(merged), key=lambda p: -p.area)
    shape = rings[0]
    for r_ in rings[1:]:
        if shape.contains(r_.representative_point()) and r_.area < shape.area:
            shape = shape.difference(r_)
    hole_pts = [p.centroid.coords[0] for p in rings[1:]]
    for c, r_ in circles:
        shape = shape.difference(Point(c).buffer(r_, 32))
        hole_pts.append(c)
    return shape.buffer(0), bends, hole_pts, circles


# ---------------------------------------------------------------- fold
class Bend:
    rr_ = None                                         # the shop's real inner radius (None = as drawn)

    @property
    def R(self):
        return self.rr_ if self.rr_ is not None else R

    @property
    def bar(self):
        return math.pi / 2 * (self.R + E.K * T)

    def __init__(self, a, b):
        a, b = np.array(a), np.array(b)
        self.mid = (a + b) / 2
        self.d = (b - a) / np.linalg.norm(b - a)
        a, b = a - self.d * 0.05, b + self.d * 0.05      # DXF bend lines are rounded to 0.01: reach the part's edge
        self.n = np.array([-self.d[1], self.d[0]])      # in-plane normal (sign fixed once the parent side is known)
        self.zone = self.strip(-BA / 2, BA / 2, a, b)
        self.a, self.b = a, b

    def strip(self, t0, t1, a=None, b=None):
        a = self.a if a is None else a; b = self.b if b is None else b
        return Polygon([a + self.n * t0, b + self.n * t0, b + self.n * t1, a + self.n * t1])

    def orient(self, n):
        self.n = n
        self.c0 = self.mid - self.n * BA / 2          # zone edge on the parent side

    def local(self, P):                                # P: (N,3) in the flat frame -> (along, across, z)
        q = P[:, :2] - self.c0
        return q @ self.d, q @ self.n, P[:, 2]

    def rigid(self, P):
        """Child side: rotate 90 deg about the bend axis, toward +z, after taking up the bend allowance."""
        a, t, z = self.local(P)
        rr = self.R + T
        out = (self.c0 + np.outer(a, self.d) + np.outer(rr - z, self.n))
        return np.column_stack([out, rr + t - self.bar])

    def arc(self, P):
        """Inside the zone: material at height z (0 = outer face, T = inner) on radius R + T - z."""
        a, t, z = self.local(P)
        if np.any(t > self.bar):                         # shop consumes less than drawn: the rest is straight flange
            out = self.rigid(P); arc = self.arc_(P, self.bar)
            return np.where((t > self.bar)[:, None], out, arc)
        return self.arc_(P, self.bar)

    def arc_(self, P, ba):
        a, t, z = self.local(P)
        th = np.clip(t / ba, 0, 1) * math.pi / 2
        rr = self.R + T - z
        out = self.c0 + np.outer(a, self.d) + np.outer(rr * np.sin(th), self.n)
        return np.column_stack([out, (self.R + T) - rr * np.cos(th)])


def extrude(poly):
    """Closed prism of a polygon (with holes) from z=0 to z=T."""
    if poly.is_empty or poly.area < 1e-6:
        return None
    return trimesh.creation.extrude_polygon(poly, T)


def fold_part(path, r_real=None):
    shape, blines, holes, circles = read_flat(path)
    bends = [Bend(a, b) for a, b in blines]
    for b in bends:
        b.rr_ = r_real
    zones = unary_union([b.zone for b in bends]) if bends else Polygon()
    faces = shape.difference(zones.buffer(1e-4))
    faces = list(faces.geoms) if hasattr(faces, "geoms") else [faces]
    faces = [f for f in faces if f.area > 1.0]
    root = max(range(len(faces)), key=lambda i: faces[i].area)
    # face graph through bends
    def face_at(pt):
        p = Point(pt)
        for i, f in enumerate(faces):
            if Polygon(f.exterior).buffer(1e-3).contains(p):
                return i
        return None
    links = []
    for k, b in enumerate(bends):
        sides = []
        for sgn in (1, -1):
            hit = None
            for frac in np.linspace(0.02, 0.98, 25):        # any point along the edge that lands on material
                q = b.a + (b.b - b.a) * frac + sgn * b.n * (BA / 2 + 0.05)
                hit = face_at(q)
                if hit is not None:
                    break
            sides.append(hit)
        links.append((k, sides[0], sides[1]))
    parent = {root: None}; chain = {root: []}; frontier = [root]
    while frontier:
        nxt = []
        for fi in frontier:
            for k, s_pos, s_neg in links:
                for here, there, n_sgn in ((s_neg, s_pos, 1), (s_pos, s_neg, -1)):
                    if here == fi and there is not None and there not in parent:
                        bends[k].orient(bends[k].n * n_sgn if n_sgn == 1 else -bends[k].n)
                        bends[k].orient(_dir(bends[k], fi, faces))
                        parent[there] = fi; chain[there] = chain[fi] + [k]; nxt.append(there)
        frontier = nxt
    unreached = [i for i in range(len(faces)) if i not in chain]
    # pieces: faces, and each zone cut in strips
    pieces = []
    for i, f in enumerate(faces):
        if i in chain:
            pieces.append((f, chain[i], None))
    for k, b in enumerate(bends):
        par = next((fi for fi in chain if fi is not None and _touches(faces[fi], b, -1)), None)
        if par is None:
            continue
        for s in range(STRIPS):
            t0, t1 = -BA / 2 + BA * s / STRIPS, -BA / 2 + BA * (s + 1) / STRIPS
            pc = shape.intersection(b.strip(t0, t1))
            for g in (pc.geoms if hasattr(pc, "geoms") else [pc]):
                if g.geom_type == "Polygon" and g.area > 1e-6:
                    pieces.append((g, chain[par], k))
    meshes = []
    for poly, ch, zk in pieces:
        m = extrude(poly)
        if m is None:
            continue
        if zk is not None:
            m = m.subdivide()                                # finer along the arc
        V = np.array(m.vertices)
        if zk is not None:
            V = bends[zk].arc(V)
        for k in reversed(ch):
            V = bends[k].rigid(V)
        m.vertices = V
        meshes.append(m)
    def fold_point(c):
        fi = face_at(c)
        if fi is None or fi not in chain:
            return None
        V = np.array([[c[0], c[1], T / 2]])
        for k in reversed(chain[fi]):
            V = bends[k].rigid(V)
        return V[0]
    face_meshes = []                                       # flat faces only, for the self-collision check
    for i, f in enumerate(faces):
        if i in chain:
            m = extrude(f); V = np.array(m.vertices)
            for k in reversed(chain[i]):
                V = bends[k].rigid(V)
            m.vertices = V; face_meshes.append((i, m))
    return dict(mesh=trimesh.util.concatenate(meshes), fold_point=fold_point, flat_holes=holes, bends=len(bends),
                faces=len(faces), unreached=unreached, shape=shape, face_meshes=face_meshes)


def _touches(face, b, side):
    return face.buffer(0.1).intersects(LineString([b.c0 - b.n * 0.05 + b.d * 0, b.c0 - b.n * 0.05 + b.d * 1]).buffer(0.0)) \
        or face.buffer(0.1).intersects(Point(*(b.c0 - b.n * 0.05)))


def _dir(b, parent_face, faces):
    """n pointing from the parent face into the child."""
    f = faces[parent_face]
    for frac in np.linspace(0.02, 0.98, 25):
        q = b.a + (b.b - b.a) * frac
        if f.buffer(1e-3).contains(Point(*(q - b.n * (BA / 2 + 0.05)))):
            return b.n
        if f.buffer(1e-3).contains(Point(*(q + b.n * (BA / 2 + 0.05)))):
            return -b.n
    return b.n


# ---------------------------------------------------------------- place in the design frame
def design_holes(p):
    """Every hole of the design part, as a 3D point in the assembly frame (x right, y up, z front; box base underside y=0)."""
    pts = []
    kind = p.name.split("_")[0]
    Hb = T + E.H[kind]
    for h in p.holes:
        uv = h.get("uv")
        face = h["face"]
        c = h.get("c") or (np.add(h["p0"], h["p1"]) / 2).tolist()
        if p.name.endswith("body"):
            if face == "base" and uv:
                pts.append((c, (uv[0], T / 2, uv[1])))
            elif face in ("left", "right") and uv:
                x = (-1 if face == "left" else 1) * (E.WO / 2 - T / 2)
                pts.append((c, (x, uv[1], uv[0])))
            elif face == "front" and uv:
                pts.append((c, (uv[0], uv[1], E.ZF - T / 2)))
        elif p.name.endswith("lid"):
            if face == "top":
                pts.append((c, (c[0], Hb + T / 2, c[1])))
            elif face == "back" and uv:
                pts.append((c, (uv[0], uv[1], E.ZB - T / 2)))
    return pts


def kabsch(A, B):
    """Proper rotation + translation taking points A onto B (det +1: no mirroring)."""
    ca, cb = A.mean(0), B.mean(0)
    H = (A - ca).T @ (B - cb)
    U, _, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    Rm = Vt.T @ np.diag([1, 1, d]) @ U.T
    return Rm, cb - Rm @ ca


def main():
    DST.mkdir(parents=True, exist_ok=True)
    parts = {p.name: p for p in E.build()}
    report, placed, ok_all, frames = [], {}, True, {}
    def ok(c, txt):
        nonlocal ok_all
        ok_all &= bool(c); report.append(("ok  " if c else "FAIL") + " " + txt)
    for name, p in parts.items():
        dxf = SRC / f"{name}.dxf"
        if not p.bends:
            shape, _, _, _ = read_flat(dxf)
            m = extrude(shape)
            kind = name.split("_")[0]
            m.vertices = np.column_stack([m.vertices[:, 0], m.vertices[:, 2] + E.PLATE_Y[0], m.vertices[:, 1]])
            # flat plate: the drawing's Y is the box's z (front up), seen from above
            placed[name] = m
            continue
        r = fold_part(dxf)
        ok(not r["unreached"], f"{name}: every face reached through a bend ({r['faces']} faces, {r['bends']} bends)")
        A, B = [], []
        for c, want in design_holes(p):
            V = r["fold_point"](c)
            if V is not None:
                A.append(V); B.append(want)
        A, B = np.array(A), np.array(B)
        Rm, tv = kabsch(A, B)
        frames[name] = (Rm, tv)
        err = np.linalg.norm((A @ Rm.T + tv) - B, axis=1)
        ok(err.max() < 0.05, f"{name}: {len(A)} holes land where the design puts them, no mirroring (worst {err.max():.3f} mm)")
        m = r["mesh"].copy()
        m.vertices = m.vertices @ Rm.T + tv
        placed[name] = m
        # outer size vs design
        lo, hi = m.bounds
        kind = name.split("_")[0]
        Hb = T + E.H[kind]
        if name.endswith("body"):
            want = (E.WO, Hb, E.ZF - E.ZB)
        else:
            want = (E.WO + 2 * (E.CLR + T), None, (E.ZF + E.CLR + T) - (E.ZB - T))
        got = hi - lo
        ok(abs(got[0] - want[0]) < 0.05, f"{name}: folded width {got[0]:.2f} (design {want[0]:.2f})")
        if want[1]:
            ok(abs(got[1] - want[1]) < 0.05, f"{name}: folded height {got[1]:.2f} (design {want[1]:.2f})")
        ok(abs(got[2] - want[2]) < 0.6, f"{name}: folded depth {got[2]:.2f} (design {want[2]:.2f}, tabs stop {E.TAB_GAP} shy)")
        # self-collision: flanges of the part must not cut into each other
        self_hit = _self_clash(r, Rm, tv)
        ok(not self_hit, f"{name}: no flange folds into another" + ("" if not self_hit else f" — {self_hit}"))
    # stack: power at y=0, control on top of the feet
    stack_y = T + E.H["power"] + T + E.STACK["flange_h"]
    scene, inter = trimesh.Scene(), []
    for name, m in placed.items():
        mm = m.copy()
        if name.startswith("control"):
            mm.apply_translation([0, stack_y, 0])
        mm.export(DST / f"{name}.stl")
        mm.visual.face_colors = [150, 155, 160, 255] if "plate" not in name else [90, 95, 100, 255]
        scene.add_geometry(mm, node_name=name, geom_name=name)
        inter.append((name, mm))
    # assembly: no two steel parts intersect (each part as one closed solid)
    solids = {n: _solid(m) for n, m in inter}
    names = list(solids)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            x = solids[names[i]] ^ solids[names[j]]
            th = _thickness(x)                     # surfaces resting on each other give zero-thickness slivers
            ok(th < 0.05, f"assembly: {names[i]} / {names[j]} do not intersect" + ("" if th < 0.05 else f" ({x.volume():.1f} mm³, {th:.2f} mm thick)"))
    scene.export(DST / "assembly.glb")
    report.append("")
    report.append("bend tolerance: the shop's inner radius (flats drawn for R%g, K %g)" % (R, E.K))
    for kind in ("power", "control"):
        for rr in (0.6, 1.0, 1.5, 2.0, 2.5):
            res = sweep(kind, frames, rr)
            good = res["side"] > 0.2 and res["front"] > 0.2 and not res["self"] and res["tab"] >= 0
            ok(good or rr > 2.0, f"{kind} R{rr:g}: lid side play {res['side']:+.2f}, front {res['front']:+.2f}, tab to front wall {res['tab']:+.2f}, "
               f"body {res['w']:.2f} W x {res['h']:.2f} H x {res['d']:.2f} D" + (f", CLASH {res['self']}" if res["self"] else "")
               + ("" if good else "  <- would not assemble"))
    print("\n".join(report))
    print(f"wrote {DST}/assembly.glb and one STL per part")
    return 0 if ok_all else 1


def sweep(kind, frames, r_real):
    """Fold body and lid with the shop's real inner radius; seat the lid; measure the fits."""
    out = {}
    for part in ("body", "lid"):
        name = f"{kind}_{part}"
        r = fold_part(SRC / f"{name}.dxf", r_real=r_real)
        Rm, tv = frames[name]
        fm = []
        for i, m in r["face_meshes"]:
            q = m.copy(); q.vertices = q.vertices @ Rm.T + tv; fm.append(q)
        out[part] = (trimesh.util.concatenate(fm), r, Rm, tv)
    body, lid = out["body"][0], out["lid"][0]
    (bx0, by0, bz0), (bx1, by1, bz1) = body.bounds
    (lx0, ly0, lz0), (lx1, ly1, lz1) = lid.bounds
    side = ((lx1 - lx0) - 2 * T - (bx1 - bx0)) / 2
    # seat the lid: top on the body's top lips, back against the back lips
    lid_top_inner = ly1 - T
    lid_back_inner = lz0 + T
    front = (lz1 - T + (bz0 - lid_back_inner)) - bz1
    # corner tab: its outer face vs the front wall's inner face, from the folded faces
    tab = _tab_gap(out["body"])
    self_hit = _self_clash(out["body"][1], None, None)
    return dict(side=side, front=front, tab=tab, self=self_hit, w=bx1 - bx0, h=by1 - by0, d=bz1 - bz0)


def _tab_gap(b):
    """Smallest z gap between the front wall's inner face and the corner tabs' outer faces."""
    m, r, Rm, tv = b
    zs = []
    for i, f in r["face_meshes"]:
        q = f.vertices @ Rm.T + tv
        (x0, y0, z0), (x1, y1, z1) = q.min(0), q.max(0)
        if z1 - z0 < 1.5 and x1 - x0 < 20 and y1 - y0 > 20 and z0 > 0:   # a corner tab: thin in z, narrow in x, tall, at the front
            zs.append(z1)
        if z1 - z0 < 1.5 and x1 - x0 > 400 and z0 > 0:           # the front wall
            front_inner = z0
    return min(front_inner - z for z in zs) if zs else 99.0


def _thickness(x):
    """Thickest piece of an intersection, by its smallest bounding-box side (0 = faces only touching)."""
    if x.is_empty() or x.volume() < 1e-6:
        return 0.0
    mm = x.to_mesh()
    t = trimesh.Trimesh(mm.vert_properties[:, :3], mm.tri_verts, process=False)
    return max(float(min(c.bounds[1] - c.bounds[0])) for c in t.split(only_watertight=False))


def _solid(m):
    """One closed solid from the per-piece prisms (they share faces at the strip and face boundaries)."""
    import manifold3d as mf
    acc = None
    for q in m.split(only_watertight=False):
        q = q.copy(); q.merge_vertices()
        mm = mf.Manifold(mf.Mesh(np.asarray(q.vertices, np.float32), np.asarray(q.faces, np.uint32)))
        if mm.status() != mf.Error.NoError or mm.is_empty():
            raise RuntimeError(f"piece not closed: {mm.status()}")
        acc = mm if acc is None else acc + mm
    return acc


def _self_clash(r, Rm, tv):
    """Flat faces of one part, folded: any two that overlap means a flange bends into another."""
    import manifold3d as mf
    sol = []
    for i, m in r["face_meshes"]:
        q = m.copy(); q.merge_vertices()
        sol.append((i, mf.Manifold(mf.Mesh(np.asarray(q.vertices, np.float32), np.asarray(q.faces, np.uint32)))))
    hits = []
    for x in range(len(sol)):
        for y in range(x + 1, len(sol)):
            v = (sol[x][1] ^ sol[y][1]).volume()
            if v > 0.01:
                hits.append(f"faces {sol[x][0]}/{sol[y][0]} {v:.1f} mm³")
    return ", ".join(hits)


if __name__ == "__main__":
    sys.exit(main())
