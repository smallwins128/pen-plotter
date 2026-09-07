#!/usr/bin/env python3
"""Regenerate every hardware model into hardware/out/.

    python3 hardware/make.py            # everything
    python3 hardware/make.py frame      # just one part

Outputs per part:
    <name>.step   solid, for real CAD / a machinist / a fabricator
    <name>.stl    mesh, for slicing and quick viewing

hardware/out/ is generated and git-ignored. The .py files are the source of
truth; if a model and an exported file disagree, re-run this.
"""

import sys
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "parts"))

from build123d import export_step, export_stl  # noqa: E402

from params import ALUMINIUM_DENSITY  # noqa: E402

OUT = HERE / "out"


def _parts():
    """name -> (build callable, optional cut-list callable)."""
    import frame

    return {
        "frame": (frame.build, frame.cut_list),
    }


def build_part(name, build, cut_list):
    part = build()
    bb = part.bounding_box()

    OUT.mkdir(parents=True, exist_ok=True)
    step_path = OUT / f"{name}.step"
    stl_path = OUT / f"{name}.stl"
    export_step(part, str(step_path))
    export_stl(part, str(stl_path))

    volume = sum(c.volume for c in part.leaves) if part.children else part.volume
    mass = volume * ALUMINIUM_DENSITY

    print(f"\n{name}")
    print(f"  envelope   {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm")
    print(f"  sits at    Z {bb.min.Z:.1f} .. {bb.max.Z:.1f} mm")
    print(f"  volume     {volume / 1000:.1f} cm^3")
    print(f"  mass       {mass / 1000:.2f} kg  (aluminium, modelled section)")

    if cut_list is not None:
        print("  cut list")
        total = 0.0
        for qty, length, label in cut_list():
            total += qty * length
            print(f"    {qty} x {length:7.1f} mm   {label}")
        print(f"    ------ {total:.0f} mm total ({total / 1000:.2f} m of stock)")

    print(f"  wrote      {step_path.relative_to(HERE.parent)}")
    print(f"             {stl_path.relative_to(HERE.parent)}")
    return part


def main(argv):
    parts = _parts()
    wanted = argv or list(parts)

    unknown = [n for n in wanted if n not in parts]
    if unknown:
        print(f"unknown part(s): {', '.join(unknown)}", file=sys.stderr)
        print(f"available: {', '.join(parts)}", file=sys.stderr)
        return 1

    for name in wanted:
        build, cut_list = parts[name]
        build_part(name, build, cut_list)

    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
