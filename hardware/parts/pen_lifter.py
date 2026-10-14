"""Pen lifter, lofi: blocks in the right places, to agree the layout before any real part is drawn.

    python3 hardware/parts/pen_lifter.py      # -> hardware/out/pen_lifter/*.stl + meta.json
                                              #    -> hardware/web/pen_lifter.b64.txt (parts inspector data)

The idea (docs/PEN_LIFTER.md), after a reference build Allwin shared:
  * a printed loop spring stands on top of the shuttle, in line with the lift. Lifting the pen squashes it;
    it springs back and puts the pen on the paper. The shuttle runs in a printed vertical guide on the bracket
  * the shuttle carries a pick face; the pen plate (pen clamped by a grub screw) hangs on it by 4 magnets and
    locates on two 90 deg ridges
  * a servo arm lifts the shuttle by a tab. At pen down the arm drops ARM_DROP clear of the tab, so the pen lands
    on the spring and its own weight and the servo holds nothing (FINDINGS 7b: never stall it)
  * a microswitch reads "pen up" off a second tab. Sensor only, never a stop
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
from fit_kit import (FLANGE_T, FLANGE_W, PICK, SPRING_DEPTH, SPRING_H, SPRING_L, _ridge, build_pen,  # noqa: E402
                     loop_spring)
from web_bundle import pack  # noqa: E402

OUT = HW / "out" / "pen_lifter"
DATA = HW / "web" / "pen_lifter.b64.txt"

LOOP_T = 0.8              # coupon J picks this; 0.8 is the middle guess
LIFT = 4.0                # pen travel
ARM_R = 8.0               # servo arm, shaft to the tab contact
ARM_DROP = 1.2            # how far the arm falls clear of the tab at pen down
PEN_D = 9.0               # placeholder barrel; the plate's clamp bore is per pen
Z0 = 40.0                 # bottom of the moving stack at pen down
H = 32.0                  # shuttle / pick face / plate height (= PICK)

# y stations, carriage face outwards: bracket back plate, guide rails, shuttle, pick face's mating face
Y_BACK, Y_GUIDE, Y_SHUT = 5.0, 8.0, 20.0
Y_FACE = Y_SHUT + 5.0
Z_SPRING = Z0 + H                     # spring sits on the shuttle top...
Z_SHELF = Z_SPRING + SPRING_H         # ...under the bracket's top shelf
Z_SQUARE = Z0 + 30.0                  # centre of the ACRO plate's 31 mm M3 square on the bracket


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


def bracket():
    """Back plate on the ACRO 31 mm square, two guide rails for the shuttle, top shelf the spring pushes on."""
    back = box(-34, 38, 0, Y_BACK, Z0 - 6, Z_SHELF + 5)
    with BuildPart() as holes:
        for x in (-15.5, 15.5):
            for dz in (-15.5, 15.5):
                with Locations((x, Y_BACK / 2, Z_SQUARE + dz)):
                    Cylinder(1.7, Y_BACK, rotation=(90, 0, 0))
    rails = [box(xc - 2, xc + 2, Y_BACK, Y_GUIDE, Z0 - 6, Z_SHELF) for xc in (-12.0, 12.0)]
    shelf = box(-SPRING_L / 2 - 2, SPRING_L / 2 + 2, Y_BACK, Y_SHUT, Z_SHELF, Z_SHELF + 5)
    return union(back - holes.part, *rails, shelf)


def spring():
    """The loop spring, stood up: loops along x, squash along z, SPRING_DEPTH deep in y centred on the shuttle."""
    s = loop_spring(LOOP_T).rotate(Axis.X, 90)                  # v -> z, depth -> -y
    yc = (Y_GUIDE + Y_SHUT) / 2
    return s.moved(Pos(0, yc + SPRING_DEPTH / 2, Z_SPRING))


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


# servo: MG90S-sized body (12.2 x 22.8 x 22.7) on the back plate, shaft out along +y beside the pick face
SHAFT = (28.0, 27.7, Z0 + 10.0)


def servo():
    x0, z0 = SHAFT[0] - 6.1, SHAFT[2] - 5.9
    body = box(x0, x0 + 12.2, Y_BACK, SHAFT[1], z0, z0 + 22.8)
    ears = box(x0, x0 + 12.2, 16.0, 18.5, z0 - 4.7, z0 + 27.5)
    with BuildPart() as s:
        with Locations(SHAFT):
            Cylinder(2.4, 4.0, rotation=(-90, 0, 0), align=(Align.CENTER, Align.CENTER, Align.MIN))
    return body + ears + s.part


def arm():
    """Horn + arm, modelled level (the contact pose). The inspector turns it about the shaft."""
    y0 = SHAFT[1] + 4.0
    with BuildPart() as h:
        with Locations((SHAFT[0], y0, SHAFT[2])):
            Cylinder(3.5, 1.8, rotation=(-90, 0, 0), align=(Align.CENTER, Align.CENTER, Align.MIN))
    return h.part + box(SHAFT[0] - ARM_R - 1.5, SHAFT[0], y0, y0 + 4.8, SHAFT[2] - 2.0, SHAFT[2] + 2.0)


def shuttle():
    """Runs in the guide rails. Lift tab (servo side) reaches forward past the pick face to the arm; switch tab
    on the other side."""
    body = box(-16, 16, Y_GUIDE, Y_SHUT, Z0, Z0 + H)
    lift_tab = box(16, 21.5, Y_GUIDE, SHAFT[1] + 9.0, SHAFT[2] + 2.0, SHAFT[2] + 5.0)
    switch_tab = box(-24, -16, Y_GUIDE + 2, Y_SHUT - 4, Z0 + 10, Z0 + 13)
    return body + lift_tab + switch_tab


def switch():
    """Mini microswitch over the switch tab. The tab meets the lever 0.5 mm before full lift and the lever's own
    over-travel takes the rest: it reads pen up, it never stops the shuttle."""
    zb = Z0 + 13 + LIFT - 0.5
    body = box(-32.0, -19.2, Y_GUIDE + 1.1, Y_GUIDE + 6.9, zb + 3.0, zb + 9.5)
    lever = box(-30.0, -20.0, Y_GUIDE + 2.5, Y_GUIDE + 5.5, zb, zb + 3.0)
    post = box(-32.0, -26.0, Y_BACK, Y_GUIDE + 1.1, zb + 3.0, zb + 9.5)
    return body + lever + post


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
                "Back plate on the 31 mm M3 square, two guide rails for the shuttle, top shelf for the spring."),
    "spring": (spring, "Spring + shuttle", "flex", "squash",
               f"Three loops, {SPRING_L:.0f} long, {LOOP_T} thick, {SPRING_DEPTH:.0f} deep, {SPRING_H:.1f} free. "
               f"Squashes {LIFT:.0f} mm at pen up. Loop thickness from coupon J."),
    "shuttle": (shuttle, "Spring + shuttle", "flex", "lift",
                "Runs in the guide rails. Lift tab reaches the servo arm; switch tab on the far side."),
    "pick_face": (pick_face, "Pen plate + pick face", "pick", "lift",
                  "4 magnet pockets on an 18 mm square, two 90 deg ridges in an L. Coupon K."),
    "pen_plate": (plate, "Pen plate + pick face", "plate", "lift",
                  "Same outline for every pen; clamp bore per pen, grub screw on top. Flanges ride the dock rails."),
    "pen": (pen, "Pen plate + pick face", "pen", "lift", f"Placeholder pen, Ø{PEN_D:.0f}."),
    "servo": (servo, "Servo + switch", "servo", None, "MG90S-sized body on the back plate, shaft out along +y."),
    "servo_arm": (arm, "Servo + switch", "arm", "arm",
                  f"{ARM_R:.0f} mm arm. Pen down: drops {ARM_DROP} mm clear of the tab, servo holds nothing."),
    "pen_up_switch": (switch, "Servo + switch", "switch", None,
                      "Tab meets the lever 0.5 mm before full lift; lever over-travel takes the rest. Sensor only."),
    "dock": (dock, "Dock", "dock", None,
             "One dock. Rails with lips hold the flanges; slide in along +x, head backs off in -y."),
    "dock_parked_plate": (lambda: plate(LIFT, DOCK_X), "Dock", "plate", None, "A parked plate, at pen-up height."),
    "dock_parked_pen": (lambda: pen(LIFT, DOCK_X), "Dock", "pen", None, "Its pen, tip 4 mm off the paper."),
}

# where each part goes when the inspector explodes the head (mm at full explode)
EXPLODE = dict(carriage_acro_front=(0, -30, 0), bracket=(0, -12, 0), spring=(0, 0, 18), shuttle=(0, 6, 0),
               pick_face=(0, 18, 0), pen_plate=(0, 40, 0), pen=(0, 40, 0), servo=(40, 0, 0), servo_arm=(40, 18, 0),
               pen_up_switch=(-30, 0, 0))

COLOURS = dict(context="#9aa3a8", paper="#f4f4f0", fixed="#e9ecee", flex="#2fa25a", pick="#2f2f33", plate="#e9ecee",
               pen="#f2a33a", servo="#2c4a7a", arm="#f2f2f2", switch="#3b3b3b", dock="#e9ecee")


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
    names = {"J": "spring", "K": "pick face + plate", "L": "dock channel"}
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
    rig = dict(lift=LIFT, arm_r=ARM_R, arm_drop=ARM_DROP, shaft=SHAFT, spring_top=Z_SHELF, spring_h=SPRING_H)
    (OUT / "meta.json").write_text(json.dumps(dict(meta=meta, rig=rig, title="Pen lifter, lofi"), indent=1))
    pack(OUT, DATA)


if __name__ == "__main__":
    main()
