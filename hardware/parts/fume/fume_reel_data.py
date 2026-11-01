"""Pack the fume extractor meshes for the reel page (hardware/web/reel/fume_reel.html).

    python3 hardware/parts/fume/fume.py --stl && python3 hardware/parts/fume/fume_reel_data.py

Writes hardware/web/reel/fume_reel_data.js: window.FUME = {q, cy, w, h, parts: {name: {z, v, i}}}, int16 xyz in 0.01 mm
(as fume_web.py), each part in its own frame with z the depth of its front face in the assembly.
"""
import base64
import json
import pathlib

import numpy as np
import trimesh

import fume as F

HW = pathlib.Path(__file__).resolve().parents[2]
SRC, DST = HW / "out" / "fume", HW / "web" / "reel" / "fume_reel_data.js"
Q = 100.0
PARTS = dict(face=("P1_face", 0.0), filter=("P2_filter", F.T6), base=("P3_body", F.T6 + F.T5),
             grille_front=("G_hslots_front", 0.0), grille_back=("G_hslots_back", F.T6 + F.T5 + F.T3))


def main():
    out = {}
    for key, (stem, z) in PARTS.items():
        m = trimesh.load(SRC / f"{stem}.stl")
        m.merge_vertices()
        out[key] = dict(z=z, v=base64.b64encode(np.round(m.vertices * Q).astype(np.int16).tobytes()).decode(),
                        i=base64.b64encode(m.faces.astype(np.uint32).tobytes()).decode())
    data = dict(q=Q, cy=F.CY, w=F.W, h=F.H, depth=F.T6 + F.T5 + F.T3, ft=F.FT, padT=F.PAD_T, t5=F.T5,
                screws=F.SCREWS, magnets=F.MAGNET_XY, jack=F.JACK_XY, switch=F.SWITCH_XY, handle=F.HANDLE_PITCH, parts=out)
    DST.write_text("window.FUME = " + json.dumps(data) + ";\n")
    print(DST, f"{DST.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
