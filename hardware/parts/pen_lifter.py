"""Pen lifter, lofi: blocks in the right places, to agree the layout before any real part is drawn.

    python3 hardware/parts/pen_lifter.py      # -> hardware/out/pen_lifter/*.stl + meta.json
                                              #    -> hardware/web/pen_lifter.b64.txt (parts inspector data)

The idea (docs/PEN_LIFTER.md), after a reference build Allwin shared:
  * a parallel-leaf flexure carries a shuttle straight up and down; nothing slides, nothing to print loose
  * the shuttle carries a pick face; the pen plate (pen clamped by a grub screw) hangs on it by 4 magnets and
    locates on two 90 deg ridges
  * a servo arm lifts the shuttle from below. At pen down the arm drops ARM_DROP clear of the tab, so the pen
    lands under its own weight plus the flexure and the servo holds nothing (FINDINGS 7b: never stall it)
  * a microswitch reads "pen up" off a second tab. Sensor only, never a stop
  * docks hold parked plates by their flanges; the head slides a plate in along X and backs off in -Y

Frame (mm): x along the head, y out of the carriage (carriage face at y = 0), z up, paper at z = 0, pen tip on
the paper at pen down. The carriage is the ACRO front plate Allwin printed (hardware/ref/acro/), shown for
context only: ACRO is not decided yet, and only the mount bracket changes if it isn't.

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
from fit_kit import FLANGE_T, FLANGE_W, FLEX_L, PICK, _ridge, build_pen  # noqa: E402
from web_bundle import pack  # noqa: E402

OUT = HW / "out" / "pen_lifter"
DATA = HW / "web" / "pen_lifter.b64.txt"

LEAF_T = 0.8              # coupon J picks this; 0.8 is the middle guess
LIFT = 4.0                # pen travel
ARM_R = 8.0               # servo arm, shaft to the tab contact
ARM_DROP = 1.2            # how far the arm falls clear of the tab at pen down
PEN_D = 9.0               # placeholder barrel; the plate's clamp bore is per pen
Z0 = 40.0                 # bottom of the moving stack at pen down

# y stations, carriage face outwards: bracket front, flexure fixed block, shuttle, pick face's mating face
Y_FIX, Y_SHUT = 5.0, 17.0 + FLEX_L
Y_FACE = Y_SHUT + 12.0 + 5.0
H = 32.0                  # stack height (= PICK)


def box(x0, x1, y0, y1, z0, z1):
    with BuildPart() as p:
        with Locations(((x0 + x1) / 2, (y0 + y1) / 2, z0)):
            Box(x1 - x0, y1 - y0, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return p.part


def mount():
    """Printed bracket on the ACRO front plate's 31 mm M3 square (centre 85 mm below the plate's top edge)."""
    with BuildPart() as p:
        with Locations((0, Y_FIX / 2, Z0 - 5)):
            Box(50, Y_FIX, 45, align=(Align.CENTER, Align.CENTER, Align.MIN))
        for x in (-15.5, 15.5):
            for z in (-15.5, 15.5):
                with Locations((x, Y_FIX / 2, Z0 + 17.5 + z)):
                    Cylinder(1.7, Y_FIX, rotation=(90, 0, 0), mode=Mode.SUBTRACT)
    return p.part


def leaves():
    """Four leaves per side group: two pairs, 5 mm apart, top and bottom of the stack, two strips across X."""
    out = []
    for zc in (Z0 + 4.5, Z0 + H - 4.5):
        for dz in (-2.5, 2.5):
            for xc in (-13.0, 13.0):
                z = zc + dz
                out.append(box(xc - 5, xc + 5, Y_FIX + 12 - 0.1, Y_SHUT + 0.1, z - LEAF_T / 2, z + LEAF_T / 2))
    p = out[0]
    for q in out[1:]:
        p = p + q
    return p


def pick_face():
    with BuildPart() as p:
        with Locations((0, Y_FACE - 2.5, Z0)):
            Box(PICK, 5.0, H, align=(Align.CENTER, Align.CENTER, Align.MIN))
    face = p.part
    y = Y_FACE                                                          # mating face
    r1 = _ridge(along_x=True).rotate(Axis.X, -90).moved(Pos(0, y, Z0 + H / 2 + 13.0))
    r2 = _ridge(along_x=False).rotate(Axis.X, -90).moved(Pos(13.0, y, Z0 + H / 2))
    return face + r1 + r2


def plate(zoff=0.0, xoff=0.0):
    """Pen plate: body, top and bottom flanges along X (they ride the dock rails), clamp block, grub screw boss."""
    y0 = Y_FACE + 0.2                                                   # 0.2 face gap: ridges seat on their flanks
    yb = y0 + 4.0
    parts = [box(-PICK / 2, PICK / 2, y0, yb, Z0, Z0 + H),
             box(-PICK / 2, PICK / 2, yb - FLANGE_T, yb, Z0 - FLANGE_W, Z0),
             box(-PICK / 2, PICK / 2, yb - FLANGE_T, yb, Z0 + H, Z0 + H + FLANGE_W),
             box(-10, 10, yb, yb + 16, Z0, Z0 + H),
             box(-3, 3, yb + 5, yb + 11, Z0 + H, Z0 + H + 3)]           # grub screw boss
    p = parts[0]
    for q in parts[1:]:
        p = p + q
    with BuildPart() as bore:
        with Locations((0, yb + 8, Z0 - 1)):
            Cylinder(PEN_D / 2 + 0.25, H + 6, align=(Align.CENTER, Align.CENTER, Align.MIN))
    p = p - bore.part
    return p.moved(Pos(xoff, 0, zoff))


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


# servo: MG90S-sized body (12.2 x 22.8 x 22.7), shaft out along +y beside the flexure
SHAFT = (30.1, Y_SHUT - 0.3, Z0 + 9.9)


def servo():
    x0, z0 = SHAFT[0] - 6.1, SHAFT[2] - 5.9
    body = box(x0, x0 + 12.2, Y_SHUT - 27.3 - 4.0, Y_SHUT - 4.6, z0, z0 + 22.8)
    tabs = box(x0, x0 + 12.2, Y_SHUT - 12.0, Y_SHUT - 9.5, z0 - 4.7, z0 + 27.5)
    with BuildPart() as s:
        with Locations((SHAFT[0], Y_SHUT - 4.6, SHAFT[2])):
            Cylinder(2.4, 4.0, rotation=(-90, 0, 0), align=(Align.CENTER, Align.CENTER, Align.MIN))
    return body + tabs + s.part


def servo_bracket():
    return box(SHAFT[0] - 8.0, SHAFT[0] + 8.0, Y_FIX, Y_SHUT - 31.3, SHAFT[2] - 10.6, SHAFT[2] + 21.6)


def arm():
    """Horn + arm, modelled level (the contact pose). The inspector turns it about the shaft."""
    y0 = Y_SHUT - 0.6
    with BuildPart() as h:
        with Locations((SHAFT[0], y0, SHAFT[2])):
            Cylinder(3.5, 1.8, rotation=(-90, 0, 0), align=(Align.CENTER, Align.CENTER, Align.MIN))
    return h.part + box(SHAFT[0] - ARM_R - 1.5, SHAFT[0], y0, y0 + 1.8 + 3.0, SHAFT[2] - 2.0, SHAFT[2] + 2.0)


def shuttle():
    body = box(-20, 20, Y_SHUT, Y_SHUT + 12, Z0, Z0 + H)
    lift_tab = box(20, SHAFT[0] - ARM_R + 4.0, Y_SHUT - 0.6 + 1.8, Y_SHUT + 6.0, SHAFT[2] + 2.0, SHAFT[2] + 5.0)
    switch_tab = box(-27, -20, Y_SHUT + 3, Y_SHUT + 9, Z0 + H - 6, Z0 + H - 3)
    return body + lift_tab + switch_tab


def switch():
    """Mini microswitch over the switch tab. The tab meets the lever 0.5 mm before full lift and the lever's own
    over-travel takes the rest: it reads pen up, it never stops the shuttle."""
    zb = Z0 + H - 3 + LIFT - 0.5
    body = box(-30.4, -17.6, Y_SHUT + 3.1, Y_SHUT + 8.9, zb + 3.0, zb + 9.5)
    lever = box(-29.0, -19.0, Y_SHUT + 4.5, Y_SHUT + 7.5, zb, zb + 3.0)
    post = box(-31.0, -25.0, Y_FIX, Y_SHUT + 3.1, zb + 3.0, zb + 9.5)
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
    p = parts[0]
    for q in parts[1:]:
        p = p + q
    return p


def carriage():
    """Allwin's printed ACRO X_Carriage_Front, stood up: outer face at y = 0, its 31 mm square on the bracket's."""
    m = trimesh.load(HW / "ref" / "acro" / "X_Carriage_Front.stl")
    lo, hi = m.bounds
    m.apply_translation([-(lo[0] + hi[0]) / 2, -hi[1], -hi[2]])          # centre x, top edge at y=0, face at z=0
    m.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))   # plate -> XZ, face +y
    m.apply_translation([0, 0, (Z0 + 17.5) + 84.95])                     # 31 mm square centre on the bracket's
    return m


def paper():
    return box(-150, 60, -40, 150, -0.6, 0.0)


# name: (part fn, group, colour key, animation, note)
PARTS = {
    "carriage_acro_front": (carriage, "Context", "context", None,
                            "ACRO X carriage front plate, from Allwin's print. Context only: ACRO not decided."),
    "paper": (paper, "Context", "paper", None, "Paper at z = 0."),
    "mount_bracket": (mount, "Head (fixed)", "fixed", None, "Bolts to the 31 mm M3 square. 50 x 5 x 45, placeholder."),
    "flex_fixed": (lambda: box(-20, 20, Y_FIX, Y_FIX + 12, Z0, Z0 + H), "Head (fixed)", "fixed", None,
                   "Flexure fixed block. Prints in one piece with the leaves and shuttle."),
    "flex_leaves": (leaves, "Flexure", "flex", "shear",
                    f"8 leaves, {LEAF_T} thick x 10 wide x {FLEX_L:.0f} long. Thickness from coupon J."),
    "flex_shuttle": (shuttle, "Flexure", "flex", "lift", "Shuttle, with the lift tab (servo side) and switch tab."),
    "pick_face": (pick_face, "Pen plate + pick face", "pick", "lift",
                  "4 magnet pockets on an 18 mm square, two 90 deg ridges in an L. Coupon K."),
    "pen_plate": (plate, "Pen plate + pick face", "plate", "lift",
                  "Same outline for every pen; clamp bore per pen, grub screw on top. Flanges ride the dock rails."),
    "pen": (pen, "Pen plate + pick face", "pen", "lift", f"Placeholder pen, Ø{PEN_D:.0f}."),
    "servo": (servo, "Servo + switch", "servo", None, "MG90S-sized body. Shaft out along +y."),
    "servo_bracket": (servo_bracket, "Head (fixed)", "fixed", None, "Placeholder block, servo to mount bracket."),
    "servo_arm": (arm, "Servo + switch", "arm", "arm",
                  f"{ARM_R:.0f} mm arm. Pen down: drops {ARM_DROP} mm clear of the tab, servo holds nothing."),
    "pen_up_switch": (switch, "Servo + switch", "switch", None,
                      "Tab meets the lever 0.5 mm before full lift; lever over-travel takes the rest. Sensor only (FINDINGS 7b)."),
    "dock": (dock, "Dock", "dock", None, "One dock. Rails with lips hold the flanges; slide in along +x, head backs off in -y."),
    "dock_parked_plate": (lambda: plate(LIFT, DOCK_X), "Dock", "plate", None, "A parked plate, at pen-up height."),
    "dock_parked_pen": (lambda: pen(LIFT, DOCK_X), "Dock", "pen", None, "Its pen, tip 4 mm off the paper."),
}

# where each part goes when the inspector explodes the head (mm at full explode)
EXPLODE = dict(carriage_acro_front=(0, -30, 0), mount_bracket=(0, -15, 0), servo=(45, 0, 0), servo_arm=(45, 20, 0),
               servo_bracket=(30, 0, 0), pen_up_switch=(-35, 0, 20), pick_face=(0, 20, 0), pen_plate=(0, 45, 0),
               pen=(0, 45, 0), flex_shuttle=(0, 8, 0), flex_leaves=(0, 4, 0))

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
    for name, part in build_pen().items():
        bb = part.bounding_box()
        if x + bb.size.X > 85:
            x, y, row_h = -80.0, y + row_h + 8.0, 0.0
        placed = part.moved(Pos(x - bb.min.X, y - bb.min.Y, -bb.min.Z))
        export_stl(placed, str(OUT / f"fit_{name}.stl"))
        meta[f"fit_{name}"] = dict(scene="fit", group=name[0] + " " + {"J": "flexure", "K": "pick face + plate",
                                                                         "L": "dock channel"}[name[0]],
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
    rig = dict(lift=LIFT, arm_r=ARM_R, arm_drop=ARM_DROP, shaft=SHAFT, shear_y0=Y_FIX + 12, shear_len=FLEX_L)
    (OUT / "meta.json").write_text(json.dumps(dict(meta=meta, rig=rig, title="Pen lifter, lofi"), indent=1))
    pack(OUT, DATA)


if __name__ == "__main__":
    main()
