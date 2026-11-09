"""Etch frame CAD run 2: ACRO-style frame on the LINNMON; flat end brackets on the rails' outer faces.

World: x along the 1000 rails from the left end (0 = the table's left end), y from the frame's front face toward
the back, z up from the tabletop. The 1000 rails are exactly the LINNMON's length, so nothing may stand past the
table ends except the foot lips that hook over them.

Printed (PETG): 4 L-brackets on the rails' inner faces (hold the rail 28 above the 560 and bolt to the 560's inner
face), 4 corner feet (cap a LINNMON corner, take the bracket's tongue), 2 X plates (ACRO outline, 6 mm, a window
for the 700 bar and a collar round it), 1 dumb carriage plate. Bought: 2040 x 1000 x 2, 2040 x 560 x 2, 2020 x 700,
2 NEMA17, 8 V-wheels, the OpenBuilds plate on the bar.

    python3 hardware/gantry/frame.py          # checks only
    python3 hardware/gantry/frame.py --stl    # + hardware/out/frame/*.stl + summary.json
"""
import json, math, pathlib, sys
from build123d import Box, Cylinder, Polygon, Pos, Rot, extrude, export_stl, Axis, Align
from shapely.geometry import Polygon as SPoly, box as sbox

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent / "out" / "frame"
ACRO = {q["key"]: q for q in json.loads((HERE / "acrylic" / "acro_traced.json").read_text())}

# ------------------------------------------------------------------ geometry (mm)
RAIL_L, END_L, PW, PH = 1000.0, 560.0, 20.0, 40.0
F, GAP = 20.0, 0.0                  # foot pad height (lifts the whole frame so the X plates clear the table); the 1000 rests on the 560
TABLE_T, MARGIN = 34.0, 20.0        # LINNMON top PLACEHOLDER; frame face to table edge
END_Z0 = F                          # 560s sit on the feet
RZ0 = F + PH + GAP                  # rail underside
BAR, BAR_LEN, BAR_AT = 20.0, 700.0, 300.0
WHEEL_OD, WHEEL_W, SPACER = 24.4, 10.2, 6.0      # PLACEHOLDER catalogue
NEMA, NEMA_L = 42.3, 34.0
XP_T = 6.0                          # X plate, PETG (Allwin: 6 is fine)
WIN = 20.4                          # bar window
COLLAR_L, COLLAR_W = 20.0, 4.0
# bracket: flat plate on the rails' outer face (y -BT..0), x 0..BRK_W (as wide as the 560, so it costs no travel:
# the X plate's bottom wheel meets the 560 there anyway). M5 into the 560's tapped end; M5 + drop-in nut in the rail's slots.
BT, BRK_W = 6.0, 20.0
BRK_TOP = RZ0 + PH
TONGUE = (3.0, 17.0, 8.0)           # x0, x1, depth into the foot
# foot: a small corner grab under the bracket and the 560, lips halfway down the LINNMON's edge and end
LIP_T = 4.0
LIP = TABLE_T / 2
FOOT_X, FOOT_Y = (-LIP_T, BRK_W), (-MARGIN - LIP_T, 60.0)
CAR, DUMB = 65.5, (80.0, 100.0, 6.0)
BED = 256.0                         # Bambu A1
# from the traced ACRO plate
FIX_Y, SLOT_Y, BORE, BAR_PY, WHEEL_X = 101.05, 41.8, (46.94, 25.05), 115.74, (11.94, 81.94)

RAIL_MID = RZ0 + PH / 2
def pz(py): return RAIL_MID + py - (FIX_Y + SLOT_Y) / 2
Y_IN = PW / 2 - WHEEL_W / 2 - SPACER
BAR_ZC = pz(BAR_PY)

# ------------------------------------------------------------------ helpers
def prism_xz(poly, y0, t):
    """Shapely polygon in (x, z) extruded across y0..y0+t."""
    def face(ring): return Polygon(*[(a, b) for a, b in list(ring.coords)[:-1]], align=None)
    s = extrude(face(poly.exterior), t, dir=(0, 0, 1))
    for r in poly.interiors: s -= extrude(face(r), t, dir=(0, 0, 1))
    return Pos(0, y0 + t, 0) * (Rot(90, 0, 0) * s)

def box(x0, x1, y0, y1, z0, z1):
    return Pos(x0, y0, z0) * Box(x1 - x0, y1 - y0, z1 - z0, align=(Align.MIN, Align.MIN, Align.MIN))

def mirror_y(s): return s.mirror(__import__("build123d").Plane.XZ.offset(-END_L / 2))
def mirror_x(s): return s.mirror(__import__("build123d").Plane.YZ.offset(RAIL_L / 2))

