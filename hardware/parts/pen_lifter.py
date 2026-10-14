"""Pen lifter, lofi: blocks in the right places, to agree the layout before any real part is drawn.

    python3 hardware/parts/pen_lifter.py      # -> hardware/out/pen_lifter/*.stl + meta.json
                                              #    -> hardware/web/pen_lifter.b64.txt (parts inspector data)

The idea (docs/PEN_LIFTER.md): Allwin's pen guide + holder (hardware/ref/pen_guide/, as downloaded) with Etch's
swappable magnetic pen plate in place of the holder's pen clamp.
  * the guide bolts flat to the carriage. Its two end walls hold two rods, 30 apart, 23 out from the carriage;
    Allwin's rods are Ø3.92 x 79, so they jut 9 mm out of the top wall
  * the holder rides the rods on two 5 mm thick wings 40 apart: a round bore on one rod, a slot on the other, so
    it cannot bind. The guide gives it ~9 mm of free travel; the pen uses 4
  * gravity puts the pen down. No spring
  * a 9 g servo (SG90 or MG90S) sits in the guide's open-sided pocket, tabs screwed to the guide's side, body
    sticking out the side; its stock horn lifts a tab under the holder. At pen down the horn sits HORN_DROP below
    the tab, so the servo holds nothing (FINDINGS 7b)
  * the holder's front is the pick face; the pen plate (pen clamped by a grub screw) hangs on it by 4 magnets and
    locates on two 90 deg ridges, so pens swap
  * a microswitch beside the top of the guide reads "pen up". Sensor only, never a stop
  * docks hold parked plates by their flanges; the head slides a plate in along X and backs off in -Y

Frame (mm): x along the head, y out of the carriage (carriage face at y = 0), z up, paper at z = 0, pen tip on
the paper at pen down. The carriage is the ACRO front plate Allwin printed (hardware/ref/acro/), shown for
context only: ACRO is not decided yet, and only the guide's mounting holes change if it isn't.

Everything here is a placeholder size unless the fit kit (coupons J, K, L) has measured it.
"""
import json
import math
import pathlib
import sys

import trimesh
from build123d import Align, Axis, Box, BuildPart, Cylinder, Locations, Mode, Pos, export_stl

HW = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HW / "parts"))
from fit_kit import FLANGE_T, FLANGE_W, PICK, _ridge, build_pen  # noqa: E402
from web_bundle import pack  # noqa: E402

OUT = HW / "out" / "pen_lifter"
DATA = HW / "web" / "pen_lifter.b64.txt"

LIFT = 4.0                # pen travel
PEN_D = 9.0               # placeholder barrel; the plate's clamp bore is per pen
Z0 = 40.0                 # bottom of the pick face / pen plate at pen down
H = 32.0                  # pick face / plate height (= PICK)

# Guide, from Allwin's pen_guide.stl (measured): 40 wide, 70 long (along the rods), 28 deep; base 5; end walls
# 7.9 thick with the rod holes 30 apart at 23 from the base; blocks 17 high under the wings at each end; an open
# 23 mm pocket between them for the servo, tab pilot holes 28 apart in the side faces at 11 from the base.
G_W, G_L, G_D, G_BASE, G_WALL, G_BLOCK = 40.0, 70.0, 28.0, 5.0, 7.9, 17.0
G_POCKET = (27.0, 50.0)                                # along the rods, from the guide's bottom
ROD_X, ROD_Y = 15.0, 23.0
# Holder, from Allwin's pen_holder.stl: two wings 40 wide x 12 deep x 5 thick, 40 apart (45 overall), riding the
# rods; here the wings carry the pick face instead of the pen clamp.
HOLD_L, WING_T, WING_Y = 45.0, 5.0, (18.0, 30.0)
Y_SHUT = WING_Y[1]                                     # pick face back (on the wings)
Y_FACE = Y_SHUT + 5.0                                  # pick face's mating face
X_SHUT = G_W / 2
Z_HOLD = Z0 - (HOLD_L - H) / 2                         # holder bottom at pen down: pick face centred on it
Z_GUIDE = Z_HOLD - G_WALL - 3.0                        # guide bottom: 3 mm under the lower wing at pen down

