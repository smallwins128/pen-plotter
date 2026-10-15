"""Window acrylic only (it goes to a separate vendor): the three screwed-on pieces in one DXF 2004, laid out.

    python3 hardware/sheet/acrylic_pack.py "hardware/cutfiles/2026-10-15 Acrylic windows v1"
"""
import pathlib
import sys

import enclosure as E
import pack
import to_r2004


def main(folder):
    folder = pathlib.Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    rows = []
    for p in pack.acrylic_parts():
        dxf = E.OUT / f"{p.name}.dxf"
        E.write_dxf(p, dxf)
        v = E.verify_and_preview(dxf, E.OUT / f"{p.name}.svg")
        assert v["open_ends"] == 0, p.name
        rows.append(dict(part=p.name, material=p.material, qty=p.qty))
        print(p.name, "flat", [round(x, 2) for x in v["size"]], "holes", len(p.holes))
    r12 = E.OUT / "ACRYLIC_WINDOWS_r12.dxf"
    pack.combined_dxf(rows, r12, "Plotter enclosure · window acrylic ×3 · 3 mm clear cast acrylic · units mm")
    to_r2004.convert(r12, folder / "ACRYLIC_WINDOWS.dxf")
    import ezdxf
    a, b = ezdxf.readfile(r12), ezdxf.readfile(folder / "ACRYLIC_WINDOWS.dxf")
    assert to_r2004.sig(a) == to_r2004.sig(b) and b.dxfversion == "AC1018"
    print("wrote", folder / "ACRYLIC_WINDOWS.dxf", b.dxfversion)


if __name__ == "__main__":
    main(sys.argv[1])