def hole_y(s, x, z, y0, y1, d=5.5): return s - Pos(x, (y0 + y1) / 2, z) * (Rot(90, 0, 0) * Cylinder(d / 2, y1 - y0 + 2))
def hole_x(s, y, z, x0, x1, d=5.5): return s - Pos((x0 + x1) / 2, y, z) * (Rot(0, 90, 0) * Cylinder(d / 2, x1 - x0 + 2))

# ------------------------------------------------------------------ printed parts (front-left; others mirrored)
def bracket():
    p = sbox(0, F, BRK_W, BRK_TOP).buffer(-2, join_style=1).buffer(2, join_style=1)
    p = p.union(sbox(TONGUE[0], F - TONGUE[2], TONGUE[1], F + 1))
    s = prism_xz(p, -BT, BT)
    for z in (F + 10, F + 30, RZ0 + 10, RZ0 + 30): s = hole_y(s, BRK_W / 2, z, -BT, 0)
    return s

def foot():
    s = box(FOOT_X[0], FOOT_X[1], FOOT_Y[0], FOOT_Y[1], 0, F)
    s += box(FOOT_X[0], 0, FOOT_Y[0], FOOT_Y[1], -LIP, 0)                    # lip halfway down the table's end
    s += box(FOOT_X[0], FOOT_X[1], FOOT_Y[0], -MARGIN, -LIP, 0)              # lip halfway down the table's front edge
    s -= box(TONGUE[0] - 0.2, TONGUE[1] + 0.2, -BT - 0.2, 0.2, F - TONGUE[2] - 0.3, F + 1)
    return s

def x_plate():
    g = ACRO["gantry"]
    win = sbox(BORE[0] - WIN / 2, BAR_PY - WIN / 2, BORE[0] + WIN / 2, BAR_PY + WIN / 2)
    p = SPoly(g["outline"])
    for h in g["holes"]:
        hp = SPoly(h["pts"])
        if not hp.intersects(win.buffer(2)): p = p.difference(hp)
    p = p.difference(win)
    ox = BAR_AT - BORE[0]
    p = __import__("shapely.affinity", fromlist=["x"]).translate(p, ox, pz(0))
    s = prism_xz(p, Y_IN - XP_T, XP_T)
    c = box(BAR_AT - WIN / 2 - COLLAR_W, BAR_AT + WIN / 2 + COLLAR_W, Y_IN, Y_IN + COLLAR_L, BAR_ZC - WIN / 2 - COLLAR_W, BAR_ZC + WIN / 2 + COLLAR_W)
    c -= box(BAR_AT - WIN / 2, BAR_AT + WIN / 2, Y_IN - 1, Y_IN + COLLAR_L + 1, BAR_ZC - WIN / 2, BAR_ZC + WIN / 2)
    c = c - Pos(BAR_AT, Y_IN + COLLAR_L / 2, BAR_ZC + WIN / 2 + COLLAR_W / 2) * Cylinder(2.75, COLLAR_W + 2)   # M5 + T-nut into the bar's top slot
    return s + c

def dumb_plate():
    w, h, t = DUMB
    x0 = BAR_AT + BAR / 2 + 7
    return box(x0 + 6, x0 + 6 + t, END_L / 2 - w / 2, END_L / 2 + w / 2, BAR_ZC + 10 - h, BAR_ZC + 10)

