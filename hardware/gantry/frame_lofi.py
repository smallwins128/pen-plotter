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
BAR = 20.0                          # cross bar 2020: Allwin's 700, uncut, passing through both X plates
BAR_LEN = 700.0
GAP = 28.0                          # rail lifted this far above the 560 so the bottom wheels pass over it
F = 15.0                            # foot height = ride height of the frame       PLACEHOLDER (sets the clearance below)
EP_T = 6.0                          # end plate, PETG
EP_Y0, EP_Y1 = -6.0, 60.0           # end plate footprint across the rail (y), at the foot
EP_TOP = PH + GAP + PH + 8.0         # end plate top, above the frame's underside
TONGUE = (6.0, 46.0, 8.0)           # tongue on the plate's bottom edge: y0, y1, depth into the foot
FOOT_X, FOOT_Y = (-10.0, 51.0), (-24.0, 72.0)  # corner cap: x from past the table end, y from past the table's front edge
MARGIN = 20.0                       # frame face to the table edge, front and back (600 - 560) / 2
SKIRT, SKIRT_T = 20.0, 4.0           # corner cap lips down the table's edge and end           PLACEHOLDER
TABLE_T = 34.0                      # LINNMON top thickness                                    PLACEHOLDER (measure)
XP_T = 8.0                          # PETG X plate (ACRO outline), thicker than the 6 mm acrylic  PLACEHOLDER
COLLAR = 20.0                       # sleeve on the X plate's inner face round the bar
WHEEL_OD, WHEEL_W, SPACER = 24.4, 10.2, 6.0   # OpenBuilds solid V wheel + spacer   PLACEHOLDER (catalogue, not measured)
NEMA, NEMA_L = 42.3, 34.0           # Ender-3 42-34
STOP_X = (500.0, 600.0)             # where the bar stops (Allwin moves it around)
BAR_AT = 300.0                      # bar position drawn
CAR = 65.5                          # OpenBuilds 3-wheel plate on the bar (Y carriage)
DUMB = (80.0, 100.0, 6.0)           # dumb PETG plate on the carriage: w, h, t       PLACEHOLDER

g = ACRO["gantry"]
FIX_Y, SLOT_Y, BORE, BAR_BORE_PY = 101.05, 41.8, (46.94, 25.05), 115.74   # read off the traced plate (see acro_plates.gantry_layout)
RAIL_Z0 = F + PH + GAP              # rails held by the end plates, clear of the 560s
RAIL_MID = RAIL_Z0 + PH / 2
def pz(py): return RAIL_MID + py - (FIX_Y + SLOT_Y) / 2          # gantry plate local y -> world z
Y_IN = PW / 2 - WHEEL_W / 2 - SPACER                              # plate inner face (y), front side
Y_OUT = Y_IN - XP_T
BAR_Y0 = (END_L - BAR_LEN) / 2
BAR_ZC = pz(BAR_BORE_PY)
PLATE_BOT = pz(0.0)
MOTOR_BOT = pz(BORE[1] - NEMA / 2)
WHEEL_LOW = pz(SLOT_Y) - WHEEL_OD / 2
X_MIN_BAR = WHEEL_OD / 2 + (BORE[0] - 11.94) + 1.0               # leading wheel meets the end plate (wheels now pass over the 560)
X_MIN_OLD = PW + WHEEL_OD / 2 + (BORE[0] - 11.94)

PEN_DROP = BAR_ZC - BAR / 2                                        # bar underside to the tabletop
WHEEL_OVER_560 = WHEEL_LOW - (F + PH)                              # must be > 0

