"""Printed lid washers: under the M3 button heads on the box lids, over the Ø10 lid holes.

    python3 hardware/parts/washers.py      # -> hardware/out/print/lid_washer.stl + lid_washers_14.stl (a plate)

Ø15 covers the Ø10 lid hole with a 2.5 mm ring and stays clear of the lid bends (10.1 mm from each hole centre) and
flush with the lid edge at the back-lip holes (7.5 mm). 2.0 thick so PETG stays flat over the hole; with a 1.65 button
head the stack is 3.65, inside the 4.0 the control box's feet allow (enclosure.py STACK lid_fix_h). Pan heads don't
fit. Print flat, PETG, 100 % infill (it's all perimeter anyway). Snug, don't crank: plastic under a screw head creeps,
so check the lid screws once after a week.
"""
import pathlib

from build123d import Align, BuildPart, Cylinder, Locations, Mode, export_stl

OUT = pathlib.Path(__file__).resolve().parent.parent / "out" / "print"
OD, ID, T = 15.0, 3.4, 2.0
COUNT = 14                                  # 12 lid fixings (3 top + 3 back per box) + 2 spare


def washer():
    with BuildPart() as p:
        Cylinder(OD / 2, T, align=(Align.CENTER, Align.CENTER, Align.MIN))
        Cylinder(ID / 2, T, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
    return p.part


def plate(n=COUNT, pitch=OD + 4.0, cols=7):
    with BuildPart() as p:
        pts = [((i % cols) * pitch, (i // cols) * pitch, 0) for i in range(n)]
        with Locations(*pts):
            Cylinder(OD / 2, T, align=(Align.CENTER, Align.CENTER, Align.MIN))
        with Locations(*pts):
            Cylinder(ID / 2, T, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
    return p.part


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    export_stl(washer(), str(OUT / "lid_washer.stl"))
    pl = plate()
    export_stl(pl, str(OUT / f"lid_washers_{COUNT}.stl"))
    bb = pl.bounding_box()
    print(f"lid_washer.stl: Ø{OD:g} × Ø{ID:g} × {T:g};  lid_washers_{COUNT}.stl: {bb.size.X:.0f} × {bb.size.Y:.0f} mm plate")


if __name__ == "__main__":
    main()
