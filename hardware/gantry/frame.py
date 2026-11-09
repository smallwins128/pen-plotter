"""Etch frame CAD run 3: ACRO-style frame on the LINNMON; wrap-round end brackets and separate corner grabs.

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
# bracket (one print per corner): an outer plate on the 560's tapped end and the rail's outer face (x 0..BRK_W, as wide
# as the 560, so it costs no travel), a bridge over the rail's end (no wheel ever reaches x < 21), and an arm along
# the rail's inner face with a 45° gusset down to a pad on the 560's inner face. Prints upright, no supports.
BT, BRK_W = 6.0, 20.0
ARM_L = 66.0                        # arm along the inner face; the gusset meets it at 45°
PAD_W = 34.0                        # pad on the 560's inner face, across y
FIL = 6.0                           # inside fillets
# corner grab (separate print): a pad under the 560's end and the bracket, lips halfway down the LINNMON's edge and end
LIP_T = 4.0
LIP = TABLE_T / 2
FOOT_X0 = -LIP_T
FOOT_YF = -MARGIN - LIP_T
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
    yi = PW                                                                   # rail's inner face
    outer = prism_xz(sbox(0, F, BRK_W, RZ0 + PH).buffer(-2, join_style=1).buffer(2, join_style=1), -BT, BT)
    bridge = box(0, BRK_W, -BT, yi + BT, RZ0 + PH, RZ0 + PH + BT)
    prof = sbox(0, RZ0, ARM_L, RZ0 + PH).union(SPoly([(PW, F), (PW + BT, F), (ARM_L, RZ0), (PW, RZ0)]))
    prof = prof.difference(sbox(-1, F - 1, PW + 0.01, RZ0))                  # the 560 sits under the rail here
    prof = prof.buffer(-FIL / 2, join_style=1).buffer(FIL / 2, join_style=1).union(sbox(0, RZ0, PW + 1, RZ0 + PH))
    arm = prism_xz(prof, yi, BT)
    pad = box(PW, PW + BT, yi, yi + BT + PAD_W, F, RZ0)
    s = outer + bridge + arm + pad
    for z in (F + 10, F + 30, RZ0 + 10, RZ0 + 30): s = hole_y(s, BRK_W / 2, z, -BT, 0)       # 560 end (tapped) + rail outer slots
    for x, z in ((12, RZ0 + 30), (36, RZ0 + 10), (56, RZ0 + 30)): s = hole_y(s, x, z, yi, yi + BT)   # rail inner slots
    for z in (F + 10, F + 30): s = hole_x(s, yi + BT + PAD_W / 2 + 2, z, PW, PW + BT)              # 560 inner slots
    return s

def foot():
    s = box(FOOT_X0, BRK_W, FOOT_YF, 0, 0, F)                                  # outboard of the rail: only to x 20, the X plate passes beyond
    s += box(FOOT_X0, PW + BT + 4, 0, PW + BT + PAD_W + 4, 0, F)                 # under the 560 and the bracket's pad
    s += box(FOOT_X0, 0, FOOT_YF, PW + BT + PAD_W + 4, -LIP, 0)                # lip down the table's end
    s += box(FOOT_X0, BRK_W, FOOT_YF, -MARGIN, -LIP, 0)                        # lip down the table's front edge
    s += box(FOOT_X0, 0, FOOT_YF, PW + BT + PAD_W + 4, F, F + 6)               # low stop on the outer end: the 560 and bracket butt against it
    return s

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
    for n, src, how in (("bracket", pr["bracket_fl"], "upright"), ("corner_grab", pr["foot_fl"], "flip"),
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
    for n, s in lay.items():
        x0, y0, z0, x1, y1, z1 = bb(s)
        g = s.volume * 1.27e-3 * 0.55
        add(f"{n[6:].replace('_', ' ')}: as printed", max(x1-x0, y1-y0, z1-z0) <= BED, f"{x1-x0:.0f} × {y1-y0:.0f} × {z1-z0:.0f} on the bed, ≈ {g:.0f} g each")
    return res

def main():
    pr, bo, ghost, lay = assembly()
    res = checks(pr, bo, ghost, lay)
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
    for n, s in lay.items():
        export_stl(s, str(OUT / f"{n}.stl"), tolerance=0.05)
        parts.append(dict(name=n, group="prints", explode=[0, 0, 0]))
    for n, s in ghost.items():
        export_stl(s, str(OUT / f"{n}.stl"), tolerance=0.5)
        parts.append(dict(name=n, group="ghost", explode=[0, 0, -40 if n == "linnmon" else 0]))
    summary = dict(title="Etch frame · CAD run 3", up="z", q=25,
        sub=f"1000 × 560 frame on the LINNMON · 1000s rest on the 560s · 11 PETG prints, ≈ {grams:.0f} g at ~55% fill",
        size=[RAIL_L, END_L, BAR_ZC + 20],
        groups={"printed": {"label": "PETG prints", "note": "4 end brackets, 4 corner grabs, 2 X plates, 1 dumb plate (mirrored pairs)", "color": "#3f4544", "grams": round(grams)},
                "frame": {"label": "2040 frame + 2020 bar", "color": "#b9c2bf"},
                "motion": {"label": "Motors, wheels, Y carriage", "color": "#6fb3e0"},
                "prints": {"label": "Print layout (one of each, as it sits on the bed)", "color": "#e07b39"},
                "ghost": {"label": "LINNMON + enclosures", "color": "#c8955a", "ghost": True}},
        parts=parts, checks=res,
        cards=[{"title": "How it goes together", "html": "<ul>"
                "<li><b>Corner grab</b> (its own print): a 20 mm pad under the 560's end and the bracket, lips halfway down the LINNMON's end and edge, and a low stop at the outer end. How it locks to the bracket is still open.</li>"
                "<li><b>End bracket</b> wraps the rail's end: an outer plate (2 M5 into the 560's tapped end, 2 into the rail's outer slots), a bridge over the rail, an arm along the inner face (3 M5 + drop-in nuts) with a 45° gusset down to a pad on the 560's inner face (2 M5 + T-nuts). That's 9 M5, so use what you need.</li>"
                "<li>The outer plate is only as wide as the 560. Everything else sits inboard, so it costs no travel: the X plate's wheel meets the 560 at x ≈ 68 either way.</li>"
                "<li>The bracket prints upright with no supports: walls vertical, the gusset at 45°, a 20 mm bridge over the rail.</li>"
                "<li>Orange row in front: one of each print, as it sits on the bed.</li></ul>"},
               {"title": "Placeholders", "html": f"<ul><li>LINNMON thickness {TABLE_T:.0f} (measure at print time)</li><li>Wheel Ø{WHEEL_OD} × {WHEEL_W}, spacer {SPACER:.0f} (catalogue)</li><li>Dumb plate {DUMB[0]:.0f} × {DUMB[1]:.0f}, Y carriage 65.5 square stand-in</li><li>Grams: volume × 1.27 × 0.55, rough</li></ul>"}])
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1))
    print("wrote", OUT)

if __name__ == "__main__":
    main()