def ep_poly():
    """End plate outline in (y, z)."""
    core = SPoly([(EP_Y0, F), (EP_Y1, F), (EP_Y1, F + PH + 4), (PW + 8, RAIL_Z0 + 6), (PW + 8, F + EP_TOP), (EP_Y0, F + EP_TOP)])
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
    e = [R(T, 0, RAIL_L, -TABLE_T, 0, "", 'style="fill:var(--deck)" opacity=".55"')]
    e.append(TX(T, (500, -TABLE_T/2 - 4), "LINNMON top", "dim", "middle"))
    for sx in (-1, 1):
        x0, x1 = (FOOT_X[0], 0) if sx < 0 else (RAIL_L, RAIL_L - FOOT_X[0])
        e.append(R(T, x0, x1, -SKIRT, F, "plate", 'style="fill:var(--petg2)"'))
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
    e.append(f'<path class="plate" fill-rule="evenodd" d="{d}" style="fill:var(--petg)"/>')
    e.append(R(T, BAR_AT - BAR/2 - .2, BAR_AT + BAR/2 + .2, BAR_ZC - BAR/2 - .2, BAR_ZC + BAR/2 + .2, "", 'style="fill:var(--sheet)"'))
    for wx in (11.94, 81.94):
        for wy in (FIX_Y, SLOT_Y):
            e.append(circ(T, (ox + wx, pz(wy)), WHEEL_OD / 2 * k, "soft"))
    e.append(R(T, BAR_AT - BAR/2, BAR_AT + BAR/2, BAR_ZC - BAR/2, BAR_ZC + BAR/2, "rail", 'style="fill:var(--bar)"'))
    e.append(TX(T, (BAR_AT + 60, pz(120)), "X PLATE · PETG, ACRO outline", "lbl"))
    e.append(TX(T, (BAR_AT + 60, pz(105)), "the 700 bar passes through a square window", "dim"))
    e.append(TX(T, (BAR_AT + 60, pz(20)), "NEMA17 on the outside, at the bottom", "dim"))
    e.append(TX(T, (500, RAIL_Z0 + 16), "1000 RAIL · 2040 standing", "lblb", "middle"))
    e.append(TX(T, (10, F + 46 + 70), "END PLATE", "lblb", "start"))
    e.append(TX(T, (10, F + 46 + 58), "+ snap-on foot", "dim", "start"))
    e.append(TX(T, (10, F + 20), "560", "dim", "middle", 'transform="rotate(-90 {} {})"'.format(*T((10, F + 20)))))
    e.append(dimh(T, 0, RAIL_L, -18, "1000 rails · end plates and feet outside them", 14))
    e.append(dimv(T, 1030, 0, F, f"{F:.0f} foot*"))
    e.append(dimv(T, 1030, F, F + PH, "40"))
    e.append(dimv(T, 1030, F + PH, RAIL_Z0, f"{GAP:.0f} gap"))
    e.append(dimv(T, 1030, RAIL_Z0, RAIL_Z0 + PH, "40"))
    e.append(dimh(T, 0, X_MIN_BAR, pz(150), f"{X_MIN_BAR:.0f}*", -5))
    e.append(TX(T, (X_MIN_BAR + 4, pz(150) + 4), f"left limit (was {X_MIN_OLD:.0f}): the wheels now pass over the 560 and stop at the end plate", "dim"))
    W, H = (1080 - X0) * k, (Z1 + TABLE_T + 30) * k
    return f'<svg class="v" style="--fs:12px" viewBox="0 0 {W:.0f} {H:.0f}" role="img" aria-label="Front view of the frame">{"".join(e)}</svg>'

# ------------------------------------------------------------------ view 2: section across the frame at the bar (y right, z up), looking from the left
def section_view():
    k = 1.0; Y0, Z1 = -110.0, 220.0  # view spans y -110..760
    T = lambda p: ((p[0] - Y0) * k, (Z1 - p[1]) * k)
    e = [f'<line class="bench" x1="0" y1="{T((0,0))[1]}" x2="{(680-Y0)*k}" y2="{T((0,0))[1]}"/>']
    e.append(TX(T, (-105, 6), "◀ FRONT (you)", "dim"))
    e.append(TX(T, (740, 6), "BACK ▶", "dim", "end"))
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
        e.append(R(T, min(yi, yo), max(yi, yo), pz(0), pz(g["size"][1]), "plate", 'style="fill:var(--petg)"'))
        yc2 = yi + sg * COLLAR
        e.append(R(T, min(yi, yc2), max(yi, yc2), BAR_ZC - BAR/2 - 4, BAR_ZC + BAR/2 + 4, "plate", 'style="fill:var(--petg)"'))
        ym = yo - sg * NEMA_L
        e.append(R(T, min(yo, ym), max(yo, ym), MOTOR_BOT, MOTOR_BOT + NEMA, "plate", 'style="fill:var(--steel)"'))
        yc = PW/2 if sg > 0 else END_L - PW/2
        for wy in (FIX_Y, SLOT_Y):
            e.append(R(T, yc - WHEEL_W/2, yc + WHEEL_W/2, pz(wy) - r, pz(wy) + r, "", 'rx="3" fill="var(--ink)" opacity=".7"'))
    e.append(R(T, BAR_Y0, END_L - BAR_Y0, BAR_ZC - BAR/2, BAR_ZC + BAR/2, "rail", 'style="fill:var(--bar)"'))
    e.append(R(T, -MARGIN, END_L + MARGIN, -TABLE_T, 0, "", 'style="fill:var(--deck)" opacity=".55"'))
    # Y carriage + dumb plate
    yc = END_L / 2
    e.append(R(T, yc - CAR/2, yc + CAR/2, BAR_ZC - CAR/2 + 4, BAR_ZC + CAR/2 + 4, "plate", 'style="fill:var(--steel)" opacity=".85"'))
    e.append(R(T, yc - DUMB[0]/2, yc + DUMB[0]/2, BAR_ZC + 10 - DUMB[1], BAR_ZC + 10, "plate", 'style="fill:var(--petg)" opacity=".9"'))
    e.append(TX(T, (yc + DUMB[0]/2 + 6, BAR_ZC - 50), "DUMB PLATE (PETG)", "lblb"))
    e.append(TX(T, (yc + DUMB[0]/2 + 6, BAR_ZC - 62), "on the OpenBuilds Y carriage", "dim"))
    e.append(TX(T, (yc + 50, BAR_ZC + 22), f"2020 bar {BAR_LEN:.0f}, uncut, through both plates", "lbl"))
    e.append(TX(T, (-104, MOTOR_BOT + NEMA + 6), "NEMA17", "dim"))
    e.append(TX(T, (-104, pz(g["size"][1]) + 16), "X plate outside the rail", "dim"))
    e.append(TX(T, (-104, pz(g["size"][1]) + 4), f"+ {COLLAR:.0f} collar on the bar", "dim"))
    e.append(dimv(T, 640, 0, BAR_ZC - BAR/2, f"{PEN_DROP:.0f}* table to bar"))
    e.append(TX(T, (-104, -TABLE_T - 14), f"plate bottom {PLATE_BOT:.1f}* above the table · motor {MOTOR_BOT:.1f}* · feet {F:.0f}*", "dim"))
    e.append(dimh(T, Y_OUT - NEMA_L, END_L - Y_OUT + NEMA_L, 196, f"{END_L - 2*Y_OUT + 2*NEMA_L:.0f}* over the motors (560 frame)", -5))
    W, H = (760 - Y0) * k, (Z1 + TABLE_T + 40) * k
    return f'<svg class="v" style="--fs:11px" viewBox="0 0 {W:.0f} {H:.0f}" role="img" aria-label="Section across the frame at the bar">{"".join(e)}</svg>'

