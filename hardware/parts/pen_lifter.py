"""Pen lifter, lofi: blocks in the right places, to agree the layout before any real part is drawn.

    python3 hardware/parts/pen_lifter.py      # -> hardware/out/pen_lifter/*.stl + meta.json
                                              #    -> hardware/web/pen_lifter.b64.txt (parts inspector data)

The idea (docs/PEN_LIFTER.md), after a reference build Allwin shared:
  * the shuttle hangs in a folded-beam suspension: two thin layers (top and bottom of the shuttle), each with a
    folded beam left and right running ALONG the carriage face. Soft up and down, stiff every other way, and
    nothing slides: no friction, no clearance, no wobble. The suspension is also the spring
  * the servo drives a short toggle crank: at pen up the crank pin is nearly under the shaft, so the spring's
    force passes close to the shaft and the holding torque is a fraction of what a level arm needs
  * the shuttle carries a pick face; the pen plate (pen clamped by a grub screw) hangs on it by 4 magnets and
    locates on two 90 deg ridges
  * at pen down the crank pin drops clear of the shuttle's tab, so the pen lands on its own weight and the
    servo holds nothing (FINDINGS 7b: never stall it)
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
from fit_kit import FLANGE_T, FLANGE_W, PICK, _ridge, build_pen  # noqa: E402
from web_bundle import pack  # noqa: E402

OUT = HW / "out" / "pen_lifter"
DATA = HW / "web" / "pen_lifter.b64.txt"

LIFT = 4.0                # pen travel
PEN_D = 9.0               # placeholder barrel; the plate's clamp bore is per pen
Z0 = 40.0                 # bottom of the moving stack at pen down
H = 32.0                  # shuttle / pick face / plate height (= PICK)

# y stations, carriage face outwards: bracket back plate, shuttle back, shuttle front, pick face's mating face
Y_BACK, Y_SHUT0, Y_SHUT = 5.0, 8.0, 20.0
Y_FACE = Y_SHUT + 5.0
Z_SQUARE = Z0 + 16.0                  # centre of the ACRO plate's 31 mm M3 square on the bracket

# Suspension, per side per layer: beam A (front) shuttle -> truss, beam B (back) truss -> anchor on the bracket.
# The truss floats at half the lift and is free to slide in x, so the beams never have to stretch.
LEAF_T = 0.7              # leaf thickness (vertical bending); a coupon picks it
BEAM_W = 5.0              # leaf width in y; in-plane stiffness goes as (BEAM_W / LEAF_T)^2 over vertical
X_SHUT, X_ANCHOR, X_TRUSS = 16.0, 22.0, 44.0
Y_A, Y_B = (Y_SHUT - BEAM_W, Y_SHUT), (Y_SHUT0, Y_SHUT0 + BEAM_W)
Z_LAYERS = (Z0 + 1.0, Z0 + H - 1.0 - LEAF_T)          # bottom faces of the two layers

# Toggle crank: pin at CRANK_R from the shaft. Pen down at PHI_REST (pin clear of the tab), contact at PHI_CONTACT,
# pen up at PHI_UP, where the pin is nearly under the shaft and the lever on the spring force is R cos(PHI_UP).
CRANK_R, PIN_R = 3.5, 1.5
PHI_REST, PHI_CONTACT, PHI_UP = -30.0, -10.0, 80.0
SHAFT = (55.5, 27.7, Z0 + 12.0)
Z_TAB = SHAFT[2] + CRANK_R * math.sin(math.radians(PHI_CONTACT)) + PIN_R     # tab underside at pen down

# Rough figures for the inspector's torque readout (estimates, PETG E ~ 2 GPa; plate + pen + shuttle ~60 g)
E_PETG, MOVING_N = 2000.0, 0.6


def suspension_k():
    """Vertical stiffness, N/mm: per side per layer beam A and beam B in series (fixed-guided), 2 sides x 2 layers."""
    i = BEAM_W * LEAF_T ** 3 / 12
    ka, kb = (12 * E_PETG * i / ln ** 3 for ln in (X_TRUSS - X_SHUT, X_TRUSS - X_ANCHOR))
    return 4 / (1 / ka + 1 / kb)


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
    """Back plate on the ACRO 31 mm square, with the suspension's four anchor blocks standing off it."""
    back = box(-50, 64, 0, Y_BACK, Z0 - 6, Z0 + H + 6)
    with BuildPart() as holes:
        for x in (-15.5, 15.5):
            for dz in (-15.5, 15.5):
                with Locations((x, Y_BACK / 2, Z_SQUARE + dz)):
                    Cylinder(1.7, Y_BACK, rotation=(90, 0, 0))
    anchors = [box(sx * X_ANCHOR - 5 if sx > 0 else -X_ANCHOR, X_ANCHOR if sx > 0 else -X_ANCHOR + 5,
                   Y_BACK, Y_B[1], z - 2.0, z + LEAF_T + 2.0) for sx in (-1, 1) for z in Z_LAYERS]
    return union(back - holes.part, *anchors)


