"""Pack the window-insert STLs into one small binary for the enclosure inspector.

    python3 hardware/parts/web_bundle.py      # after window_inserts.py

Layout of hardware/web/window_inserts.b64.txt (base64 of): uint32 header length, JSON header (padded to 4 bytes),
then per part: int16 xyz in 0.01 mm (shared vertices) and uint32 triangle indices.
Coordinates stay as the parts were modelled: u = x along the front, v = height in the wall, w = out of the steel.
"""
import base64
import json
import pathlib
import struct

import numpy as np
import trimesh

HW = pathlib.Path(__file__).resolve().parent.parent
SRC, DST = HW / "out" / "window_inserts", HW / "web" / "window_inserts.b64.txt"   # base64 text: artifacts serve no raw binary
Q = 100.0   # 0.01 mm steps; ±327 mm fits int16


def main():
    head, blobs, off = [], [], 0
    for f in sorted(SRC.glob("*.stl")):
        m = trimesh.load(f)
        m.merge_vertices()
        v = np.round(m.vertices * Q).astype(np.int16).tobytes()
        i = m.faces.astype(np.uint32).tobytes()
        head.append(dict(name=f.stem, nv=len(m.vertices), nt=len(m.faces), v=off, i=off + len(v)))
        blobs += [v, i]
        off += len(v) + len(i)
        if off % 4:
            blobs.append(b"\0" * (4 - off % 4)); off += 4 - off % 4
    h = json.dumps(dict(q=Q, parts=head)).encode()
    h += b" " * (-len(h) % 4)
    DST.write_bytes(base64.b64encode(struct.pack("<I", len(h)) + h + b"".join(blobs)))
    print(f"{len(head)} parts -> {DST.relative_to(HW.parent)} ({DST.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
