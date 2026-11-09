"""Etch frame lo-fi v3: ACRO-style frame on the 1000 rails, PETG end plates with snap-on feet.

Allwin's 2026-11-09 sketches: two 1000 rails (2040, standing) rest on two 560 ends (2040, standing) at the left
and right; one PETG end plate per rail end bolts to the rail end and the 560 below it, and sits in a broader foot
(a second print, snap fit). Allwin's ACRO acrylic gantry plates ride outside the 1000 rails, stepper at the bottom,
and carry the cross bar (his 700 mm 2020). A plain PETG plate rides the bar on the Y carriage for now.

Gantry plate geometry is traced from Allwin's ACRO STL (acrylic/acro_traced.json, git-ignored like the STL).
Every other number is in the GEOMETRY block; PLACEHOLDER marks a guess.

    python3 hardware/gantry/frame_lofi.py OUT.html
"""
import json, math, pathlib, sys
from shapely.geometry import Polygon as SPoly, box as sbox
from shapely.ops import unary_union

HERE = pathlib.Path(__file__).resolve().parent
CSS = pathlib.Path(sys.argv[2]).read_text() if len(sys.argv) > 2 else ""
OUT = pathlib.Path(sys.argv[1])
ACRO = {q["key"]: q for q in json.loads((HERE / "acrylic" / "acro_traced.json").read_text())}

# ------------------------------------------------------------------ GEOMETRY (mm; x along the 1000s from the left end, y from the front face inward, z up from the tabletop)
RAIL_L, END_L = 1000.0, 560.0
PW, PH = 20.0, 40.0                 # 2040 standing: 20 wide, 40 tall
BAR = 20.0                          # cross bar 2020 (Allwin's 700, to be cut)
F = 15.0                            # foot height = ride height of the frame       PLACEHOLDER (sets the clearance below)
EP_T = 6.0                          # end plate, PETG
EP_Y0, EP_Y1 = -6.0, 60.0           # end plate footprint across the rail (y), at the foot
EP_TOP = 88.0                       # end plate top, above the frame's underside
TONGUE = (6.0, 46.0, 8.0)           # tongue on the plate's bottom edge: y0, y1, depth into the foot
FOOT_X, FOOT_Y = (-9.0, 51.0), (-18.0, 72.0)   # x: inward under the 560, so only the plate overhangs the 1000 top
WHEEL_OD, WHEEL_W, SPACER = 24.4, 10.2, 6.0   # OpenBuilds solid V wheel + spacer   PLACEHOLDER (catalogue, not measured)
NEMA, NEMA_L = 42.3, 34.0           # Ender-3 42-34
STOP_X = (500.0, 600.0)             # where the bar stops (Allwin moves it around)
BAR_AT = 300.0                      # bar position drawn
CAR = 65.5                          # OpenBuilds 3-wheel plate on the bar (Y carriage)
DUMB = (80.0, 100.0, 6.0)           # dumb PETG plate on the carriage: w, h, t       PLACEHOLDER

g = ACRO["gantry"]
FIX_Y, SLOT_Y, BORE, BAR_BORE_PY = 101.05, 41.8, (46.94, 25.05), 115.74   # read off the traced plate (see acro_plates.gantry_layout)
RAIL_Z0 = F + PH                    # rails sit on the 560s
RAIL_MID = RAIL_Z0 + PH / 2
def pz(py): return RAIL_MID + py - (FIX_Y + SLOT_Y) / 2          # gantry plate local y -> world z
Y_IN = PW / 2 - WHEEL_W / 2 - SPACER                              # plate inner face (y), front side
Y_OUT = Y_IN - 6.0
BAR_LEN = END_L - 2 * Y_IN
BAR_ZC = pz(BAR_BORE_PY)
PLATE_BOT = pz(0.0)
MOTOR_BOT = pz(BORE[1] - NEMA / 2)
WHEEL_LOW = pz(SLOT_Y) - WHEEL_OD / 2
X_MIN_BAR = PW + WHEEL_OD / 2 + (BORE[0] - 11.94)                 # leading bottom wheel meets the left 560
PEN_DROP = BAR_ZC - BAR / 2                                        # bar underside to the tabletop

