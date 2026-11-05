"""Pack the Cedar meshes into the inspector page (hardware/web/cedar_inspector.html).

    python3 hardware/parts/cedar/cedar.py --stl && python3 hardware/parts/cedar/cedar_web.py

The page carries its meshes inline (base64 int16 xyz in 0.01 mm + uint32 indices, as fume_web.py). No STL downloads.
"""
import base64
import json
import pathlib

import numpy as np
import trimesh

HW = pathlib.Path(__file__).resolve().parents[2]
SRC = HW / "out" / "cedar"
TPL, DST = pathlib.Path(__file__).with_name("cedar_inspector.tpl.html"), HW / "web" / "cedar_inspector.html"
Q = 100.0


def main():
    summary = json.loads((SRC / "summary.json").read_text())
    meshes = {}
    for p in summary["parts"]:
        m = trimesh.load(SRC / f"{p['name']}.stl")
        m.merge_vertices()
        v = np.round(m.vertices * Q).astype(np.int16).tobytes()
        i = m.faces.astype(np.uint32).tobytes()
        meshes[p["name"]] = dict(v=base64.b64encode(v).decode(), i=base64.b64encode(i).decode())
    data = json.dumps(dict(q=Q, summary=summary, meshes=meshes))
    DST.write_text(TPL.read_text().replace("/*DATA*/null", data))
    print(DST, f"{DST.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