# rods: Allwin's, measured 2026-10-14. Pressed into the guide's end walls; the holder slides on them
ROD_D, ROD_LEN = 3.92, 79.0
ROD_PRESS = 3.85                      # end-wall holes (coupon J)
BUSH_D, BUSH_SLOT = 4.05, 6.0         # wing bores: round on +x, slot on -x (coupon J)
Z_ROD = (Z_GUIDE, Z_GUIDE + ROD_LEN)  # stand on the guide's bottom, jut out of the top wall

# servo: 9 g class (catalogue). Tabs on the guide's -x side face, body sticking out; shaft along +x
SERVO = dict(hx=22.7, wy=12.2, lz=22.8, shaft_z=5.9, spline=4.0, tabs=32.5, tab_from_top=6.8)
X_TABS = -G_W / 2                                      # tab plane: the guide's side face
X_TOP = X_TABS + 2.5 + SERVO["tab_from_top"]           # body face the shaft comes out of
SHAFT = (X_TOP + SERVO["spline"], G_BASE + SERVO["wy"] / 2 + 0.1, Z_GUIDE + G_POCKET[1] - SERVO["shaft_z"])
HORN_R, HORN_T, HORN_W = 8.0, 1.8, 4.0               # stock single-arm horn, pointing out (+y) at contact
HORN_DROP = 1.5                                        # horn tip below the tab at pen down (AxiDraw: 1-2 mm)
PHI_REST, PHI_CONTACT = -math.degrees(math.asin(HORN_DROP / HORN_R)), 0.0
PHI_UP = math.degrees(math.asin(LIFT / HORN_R))
Z_TAB = SHAFT[2] + HORN_W / 2                          # tab underside at pen down: on the level horn's top edge
Z_SQUARE = Z_GUIDE + G_L / 2                           # ACRO 31 mm M3 square, centred on the guide

MOVING_N = 0.45           # holder + pick face + plate + pen, ~45 g: an ESTIMATE, weigh it