def ep_poly():
    """End plate outline in (y, z)."""
    core = SPoly([(EP_Y0, F), (EP_Y1, F), (EP_Y1, F + PH), (PW + 6, F + PH + 34), (PW + 6, F + EP_TOP), (EP_Y0, F + EP_TOP)])
    p = core.buffer(-4, join_style=1).buffer(4, join_style=1)
    return p.union(sbox(TONGUE[0], F - TONGUE[2], TONGUE[1], F + 1))
EP_HOLES = [(PW / 2, RAIL_Z0 + 10), (PW / 2, RAIL_Z0 + 30), (40.0, F + 10), (40.0, F + 30)]   # M5: 2 into the tapped rail end, 2 T-nuts in the 560

# ------------------------------------------------------------------ svg helpers
def pts(ps): return " ".join(f"{x:.2f},{y:.2f}" for x, y in ps)
def path_of(poly, T):
    out = []
    for ring in [poly.exterior] + list(poly.interiors):
        out.append("M " + " L ".join(f"{a:.2f},{b:.2f}" for a, b in map(T, ring.coords)) + " Z")
    return " ".join(out)
def loop_d(loop, T): return "M " + " L ".join(f"{a:.2f},{b:.2f}" for a, b in map(T, loop)) + " Z"
def R(T, x0, x1, z0, z1, cls, extra=""):
    (a, b), (c, d) = T((x0, z1)), T((x1, z0))
    return f'<rect class="{cls}" x="{min(a,c):.2f}" y="{min(b,d):.2f}" width="{abs(c-a):.2f}" height="{abs(d-b):.2f}" {extra}/>'
def TX(T, p, s, cls="lbl", anchor="start", extra=""):
    x, y = T(p); return f'<text class="{cls}" x="{x:.2f}" y="{y:.2f}" text-anchor="{anchor}" {extra}>{s}</text>'
def circ(T, p, r, cls, extra=""):
    x, y = T(p); return f'<circle class="{cls}" cx="{x:.2f}" cy="{y:.2f}" r="{r:.2f}" {extra}/>'
def dimh(T, a, b, z, s, off=-4):
    (x0, y), (x1, _) = T((a, z)), T((b, z))
    return (f'<line class="soft" x1="{x0:.2f}" y1="{y:.2f}" x2="{x1:.2f}" y2="{y:.2f}"/>'
            f'<line class="soft" x1="{x0:.2f}" y1="{y-3:.2f}" x2="{x0:.2f}" y2="{y+3:.2f}"/><line class="soft" x1="{x1:.2f}" y1="{y-3:.2f}" x2="{x1:.2f}" y2="{y+3:.2f}"/>'
            f'<text class="dim" x="{(x0+x1)/2:.2f}" y="{y+off:.2f}" text-anchor="middle">{s}</text>')
def dimv(T, x, a, b, s, side=1):
    (X, y0), (_, y1) = T((x, a)), T((x, b))
    return (f'<line class="soft" x1="{X:.2f}" y1="{y0:.2f}" x2="{X:.2f}" y2="{y1:.2f}"/>'
            f'<line class="soft" x1="{X-3:.2f}" y1="{y0:.2f}" x2="{X+3:.2f}" y2="{y0:.2f}"/><line class="soft" x1="{X-3:.2f}" y1="{y1:.2f}" x2="{X+3:.2f}" y2="{y1:.2f}"/>'
            f'<text class="dim" x="{X+5*side:.2f}" y="{(y0+y1)/2+3:.2f}" text-anchor="{"start" if side>0 else "end"}">{s}</text>')

