"""R05 Harbor: iPad sleeve on the SKÅDIS (2026-11-02). Four clips hold an iPad 8th gen (10.2", 2020) in landscape,
its back flat on the board.

Allwin's sketch: two SIDE clips near the top of the short edges, two BOTTOM corner clips (an L). Asked for: clips
that don't stand out, and the iPad as flush to the board as possible. So the clips skip the rail system: each clip
carries its own SKÅDIS lugs (the hook's neck and lip from skadis_rail.py, which slid well on the fit test), and the
iPad's back lies on the board face. Clip front = 7.5 iPad + 0.5 clearance + 1.6 lip = 9.6 mm off the board; the
lip covers 3 mm of the bezel.

    SIDE L / SIDE R      31 tall, 9.4 wide seen from the front; one lug. Channel open top and bottom.
    BOTTOM L / BOTTOM R  L-shaped: bar 18 tall under the iPad (15 + 3 lip), 69 long; arm 9.4 wide, 43 tall.
                         Two lugs, both in the bar, 40 apart; they carry the iPad's weight (490 g).

Fit: the clips hang on a fixed slot grid, so the iPad's place is set by the slots, not by the clips. Slot columns are
20 apart and alternate 20 mm in height; the two short edges land 13 columns apart (260 mm), on opposite column types.
That is why the left and right clips have their lugs in different places behind the same outline.

iPad side, port on the right (Allwin): the cable leaves the right edge mid-height, clear of the right side clip
(it starts 22 mm above the port). The top button and volume keys end up at the top-left; the left side clip stops
34 mm below the top corner. The headphone jack (bottom of the left edge) sits behind the bottom-left arm.

Print: BOTTOM clips stand upright as modelled (bar on the bed; each neck bridges 5.4 mm, as on the hook). SIDE clips
lie on their outer face: the lug's neck and lip are flush with that face, so they print on the bed too. No supports.

    python3 ipad_sleeve.py            # checks only (fit, slide, overhangs)
    python3 ipad_sleeve.py --stl      # + out/harbor/ipad_*.stl (print orientation) and a preview PNG

Frame as skadis_rail.py: x along the board, y out of it (board front y = 0), z up. Slot column x = 0 is an even
column: its slot floors sit at z = 6 + 40 k (odd columns: -14 + 40 k).
iPad numbers: 250.6 x 174.1 x 7.5 mm, Apple's published size (dimensions.com, gsmarena agree). Corner radius and
button positions are not published; the pocket corner is square so any radius sits, and clip positions avoid
where the buttons should be. SKÅDIS slot sizes: community figures (see skadis_rail.py).
"""
import pathlib
import sys

from build123d import BuildPart, BuildSketch, Plane, Polygon, Pos, export_stl, extrude, fillet, mirror

from skadis_rail import LIP, NECK, OUT, board_piece, box, prism_yz

IPAD = dict(w=250.6, h=174.1, t=7.5)           # Apple, verified
CLR = 0.5                                      # per side, around the iPad (edges and thickness)
LIP_T, LIP_OVER = 1.6, 3.0                     # front lip: thickness, how far it covers the bezel
Y_POCKET = IPAD["t"] + CLR                     # back of the lip
Y_FRONT = Y_POCKET + LIP_T                     # 9.6: front face of every clip
LUG_OUT = 4.2                                  # slot centre outside the iPad's edge (edges + clearance land 260 apart)
WALL = LUG_OUT + NECK["w"] / 2                 # 6.4: wall outside the edge; the lug is flush with its outer face
BAR = NECK["h"] + 6.0 + 2.0                    # 15: under the iPad; lug lip hangs 6 below the neck, 2 mm above it
ARM = 25.0                                     # corner arm above the iPad's bottom edge (short: speakers, jack)
REACH = 60.0                                   # corner bar inward from the iPad's edge (second lug at 55.8)
SIDE_Z = (109.0, 140.0)                        # side clips, above the iPad's bottom edge
LEAD = 1.5                                     # lead-in chamfer at the top of every channel

