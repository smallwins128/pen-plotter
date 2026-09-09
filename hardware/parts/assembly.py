"""The machine so far: frame + cross bar, in one coordinate system.

Everything shares frame.py's datum -- origin at the centre of the frame's outer
envelope, Z = 0 at the tabletop -- so assembling is just collecting the parts.
Anything that does not line up here will not line up on the table either.
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from build123d import Compound

from params import ALUMINIUM_DENSITY

import cross_bar
import deck
import frame
import table


def build():
    parts = [table.build(), deck.build()] + list(frame.build().children) + [cross_bar.build()]
    asm = Compound(children=parts)
    asm.label = "assembly"
    return asm


def cut_list():
    return deck.cut_list() + frame.cut_list() + cross_bar.cut_list()


# The assembly is steel and aluminium together, so no single density applies --
# add the parts up instead. The cut list mixes sheet and bar, so it carries no
# meaningful "metres of stock" total either.
LINEAR_STOCK = False


def mass():
    """Total mass, kg."""
    alu = sum(c.volume for c in frame.build().children) + cross_bar.build().volume
    return deck.mass() + alu * ALUMINIUM_DENSITY / 1000.0


if __name__ == "__main__":
    p = build()
    bb = p.bounding_box()
    print(f"assembly bbox {bb.size.X:.0f} x {bb.size.Y:.0f} x {bb.size.Z:.0f} mm")
    for line in cross_bar.report():
        print(" ", line)