# ------------------------------------------------------------------ view 1: front (x right, z up), the whole frame
def front_view():
    k = 1.0; X0, Z1 = -70.0, 250.0
    T = lambda p: ((p[0] - X0) * k, (Z1 - p[1]) * k)
    e = [f'<line class="bench" x1="0" y1="{T((0,0))[1]}" x2="{(1080-X0)*k}" y2="{T((0,0))[1]}"/>']
    e.append(R(T, STOP_X[0], 1000, 0, 0.1, "soft"))
    e.append(R(T, 620, 960, 0, 200, "dash", 'rx="4"'))
    e.append(TX(T, (790, 180), "ENCLOSURES (behind the rail)", "lbl", "middle"))
    e.append(R(T, STOP_X[0], STOP_X[1], 0, 230, "", 'fill="var(--accent)" opacity=".08"'))
    e.append(TX(T, (sum(STOP_X)/2, 222), "bar stops here (moves)", "dim acctext", "middle"))
    for x0 in (0.0, RAIL_L - PW):
        e.append(R(T, x0, x0 + PW, F, F + PH, "rail"))
    e.append(R(T, 0, RAIL_L, RAIL_Z0, RAIL_Z0 + PH, "rail"))
    for zz in (RAIL_Z0 + 10, RAIL_Z0 + 30):
        e.append(f'<line class="soft" x1="{T((0,zz))[0]}" y1="{T((0,zz))[1]}" x2="{T((RAIL_L,zz))[0]}" y2="{T((RAIL_L,zz))[1]}"/>')
    for xp, sg in ((-EP_T, -1), (RAIL_L, 1)):
        e.append(R(T, xp, xp + EP_T, F - TONGUE[2], F + EP_TOP, "plate", 'style="fill:var(--petg)"'))
        fx = (FOOT_X[0], FOOT_X[1]) if sg < 0 else (RAIL_L - FOOT_X[1], RAIL_L - FOOT_X[0])
        e.append(R(T, fx[0], fx[1], 0, F, "plate", 'style="fill:var(--petg2)"'))
    # gantry plate (traced), seen face-on from the front, with the motor behind the plate's outer face
    ox = BAR_AT - BORE[0]
    P = lambda q: T((ox + q[0], pz(q[1])))
    d = loop_d(g["outline"], P) + " " + " ".join(loop_d(h["pts"], P) for h in g["holes"])
    e.append(R(T, BAR_AT - NEMA/2, BAR_AT + NEMA/2, MOTOR_BOT, MOTOR_BOT + NEMA, "dash", 'rx="3"'))
    e.append(f'<path class="plate" fill-rule="evenodd" d="{d}" style="fill:var(--acrylic)"/>')
    for wx in (11.94, 81.94):
        for wy in (FIX_Y, SLOT_Y):
            e.append(circ(T, (ox + wx, pz(wy)), WHEEL_OD / 2 * k, "soft"))
    e.append(R(T, BAR_AT - BAR/2, BAR_AT + BAR/2, BAR_ZC - BAR/2, BAR_ZC + BAR/2, "rail", 'style="fill:var(--bar)"'))
    e.append(TX(T, (BAR_AT + 60, pz(120)), "ACRO gantry plate (your acrylic)", "lbl"))
    e.append(TX(T, (BAR_AT + 60, pz(105)), "2020 bar end-on, M5 through the slot", "dim"))
    e.append(TX(T, (BAR_AT + 60, pz(20)), "NEMA17 on the outside, at the bottom", "dim"))
    e.append(TX(T, (500, RAIL_Z0 + 16), "1000 RAIL · 2040 standing", "lblb", "middle"))
    e.append(TX(T, (10, F + 46 + 70), "END PLATE", "lblb", "start"))
    e.append(TX(T, (10, F + 46 + 58), "+ snap-on foot", "dim", "start"))
    e.append(TX(T, (10, F + 20), "560", "dim", "middle", 'transform="rotate(-90 {} {})"'.format(*T((10, F + 20)))))
    e.append(dimh(T, 0, RAIL_L, -18, "1000 rails · end plates and feet outside them", 14))
    e.append(dimv(T, 1030, 0, F, f"{F:.0f} foot*"))
    e.append(dimv(T, 1030, F, RAIL_Z0, "40"))
    e.append(dimv(T, 1030, RAIL_Z0, RAIL_Z0 + PH, "40"))
    e.append(dimh(T, 0, X_MIN_BAR, pz(150), f"{X_MIN_BAR:.0f}*", -5))
    e.append(TX(T, (X_MIN_BAR + 4, pz(150) + 4), "bar can't go further left: its bottom wheel meets the 560", "dim"))
    W, H = (1080 - X0) * k, (Z1 + 34) * k
    return f'<svg class="v" style="--fs:12px" viewBox="0 0 {W:.0f} {H:.0f}" role="img" aria-label="Front view of the frame">{"".join(e)}</svg>'