X0 = 10.0                                      # iPad centre: puts the left edge's lug column on x = -120
XL = X0 - IPAD["w"] / 2 - CLR                  # -115.8: left channel face
XR = X0 + IPAD["w"] / 2 + CLR                  # 135.8
ZB = 35.0                                      # iPad bottom edge: bar lugs' neck floor at ZB - 9 = 26 (odd columns)

# Lugs (slot column x, neck floor z). Left corner: odd columns 15.8 and 55.8 in from the edge; right corner: its
# wall column (4.2 out) and 35.8 in. Side clips: left in even column -120, right in odd column 140.
LUGS = {
    "bottom_l": [(-100.0, ZB - 9), (-60.0, ZB - 9)],
    "bottom_r": [(140.0, ZB - 9), (100.0, ZB - 9)],
    "side_l": [(-120.0, ZB + 131)],
    "side_r": [(140.0, ZB + 111)],
}


def slot_floor_ok(x, z):
    """True if column x has a slot whose floor is at z (the neck sits on the floor)."""
    base = 6.0 if (int(x) // 20) % 2 == 0 else -14.0
    return abs(((z - base) / 40) - round((z - base) / 40)) < 1e-6


def lug(x, zn):
    """The hook's neck and lip at slot column x, neck floor zn. Lip behind the board, hanging 6 below the neck,
    with the hook's chamfer on its top-back corner so it tips in."""
    yb, w, c = -NECK["len"], NECK["w"] / 2, LIP["chamfer"]
    lip = [(yb - LIP["t"], zn - 6), (yb, zn - 6), (yb, zn + 7), (yb - LIP["t"] + c, zn + 7), (yb - LIP["t"], zn + 7 - c)]
    part = prism_yz(lip, x - w, x + w)
    part += box(x - w, x + w, yb - 0.1, 0.1, zn, zn + NECK["h"])
    return part


def outline(pts, fillets, y0, y1):
    """Front outline (x, z) extruded y0..y1, with vertex fillets {index: radius}."""
    with BuildPart() as p:
        with BuildSketch(Plane.XZ.offset(-y0)) as sk:          # sketch x = world x, sketch y = world z
            Polygon(*pts, align=None)
            for i, r in fillets.items():
                fillet([v for v in sk.vertices() if abs(v.X - pts[i][0]) < 1e-6 and abs(v.Y - pts[i][1]) < 1e-6], r)
        extrude(amount=-(y1 - y0))
    return p.part


def lead_in(x_face, z_top, inward):
    """45 deg chamfer at the top of a channel: along the wall's inner face (x_face) and the lip's back face, so the
    iPad's edge finds its way in. inward = +1 if the iPad lies at x > x_face."""
    xa, xb = sorted((x_face - inward * 0.01, x_face + inward * (LIP_OVER + 1)))
    # wall face: triangle in (x, z), through all y up to the lip
    with BuildPart() as p:
        with BuildSketch(Plane.XZ.offset(1)):
            Polygon((x_face, z_top + 0.01), (x_face - inward * LEAD, z_top + 0.01), (x_face, z_top - LEAD), align=None)
        extrude(amount=-(Y_POCKET + 1))
    cut = p.part
    # lip back face: triangle in (y, z), along the lip's width
    cut += prism_yz([(Y_POCKET + 0.01, z_top + 0.01), (Y_POCKET + LEAD, z_top + 0.01), (Y_POCKET + 0.01, z_top - LEAD)],
                    xa, xb)
    return cut


def pocket():
    """The iPad's space plus clearance (square corners)."""
    return box(XL, XR, -1.0, Y_POCKET, ZB, ZB + 400)


def bottom_l():
    xo, xe, zb = XL - WALL, XL + REACH, ZB - BAR
    pts = [(xo, zb), (xe, zb), (xe, ZB + LIP_OVER), (XL + LIP_OVER, ZB + LIP_OVER), (XL + LIP_OVER, ZB + ARM),
           (xo, ZB + ARM)]
    part = outline(pts, {0: 4.0, 1: 1.5, 2: 1.5, 3: 2.0, 4: 1.5, 5: 1.5}, 0.0, Y_FRONT)
    part -= pocket()
    part -= lead_in(XL, ZB + ARM, +1)
    return part


def side_l():
    xo, xi = XL - WALL, XL + LIP_OVER
    z0, z1 = ZB + SIDE_Z[0], ZB + SIDE_Z[1]
    part = outline([(xo, z0), (xi, z0), (xi, z1), (xo, z1)], {0: 1.5, 1: 1.5, 2: 1.5, 3: 1.5}, 0.0, Y_FRONT)
    part -= pocket()
    part -= lead_in(XL, z1, +1)
    return part


def mirrored(part):
    return mirror(part, Plane.YZ.offset(X0))


def pieces():
    body = {"bottom_l": bottom_l(), "side_l": side_l()}
    body["bottom_r"], body["side_r"] = mirrored(body["bottom_l"]), mirrored(body["side_l"])
    out = {}
    for name, b in body.items():
        for x, zn in LUGS[name]:
            b += lug(x, zn)
        out[name] = b
    return out


# ---------------------------------------------------------------- checks

def vol(a, b):
    try:
        return (a & b).volume
    except Exception:
        return 0.0


def checks(ps):
    ok = True
    fail = lambda msg: print("  FAIL", msg)
    print("lug slots:")
    for name, lugs in LUGS.items():
        for x, zn in lugs:
            good = slot_floor_ok(x, zn)
            print(f"  {name:9s} column {x:6.0f}  neck floor {zn:5.0f}  {'ok' if good else 'NOT A SLOT'}")
            ok &= good
    board = board_piece(-150, 170, ZB - 30, ZB + 190)
    print("seated clips vs board / each other:")
    names = list(ps)
    for n in names:
        v = vol(ps[n], board)
        print(f"  {n:9s} vs board {v:.3f} mm3")
        ok &= v < 0.01
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            v = vol(ps[a], ps[b])
            if v > 0.01:
                fail(f"{a} vs {b}: {v:.2f}")
                ok = False
    print("hang each clip: push in 6.5 mm high, then drop (0.5 mm steps):")
    for n in names:
        worst = 0.0
        path = [(y, 6.5) for y in [12 - 0.5 * i for i in range(25)]] + [(0.0, 6.5 - 0.5 * i) for i in range(14)]
        for dy, dz in path:
            worst = max(worst, vol(Pos(0, dy, dz) * ps[n], board))
        print(f"  {n:9s} worst overlap {worst:.3f} mm3")
        ok &= worst < 0.05
    print("iPad drops in from above (1 mm steps):")
    ipad = box(X0 - IPAD["w"] / 2, X0 + IPAD["w"] / 2, 0.0, IPAD["t"], ZB, ZB + IPAD["h"])
    allp = ps["bottom_l"] + ps["bottom_r"] + ps["side_l"] + ps["side_r"]
    worst = max(vol(Pos(0, 0, dz) * ipad, allp) for dz in range(0, 230, 1))
    print(f"  worst overlap {worst:.3f} mm3; rests on the bars at z = {ZB}")
    ok &= worst < 0.05
    rest = vol(Pos(0, 0, -0.3) * ipad, allp)
    print(f"  0.3 mm lower it would hit the bars: {rest:.1f} mm3 (> 0 means it rests on them)")
    ok &= rest > 1
    return ok


def print_meshes(ps):
    """Each clip in print orientation, as trimesh meshes on z = 0."""
    import numpy as np, trimesh
    from trimesh.transformations import rotation_matrix
    out = {}
    for n, p in ps.items():
        path = OUT / f"_ipad_{n}.stl"
        export_stl(p, str(path))
        m = trimesh.load(str(path))
        path.unlink()
        if n.startswith("side"):                       # outer face down: the outer face's normal becomes -z
            m.apply_transform(rotation_matrix(np.radians(-90 if n == "side_l" else 90), [0, 1, 0]))
        m.apply_translation(-m.bounds[0])
        out[n] = m
    return out


def overhangs(meshes):
    """Down-facing area above the bed, by how far it hangs (bridges under the bottom clips' necks are expected)."""
    import numpy as np
    ok = True
    print("overhangs in print orientation (down-facing faces more than 45 deg, above the bed):")
    for n, m in meshes.items():
        nz = m.face_normals[:, 2]
        zc = m.triangles_center[:, 2]
        bad = (nz < -0.71) & (zc > 1.2)            # below 1.2 mm: the R4 / R1.5 corner fillets meeting the bed
        area = m.area_faces[bad].sum()
        spans = sorted(set(float(round(z, 1)) for z in zc[bad]))
        print(f"  {n:9s} {m.extents.round(1)} mm, {m.volume / 1000:.1f} cm3, down-facing {area:.1f} mm2 at z {spans}")
        expected = 2 * NECK["w"] * NECK["len"] if n.startswith("bottom") else 0.0   # the two neck bridges
        if area > expected + 0.5:
            ok = False
    return ok


def preview(ps, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import trimesh
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig = plt.figure(figsize=(12, 6.5))
    ax = fig.add_subplot(1, 1, 1)
    ax.set_aspect("equal")
    # board slots, iPad, clips: front view (x, z)
    for cx in range(-160, 200, 20):
        base = 6.0 if (cx // 20) % 2 == 0 else -14.0
        for k in range(-2, 7):
            zf = base + 40 * k
            if ZB - 40 < zf < ZB + 200:
                ax.add_patch(plt.Rectangle((cx - 2.5, zf), 5, 15, color="#cfcfcf"))
    ax.add_patch(plt.Rectangle((X0 - IPAD["w"] / 2, ZB), IPAD["w"], IPAD["h"], color="#1d1d1f"))
    for n, p in ps.items():
        export_stl(p, str(OUT / "_pv.stl"))
        m = trimesh.load(str(OUT / "_pv.stl"))
        front = m.triangles[(m.face_normals[:, 1] > 0.9) & (m.triangles_center[:, 1] > 0)]   # not the lugs
        for t in front:
            ax.add_patch(plt.Polygon(t[:, [0, 2]], fc="#e0913a", ec="#e0913a", lw=0.3))
    (OUT / "_pv.stl").unlink()
    ax.set_xlim(-160, 180)
    ax.set_ylim(ZB - 30, ZB + 190)
    ax.set_title("iPad sleeve, front view (mm). Grey: SKÅDIS slots; orange: clips")
    fig.savefig(path, dpi=110, bbox_inches="tight")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ps = pieces()
    ok = checks(ps)
    for n, p in ps.items():
        solids = len(p.solids())
        print(f"  {n:9s} {solids} solid{'s' if solids > 1 else ''}")
        ok &= solids == 1
    meshes = print_meshes(ps)
    ok &= overhangs(meshes)
    if "--stl" in sys.argv:
        for n, m in meshes.items():
            m.export(str(OUT / f"ipad_{n}.stl"))
            export_stl(ps[n], str(OUT / f"ipad_{n}_assembly.stl"))
        export_stl(board_piece(-170, 190, ZB - 30, ZB + 200), str(OUT / "ipad_board.stl"))     # for the inspector
        export_stl(box(X0 - IPAD["w"] / 2, X0 + IPAD["w"] / 2, 0.0, IPAD["t"], ZB, ZB + IPAD["h"]), str(OUT / "ipad_ipad.stl"))
        preview(ps, OUT / "ipad_sleeve_front.png")
        print("wrote", OUT)
    print("ALL CHECKS PASS" if ok else "CHECKS FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
