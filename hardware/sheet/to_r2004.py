"""Re-save the released DXFs as DXF 2004 (AC1018) for fabricators whose CAD can't read R12.

    python3 hardware/sheet/to_r2004.py "hardware/cutfiles/2026-10-14 v5"

Writes <folder>/DXF 2004/<same names>.dxf: same entities, layers and linetypes, units set to mm ($INSUNITS 4,
which R2004 stores and R12 does not). Then reads every file back and checks it against its R12 source,
entity by entity (type, layer, coordinates to 1e-6 mm).
"""
import pathlib
import sys

import ezdxf
from ezdxf.addons import Importer


def convert(src, dst):
    s = ezdxf.readfile(src)
    d = ezdxf.new("R2004", setup=True)
    d.header["$INSUNITS"] = 4
    d.header["$MEASUREMENT"] = 1
    imp = Importer(s, d)
    imp.import_tables()
    imp.import_modelspace()
    imp.finalize()
    d.saveas(dst)


def sig(doc):
    out = []
    for e in doc.modelspace():
        t = e.dxftype()
        k = [t, e.dxf.layer]
        if t == "LINE":
            k += [*e.dxf.start, *e.dxf.end]
        elif t in ("CIRCLE", "ARC"):
            k += [*e.dxf.center, e.dxf.radius] + ([e.dxf.start_angle, e.dxf.end_angle] if t == "ARC" else [])
        elif t == "TEXT":
            k += [*e.dxf.insert, e.dxf.height, e.dxf.text]
        else:
            k += [str(e.dxfattribs())]
        out.append(tuple(round(v, 6) if isinstance(v, float) else v for v in k))
    return sorted(out, key=str)


def main(folder):
    folder = pathlib.Path(folder)
    out = folder / "DXF 2004"
    out.mkdir(exist_ok=True)
    bad = 0
    for src in sorted(folder.glob("*.dxf")):
        dst = out / src.name
        convert(src, dst)
        a, b = ezdxf.readfile(src), ezdxf.readfile(dst)
        ok = sig(a) == sig(b) and b.dxfversion == "AC1018" and b.header["$INSUNITS"] == 4
        bad += not ok
        print(f"{'ok ' if ok else 'BAD'} {src.name:28s} {b.dxfversion}  {len(list(b.modelspace()))} entities  layers {sorted(l.dxf.name for l in b.layers)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