# ------------------------------------------------------------------ assembly
def assembly():
    pr, bo = {}, {}
    b, f, xp = bracket(), foot(), x_plate()
    for nm, s in (("bracket", b), ("foot", f)):
        pr[f"{nm}_fl"] = s
        pr[f"{nm}_fr"] = mirror_x(s)
        pr[f"{nm}_bl"] = mirror_y(s)
        pr[f"{nm}_br"] = mirror_x(mirror_y(s))
    pr["xplate_front"], pr["xplate_back"] = xp, mirror_y(xp)
    pr["dumb_plate"] = dumb_plate()
    bo["rail_front"] = box(0, RAIL_L, 0, PW, RZ0, RZ0 + PH)
    bo["rail_back"] = box(0, RAIL_L, END_L - PW, END_L, RZ0, RZ0 + PH)
    bo["end_left"] = box(0, PW, 0, END_L, END_Z0, END_Z0 + PH)
    bo["end_right"] = box(RAIL_L - PW, RAIL_L, 0, END_L, END_Z0, END_Z0 + PH)
    bo["bar"] = box(BAR_AT - BAR / 2, BAR_AT + BAR / 2, (END_L - BAR_LEN) / 2, (END_L + BAR_LEN) / 2, BAR_ZC - BAR / 2, BAR_ZC + BAR / 2)
    ox = BAR_AT - BORE[0]
    for side, sg in (("front", 1), ("back", -1)):
        yo = Y_IN - XP_T
        m = box(BAR_AT - NEMA / 2, BAR_AT + NEMA / 2, yo - NEMA_L, yo, pz(BORE[1]) - NEMA / 2, pz(BORE[1]) + NEMA / 2)
        bo[f"motor_{side}"] = m if sg > 0 else mirror_y(m)
        for i, (wx, wy) in enumerate((a, c) for a in WHEEL_X for c in (FIX_Y, SLOT_Y)):
            w = Pos(ox + wx, PW / 2, pz(wy)) * (Rot(90, 0, 0) * Cylinder(WHEEL_OD / 2, WHEEL_W))
            bo[f"wheel_{side}{i}"] = w if sg > 0 else mirror_y(w)
    x0 = BAR_AT + BAR / 2 + 7
    bo["y_carriage"] = box(x0, x0 + 6, END_L / 2 - CAR / 2, END_L / 2 + CAR / 2, BAR_ZC - CAR / 2, BAR_ZC + CAR / 2)
    ghost = {"linnmon": box(0, RAIL_L, -MARGIN, END_L + MARGIN, -TABLE_T, 0),
             "enclosures": box(620, 960, 60, 500, F, 200)}
    return pr, bo, ghost

# ------------------------------------------------------------------ checks
def bb(s): b = s.bounding_box(); return (b.min.X, b.min.Y, b.min.Z, b.max.X, b.max.Y, b.max.Z)

def checks(pr, bo, ghost):
    res = []
    def add(n, ok, d): res.append(dict(name=n, ok=bool(ok), detail=d))
    allp = {**pr, **bo}
    names = list(allp); boxes = {n: bb(allp[n]) for n in names}
    clashes = []
    for i, a in enumerate(names):
        for c in names[i + 1:]:
            if {a.split("_")[0], c.split("_")[0]} == {"wheel", "rail"}: continue    # V-groove engagement
            A, B = boxes[a], boxes[c]
            if any(A[k] >= B[k + 3] - 1e-6 or B[k] >= A[k + 3] - 1e-6 for k in range(3)): continue
            v = (allp[a] & allp[c]).volume
            if v > 1.0: clashes.append(f"{a}/{c} {v:.0f} mm³")
    add("No part clashes (pairwise, wheels in the V-slot excepted)", not clashes, "; ".join(clashes) or f"{len(names)} parts")
    for n, s in pr.items():
        x0, y0, z0, x1, y1, z1 = boxes[n]
        dims = sorted([x1 - x0, y1 - y0, z1 - z0])
        if not dims[0] <= BED or dims[1] > BED or dims[2] > BED:
            add(f"{n} fits the A1 bed", False, f"{dims}")
    add("Every print fits the A1 bed (256³)", all(sorted([boxes[n][3+k]-boxes[n][k] for k in range(3)])[-1] <= BED for n in pr), "largest " + max(pr, key=lambda n: max(boxes[n][3+k]-boxes[n][k] for k in range(3))))
    add("1000 rails rest on the 560s", abs(RZ0 - (END_Z0 + PH)) < 1e-6, "an inner L-bracket can still be added later")
    low = min(boxes[n][2] for n in ("xplate_front", "motor_front"))
    add("X plate and motor clear the tabletop (≥ 8)", low >= 8, f"lowest {low:.1f} above the table; feet {F:.0f} tall")
    X_MIN = PW + WHEEL_OD / 2 + (BORE[0] - WHEEL_X[0]) + 1.0               # bottom wheel 1 mm off the 560
    add("Left limit", True, f"bar at x ≈ {X_MIN:.0f}: the bottom wheel meets the 560, the X plate edge is {X_MIN - BORE[0] - BRK_W:.1f} past the bracket")
    dx = X_MIN - BAR_AT                                          # carriage parked at the left limit
    moving = [n for n in allp if n.startswith(("xplate_front", "motor_front", "wheel_front"))]
    corner = [n for n in ("bracket_fl", "foot_fl", "end_left")]
    hits = [f"{m}/{c}" for m in moving for c in corner if (Pos(dx, 0, 0) * allp[m] & allp[c]).volume > 1.0]
    add("Parked at the left limit, the X plate clears the corner", not hits, ", ".join(hits) or f"bar at x {X_MIN:.0f}")
    past = [n for n in allp if boxes[n][0] < -1e-6 and not n.startswith("foot")] + [n for n in allp if boxes[n][3] > RAIL_L + 1e-6 and not n.startswith("foot")]
    add("Nothing past the table ends but the foot lips", not past, ", ".join(past) or "rails flush with the LINNMON ends")
    yfr = min(boxes[n][1] for n in allp)
    add("Overhang past the front edge (motors, bar)", True, f"{-MARGIN - yfr:.0f} mm past the table's front edge")
    sizes = {n: boxes[n] for n in pr}
    for n in ("bracket_fl", "foot_fl", "xplate_front"):
        x0, y0, z0, x1, y1, z1 = sizes[n]
        add(f"{n.split('_')[0]} size", True, f"{x1-x0:.0f} × {y1-y0:.0f} × {z1-z0:.0f}")
    return res

