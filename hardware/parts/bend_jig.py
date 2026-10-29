"""Wire-bending sleeves for a Meccano plate: round formers that slide over M3 posts, so bends come out round and repeatable.

Post: M3 × 16 screw up through a Meccano hole (12.7 mm grid), nut snug on top of the plate. The sleeve drops over it:
the nut sits in a round recess in the sleeve's foot, so the sleeve spins (the wire rolls instead of dragging), and a lip
on top stops the wire riding off. Diameter = 2 × bend radius; minimum radius ≈ 5 × the wire's outside diameter.

    python3 hardware/parts/bend_jig.py      # writes hardware/out/bend_jig/bend_sleeve_d{16,24,40}.stl (one of each)
"""
import pathlib

from build123d import Cylinder, Pos, export_stl

OUT = pathlib.Path(__file__).resolve().parent.parent / "out" / "bend_jig"
SIZES = (16.0, 24.0, 40.0)            # Ø16 signal wire (~1.5 OD), Ø24 18 AWG (~2.5 OD), Ø40 multi-core (~6 OD)
H, LIP, LIP_T = 14.0, 3.0, 1.5        # former height, lip overhang per side, lip thickness
BORE, NUT_D, NUT_H = 3.5, 6.8, 2.8    # M3 clearance; round recess over the M3 nut (6.35 across corners) so it can spin


def sleeve(d):
    p = Pos(0, 0, H / 2) * Cylinder(d / 2, H) + Pos(0, 0, H + LIP_T / 2 - 0.01) * Cylinder(d / 2 + LIP, LIP_T)
    p -= Pos(0, 0, (H + LIP_T) / 2) * Cylinder(BORE / 2, H + LIP_T + 2)
    p -= Pos(0, 0, NUT_H / 2 - 0.01) * Cylinder(NUT_D / 2, NUT_H)
    if d >= 30:                       # lighten the big one: a ring of pockets from the top, 2 mm floor
        core = Pos(0, 0, (H + LIP_T) / 2 + 2) * Cylinder(d / 2 - 3, H + LIP_T)
        hub = Pos(0, 0, (H + LIP_T) / 2) * Cylinder(NUT_D / 2 + 3, H + LIP_T + 4)
        p -= core - hub
    return p


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for d in SIZES:
        s = sleeve(d)
        export_stl(s, str(OUT / f"bend_sleeve_d{d:g}.stl"))
        print(f"bend_sleeve_d{d:g}: Ø{d:g} former, Ø{d + 2 * LIP:g} lip, {H + LIP_T:g} tall, {s.volume / 1000:.1f} cm3")


if __name__ == "__main__":
    main()
