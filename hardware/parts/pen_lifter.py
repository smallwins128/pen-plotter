"""Pen lifter, lofi: blocks in the right places, to agree the layout before any real part is drawn.

    python3 hardware/parts/pen_lifter.py      # -> hardware/out/pen_lifter/*.stl + meta.json
                                              #    -> hardware/web/pen_lifter.b64.txt (parts inspector data)

The idea (docs/PEN_LIFTER.md):
  * the shuttle rides Allwin's two smooth rods (Ø3.92 x 79, measured), 28 apart, on bushings printed into it:
    a round bore on one rod locates it, a slot on the other only stops it turning, so two rods that are not
    perfectly parallel cannot bind it. Each bore runs the shuttle's full 32 mm height, so it cannot rock. The rods
    press snug into a thick bottom ear, pass through the top ear and jut out above it
  * gravity puts the pen down: the pen force is the weight of shuttle + plate + pen. No spring
  * the servo only lifts. It lies above the shuttle, between the rods, and turns a short toggle crank whose
    pin sits in a window on the shuttle. The pin pushes the window's top edge up; at pen down it drops clear, so
    the servo holds nothing (FINDINGS 7b). At pen up the pin is nearly over the shaft, so even the weight it
    holds has almost no lever
  * the shuttle carries a pick face; the pen plate (pen clamped by a grub screw) hangs on it by 4 magnets and
    locates on two 90 deg ridges
  * a microswitch reads "pen up" off the window plate. Sensor only, never a stop
  * docks hold parked plates by their flanges; the head slides a plate in along X and backs off in -Y

Frame (mm): x along the head, y out of the carriage (carriage face at y = 0), z up, paper at z = 0, pen tip on
the paper at pen down. The carriage is the ACRO front plate Allwin printed (hardware/ref/acro/), shown for
context only: ACRO is not decided yet, and only the bracket's back changes if it isn't.

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
Z0 = 40.0                 # bottom of the moving stack at pen down
H = 32.0                  # shuttle / pick face / plate height (= PICK)

# y stations, carriage face outwards: bracket back plate, shuttle back, shuttle front, pick face's mating face
Y_BACK, Y_SHUT0, Y_SHUT = 5.0, 6.0, 24.0
Y_FACE = Y_SHUT + 5.0
X_SHUT = 18.0             # shuttle half width: the head is this wide plus the window plate on one side

# rods: Allwin's, measured 2026-10-14. Bores are placeholders until coupon J picks them
ROD_D, ROD_LEN = 3.92, 79.0
ROD_X, ROD_Y = 14.0, 19.5             # 28 apart so the servo fits between them; forward of the servo's body
ROD_PRESS = 3.85                      # bottom and top ear holes: snug press on the rod
BUSH_D, BUSH_SLOT = 4.05, 6.0         # shuttle bores: round on +x, slot BUSH_SLOT long in x on -x
EAR_LO_T, EAR_T = 8.0, 5.0
Z_EAR_LO = Z0 - 1.0 - EAR_LO_T                         # bottom ear under the shuttle at pen down
Z_EAR_HI = Z0 + H + LIFT + 1.0                         # top ear over it at pen up
Z_ROD_TOP = Z_EAR_LO + ROD_LEN                         # rods stand on the bottom ear's underside, jut out above

# servo lies above the top ear, shaft along +x; toggle crank turns in the YZ plane
CRANK_R, PIN_R = 3.5, 1.5
PHI_REST, PHI_CONTACT, PHI_UP = -30.0, -10.0, 80.0
SHAFT = (22.7 / 2, Y_BACK + 6.1, Z_EAR_HI + EAR_T + 4.7 + 5.9 + 0.5)   # body centred between the rods
X_WIN = (X_SHUT + 0.5, X_SHUT + 3.5)                   # window plate, beside the top ear
Z_WIN = SHAFT[2] + CRANK_R * math.sin(math.radians(PHI_CONTACT)) + PIN_R   # window's top inner edge, pen down
Z_SQUARE = Z0 + 20.0                                   # centre of the ACRO plate's 31 mm M3 square

MOVING_N = 0.5            # shuttle + pick face + plate + pen, ~50 g: an ESTIMATE, weigh it


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


def bracket():
    """Back plate on the ACRO 31 mm square; a thick bottom ear and a top ear that the rods press snug into."""
    top = SHAFT[2] + 22.0
    back = box(-X_SHUT - 4, X_SHUT + 8, 0, Y_BACK, Z_EAR_LO - 2, top)
    with BuildPart() as holes:
        for x in (-15.5, 15.5):
            for dz in (-15.5, 15.5):
                with Locations((x, Y_BACK / 2, Z_SQUARE + dz)):
                    Cylinder(1.7, Y_BACK, rotation=(90, 0, 0))
    ears = [box(-X_SHUT, X_SHUT, Y_BACK, Y_SHUT - 1, Z_EAR_LO, Z_EAR_LO + EAR_LO_T),
            box(-X_SHUT, X_SHUT, Y_BACK, Y_SHUT - 1, Z_EAR_HI, Z_EAR_HI + EAR_T)]
    p = union(back - holes.part, *ears)
    for sx in (-1, 1):
        p = p - zcyl(sx * ROD_X, ROD_Y, Z_EAR_LO - 1, Z_EAR_HI + EAR_T + 1, ROD_PRESS)
    return p


def rods():
    return union(*[zcyl(sx * ROD_X, ROD_Y, Z_EAR_LO, Z_ROD_TOP, ROD_D) for sx in (-1, 1)])


def shuttle():
    """Body with the printed bushings (round bore on +x, slot on -x), and the window plate that rises beside the
    top ear to the crank pin."""
    body = box(-X_SHUT, X_SHUT, Y_SHUT0, Y_SHUT, Z0, Z0 + H)
    body = body - zcyl(ROD_X, ROD_Y, Z0 - 1, Z0 + H + 1, BUSH_D)
    slot = box(-ROD_X - (BUSH_SLOT - BUSH_D) / 2, -ROD_X + (BUSH_SLOT - BUSH_D) / 2, ROD_Y - BUSH_D / 2,
               ROD_Y + BUSH_D / 2, Z0 - 1, Z0 + H + 1)
    for dx in (-(BUSH_SLOT - BUSH_D) / 2, (BUSH_SLOT - BUSH_D) / 2):
        slot = slot + zcyl(-ROD_X + dx, ROD_Y, Z0 - 1, Z0 + H + 1, BUSH_D)
    body = body - slot
    bridge = box(X_SHUT - 1.0, X_WIN[1], Y_SHUT0, Y_SHUT, Z0 + H - 6.0, Z0 + H)
    win = box(*X_WIN, Y_SHUT0, Y_SHUT, Z0 + H - 6.0, Z_WIN + 3.0)
    hole = box(X_WIN[0] - 1, X_WIN[1] + 1, SHAFT[1] - 2.0, SHAFT[1] + CRANK_R + PIN_R + 2.5,
               SHAFT[2] - CRANK_R - PIN_R - 1.5, Z_WIN)
    return union(body, bridge, win - hole)


def servo():
    """MG90S-sized body lying on its side over the top ear: shaft along +x, mounting ears along z."""
    zs = SHAFT[2]
    body = box(SHAFT[0] - 22.7, SHAFT[0], SHAFT[1] - 6.1, SHAFT[1] + 6.1, zs - 5.9, zs + 16.9)
    ears = box(SHAFT[0] - 6.7, SHAFT[0] - 4.2, SHAFT[1] - 6.1, SHAFT[1] + 6.1, zs - 10.6, zs + 21.6)
    with BuildPart() as s:
        with Locations(SHAFT):
            Cylinder(2.4, 4.0, rotation=(0, 90, 0), align=(Align.CENTER, Align.CENTER, Align.MIN))
    return body + ears + s.part


def crank():
    """Toggle crank, modelled at phi = 0 with the pin towards +y. The inspector turns it about the shaft (x)."""
    x0 = SHAFT[0] + 4.0
    with BuildPart() as c:
        with Locations((x0, SHAFT[1], SHAFT[2])):
            Cylinder(3.0, 2.0, rotation=(0, 90, 0), align=(Align.CENTER, Align.CENTER, Align.MIN))
        with Locations((x0 + 2.0, SHAFT[1] + CRANK_R, SHAFT[2])):
            Cylinder(PIN_R, X_WIN[1] + 1.5 - x0 - 2.0, rotation=(0, 90, 0), align=(Align.CENTER, Align.CENTER, Align.MIN))
    return c.part


def switch():
    """Mini microswitch over the window plate. The plate meets the lever 0.5 mm before full lift and the lever's
    own over-travel takes the rest: it reads pen up, it never stops the shuttle."""
    zb = Z_WIN + 3.0 + LIFT - 0.5
    body = box(X_WIN[0] - 1.5, X_WIN[1] + 1.5, Y_BACK, Y_BACK + 12.8, zb + 3.0, zb + 9.5)
    lever = box(*X_WIN, Y_BACK + 2.0, Y_BACK + 10.0, zb, zb + 3.0)
    return body + lever


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
    "bracket": (bracket, "Head (fixed)", "fixed", None,
                "Back plate on the 31 mm M3 square; bottom and top ears clamp the two rods."),
    "rods": (rods, "Head (fixed)", "steel", None,
             f"Allwin's rods, \u00d8{ROD_D} x {ROD_LEN:.0f} (measured), {2 * ROD_X:.0f} apart. Snug in both ears, "
             f"jut {Z_ROD_TOP - Z_EAR_HI - EAR_T:.0f} mm above the top ear."),
    "shuttle": (shuttle, "Shuttle", "shuttle", "lift",
                f"Printed bushings, full {H:.0f} mm height: round \u00d8{BUSH_D} bore on the right rod, "
                f"{BUSH_SLOT:.0f} mm slot on the left (no binding). Window plate for the crank pin."),
    "pick_face": (pick_face, "Pen plate + pick face", "pick", "lift",
                  "4 magnet pockets on an 18 mm square, two 90 deg ridges in an L. Coupon K."),
    "pen_plate": (plate, "Pen plate + pick face", "plate", "lift",
                  "Same outline for every pen; clamp bore per pen, grub screw on top. Flanges ride the dock rails."),
    "pen": (pen, "Pen plate + pick face", "pen", "lift", f"Placeholder pen, \u00d8{PEN_D:.0f}."),
    "servo": (servo, "Servo + switch", "servo", None, "MG90S-sized, lying over the top ear between the rods, shaft along +x."),
    "servo_crank": (crank, "Servo + switch", "arm", "crank",
                    f"Toggle crank, pin at {CRANK_R} mm. {PHI_REST:.0f} deg pen down (pin clear), contact at "
                    f"{PHI_CONTACT:.0f}, pen up at {PHI_UP:.0f}: lever on the weight only "
                    f"{CRANK_R * math.cos(math.radians(PHI_UP)):.1f} mm."),
    "pen_up_switch": (switch, "Servo + switch", "switch", None,
                      "Window plate meets the lever 0.5 mm before full lift; over-travel takes the rest. Sensor only."),
    "dock": (dock, "Dock", "dock", None,
             "One dock. Rails with lips hold the flanges; slide in along +x, head backs off in -y."),
    "dock_parked_plate": (lambda: plate(LIFT, DOCK_X), "Dock", "plate", None, "A parked plate, at pen-up height."),
    "dock_parked_pen": (lambda: pen(LIFT, DOCK_X), "Dock", "pen", None, "Its pen, tip 4 mm off the paper."),
}

# where each part goes when the inspector explodes the head (mm at full explode)
EXPLODE = dict(carriage_acro_front=(0, -30, 0), bracket=(0, -14, 0), rods=(0, -7, 0),
               shuttle=(0, 8, 0), pick_face=(0, 18, 0), pen_plate=(0, 40, 0), pen=(0, 40, 0), servo=(0, 0, 30),
               servo_crank=(12, 0, 30), pen_up_switch=(0, 0, 45))

COLOURS = dict(context="#9aa3a8", paper="#f4f4f0", fixed="#e9ecee", pick="#2f2f33", plate="#e9ecee", pen="#f2a33a",
               servo="#2c4a7a", arm="#f2f2f2", switch="#3b3b3b", dock="#e9ecee", shuttle="#2fa25a", steel="#8f989e")


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
                          opacity=0.35 if name == "carriage_acro_front" else 1.0, explode=EXPLODE.get(name))
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
    rig = dict(lift=LIFT, shaft=SHAFT, crank_axis="x", crank_r=CRANK_R, phi_rest=PHI_REST, phi_contact=PHI_CONTACT,
               phi_up=PHI_UP, k_est=0.0, moving_n=MOVING_N, compare_arm=8.0)
    (OUT / "meta.json").write_text(json.dumps(dict(meta=meta, rig=rig, title="Pen lifter, lofi"), indent=1))
    pack(OUT, DATA)


if __name__ == "__main__":
    main()