# ------------------------------------------------------------------ view 3: end plate + foot detail (y right, z up), seen from outside the left end
def endplate_view():
    k = 2.2; Y0, Z1 = -62.0, F + EP_TOP + 14
    T = lambda p: ((p[0] - Y0) * k, (Z1 - p[1]) * k)
    e = [R(T, -MARGIN, 175, -TABLE_T, 0, "", 'style="fill:var(--deck)" opacity=".55"')]
    e.append(TX(T, (60, -TABLE_T/2 - 2), "LINNMON top (front corner)", "dim", "middle"))
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
    e.append(R(T, fy[0], -MARGIN, -SKIRT, 0, "plate", 'style="fill:var(--petg2)" opacity=".85"'))
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
    e.append(TX(T, (98, 2), "snaps on, caps the corner", "dim"))
    e.append(dimh(T, EP_Y0, EP_Y1, F + EP_TOP + 6, f"{EP_Y1-EP_Y0:.0f}", -4))
    e.append(dimh(T, fy[0], fy[1], -TABLE_T - 6, f"foot {fy[1]-fy[0]:.0f} × {FOOT_X[1]-FOOT_X[0]:.0f}*, {SKIRT:.0f} lips", 12))
    e.append(dimv(T, -30, F, F + EP_TOP, f"{EP_TOP:.0f}", -1))
    W, H = (175 - Y0) * k, (Z1 + TABLE_T + 26) * k
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
        e.append(R(T, BAR_AT - BORE[0], BAR_AT - BORE[0] + g["size"][0], min(yi, yo), max(yi, yo), "plate", 'style="fill:var(--petg)"'))
        ym = yo - sg * NEMA_L
        e.append(R(T, BAR_AT - NEMA/2, BAR_AT + NEMA/2, min(yo, ym), max(yo, ym), "plate", 'style="fill:var(--steel)"'))
    e.append(R(T, BAR_AT - BAR/2, BAR_AT + BAR/2, BAR_Y0, END_L - BAR_Y0, "rail", 'style="fill:var(--bar)"'))
    e.append(R(T, BAR_AT + BAR/2 + 2, BAR_AT + BAR/2 + 10, END_L/2 - DUMB[0]/2, END_L/2 + DUMB[0]/2, "plate", 'style="fill:var(--petg)"'))
    e.append(TX(T, (sum(STOP_X)/2, 600), "stop range", "dim acctext", "middle"))
    e.append(TX(T, (BAR_AT + 60, -95), "FRONT (you)", "lblb", "start"))
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
    <h1>Etch frame · lo-fi v4</h1>
    <p>The ACRO layout on your frame. The 1000 rails are now held up by the end plates, 28 mm clear of the 560s, so the X plates' wheels pass over the 560s. The X plates are PETG prints of the ACRO outline with a window for the 700 bar, which passes through uncut. Each end plate stands in a foot that caps a LINNMON corner.</p>
  </div>
  <div class="tblock">
    <div><span>Room</span> <b>R04 Etch</b></div>
    <div><span>Date</span> <b>2026-11-09</b></div>
    <div><span>Frame</span> <b>1000 × 560 · 2040</b></div>
    <div><span>Prints</span> <b>4 end plates · 4 corner feet · 2 X plates · 1 plate</b></div>
    <div><span>Status</span> <b>sketch · inspector after go</b></div>
  </div>