def box(x0, x1, y0, y1, z0, z1):
    with BuildPart() as p:
        with Locations(((x0 + x1) / 2, (y0 + y1) / 2, z0)):
            Box(x1 - x0, y1 - y0, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return p.part


def union(*parts):
    p = parts[0]
    for q in parts[1:]:
        p = p + q
    return p


def zcyl(x, y, z0, z1, d):
    with BuildPart() as c:
        with Locations((x, y, z0)):
            Cylinder(d / 2, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return c.part


def guide():
    """Allwin's guide, re-drawn: base on the carriage (4 M3 on the ACRO 31 mm square added), end walls with the
    rod holes, blocks under the wings, the open servo pocket between them."""
    zg = Z_GUIDE
    base = box(-X_SHUT, X_SHUT, 0, G_BASE, zg, zg + G_L)
    walls = [box(-X_SHUT, X_SHUT, 0, G_D, z, z + G_WALL) for z in (zg, zg + G_L - G_WALL)]
    blocks = [box(-X_SHUT, X_SHUT, 0, G_BLOCK, zg + G_WALL, zg + G_POCKET[0]),
              box(-X_SHUT, X_SHUT, 0, G_BLOCK, zg + G_POCKET[1], zg + G_L - G_WALL)]
    g = union(base, *walls, *blocks)
    for sx in (-1, 1):
        g = g - zcyl(sx * ROD_X, ROD_Y, zg - 1, zg + G_L + 1, ROD_PRESS)
    with BuildPart() as holes:
        for x in (-15.5, 15.5):
            for dz in (-15.5, 15.5):
                with Locations((x, G_BASE / 2, Z_SQUARE + dz)):
                    Cylinder(1.7, G_BASE, rotation=(90, 0, 0))
    return g - holes.part


def rods():
    return union(*[zcyl(sx * ROD_X, ROD_Y, *Z_ROD, ROD_D) for sx in (-1, 1)])


def holder():
    """Allwin's holder, re-drawn: two wings on the rods (round bore +x, slot -x), joined by the pick face's back
    plate, and a tab under it at the servo side for the horn to lift."""
    wings = [box(-X_SHUT, X_SHUT, *WING_Y, z, z + WING_T) for z in (Z_HOLD, Z_HOLD + HOLD_L - WING_T)]
    back = box(-X_SHUT, X_SHUT, WING_Y[1] - 4.0, Y_SHUT, Z_HOLD, Z_HOLD + HOLD_L)
    tab = box(SHAFT[0] - 1.0, SHAFT[0] + HORN_T + 3.0, G_BLOCK + 0.5, Y_SHUT, Z_TAB, Z_TAB + 4.0)   # clears the blocks
    h = union(*wings, back, tab)
    for z in (Z_HOLD, Z_HOLD + HOLD_L - WING_T):
        h = h - zcyl(ROD_X, ROD_Y, z - 1, z + WING_T + 1, BUSH_D)
        half = (BUSH_SLOT - BUSH_D) / 2
        slot = box(-ROD_X - half, -ROD_X + half, ROD_Y - BUSH_D / 2, ROD_Y + BUSH_D / 2, z - 1, z + WING_T + 1)
        for dx in (-half, half):
            slot = slot + zcyl(-ROD_X + dx, ROD_Y, z - 1, z + WING_T + 1, BUSH_D)
        h = h - slot
    return h


def servo():
    """9 g servo in the guide's pocket: tabs on the -x side face, body out the side, shaft along +x."""
    d = SERVO
    zb = SHAFT[2] + d["shaft_z"] - d["lz"]                         # shaft near the body's upper end
    y0, y1 = SHAFT[1] - d["wy"] / 2, SHAFT[1] + d["wy"] / 2
    body = box(X_TOP - d["hx"], X_TOP, y0, y1, zb, zb + d["lz"])
    ext = (d["tabs"] - d["lz"]) / 2
    tabs = box(X_TABS - 2.5, X_TABS, y0, y1, zb - ext, zb + d["lz"] + ext)
    with BuildPart() as sp:
        with Locations((X_TOP, SHAFT[1], SHAFT[2])):
            Cylinder(2.4, d["spline"], rotation=(0, 90, 0), align=(Align.CENTER, Align.CENTER, Align.MIN))
    return body + tabs + sp.part


def horn():
    """Stock single-arm horn, modelled level pointing out (+y). The inspector turns it about the shaft (x)."""
    with BuildPart() as h:
        with Locations(SHAFT):
            Cylinder(3.5, HORN_T, rotation=(0, 90, 0), align=(Align.CENTER, Align.CENTER, Align.MIN))
    arm = box(SHAFT[0], SHAFT[0] + HORN_T, SHAFT[1], SHAFT[1] + HORN_R, SHAFT[2] - HORN_W / 2, SHAFT[2] + HORN_W / 2)
    return h.part + arm


def switch():
    """Mini microswitch on the guide's +x side over a tab on the upper wing. The tab meets the lever 0.5 mm before
    full lift and the lever's over-travel takes the rest: it reads pen up, it never stops the holder."""
    zt = Z_HOLD + HOLD_L                                           # upper wing top at pen down
    zb = zt + LIFT - 0.5
    body = box(X_SHUT + 1.0, X_SHUT + 7.5, WING_Y[0], WING_Y[0] + 12.8, zb + 3.0, zb + 9.5)
    lever = box(X_SHUT + 2.0, X_SHUT + 6.5, WING_Y[0] + 2.0, WING_Y[0] + 10.0, zb, zb + 3.0)
    post = box(X_SHUT, X_SHUT + 1.0, 0, WING_Y[0] + 12.8, zb + 3.0, zb + 9.5)
    return union(body, lever, post)


def switch_tab():
    zt = Z_HOLD + HOLD_L
    return box(X_SHUT - 1.0, X_SHUT + 7.0, WING_Y[0] + 2.0, WING_Y[0] + 10.0, zt - 3.0, zt)


def reference():
    """Allwin's two STLs as downloaded, placed where the re-drawn parts are: a check that the re-draw matches."""
    g = trimesh.load(HW / "ref" / "pen_guide" / "pen_guide.stl")
    h = trimesh.load(HW / "ref" / "pen_guide" / "pen_holder.stl")
    to_ours = trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0])   # (x, y, z) -> (x, -z, y)
    for m in (g, h):
        m.apply_transform(to_ours)
        m.apply_transform(trimesh.transformations.scale_matrix(-1, [0, 0, 0], [0, 1, 0]))   # y back to +out
    g.apply_translation([-G_W / 2, 0, Z_GUIDE])
    h.apply_translation([-G_W / 2 + 10.0, 28.0, Z_HOLD])
    return g + h


