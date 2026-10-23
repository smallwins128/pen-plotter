"""OpenBuilds ACRO acrylic plates, read straight from Allwin's STL.

The STL (acrylic/Openbuilds_ACRO_Plates.stl, from Printables model 260803 via
Drive) is one flat sheet of 11 separate 6 mm parts. This splits it into parts,
traces each part's top face into an outline plus holes, and names the parts by
their size. Nothing here is typed in from a drawing: every number the gantry
views use comes from the mesh, so the views can't drift from the file.

Numpy only, no CAD kernel: python3 hardware/gantry/acro_plates.py prints the
parts and their holes.

Part roles are read from the hole patterns and are GUESSES until Allwin
confirms them against the real ACRO kit.
"""

import pathlib
from collections import defaultdict

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
STL = HERE / "acrylic" / "Openbuilds_ACRO_Plates.stl"

# Size signature (w x h, mm, rounded) -> (key, name, role guess).
ROLES = {
    (93.9, 135.7): ("gantry", "Gantry plate",
                    "rides a frame rail, carries the bar and a NEMA17"),
    (93.9, 122.7): ("carriage", "Carriage plate",
                    "rides a 2040 bar; long side slots take the tool plate"),
    (93.9, 110.0): ("motorplate", "Short motor plate",
                    "NEMA17 + wheels set for 2040; role unclear"),
    (93.9, 80.7): ("tool", "Tool plate",
                   "bolts to the carriage slots: height-adjustable head mount"),
    (43.0, 108.7): ("bracket", "End bracket", "frame corner / rail end"),
    (11.9, 41.9): ("link", "Link", "two M5 holes 20 apart"),
}


def load(path=STL):
    """Triangles as an (n, 3, 3) float array. Binary STL only."""
    b = pathlib.Path(path).read_bytes()
    n = int.from_bytes(b[80:84], "little")
    if 84 + 50 * n != len(b):
        raise ValueError(f"{path} is not a binary STL")
    dt = np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    return np.frombuffer(b, dtype=dt, count=n, offset=84)["v"].astype(float)


