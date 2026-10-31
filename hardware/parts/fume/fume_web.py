"""Pack the fume-extractor layers into the viewer page (hardware/web/fume_viewer.html).

    python3 hardware/parts/fume/fume_web.py     # after fume.py

The page carries its meshes inline: base64 of int16 xyz in 0.01 mm and uint32 indices per layer (as web_bundle.py).
"""
import base64
import json
import pathlib

import numpy as np
import trimesh

HW = pathlib.Path(__file__).resolve().parents[2]
SRC = HW / "out" / "fume"
TPL, DST = pathlib.Path(__file__).with_name("fume_viewer.tpl.html"), HW / "web" / "fume_viewer.html"
Q = 100.0


def main():
    summary = json.loads((SRC / "summary.json").read_text())
    parts = []
    for m in summary["layers"]:
        mesh = trimesh.load(SRC / f"{m['name']}.stl")
        mesh.merge_vertices()
        v = np.round(mesh.vertices * Q).astype(np.int16).tobytes()
        i = mesh.faces.astype(np.uint32).tobytes()
        parts.append(dict(m, v=base64.b64encode(v).decode(), i=base64.b64encode(i).decode()))
    data = json.dumps(dict(q=Q, summary=summary, parts=parts))
    DST.write_text(TPL.read_text().replace("/*DATA*/null", data))
    print(DST, f"{DST.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