def pick_face():
    face = box(-PICK / 2, PICK / 2, Y_SHUT, Y_FACE, Z0, Z0 + H)
    r1 = _ridge(along_x=True).rotate(Axis.X, -90).moved(Pos(0, Y_FACE, Z0 + H / 2 + 13.0))
    r2 = _ridge(along_x=False).rotate(Axis.X, -90).moved(Pos(13.0, Y_FACE, Z0 + H / 2))
    return face + r1 + r2


def plate(zoff=0.0, xoff=0.0):
    """Pen plate: body, top and bottom flanges along X (they ride the dock rails), clamp block, grub screw boss."""
    y0 = Y_FACE + 0.2                                                   # 0.2 face gap: ridges seat on their flanks
    yb = y0 + 4.0
    p = union(box(-PICK / 2, PICK / 2, y0, yb, Z0, Z0 + H),
              box(-PICK / 2, PICK / 2, yb - FLANGE_T, yb, Z0 - FLANGE_W, Z0),
              box(-PICK / 2, PICK / 2, yb - FLANGE_T, yb, Z0 + H, Z0 + H + FLANGE_W),
              box(-10, 10, yb, yb + 16, Z0, Z0 + H),
              box(-3, 3, yb + 5, yb + 11, Z0 + H, Z0 + H + 3))          # grub screw boss
    with BuildPart() as bore:
        with Locations((0, yb + 8, Z0 - 1)):
            Cylinder(PEN_D / 2 + 0.25, H + 6, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return (p - bore.part).moved(Pos(xoff, 0, zoff))


def pen(zoff=0.0, xoff=0.0):
    yc = Y_FACE + 0.2 + 4.0 + 8.0
    with BuildPart() as p:
        with Locations((0, yc, 8.0)):
            Cylinder(PEN_D / 2, 140.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
        with Locations((0, yc, 0.0)):
            Cylinder(0.6, 8.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
        with Locations((0, yc, 4.0)):
            Cylinder(2.2, 4.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return p.part.moved(Pos(xoff, 0, zoff))


DOCK_X = -110.0


def dock():
    """A dock for one plate: two rails with lips in front of the flanges (towards the carriage), an end wall,
    legs to the bed. Parked plate sits at pen-up height so the head docks without dragging the tip."""
    z = Z0 + LIFT
    yb = Y_FACE + 0.2 + 4.0
    y_lip0, y_lip1 = Y_FACE - 0.5, yb - FLANGE_T - 0.3
    y_back = yb + 5.0
    xs = (DOCK_X - PICK / 2 - 4.0, DOCK_X + PICK / 2 + 2.0)
    parts = []
    for zf0, zf1, sgn in ((z - FLANGE_W, z, -1), (z + H, z + H + FLANGE_W, 1)):
        zo = zf0 - 0.3 if sgn < 0 else zf1 + 0.3                       # rail floor / ceiling beyond the flange
        z_rail0, z_rail1 = (zo - 4.0, zf1 - 0.2) if sgn < 0 else (zf0 + 0.2, zo + 4.0)
        parts.append(box(*xs, y_lip0, y_lip1, z_rail0, z_rail1))       # lip, carriage side of the flange
        parts.append(box(*xs, y_lip1, y_back, *((z_rail0, zo) if sgn < 0 else (zo, z_rail1))))
    parts.append(box(xs[0] - 3.0, xs[0], y_lip0, y_back, z - FLANGE_W - 4.6, z + H + FLANGE_W + 4.6))
    parts.append(box(xs[0] - 9.0, xs[0], y_lip0, y_back, 0.0, z - FLANGE_W - 4.6))
    return union(*parts)


def carriage():
    """Allwin's printed ACRO X_Carriage_Front, stood up: outer face at y = 0, its 31 mm square on the bracket's."""
    m = trimesh.load(HW / "ref" / "acro" / "X_Carriage_Front.stl")
    lo, hi = m.bounds
    m.apply_translation([-(lo[0] + hi[0]) / 2, -hi[1], -lo[2]])          # centre x, top edge at y=0, z 0..6
    m.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))   # plate -> XZ, y -6..0
    m.apply_translation([0, 0, Z_SQUARE + 84.95])                        # square centre 84.95 below the top edge
    return m


def paper():
    return box(-150, 60, -40, 120, -0.6, 0.0)


# name: (part fn, group, colour key, animation, note)
PARTS = {
    "carriage_acro_front": (carriage, "Context", "context", None,
                            "ACRO X carriage front plate, from Allwin's print. Context only: ACRO not decided."),
    "paper": (paper, "Context", "paper", None, "Paper at z = 0."),
    "guide": (guide, "Guide (fixed)", "fixed", None,
              f"Allwin's pen guide, re-drawn: {G_W:.0f} x {G_L:.0f} x {G_D:.0f}, rods {2 * ROD_X:.0f} apart; "
              f"4 M3 on the ACRO 31 mm square added; rod holes \u00d8{ROD_PRESS} press fit."),
    "rods": (rods, "Guide (fixed)", "steel", None,
             f"Allwin's rods, \u00d8{ROD_D} x {ROD_LEN:.0f} (measured), pressed into the end walls, jutting "
             f"{Z_ROD[1] - Z_GUIDE - G_L:.0f} mm out of the top."),
    "holder": (holder, "Holder (moving)", "shuttle", "lift",
               f"Allwin's holder, re-drawn: two wings on the rods (round \u00d8{BUSH_D} bore right, slot left), "
               f"carrying the pick face instead of the pen clamp. Lift tab under it for the horn."),
    "switch_tab": (switch_tab, "Holder (moving)", "shuttle", "lift", "Tab that trips the pen-up switch."),
    "pick_face": (pick_face, "Pen plate + pick face", "pick", "lift",
                  "4 magnet pockets on an 18 mm square, two 90 deg ridges in an L. Coupon K."),
    "pen_plate": (plate, "Pen plate + pick face", "plate", "lift",
                  "Same outline for every pen; clamp bore per pen, grub screw on top. Flanges ride the dock rails."),
    "pen": (pen, "Pen plate + pick face", "pen", "lift", f"Placeholder pen, \u00d8{PEN_D:.0f}."),
    "servo": (servo, "Servo + switch", "servo", None,
              "9 g servo (SG90 / MG90S; catalogue size) in the guide's pocket, tabs on its side, body out the side."),
    "servo_horn": (horn, "Servo + switch", "arm", "crank",
                   f"Stock single-arm horn, {HORN_R:.0f} mm to the contact. Pen down {PHI_REST:.0f} deg "
                   f"({HORN_DROP} mm under the tab), pen up {PHI_UP:.0f} deg."),
    "pen_up_switch": (switch, "Servo + switch", "switch", None,
                      "Tab meets the lever 0.5 mm before full lift; over-travel takes the rest. Sensor only."),
    "reference_as_downloaded": (reference, "Reference: Allwin's STLs", "ref", None,
                                "pen_guide.stl and pen_holder.stl exactly as downloaded, placed over the re-draw."),
    "dock": (dock, "Dock", "dock", None,
             "One dock. Rails with lips hold the flanges; slide in along +x, head backs off in -y."),
    "dock_parked_plate": (lambda: plate(LIFT, DOCK_X), "Dock", "plate", None, "A parked plate, at pen-up height."),
    "dock_parked_pen": (lambda: pen(LIFT, DOCK_X), "Dock", "pen", None, "Its pen, tip 4 mm off the paper."),
}

# where each part goes when the inspector explodes the head (mm at full explode)
EXPLODE = dict(carriage_acro_front=(0, -30, 0), guide=(0, -12, 0), rods=(0, -6, 40), holder=(0, 10, 0),
               switch_tab=(0, 10, 0), pick_face=(0, 22, 0), pen_plate=(0, 42, 0), pen=(0, 42, 0),
               servo=(-30, 0, 0), servo_horn=(-30, 10, 0), pen_up_switch=(25, 0, 0))

COLOURS = dict(context="#9aa3a8", paper="#f4f4f0", fixed="#e9ecee", pick="#2f2f33", plate="#e9ecee", pen="#f2a33a",
               servo="#2c4a7a", arm="#f2f2f2", switch="#3b3b3b", dock="#e9ecee", shuttle="#2fa25a", steel="#8f989e",
               ref="#d9480f")


def export_assembly():
    OUT.mkdir(parents=True, exist_ok=True)
    for f in OUT.glob("*.stl"):
        f.unlink()
    meta = {}
    for name, (fn, group, col, anim, note) in PARTS.items():
        part = fn()
        if isinstance(part, trimesh.Trimesh):
            part.export(OUT / f"{name}.stl")
        else:
            export_stl(part, str(OUT / f"{name}.stl"))
        meta[name] = dict(scene="assembly", group=group, color=COLOURS[col], anim=anim, note=note,
                          opacity=0.35 if name in ("carriage_acro_front", "reference_as_downloaded") else 1.0,
                          explode=EXPLODE.get(name), hidden=name == "reference_as_downloaded")
    return meta


def export_fit_kit():
    """The pen-lifter coupons, laid out on the A1 mini's 180 mm bed."""
    meta, x, y, row_h = {}, -80.0, -80.0, 0.0
    names = {"J": "rod fits", "K": "pick face + plate", "L": "dock channel"}
    for name, part in build_pen().items():
        bb = part.bounding_box()
        if x + bb.size.X > 85:
            x, y, row_h = -80.0, y + row_h + 8.0, 0.0
        placed = part.moved(Pos(x - bb.min.X, y - bb.min.Y, -bb.min.Z))
        export_stl(placed, str(OUT / f"fit_{name}.stl"))
        meta[f"fit_{name}"] = dict(scene="fit", group=f"{name[0]} {names[name[0]]}",
                                   color={"J": "#2fa25a", "K": "#2f2f33", "L": "#e9ecee"}[name[0]], anim=None,
                                   note=f"{name}: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm, as printed.",
                                   opacity=1.0)
        x += bb.size.X + 8.0
        row_h = max(row_h, bb.size.Y)
    export_stl(box(-90, 90, -90, 90, -0.8, 0.0), str(OUT / "fit_bed.stl"))
    meta["fit_bed"] = dict(scene="fit", group="Bed", color="#c9ced2", anim=None, note="A1 mini bed, 180 x 180.",
                           opacity=1.0)
    return meta


def main():
    meta = export_assembly()
    meta.update(export_fit_kit())
    rig = dict(lift=LIFT, shaft=SHAFT, crank_axis="x", crank_r=HORN_R, phi_rest=PHI_REST, phi_contact=PHI_CONTACT,
               phi_up=PHI_UP, k_est=0.0, moving_n=MOVING_N, compare_arm=HORN_R)
    (OUT / "meta.json").write_text(json.dumps(dict(meta=meta, rig=rig, title="Pen lifter, lofi"), indent=1))
    pack(OUT, DATA)


if __name__ == "__main__":
    main()
