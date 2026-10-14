"""Pen lifter, lofi: blocks in the right places, to agree the layout before any real part is drawn.

    python3 hardware/parts/pen_lifter.py      # -> hardware/out/pen_lifter/*.stl + meta.json
                                              #    -> hardware/web/pen_lifter.b64.txt (parts inspector data)

The idea (docs/PEN_LIFTER.md), after the AxiDraw pen lift:
  * the moving stage is a pen carrier at the bottom and a bridge at the top, joined by Allwin's two rods
    (Ø3.92 x 79, measured). The rods slide through a fixed block on the bracket: a round bore on one rod locates
    the stage, a slot on the other only stops it turning, so the stage cannot bind
  * gravity puts the pen down: the pen force is the stage's weight. No spring
  * the servo only lifts. A 9 g servo (SG90 or MG90S, same body) lies on top of the block between the rods; its
    stock horn lifts a lip that hangs down from the bridge. At pen down the horn sits HORN_DROP below the lip, so
    the servo holds nothing (FINDINGS 7b)
  * the carrier holds a pick face; the pen plate (pen clamped by a grub screw) hangs on it by 4 magnets and
    locates on two 90 deg ridges, so pens swap
  * a microswitch over the bridge reads "pen up". Sensor only, never a stop
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
Z0 = 40.0                 # bottom of the carrier at pen down
H = 32.0                  # carrier / pick face / plate height (= PICK)

# y stations, carriage face outwards: bracket back plate, carrier back, carrier front, pick face's mating face
Y_BACK, Y_SHUT0, Y_SHUT = 5.0, 6.0, 24.0
Y_FACE = Y_SHUT + 5.0
X_SHUT = 18.0             # carrier / block / bridge half width

# rods: Allwin's, measured 2026-10-14. They move with the stage, pressed into the carrier and the bridge
ROD_D, ROD_LEN = 3.92, 79.0
ROD_X, ROD_Y = 14.0, 11.0             # 28 apart, near the back so the servo's mounting tabs clear them
BUSH_D, BUSH_SLOT = 4.05, 6.0         # block bores: round on +x, slot BUSH_SLOT long in x on -x (coupon J)

# z stack at pen down: carrier, gap (lift + 1), fixed block, servo on the block, bridge just over the servo
Z_BLOCK = (Z0 + H + LIFT + 1.0, Z0 + H + LIFT + 1.0 + 25.0)
SERVO = dict(lx=22.8, wz=12.2, hy=22.7, shaft_x=5.9, spline=4.0, tabs=32.5, tab_y=15.9)   # 9 g class, catalogue
Z_SERVO = Z_BLOCK[1] + 0.5                             # body bottom
SHAFT = (-SERVO["lx"] / 2 + SERVO["shaft_x"], Y_BACK + SERVO["hy"] + SERVO["spline"], Z_SERVO + SERVO["wz"] / 2)
HORN_R, HORN_T, HORN_W = 10.0, 1.8, 4.0               # stock single-arm horn: contact radius, thickness, width
HORN_DROP = 1.5                                        # horn tip below the lip at pen down (AxiDraw: 1-2 mm)
PHI_REST, PHI_CONTACT = -math.degrees(math.asin(HORN_DROP / HORN_R)), 0.0
PHI_UP = math.degrees(math.asin(LIFT / HORN_R))
Z_LIP = SHAFT[2] + HORN_W / 2                          # lip underside at pen down: on the level horn's top edge
Z_BRIDGE = Z_SERVO + SERVO["wz"] + 1.3                 # bridge underside at pen down
BRIDGE_T = 6.0
Z_ROD = (Z_BRIDGE + BRIDGE_T - ROD_LEN, Z_BRIDGE + BRIDGE_T)   # rods end flush with the bridge top
X_LIP = (-X_SHUT, -X_SHUT + 8.0)                       # the lip hangs down at the -x end, over the horn tip
Y_LIP = (SHAFT[1] - 3.7, SHAFT[1] + HORN_T + 2.5)
Z_SQUARE = Z0 + 30.0                                   # centre of the ACRO plate's 31 mm M3 square

MOVING_N = 0.7            # carrier + rods (~15 g) + bridge + pick face + plate + pen, ~70 g: ESTIMATE, weigh it


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
    """Back plate on the ACRO 31 mm square, and the fixed block the rods slide through: round bore on +x, slot
    on -x."""
    top = Z_BRIDGE + BRIDGE_T + LIFT + 14.0
    back = box(-X_SHUT - 4, X_SHUT + 4, 0, Y_BACK, Z0 - 6, top)
    with BuildPart() as holes:
        for x in (-15.5, 15.5):
            for dz in (-15.5, 15.5):
                with Locations((x, Y_BACK / 2, Z_SQUARE + dz)):
                    Cylinder(1.7, Y_BACK, rotation=(90, 0, 0))
    block = box(-X_SHUT, X_SHUT, Y_BACK, Y_SHUT, *Z_BLOCK)
    block = block - zcyl(ROD_X, ROD_Y, Z_BLOCK[0] - 1, Z_BLOCK[1] + 1, BUSH_D)
    half = (BUSH_SLOT - BUSH_D) / 2
    slot = box(-ROD_X - half, -ROD_X + half, ROD_Y - BUSH_D / 2, ROD_Y + BUSH_D / 2, Z_BLOCK[0] - 1, Z_BLOCK[1] + 1)
    for dx in (-half, half):
        slot = slot + zcyl(-ROD_X + dx, ROD_Y, Z_BLOCK[0] - 1, Z_BLOCK[1] + 1, BUSH_D)
    return union(back - holes.part, block - slot)


def rods():
    return union(*[zcyl(sx * ROD_X, ROD_Y, *Z_ROD, ROD_D) for sx in (-1, 1)])


def carrier():
    """Bottom of the moving stage: rods pressed in from above, pick face on its front."""
    c = box(-X_SHUT, X_SHUT, Y_SHUT0, Y_SHUT, Z0, Z0 + H)
    for sx in (-1, 1):
        c = c - zcyl(sx * ROD_X, ROD_Y, Z_ROD[0], Z0 + H + 1, ROD_D)
    return c


def bridge():
    """Top of the moving stage: rods pressed in, a lip hanging down in front of the servo for the horn to lift,
    and a tab for the pen-up switch."""
    b = box(-X_SHUT, X_SHUT, Y_SHUT0, Y_SHUT, Z_BRIDGE, Z_BRIDGE + BRIDGE_T)
    reach = box(X_LIP[0], X_LIP[1], Y_SHUT, Y_LIP[1], Z_BRIDGE, Z_BRIDGE + BRIDGE_T)      # forward over the servo
    lip = box(X_LIP[0], X_LIP[1], Y_LIP[0], Y_LIP[1], Z_LIP, Z_BRIDGE)                    # down to the horn
    for sx in (-1, 1):
        b = b - zcyl(sx * ROD_X, ROD_Y, Z_BRIDGE - 1, Z_BRIDGE + BRIDGE_T + 1, ROD_D)
    return union(b, reach, lip)


def servo():
    """9 g servo lying on the block: length along x, shaft out along +y, mounting tabs clear of the rods."""
    d = SERVO
    x0, y1 = -d["lx"] / 2, Y_BACK + d["hy"]
    body = box(x0, x0 + d["lx"], Y_BACK, y1, Z_SERVO, Z_SERVO + d["wz"])
    ext = (d["tabs"] - d["lx"]) / 2
    tabs = box(x0 - ext, x0 + d["lx"] + ext, Y_BACK + d["tab_y"], Y_BACK + d["tab_y"] + 2.5, Z_SERVO, Z_SERVO + d["wz"])
    with BuildPart() as sp:
        with Locations((SHAFT[0], y1, SHAFT[2])):
            Cylinder(2.4, d["spline"], rotation=(-90, 0, 0), align=(Align.CENTER, Align.CENTER, Align.MIN))
    return body + tabs + sp.part


def horn():
    """Stock single-arm horn, modelled level with the arm towards -x. The inspector turns it about the shaft (y)."""
    with BuildPart() as h:
        with Locations(SHAFT):
            Cylinder(3.5, HORN_T, rotation=(-90, 0, 0), align=(Align.CENTER, Align.CENTER, Align.MIN))
    arm = box(SHAFT[0] - HORN_R, SHAFT[0], SHAFT[1], SHAFT[1] + HORN_T, SHAFT[2] - HORN_W / 2, SHAFT[2] + HORN_W / 2)
    return h.part + arm


def switch():
    """Mini microswitch over the bridge, between the rods. The bridge meets the lever 0.5 mm before full lift and
    the lever's over-travel takes the rest: it reads pen up, it never stops the stage."""
    zb = Z_BRIDGE + BRIDGE_T + LIFT - 0.5
    body = box(-2.0, 10.8, Y_SHUT0 + 2, Y_SHUT0 + 7.8, zb + 3.0, zb + 9.5)
    lever = box(0.0, 9.0, Y_SHUT0 + 3, Y_SHUT0 + 6.8, zb, zb + 3.0)
    post = box(-2.0, 10.8, Y_BACK, Y_SHUT0 + 2, zb + 3.0, zb + 9.5)
    return union(body, lever, post)


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
                f"Back plate on the 31 mm M3 square, and the fixed block the rods slide through: round "
                f"\u00d8{BUSH_D} bore on the right, {BUSH_SLOT:.0f} mm slot on the left, {Z_BLOCK[1] - Z_BLOCK[0]:.0f} long."),
    "rods": (rods, "Moving stage", "steel", "lift",
             f"Allwin's rods, \u00d8{ROD_D} x {ROD_LEN:.0f} (measured), {2 * ROD_X:.0f} apart. Pressed into the "
             f"carrier and the bridge; they move with the pen."),
    "carrier": (carrier, "Moving stage", "shuttle", "lift", "Bottom of the moving stage; the pick face is on its front."),
    "bridge": (bridge, "Moving stage", "shuttle", "lift",
               f"Top of the moving stage. Its lip hangs down in front of the servo; the horn lifts it."),
    "pick_face": (pick_face, "Pen plate + pick face", "pick", "lift",
                  "4 magnet pockets on an 18 mm square, two 90 deg ridges in an L. Coupon K."),
    "pen_plate": (plate, "Pen plate + pick face", "plate", "lift",
                  "Same outline for every pen; clamp bore per pen, grub screw on top. Flanges ride the dock rails."),
    "pen": (pen, "Pen plate + pick face", "pen", "lift", f"Placeholder pen, \u00d8{PEN_D:.0f}."),
    "servo": (servo, "Servo + switch", "servo", None,
              "9 g servo (SG90 or MG90S, same body; catalogue size), lying on the block between the rods."),
    "servo_horn": (horn, "Servo + switch", "arm", "crank",
                   f"Stock single-arm horn, {HORN_R:.0f} mm to the contact. Pen down {PHI_REST:.0f} deg "
                   f"({HORN_DROP} mm under the lip), pen up {PHI_UP:.0f} deg."),
    "pen_up_switch": (switch, "Servo + switch", "switch", None,
                      "Bridge meets the lever 0.5 mm before full lift; over-travel takes the rest. Sensor only."),
    "dock": (dock, "Dock", "dock", None,
             "One dock. Rails with lips hold the flanges; slide in along +x, head backs off in -y."),
    "dock_parked_plate": (lambda: plate(LIFT, DOCK_X), "Dock", "plate", None, "A parked plate, at pen-up height."),
    "dock_parked_pen": (lambda: pen(LIFT, DOCK_X), "Dock", "pen", None, "Its pen, tip 4 mm off the paper."),
}

# where each part goes when the inspector explodes the head (mm at full explode)
EXPLODE = dict(carriage_acro_front=(0, -30, 0), bracket=(0, -14, 0), rods=(0, 0, 25), bridge=(0, 0, 40),
               carrier=(0, 6, -10), pick_face=(0, 18, -10), pen_plate=(0, 40, -10), pen=(0, 40, -10),
               servo=(0, 0, 22), servo_horn=(0, 12, 22), pen_up_switch=(0, 0, 55))

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
    rig = dict(lift=LIFT, shaft=SHAFT, crank_axis="y", crank_r=HORN_R, phi_rest=PHI_REST, phi_contact=PHI_CONTACT,
               phi_up=PHI_UP, k_est=0.0, moving_n=MOVING_N, compare_arm=HORN_R)
    (OUT / "meta.json").write_text(json.dumps(dict(meta=meta, rig=rig, title="Pen lifter, lofi"), indent=1))
    pack(OUT, DATA)


if __name__ == "__main__":
    main()