def main():
    pr, bo, ghost = assembly()
    res = checks(pr, bo, ghost)
    for r in res: print("PASS" if r["ok"] else "FAIL", r["name"], "·", r["detail"])
    if "--stl" not in sys.argv: return
    OUT.mkdir(parents=True, exist_ok=True)
    parts = []
    def ex(n): return [0, -60 if n.endswith(("fl", "fr", "front")) else 60, 0]
    grams = 0.0
    for n, s in pr.items():
        export_stl(s, str(OUT / f"{n}.stl"), tolerance=0.05)
        grams += s.volume * 1.27e-3 * 0.55
        e = {"bracket": [0, 0, 0], "foot": [0, 0, -50], "xplate": [0, 0, 0], "dumb": [40, 0, 0]}[n.split("_")[0]]
        if n.startswith("bracket"): e = [0, 50 if n[-2] == "f" else -50, 30]
        if n.startswith("xplate"): e = [0, -70 if n.endswith("front") else 70, 0]
        parts.append(dict(name=n, group="printed", explode=e))
    for n, s in bo.items():
        export_stl(s, str(OUT / f"{n}.stl"), tolerance=0.1)
        grp = "frame" if n.split("_")[0] in ("rail", "end", "bar") else "motion"
        e = [0, 0, 60] if n.startswith("rail") else [0, 0, 0]
        if n == "bar": e = [0, 0, 120]
        if n.startswith(("motor", "wheel")): e = [0, -110 if "front" in n else 110, 0]
        if n in ("y_carriage",): e = [0, 0, 120]
        parts.append(dict(name=n, group=grp, explode=e))
    for n, s in ghost.items():
        export_stl(s, str(OUT / f"{n}.stl"), tolerance=0.5)
        parts.append(dict(name=n, group="ghost", explode=[0, 0, -40 if n == "linnmon" else 0]))
    summary = dict(title="Etch frame · CAD run 2", up="z", q=25,
        sub=f"1000 × 560 frame on the LINNMON · 1000s rest on the 560s · 11 PETG prints, ≈ {grams:.0f} g at ~55% fill",
        size=[RAIL_L, END_L, BAR_ZC + 20],
        groups={"printed": {"label": "PETG prints", "note": "4 end brackets, 4 corner grabs, 2 X plates, 1 dumb plate", "color": "#3f4544", "grams": round(grams)},
                "frame": {"label": "2040 frame + 2020 bar", "color": "#b9c2bf"},
                "motion": {"label": "Motors, wheels, Y carriage", "color": "#6fb3e0"},
                "ghost": {"label": "LINNMON + enclosures", "color": "#c8955a", "ghost": True}},
        parts=parts, checks=res,
        cards=[{"title": "How it goes together", "html": "<ul>"
                "<li>Each <b>corner grab</b> sits on a LINNMON corner with lips halfway down the end and the front (or back) edge. Its pad lifts the frame 20 so the X plates clear the table.</li>"
                "<li>The <b>560</b> sits on the corner grabs and the <b>1000</b> rests on the 560, so an inner L-bracket can still go in later.</li>"
                "<li>The <b>end bracket</b> is a flat 20 × 6 plate on the outside face, the 560's width. Two M5 go into the 560's tapped end and two M5 into drop-in nuts in the rail's slots. Its tongue snaps into the corner grab.</li>"
                "<li>The <b>X plates</b> (ACRO outline, 6 mm PETG) ride outside the rails, with the motors at the bottom. The 700 bar passes through a window and a 20 mm collar.</li></ul>"},
               {"title": "Placeholders", "html": f"<ul><li>LINNMON thickness {TABLE_T:.0f} (measure at print time)</li><li>Wheel Ø{WHEEL_OD} × {WHEEL_W}, spacer {SPACER:.0f} (catalogue)</li><li>Dumb plate {DUMB[0]:.0f} × {DUMB[1]:.0f}, Y carriage 65.5 square stand-in</li><li>Grams: volume × 1.27 × 0.55, rough</li></ul>"}])
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1))
    print("wrote", OUT)

if __name__ == "__main__":
    main()