# ------------------------------------------------------------------ view 2: section across the frame at the bar (y right, z up), looking from the left
def section_view():
    k = 1.0; Y0, Z1 = -110.0, 220.0  # view spans y -110..760
    T = lambda p: ((p[0] - Y0) * k, (Z1 - p[1]) * k)
    e = [f'<line class="bench" x1="0" y1="{T((0,0))[1]}" x2="{(680-Y0)*k}" y2="{T((0,0))[1]}"/>']
    e.append(TX(T, (-105, -14), "◀ FRONT (you)", "dim"))
    e.append(TX(T, (700, -14), "BACK ▶", "dim", "end"))
    # the 560 (beyond, dashed) and the rails end-on
    e.append(R(T, 0, END_L, F, F + PH, "dash"))
    e.append(TX(T, (END_L/2 - 120, F + 14), "left 560 beyond (dashed)", "dim", "middle"))
    for y0 in (0.0, END_L - PW):
        e.append(R(T, y0, y0 + PW, RAIL_Z0, RAIL_Z0 + PH, "rail"))
    # gantry plates edge-on, wheels, motors
    r = WHEEL_OD / 2
    for sg in (1, -1):
        yi = Y_IN if sg > 0 else END_L - Y_IN
        yo = Y_OUT if sg > 0 else END_L - Y_OUT
        e.append(R(T, min(yi, yo), max(yi, yo), pz(0), pz(g["size"][1]), "plate", 'style="fill:var(--acrylic)"'))
        ym = yo - sg * NEMA_L
        e.append(R(T, min(yo, ym), max(yo, ym), MOTOR_BOT, MOTOR_BOT + NEMA, "plate", 'style="fill:var(--steel)"'))
        yc = PW/2 if sg > 0 else END_L - PW/2
        for wy in (FIX_Y, SLOT_Y):
            e.append(R(T, yc - WHEEL_W/2, yc + WHEEL_W/2, pz(wy) - r, pz(wy) + r, "", 'rx="3" fill="var(--ink)" opacity=".7"'))
    e.append(R(T, Y_IN, END_L - Y_IN, BAR_ZC - BAR/2, BAR_ZC + BAR/2, "rail", 'style="fill:var(--bar)"'))
    # Y carriage + dumb plate
    yc = END_L / 2
    e.append(R(T, yc - CAR/2, yc + CAR/2, BAR_ZC - CAR/2 + 4, BAR_ZC + CAR/2 + 4, "plate", 'style="fill:var(--steel)" opacity=".85"'))
    e.append(R(T, yc - DUMB[0]/2, yc + DUMB[0]/2, BAR_ZC + 10 - DUMB[1], BAR_ZC + 10, "plate", 'style="fill:var(--petg)" opacity=".9"'))
    e.append(TX(T, (yc + DUMB[0]/2 + 6, BAR_ZC - 50), "DUMB PLATE (PETG)", "lblb"))
    e.append(TX(T, (yc + DUMB[0]/2 + 6, BAR_ZC - 62), "on the OpenBuilds Y carriage", "dim"))
    e.append(TX(T, (yc + 50, BAR_ZC + 14), f"2020 bar ≈ {BAR_LEN:.0f}* (your 700, cut)", "lbl"))
    e.append(TX(T, (-104, MOTOR_BOT + NEMA + 6), "NEMA17", "dim"))
    e.append(TX(T, (-104, pz(g["size"][1]) + 6), "ACRO plate outside the rail", "dim"))
    e.append(dimv(T, 640, 0, BAR_ZC - BAR/2, f"{PEN_DROP:.0f}* table to bar"))
    e.append(TX(T, (-104, -30), f"plate bottom {PLATE_BOT:.1f}* above the table · motor {MOTOR_BOT:.1f}* · feet {F:.0f}*", "dim"))
    e.append(dimh(T, Y_OUT - NEMA_L, END_L - Y_OUT + NEMA_L, 196, f"{END_L - 2*Y_OUT + 2*NEMA_L:.0f}* over the motors (560 frame)", -5))
    W, H = (760 - Y0) * k, (Z1 + 40) * k
    return f'<svg class="v" style="--fs:11px" viewBox="0 0 {W:.0f} {H:.0f}" role="img" aria-label="Section across the frame at the bar">{"".join(e)}</svg>'

