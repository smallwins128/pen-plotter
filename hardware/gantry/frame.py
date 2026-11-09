"""Etch frame CAD run 5: ACRO-style frame on the LINNMON; one flat end plate per corner on the rails' outer faces.

World: x along the 1000 rails from the left end (0 = the table's left end), y from the frame's front face toward
the back, z up from the tabletop. The 1000 rails are exactly the LINNMON's length, so nothing may stand past the
table ends except the foot lips that hook over them.

Printed (PETG): 4 L-brackets on the rails' inner faces (hold the rail 28 above the 560 and bolt to the 560's inner
face), 4 corner feet (cap a LINNMON corner, take the bracket's tongue), 2 X plates (ACRO outline, 6 mm, a window
for the 700 bar and a collar round it), 1 dumb carriage plate. Bought: 2040 x 1000 x 2, 2040 x 560 x 2, 2020 x 700,
2 NEMA17, 8 V-wheels, the OpenBuilds plate on the bar.

    python3 hardware/gantry/frame.py          # checks only
    python3 hardware/gantry/frame.py --stl    # + hardware/out/frame/*.stl + summary.json
    python3 hardware/gantry/frame.py --print  # + hardware/out/frame/print/*.stl, laid flat for the A1
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
# end plate (one flat print per corner) on the outer face: a column over the 560's tapped end and the rail, an arm
# along the rail at rail height, a 45° chamfer between them (Allwin's sketch 2026-11-09, directional).
BT = 6.0
COL, BRK_W, CH = 28.0, 64.0, 24.0   # column width, overall width along the rail, chamfer
RAIL_HOLES_X = (10.0, 34.0)         # two per rail slot row
KEY = 5.0                           # end plate's column drops this far into a closed pocket in the foot
KEY_CL = 0.2                        # pocket clearance per side
# corner grab: PLACEHOLDER block (Allwin will redesign): pad under the corner, lips halfway down the end and edge
LIP_T = 4.0
LIP = TABLE_T / 2
FOOT_X0, FOOT_X1 = -LIP_T, COL + 6.0
FOOT_YF, FOOT_YB = -MARGIN - LIP_T, 40.0
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
    prof = SPoly([(0, F - KEY), (COL, F - KEY), (COL, RZ0 - CH), (COL + CH, RZ0), (BRK_W, RZ0), (BRK_W, RZ0 + PH), (0, RZ0 + PH)])
    prof = prof.buffer(-4, join_style=1).buffer(4, join_style=1).buffer(5, join_style=1).buffer(-5, join_style=1)
    s = prism_xz(prof, -BT, BT)
    for z in (F + 10, F + 30): s = hole_y(s, PW / 2, z, -BT, 0)                       # 560's tapped end
    for x in RAIL_HOLES_X:
        for z in (RZ0 + 10, RZ0 + 30): s = hole_y(s, x, z, -BT, 0)                    # rail's outer slots, drop-in nuts
    return s

def foot():
    s = box(FOOT_X0, FOOT_X1, FOOT_YF, FOOT_YB, 0, F)
    s += box(FOOT_X0, 0, FOOT_YF, FOOT_YB, -LIP, 0)                            # lip halfway down the table's end
    s += box(FOOT_X0, FOOT_X1, FOOT_YF, -MARGIN, -LIP, 0)                      # lip halfway down the table's front edge
    s -= box(-KEY_CL, COL + KEY_CL, -BT - KEY_CL, KEY_CL, F - KEY - 0.3, F + 1)   # closed pocket for the end plate's column
    return s

def fit_coupon():
    """Key + pocket fit checker: a pocket block with three clearances side by side, and a key on a stop flange
    (the key stands KEY proud of the flange, like the end plate's column). Returns (block, key), both bed-ready."""
    cls = (0.1, 0.2, 0.3)
    w, gap, depth = COL, 6.0, KEY + 0.3
    bw = 2 * 5 + len(cls) * (BT + 0.6) + (len(cls) - 1) * gap
    block = box(0, w + 10, 0, bw, 0, depth + 3)
    y = 5.0
    for c in cls:
        block -= box(5 - c, 5 + w + c, y - c, y + BT + c, 3, depth + 4)
        for i in range(int(round(c * 10))):                                      # 1/2/3 nicks on the rim = 0.1/0.2/0.3
            block -= box(w + 6.5, w + 8.5, y + 0.8 + i * 1.8, y + 1.8 + i * 1.8, depth + 2.4, depth + 4)
        y += BT + 0.6 + gap
    key = box(0, w + 8, 0, BT + 8, 0, 3) + box(4, 4 + w, 4, 4 + BT, 3, 3 + KEY)
    return block, Pos(0, bw + 10, 0) * key

def flat(s, how):
    """A copy laid on the bed the way it prints, min corner at the origin."""
    if how == "x_face": s = Rot(90, 0, 0) * s                                 # plate lying on its face
    if how == "flip": s = Rot(180, 0, 0) * s                                  # upside down (lips up)
    b = s.bounding_box()
    return Pos(-b.min.X, -b.min.Y, -b.min.Z) * s

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
    lay, x = {}, 0.0
    for n, src, how in (("end_plate", pr["bracket_fl"], "x_face"), ("corner_grab", pr["foot_fl"], "flip"),
                        ("x_plate", pr["xplate_front"], "x_face"), ("dumb_plate", pr["dumb_plate"], "x_face_y")):
        f = flat(src if how != "x_face_y" else Rot(0, 90, 0) * src, "x_face" if how == "x_face" else ("flip" if how == "flip" else ""))
        b = f.bounding_box()
        lay[f"print_{n}"] = Pos(x, -MARGIN - 330, -TABLE_T) * f
        x += b.max.X - b.min.X + 40
    ghost = {"linnmon": box(0, RAIL_L, -MARGIN, END_L + MARGIN, -TABLE_T, 0),
             "enclosures": box(620, 960, 60, 500, F, 200)}
    return pr, bo, ghost, lay

# ------------------------------------------------------------------ checks
def bb(s): b = s.bounding_box(); return (b.min.X, b.min.Y, b.min.Z, b.max.X, b.max.Y, b.max.Z)

def checks(pr, bo, ghost, lay):
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
    kd = boxes["bracket_fl"][2] - boxes["foot_fl"][2]
    add("End plate sits in the foot's pocket", abs(boxes["bracket_fl"][2] - (F - KEY)) < 0.01, f"{KEY:.0f} mm deep, {KEY_CL} clearance per side, 0.3 below")
    add("1000 rails rest on the 560s", abs(RZ0 - (END_Z0 + PH)) < 1e-6, "an inner L-bracket can still be added later")
    low = min(boxes[n][2] for n in ("xplate_front", "motor_front"))
    add("X plate and motor clear the tabletop (≥ 8)", low >= 8, f"lowest {low:.1f} above the table; feet {F:.0f} tall")
    X_WHEEL = PW + WHEEL_OD / 2 + (BORE[0] - WHEEL_X[0]) + 1.0             # bottom wheel 1 mm off the 560
    X_PLATE = BRK_W + 1.0 + BORE[0]                                          # X plate 1 mm off the end plate
    X_MIN = max(X_WHEEL, X_PLATE)
    add("Left limit", True, f"bar at x ≈ {X_MIN:.0f}, set by the {'end plate' if X_PLATE > X_WHEEL else 'wheel on the 560'} (the wheel alone would allow {X_WHEEL:.0f})")
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
    for n, s in lay.items():
        x0, y0, z0, x1, y1, z1 = bb(s)
        g = s.volume * 1.27e-3 * 0.55
        add(f"{n[6:].replace('_', ' ')}: as printed", max(x1-x0, y1-y0, z1-z0) <= BED, f"{x1-x0:.0f} × {y1-y0:.0f} × {z1-z0:.0f} on the bed, ≈ {g:.0f} g each")
    return res

def main():
    pr, bo, ghost, lay = assembly()
    res = checks(pr, bo, ghost, lay)
    for r in res: print("PASS" if r["ok"] else "FAIL", r["name"], "·", r["detail"])
    if "--print" in sys.argv:                                                  # print files, laid flat, quantity in the name
        d = OUT / "print"; d.mkdir(parents=True, exist_ok=True)
        for n, src, how in (("etch_end_plate_x4", "bracket_fl", "x_face"), ("etch_corner_grab_A_x2", "foot_fl", "flip"),
                            ("etch_corner_grab_B_x2", "foot_fr", "flip"), ("etch_x_plate_x2", "xplate_front", "x_face")):
            export_stl(flat(pr[src], how), str(d / f"{n}.stl"), tolerance=0.02, angular_tolerance=0.1)
        blk, key = fit_coupon()
        export_stl(blk + key, str(d / "etch_fit_test_key_pocket_x1.stl"), tolerance=0.02, angular_tolerance=0.1)
        print("wrote", d)
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
    for n, s in lay.items():
        export_stl(s, str(OUT / f"{n}.stl"), tolerance=0.05)
        parts.append(dict(name=n, group="prints", explode=[0, 0, 0]))
    for n, s in ghost.items():
        export_stl(s, str(OUT / f"{n}.stl"), tolerance=0.5)
        parts.append(dict(name=n, group="ghost", explode=[0, 0, -40 if n == "linnmon" else 0]))
    summary = dict(title="Etch frame · CAD run 5", up="z", q=25,
        sub=f"1000 × 560 frame on the LINNMON · 1000s rest on the 560s · 11 PETG prints, ≈ {grams:.0f} g at ~55% fill",
        size=[RAIL_L, END_L, BAR_ZC + 20],
        groups={"printed": {"label": "PETG prints", "note": "4 end plates, 4 corner grabs (placeholder), 2 X plates, 1 dumb plate", "color": "#3f4544", "grams": round(grams)},
                "frame": {"label": "2040 frame + 2020 bar", "color": "#b9c2bf"},
                "motion": {"label": "Motors, wheels, Y carriage", "color": "#6fb3e0"},
                "prints": {"label": "Print layout (one of each, as it sits on the bed)", "color": "#e07b39"},
                "ghost": {"label": "LINNMON + enclosures", "color": "#c8955a", "ghost": True}},
        parts=parts, checks=res,
        cards=[{"title": "How it goes together", "html": "<ul>"
                f"<li><b>End plate</b>: one flat 6 mm plate per corner on the outer face. A {COL:.0f} mm column covers the 560's end (2 M5 into its tapped end), and an arm runs {BRK_W:.0f} mm along the rail (4 M5 into drop-in nuts, two per slot), with a 45° chamfer between them. It prints flat.</li>"
                "<li>The 1000 rests on the 560. The end plate ties them together.</li>"
                f"<li><b>Corner grab</b>: a pad with lips halfway down the edge and end. The end plate's column drops {KEY:.0f} mm into a closed pocket in its top ({COL + 2*KEY_CL:.1f} × {BT + 2*KEY_CL:.1f}), which locates it both ways with no hardware. Lift the frame and the feet come away. If you ever want it to hold down, add one M5 up through the pad into a T-nut in the 560.</li>"
                "<li>The X plates ride outside the rails and stop 1 mm short of the end plate.</li>"
                "<li>Orange row in front: one of each print, as it sits on the bed.</li></ul>"},
               {"title": "Placeholders", "html": f"<ul><li>LINNMON thickness {TABLE_T:.0f} (measure at print time)</li><li>Wheel Ø{WHEEL_OD} × {WHEEL_W}, spacer {SPACER:.0f} (catalogue)</li><li>Dumb plate {DUMB[0]:.0f} × {DUMB[1]:.0f}, Y carriage 65.5 square stand-in</li><li>Grams: volume × 1.27 × 0.55, rough</li></ul>"}])
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1))
    print("wrote", OUT)

if __name__ == "__main__":
    main()