def _components(tri):
    """Label each triangle with the connected part it belongs to."""
    v = np.round(tri.reshape(-1, 3), 4)
    _, inv = np.unique(v, axis=0, return_inverse=True)
    inv = inv.reshape(-1, 3)
    parent = np.arange(inv.max() + 1)

    def root(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b, c in inv:
        ra = root(a)
        parent[root(b)] = ra
        parent[root(c)] = ra
    return np.array([root(i) for i in inv[:, 0]])


def _loops(t):
    """Boundary loops of the part's top face, in sheet XY."""
    zmax = t[:, :, 2].max()
    top = t[(np.abs(t[:, :, 2] - zmax) < 1e-3).all(1)][:, :, :2]
    key = lambda p: (round(p[0], 3), round(p[1], 3))
    count, directed = defaultdict(int), {}
    for tr in top:
        for i, j in ((0, 1), (1, 2), (2, 0)):
            a, b = key(tr[i]), key(tr[j])
            e = tuple(sorted((a, b)))
            count[e] += 1
            directed[e] = (a, b)
    nxt = {directed[e][0]: directed[e][1] for e, c in count.items() if c == 1}
    loops, seen = [], set()
    for s in nxt:
        if s in seen:
            continue
        loop, c = [s], nxt[s]
        seen.add(s)
        while c != s:
            loop.append(c)
            seen.add(c)
            c = nxt[c]
        loops.append(np.array(loop))
    return loops, zmax


def _area(p):
    x, y = p[:, 0], p[:, 1]
    return 0.5 * (x @ np.roll(y, -1) - y @ np.roll(x, -1))


def _hole(p):
    mn, mx = p.min(0), p.max(0)
    w, h = mx - mn
    c = (mn + mx) / 2
    r = np.hypot(*(p - c).T)
    circle = abs(w - h) < 0.05 and r.std() < 0.02
    return {"cx": float(c[0]), "cy": float(c[1]), "w": float(w), "h": float(h),
            "d": float(w) if circle else None, "pts": p}


def parts(path=STL):
    """Every part as a dict, in part-local coordinates (origin = bbox min).

    Keys: key, name, role, size (w, h, t), outline (k, 2), holes (list of
    {cx, cy, w, h, d, pts}), sheet_origin (where it sat in the STL).
    """
    tri = load(path)
    lab = _components(tri)
    out = []
    for i in np.unique(lab):
        t = tri[lab == i]
        p = t.reshape(-1, 3)
        mn, mx = p.min(0), p.max(0)
        loops, _ = _loops(t)
        loops = sorted((l - mn[:2] for l in loops), key=lambda l: -abs(_area(l)))
        w, h, th = mx - mn
        key, name, role = next((v for (rw, rh), v in ROLES.items()
                                if abs(rw - w) < 0.1 and abs(rh - h) < 0.1),
                               ("?", "Unknown", ""))
        out.append({"key": key, "name": name, "role": role,
                    "size": (float(w), float(h), float(th)),
                    "outline": loops[0], "holes": [_hole(l) for l in loops[1:]],
                    "sheet_origin": (float(mn[0]), float(mn[1]))})
    out.sort(key=lambda q: (-q["size"][0] * q["size"][1], q["sheet_origin"]))
    return out


def by_key(ps, key):
    return [q for q in ps if q["key"] == key]


# ---------------------------------------------------------------------------
# Readings off the gantry plate, used by the views
# ---------------------------------------------------------------------------

def gantry_layout(ps):
    """Wheel, motor and bar-bolt positions on the gantry plate, plate-local.

    x runs along the rail (direction of travel), y across it. The two round
    M5 holes on one line are the fixed wheels; the long slots on the same
    x are the adjustable wheels; the 32 mm bore is the NEMA17 boss.
    """
    g = by_key(ps, "gantry")[0]
    holes = g["holes"]
    m5 = [h for h in holes if h["d"] and abs(h["d"] - 5.2) < 0.05]
    long_slots = [h for h in holes if not h["d"] and h["h"] > 20 and h["w"] < 8]
    xs = sorted({round(h["cx"], 2) for h in long_slots})   # wheel lines
    fixed = [h for h in m5 if round(h["cx"], 2) in xs]
    short_slots = [h for h in holes if not h["d"] and 7 < h["h"] < 8
                   and round(h["cx"], 2) in xs]
    bore = [h for h in holes if h["d"] and h["d"] > 30][0]
    nema = [h for h in holes if h["d"] and abs(h["d"] - 3.0) < 0.05]
    fy = fixed[0]["cy"]
    ls = long_slots[0]
    travel = (ls["h"] - ls["w"]) / 2
    return {
        "plate": g,
        "wheel_x": xs,                                  # along travel
        "fixed_y": fy,
        "slot_y": (ls["cy"] - travel, ls["cy"] + travel),  # adjustable wheel range
        "short_slot_y": short_slots[0]["cy"],
        "bore": (bore["cx"], bore["cy"], bore["d"]),
        "nema_pitch": max(h["cx"] for h in nema) - min(h["cx"] for h in nema),
    }


def carriage_wheels(ps):
    """Fixed-to-adjustable wheel spacing across the bar on the carriage plate."""
    c = by_key(ps, "carriage")[0]
    m5 = [h for h in c["holes"] if h["d"] and abs(h["d"] - 5.2) < 0.05]
    short = [h for h in c["holes"] if not h["d"] and 7 < h["h"] < 8]
    return {"fixed_y": m5[0]["cy"], "adj_y": short[0]["cy"],
            "spacing": m5[0]["cy"] - short[0]["cy"],
            "along": abs(m5[0]["cx"] - m5[1]["cx"])}


if __name__ == "__main__":
    ps = parts()
    print(f"{len(ps)} parts from {STL.name}")
    for q in ps:
        w, h, t = q["size"]
        print(f"  {q['name']:<18} {w:6.2f} x {h:6.2f} x {t:.1f}  "
              f"{len(q['holes']):2d} holes   {q['role']}")
    g = gantry_layout(ps)
    print("gantry plate: wheels at x", g["wheel_x"], "fixed y", round(g["fixed_y"], 2),
          "adjustable y", tuple(round(v, 2) for v in g["slot_y"]),
          "2040 slot y", round(g["short_slot_y"], 2))
    print("  NEMA17 bore", g["bore"], "pitch", round(g["nema_pitch"], 2))
    print("carriage plate:", {k: round(v, 2) for k, v in carriage_wheels(ps).items()})