# ------------------------------------------------------------------ view 3: end plate + foot detail (y right, z up), seen from outside the left end
def endplate_view():
    k = 2.2; Y0, Z1 = -40.0, F + EP_TOP + 14
    T = lambda p: ((p[0] - Y0) * k, (Z1 - p[1]) * k)
    e = [f'<line class="bench" x1="0" y1="{T((0,0))[1]}" x2="{(175-Y0)*k:.1f}" y2="{T((0,0))[1]}"/>']
    e.append(R(T, 0, 90, F, F + PH, "dash"))
    for hy, hz in EP_HOLES:
        xa, ya = T((hy + 4, hz)); xb, _ = T((96, hz))
        e.append(f'<line class="soft" x1="{xa:.1f}" y1="{ya:.1f}" x2="{xb:.1f}" y2="{ya:.1f}"/>')
    e.append(R(T, 0, PW, RAIL_Z0, RAIL_Z0 + PH, "dash"))
    p = ep_poly()
    for hy, hz in EP_HOLES: p = p.difference(sbox(hy - 2.75, hz - 2.75, hy + 2.75, hz + 2.75).buffer(0.01).envelope.buffer(0))
    e.append(f'<path class="plate" fill-rule="evenodd" style="fill:var(--petg)" d="{path_of(ep_poly(), T)}"/>')
    for hy, hz in EP_HOLES: e.append(circ(T, (hy, hz), 2.75 * k, "", 'fill="var(--sheet)" stroke="var(--ink)" stroke-width=".8"'))
    # foot, sectioned at the tongue
    fy = FOOT_Y
    e.append(R(T, fy[0], fy[1], 0, F, "plate", 'style="fill:var(--petg2)" opacity=".85"'))
    e.append(R(T, TONGUE[0] - .2, TONGUE[1] + .2, F - TONGUE[2] - .3, F, "", 'fill="var(--sheet)" stroke="var(--ink)" stroke-width=".6"'))
    e.append(R(T, TONGUE[0], TONGUE[1], F - TONGUE[2], F, "", 'fill="var(--petg)" stroke="var(--ink)" stroke-width=".6"'))
    for yy, sg in ((TONGUE[0], -1), (TONGUE[1], 1)):    # snap barbs
        a = [(yy, F - TONGUE[2] + 1), (yy + sg * 1.4, F - TONGUE[2] + 3.5), (yy, F - TONGUE[2] + 5)]
        e.append(f'<polygon points="{pts(map(T, a))}" fill="var(--accent)"/>')
    e.append(TX(T, (98, RAIL_Z0 + 22), "M5 × 2, rail end", "dim"))
    e.append(TX(T, (98, RAIL_Z0 + 16), "(tapped)", "dim"))
    e.append(TX(T, (98, F + 22), "M5 + T-nut × 2", "dim"))
    e.append(TX(T, (98, F + 16), "into the 560", "dim"))
    e.append(TX(T, (98, F + 46), "dashed = rail", "dim"))
    e.append(TX(T, (98, F + 40), "+ 560 behind", "dim"))
    e.append(TX(T, (98, 9), "FOOT", "lblb"))
    e.append(TX(T, (98, 2), "snaps on", "dim"))
    e.append(dimh(T, EP_Y0, EP_Y1, F + EP_TOP + 6, f"{EP_Y1-EP_Y0:.0f}", -4))
    e.append(dimh(T, fy[0], fy[1], -8, f"foot {fy[1]-fy[0]:.0f} × {FOOT_X[1]-FOOT_X[0]:.0f}*", 12))
    e.append(dimv(T, -30, F, F + EP_TOP, f"{EP_TOP:.0f}", -1))
    W, H = (175 - Y0) * k, (Z1 + 22) * k
    return f'<svg class="v" style="--fs:12px" viewBox="0 0 {W:.0f} {H:.0f}" role="img" aria-label="End plate and foot">{"".join(e)}</svg>'