</header>

<div class="view">
  <h2>Front view</h2>
  <p class="sub">To scale, from where you sit. Grey = 2040, dark = PETG prints, tan = the 2020 bar end-on, wood = the LINNMON top. * = rests on catalogue sizes (wheels, spacers) or a placeholder.</p>
  <div class="svgbox">{front_view()}</div>
</div>

<div class="views2">
  <div class="view">
    <h2>End plate + foot</h2>
    <p class="sub">From outside the left end, front corner. Two M5 go into the tapped rail end and two M5 with T-nuts into the 560. The plate's tongue drops into the foot and two barbs (blue) click it in. The foot's lips hook over the LINNMON's front edge and its end, so the whole frame registers off the table corner.</p>
    <div class="svgbox">{endplate_view()}</div>
  </div>
  <div class="view">
    <h2>Section at the bar</h2>
    <p class="sub">Looking from the left. The bar runs right through both X plates and stands about 69 mm proud of each one. A 20 mm collar on the plate's inner face keeps it square.</p>
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
    <h2>What changed from v3</h2>
    <ul>
      <li><b>Rails lifted {GAP:.0f} mm clear of the 560s</b> (your "longer feet"). The bottom wheels run {WHEEL_OVER_560:.1f}* above the 560, so the left limit drops from {X_MIN_OLD:.0f} to ≈ {X_MIN_BAR:.0f}*: the leading wheel now stops at the end plate. The plate's bottom edge clears the table by {PLATE_BOT:.0f}* and the motor by {MOTOR_BOT:.0f}* (were 3.6 and 7.5).</li>
      <li><b>The rails hang on the end plates.</b> Each rail end is held by 2 M5 into its tapped end, through 6 mm PETG. That's the part to watch in the inspector.</li>
      <li><b>The 700 bar stays uncut.</b> It passes through a 20.4 mm square window in each X plate, plus a {COLLAR:.0f} mm collar with M5 + T-nuts into the bar's slots. The X plates become PETG prints of the ACRO outline, {XP_T:.0f} mm thick* (acrylic is 6).</li>
      <li><b>Corner feet:</b> each foot caps a LINNMON corner, with {SKIRT:.0f} mm lips down the front or back edge and the end. The frame sits {MARGIN:.0f} mm in from the front and back edges, which centres it.</li>
      <li><b>Pen drop</b> is now ≈ {PEN_DROP:.0f}*. That's for the carriage redesign to handle, as agreed.</li>
    </ul>
  </section>
  <section>
    <h2>Need your call</h2>
    <ol class="q">
      <li><b>LINNMON top thickness:</b> I've used {TABLE_T:.0f}* mm. Can you measure it? The lips need it.</li>
      <li><b>Gap:</b> {GAP:.0f} mm between each rail and its 560 leaves the wheels {WHEEL_OVER_560:.1f}* of clearance. OK, or do you want more?</li>
      <li><b>Rail hold:</b> 2 M5 into each tapped rail end, with nothing under the rail, is the lean option. Want a rib on the end plate under the rail as well? It would sit inside the wheels' path at the very end.</li>
      <li><b>X plate thickness:</b> 8 mm PETG, or keep it 6 like the acrylic?</li>
    </ol>
    <p>Say go, and the inspector comes next.</p>
    <p class="unv">Placeholders: foot {F:.0f}, wheel Ø{WHEEL_OD} × {WHEEL_W}, spacer {SPACER:.0f}, dumb plate {DUMB[0]:.0f} × {DUMB[1]:.0f}. The ACRO plate holes are traced from your STL.</p>
  </section>
</div>
</div></body></html>"""

OUT.write_text(page())
print(f"ok  plate bottom {PLATE_BOT:.1f}  motor bottom {MOTOR_BOT:.1f}  wheel low {WHEEL_LOW:.1f}  bar {BAR_LEN:.1f} at z {BAR_ZC:.1f}  x_min {X_MIN_BAR:.1f}")