def beams(which, sx):
    """Both layers' beam A (front, shuttle -> truss) or beam B (back, truss -> anchor) on side sx."""
    x0 = X_SHUT if which == "A" else X_ANCHOR
    y0, y1 = Y_A if which == "A" else Y_B
    out = [box(*sorted((sx * (x0 - 0.1), sx * (X_TRUSS + 0.1))), y0, y1, z, z + LEAF_T) for z in Z_LAYERS]
    return union(*out)


def trusses():
    """The floating bars that join beam A to beam B at each outer end. They ride at half the lift."""
    out = [box(*sorted((sx * X_TRUSS, sx * (X_TRUSS + 4.0))), Y_SHUT0, Y_SHUT, z - 1.0, z + LEAF_T + 1.0)
           for sx in (-1, 1) for z in Z_LAYERS]
    return union(*out)


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


# servo: MG90S-sized body (12.2 x 22.8 x 22.7) on the back plate, outboard of the suspension, shaft out along +y


def servo():
    x0, z0 = SHAFT[0] - 6.1, SHAFT[2] - 5.9
    body = box(x0, x0 + 12.2, Y_BACK, SHAFT[1], z0, z0 + 22.8)
    ears = box(x0, x0 + 12.2, 16.0, 18.5, z0 - 4.7, z0 + 27.5)
    with BuildPart() as s:
        with Locations(SHAFT):
            Cylinder(2.4, 4.0, rotation=(-90, 0, 0), align=(Align.CENTER, Align.CENTER, Align.MIN))
    return body + ears + s.part


def crank():
    """Toggle crank, modelled at phi = 0 with the pin towards -x. The inspector turns it about the shaft."""
    y0 = SHAFT[1] + 4.0
    with BuildPart() as c:
        with Locations((SHAFT[0], y0, SHAFT[2])):
            Cylinder(3.0, 2.0, rotation=(-90, 0, 0), align=(Align.CENTER, Align.CENTER, Align.MIN))
        with Locations((SHAFT[0] - CRANK_R, y0, SHAFT[2])):
            Cylinder(PIN_R, 7.0, rotation=(-90, 0, 0), align=(Align.CENTER, Align.CENTER, Align.MIN))
    return c.part


def shuttle():
    """Hangs in the suspension. The lift tab runs out past the truss to the crank pin; switch tab on the far side."""
    body = box(-X_SHUT, X_SHUT, Y_SHUT0, Y_SHUT, Z0, Z0 + H)
    # between the two layers: out along x in front of the beams, round the front of the servo, over the pin
    x_turn = SHAFT[0] - 11.0
    arm = box(X_SHUT, x_turn + 3.5, Y_SHUT - 4.0, Y_SHUT + 4.0, Z_TAB, Z_TAB + 4.0)
    riser = box(x_turn, x_turn + 3.5, Y_SHUT, SHAFT[1] + 12.0, Z_TAB, Z_TAB + 3.0)
    hook = box(x_turn, SHAFT[0] + 1.0, SHAFT[1] + 6.3, SHAFT[1] + 12.0, Z_TAB, Z_TAB + 3.0)
    switch_tab = box(-X_SHUT - 8, -X_SHUT, Y_SHUT0 + 2, Y_SHUT - 4, Z0 + 10, Z0 + 13)
    return union(body, arm, riser, hook, switch_tab)