# ------------------------------------------------------------------ view 4: plan (x right, y up the page = away from you)
def plan_view():
    k = 0.62; X0, Y1 = -70.0, 640.0
    T = lambda p: ((p[0] - X0) * k, (Y1 - p[1]) * k)
    e = []
    e.append(R(T, 0, 1000, -20, 580, "", 'style="fill:var(--deck)" opacity=".35"'))
    e.append(R(T, STOP_X[0], STOP_X[1], -20, 580, "", 'fill="var(--accent)" opacity=".10"'))
    e.append(R(T, 620, 960, 60, 500, "dash", 'rx="4"'))
    e.append(TX(T, (790, 280), "ENCLOSURES", "lblb", "middle"))
    for y0 in (0.0, END_L - PW): e.append(R(T, 0, RAIL_L, y0, y0 + PW, "rail"))
    for x0 in (0.0, RAIL_L - PW): e.append(R(T, x0, x0 + PW, 0, END_L, "rail"))
    for xs, ys in ((-1, 1), (1, 1), (-1, -1), (1, -1)):
        x = (-EP_T, 0) if xs < 0 else (RAIL_L, RAIL_L + EP_T)
        fx = FOOT_X if xs < 0 else (RAIL_L - FOOT_X[1], RAIL_L - FOOT_X[0])
        fy = FOOT_Y if ys > 0 else (END_L - FOOT_Y[1], END_L - FOOT_Y[0])
        ey = (EP_Y0, EP_Y1) if ys > 0 else (END_L - EP_Y1, END_L - EP_Y0)
        e.append(R(T, fx[0], fx[1], fy[0], fy[1], "plate", 'style="fill:var(--petg2)" opacity=".8"'))
        e.append(R(T, x[0], x[1], ey[0], ey[1], "plate", 'style="fill:var(--petg)"'))
    for sg in (1, -1):
        yo = Y_OUT if sg > 0 else END_L - Y_OUT
        yi = Y_IN if sg > 0 else END_L - Y_IN
        e.append(R(T, BAR_AT - BORE[0], BAR_AT - BORE[0] + g["size"][0], min(yi, yo), max(yi, yo), "plate", 'style="fill:var(--acrylic)"'))
        ym = yo - sg * NEMA_L
        e.append(R(T, BAR_AT - NEMA/2, BAR_AT + NEMA/2, min(yo, ym), max(yo, ym), "plate", 'style="fill:var(--steel)"'))
    e.append(R(T, BAR_AT - BAR/2, BAR_AT + BAR/2, Y_IN, END_L - Y_IN, "rail", 'style="fill:var(--bar)"'))
    e.append(R(T, BAR_AT + BAR/2 + 2, BAR_AT + BAR/2 + 10, END_L/2 - DUMB[0]/2, END_L/2 + DUMB[0]/2, "plate", 'style="fill:var(--petg)"'))
    e.append(TX(T, (sum(STOP_X)/2, 600), "stop range", "dim acctext", "middle"))
    e.append(TX(T, (BAR_AT, -70), "FRONT (you)", "lblb", "middle"))
    e.append(TX(T, (-60, 610), "LINNMON 1000 × 600", "dim"))
    W, H = (1080 - X0) * k, (Y1 + 110) * k
    return f'<svg class="v" style="--fs:9px" viewBox="0 0 {W:.0f} {H:.0f}" role="img" aria-label="Plan of the frame on the table">{"".join(e)}</svg>'

EXTRA = """
:root { --petg: #3b3f3e; --petg2: #5a605e; --acrylic: rgba(120,170,210,.45); --bar: #c9b28a; --deck: #e0c79c; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --petg: #8b9592; --petg2: #6b7572; --acrylic: rgba(111,179,224,.35); --bar: #8a7752; --deck: #5a4a2e; } }
:root[data-theme="dark"] { --petg: #8b9592; --petg2: #6b7572; --acrylic: rgba(111,179,224,.35); --bar: #8a7752; --deck: #5a4a2e; }
.views2 { grid-template-columns: minmax(0, 1fr) minmax(0, 1.9fr); }
.views2 svg.v { min-width: 0; }
svg.v * { vector-effect: non-scaling-stroke; }
svg.v text { font-size: var(--fs); }
svg.v .dim { font-size: calc(var(--fs) * .92); }
svg.v .lblb { font-size: calc(var(--fs) * 1.2); }
svg.v .plate { stroke-width: 1; } svg.v .rail { stroke-width: 1; } svg.v .soft { stroke-width: .8; } svg.v .dash { stroke-width: 1; }
"""

def page():
    over = END_L - 2 * Y_OUT + 2 * NEMA_L
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Etch Gantry Lofi</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@700&family=IBM+Plex+Mono&family=IBM+Plex+Sans:wght@400;600&display=swap">
<style>{CSS}{EXTRA}</style></head><body>
<div class="wrap">
<header class="title">
  <div>
    <h1>Etch frame · lo-fi v3</h1>
    <p>The ACRO layout on your frame. The two 1000 rails rest on the two 560s. Each rail end gets a PETG end plate, bolted to the rail end and to the 560 below it, and each end plate stands in a broader foot that snaps on. Your acrylic ACRO gantry plates ride outside the 1000 rails with the steppers at the bottom and carry the 2020 bar. A plain PETG plate rides the bar for now.</p>
  </div>
  <div class="tblock">
    <div><span>Room</span> <b>R04 Etch</b></div>
    <div><span>Date</span> <b>2026-11-09</b></div>
    <div><span>Frame</span> <b>1000 × 560 · 2040</b></div>
    <div><span>Prints</span> <b>4 end plates · 4 feet · 1 plate</b></div>
    <div><span>Status</span> <b>sketch · inspector after go</b></div>
  </div>
</header>

<div class="view">
  <h2>Front view</h2>
  <p class="sub">To scale, from where you sit. Grey = 2040, dark = PETG prints, blue = your acrylic ACRO plate, tan = the 2020 bar end-on. * = rests on catalogue sizes (wheels, spacers) or a placeholder.</p>
  <div class="svgbox">{front_view()}</div>
</div>

<div class="views2">
  <div class="view">
    <h2>End plate + foot</h2>
    <p class="sub">From outside the left end, front corner. Two M5 go into the tapped rail end and two M5 with T-nuts into the 560. The plate's tongue drops into the foot, and two barbs (blue) click under the foot's ledge.</p>
    <div class="svgbox">{endplate_view()}</div>
  </div>
  <div class="view">
    <h2>Section at the bar</h2>
    <p class="sub">Looking from the left. The plates' bottom wheels run under the rails, so the rails have to sit up on the 560s. That's why your layout works.</p>
    <div class="svgbox">{section_view()}</div>
  </div>