def switch():
    """Mini microswitch over the switch tab. The tab meets the lever 0.5 mm before full lift and the lever's own
    over-travel takes the rest: it reads pen up, it never stops the shuttle."""
    zb = Z0 + 13 + LIFT - 0.5
    body = box(-32.0, -19.2, Y_SHUT0 + 1.1, Y_SHUT0 + 6.9, zb + 3.0, zb + 9.5)
    lever = box(-30.0, -20.0, Y_SHUT0 + 2.5, Y_SHUT0 + 5.5, zb, zb + 3.0)
    post = box(-32.0, -26.0, Y_BACK, Y_SHUT0 + 1.1, zb + 3.0, zb + 9.5)
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
                "Back plate on the 31 mm M3 square; the suspension's four anchor blocks stand off it."),
    "beams_A_right": (lambda: beams("A", 1), "Suspension", "flex",
                      dict(type="shear", x0=X_SHUT, x1=X_TRUSS, f0=1.0, f1=0.5),
                      f"Front beams, shuttle to truss, {X_TRUSS - X_SHUT:.0f} long x {BEAM_W:.0f} wide x {LEAF_T} thick."),
    "beams_A_left": (lambda: beams("A", -1), "Suspension", "flex",
                     dict(type="shear", x0=-X_SHUT, x1=-X_TRUSS, f0=1.0, f1=0.5), "Front beams, left."),
    "beams_B_right": (lambda: beams("B", 1), "Suspension", "flex",
                      dict(type="shear", x0=X_ANCHOR, x1=X_TRUSS, f0=0.0, f1=0.5),
                      f"Back beams, anchor to truss, {X_TRUSS - X_ANCHOR:.0f} long."),
    "beams_B_left": (lambda: beams("B", -1), "Suspension", "flex",
                     dict(type="shear", x0=-X_ANCHOR, x1=-X_TRUSS, f0=0.0, f1=0.5), "Back beams, left."),
    "trusses": (trusses, "Suspension", "truss", dict(type="lift", f=0.5),
                "Floating trusses: ride at half the lift and slide in x, so the beams never stretch."),
    "shuttle": (shuttle, "Suspension", "shuttle", "lift",
                "Hangs in the suspension. Lift tab runs out to the crank pin; switch tab on the far side."),
    "pick_face": (pick_face, "Pen plate + pick face", "pick", "lift",
                  "4 magnet pockets on an 18 mm square, two 90 deg ridges in an L. Coupon K."),
    "pen_plate": (plate, "Pen plate + pick face", "plate", "lift",
                  "Same outline for every pen; clamp bore per pen, grub screw on top. Flanges ride the dock rails."),
    "pen": (pen, "Pen plate + pick face", "pen", "lift", f"Placeholder pen, Ø{PEN_D:.0f}."),
    "servo": (servo, "Servo + switch", "servo", None, "MG90S-sized body on the back plate, shaft out along +y."),
    "servo_crank": (crank, "Servo + switch", "arm", "crank",
                    f"Toggle crank, pin at {CRANK_R} mm. {PHI_REST:.0f} deg pen down (pin clear), contact at "
                    f"{PHI_CONTACT:.0f}, pen up at {PHI_UP:.0f}: lever on the spring force only "
                    f"{CRANK_R * math.cos(math.radians(PHI_UP)):.1f} mm."),
    "pen_up_switch": (switch, "Servo + switch", "switch", None,
                      "Tab meets the lever 0.5 mm before full lift; lever over-travel takes the rest. Sensor only."),
    "dock": (dock, "Dock", "dock", None,
             "One dock. Rails with lips hold the flanges; slide in along +x, head backs off in -y."),
    "dock_parked_plate": (lambda: plate(LIFT, DOCK_X), "Dock", "plate", None, "A parked plate, at pen-up height."),
    "dock_parked_pen": (lambda: pen(LIFT, DOCK_X), "Dock", "pen", None, "Its pen, tip 4 mm off the paper."),
}

# where each part goes when the inspector explodes the head (mm at full explode)
EXPLODE = dict(carriage_acro_front=(0, -30, 0), bracket=(0, -14, 0), shuttle=(0, 6, 0), trusses=(0, 3, 0),
               pick_face=(0, 18, 0), pen_plate=(0, 40, 0), pen=(0, 40, 0), servo=(30, 0, 0),
               servo_crank=(30, 18, 0), pen_up_switch=(-30, 0, 0))

COLOURS = dict(context="#9aa3a8", paper="#f4f4f0", fixed="#e9ecee", flex="#2fa25a", pick="#2f2f33", plate="#e9ecee",
               pen="#f2a33a", servo="#2c4a7a", arm="#f2f2f2", switch="#3b3b3b", dock="#e9ecee",
               truss="#1f7a43", shuttle="#d7dcdf")


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
    rig = dict(lift=LIFT, shaft=SHAFT, crank_r=CRANK_R, phi_rest=PHI_REST, phi_contact=PHI_CONTACT, phi_up=PHI_UP,
               k_est=round(suspension_k(), 3), moving_n=MOVING_N, compare_arm=8.0)
    (OUT / "meta.json").write_text(json.dumps(dict(meta=meta, rig=rig, title="Pen lifter, lofi"), indent=1))
    pack(OUT, DATA)


if __name__ == "__main__":
    main()