</div>

<div class="view">
  <h2>Plan on the table</h2>
  <p class="sub">Bar drawn at x {BAR_AT:.0f}. The steppers stick out front and back, outside the 560 frame.</p>
  <div class="svgbox">{plan_view()}</div>
</div>

<div class="notes">
  <section>
    <h2>What the sketch says</h2>
    <ul>
      <li><b>End plates go on the 1000 side:</b> each one caps a rail end and bolts to the 560 below it. That's 4 plates, 4 × M5 each (stock M5).</li>
      <li><b>The feet set the ride height.</b> The ACRO plate hangs {abs(PLATE_BOT - F):.0f}* below the frame's underside and the motor {abs(MOTOR_BOT - F):.0f}*. With {F:.0f} mm feet the plate clears the table by {PLATE_BOT:.1f}*. The feet aren't just broader, they have to be at least about 14 mm tall.</li>
      <li><b>The 700 bar is too long:</b> between the two plates' inner faces it's ≈ {BAR_LEN:.0f}*. Cut your 700 or buy a new one. Neither needs anything else to change.</li>
      <li><b>Left limit:</b> the bar can't get closer than ≈ {X_MIN_BAR:.0f}* to the left end, because the plate's bottom wheel meets the 560. The right side is the stop, wherever you set it.</li>
      <li><b>Front to back over the motors:</b> ≈ {over:.0f}* on a 600 table, so they hang ≈ {(over - 600)/2:.0f}* past the edges if the frame is centred.</li>
      <li><b>Pen drop:</b> the bar's underside is ≈ {PEN_DROP:.0f}* above the table. The Y carriage redesign has to reach down that far.</li>
    </ul>
  </section>
  <section>
    <h2>Need your call</h2>
    <ol class="q">
      <li><b>Motors past the table edge:</b> the motors hang ≈ {(over - 600)/2:.0f}* past the front and back edges. OK? They can't go inside the plate: there they'd hit the bottom wheels. The wall behind needs the same room.</li>
      <li><b>Ends:</b> the end plates make the frame {RAIL_L + 2*EP_T:.0f} long, so they stand {EP_T:.0f} past each end of the 1000 top. The feet reach inward under the 560s, not outward. Is that OK?</li>
      <li><b>Feet:</b> {F:.0f} mm tall, {FOOT_Y[1]-FOOT_Y[0]:.0f} × {FOOT_X[1]-FOOT_X[0]:.0f} footprint, plain PETG. Do you want rubber pads or screws into the table?</li>
      <li><b>Rail ends:</b> are your 1000s tapped at the ends (M5)? If not, the plate takes T-nuts in the rail's side slots instead.</li>
      <li><b>Bar:</b> cut the 700 to ≈ {BAR_LEN:.0f}, or buy a new one?</li>
      <li><b>Y carriage:</b> is the dumb plate going on your OpenBuilds 65.5 plate (3 wheels on the 2020)?</li>
    </ol>
    <p>Say go, and the inspector comes next.</p>
    <p class="unv">Placeholders: foot {F:.0f}, wheel Ø{WHEEL_OD} × {WHEEL_W}, spacer {SPACER:.0f}, dumb plate {DUMB[0]:.0f} × {DUMB[1]:.0f}. The ACRO plate holes are traced from your STL.</p>
  </section>
</div>
</div></body></html>"""

OUT.write_text(page())
print(f"ok  plate bottom {PLATE_BOT:.1f}  motor bottom {MOTOR_BOT:.1f}  wheel low {WHEEL_LOW:.1f}  bar {BAR_LEN:.1f} at z {BAR_ZC:.1f}  x_min {X_MIN_BAR:.1f}")
