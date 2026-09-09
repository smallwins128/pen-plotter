#!/usr/bin/env python3
"""Pack the models into the data blob the 3D viewer reads.

Geometry goes over as base64 Float32 triangle positions -- no index buffer, so
three.js computes flat per-face normals for free and the extrusion reads as
faceted metal rather than a smoothed blob.

Run via viewer.py; this module is the data half.
"""

import base64
import json
import pathlib
import sys

import numpy as np
import trimesh

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "parts"))

from build123d import export_stl  # noqa: E402

OUT = HERE / "out"


def _positions_b64(part, name):
    """Triangle soup for a part, as base64 Float32 (x, y, z per vertex)."""
    OUT.mkdir(parents=True, exist_ok=True)
    stl = OUT / f"_web_{name}.stl"
    export_stl(part, str(stl))
    mesh = trimesh.load(str(stl))
    stl.unlink()

    tris = mesh.vertices[mesh.faces].astype(np.float32).reshape(-1)
    return {
        "b64": base64.b64encode(tris.tobytes()).decode("ascii"),
        "tris": int(len(mesh.faces)),
    }


def _simplify(pts, tol=1e-4):
    """Drop points that lie on the straight line between their neighbours."""
    out = [pts[0]]
    for prev, cur, nxt in zip(pts, pts[1:], pts[2:]):
        cross = (cur[0] - prev[0]) * (nxt[1] - prev[1]) - (cur[1] - prev[1]) * (nxt[0] - prev[0])
        if abs(cross) > tol:
            out.append(cur)
    out.append(pts[-1])
    return [[round(x, 3), round(y, 3)] for x, y in out]


def build_data():
    import cross_bar
    import deck as deck_mod
    import frame
    import table as table_mod
    from profiles import section_moments, section_polylines
    from params import (
        CROSS_BAR_H,
        DECK_HOLE_D,
        DECK_T,
        DECK_X,
        DECK_Y,
        CROSS_BAR_LEN,
        CROSS_BAR_W,
        FRAME_OUTER_X,
        FRAME_OUTER_Y,
        GANTRY_PLATE_LEN,
        GANTRY_RISE,
        PROFILE_H,
        PROFILE_W,
    )

    # The frame is static; the cross bar moves, so it ships as its own object
    # with its geometry centred on the bar so the viewer can translate it in X.
    frame_part = frame.build()
    bar_part = cross_bar.build()
    deck_part = deck_mod.build()
    table_part = table_mod.build()

    sections = {}
    for label, (w, h) in {"2020": (20, 20), "2040": (20, 40)}.items():
        lines = section_polylines(w, h, samples=400)
        sections[label] = {
            "outline": _simplify(lines[0]),
            "holes": [_simplify(g) for g in lines[1:]],
            **{k: round(v, 1) for k, v in section_moments(w, h).items()},
        }

    d = cross_bar.deflection()

    return {
        "parts": {
            "table": {"geom": _positions_b64(table_part, "table"), "moves": False},
            "deck": {"geom": _positions_b64(deck_part, "deck"), "moves": False},
            "frame": {"geom": _positions_b64(frame_part, "frame"), "moves": False},
            "cross_bar": {"geom": _positions_b64(bar_part, "cross_bar"), "moves": True},
        },
        "frame": {
            "outer_x": FRAME_OUTER_X,
            "outer_y": FRAME_OUTER_Y,
            "profile": f"{PROFILE_W:g}x{PROFILE_H:g}",
            "opening_x": FRAME_OUTER_X - 2 * PROFILE_W,
            "opening_y": FRAME_OUTER_Y - 2 * PROFILE_W,
        },
        "bar": {
            "len": CROSS_BAR_LEN,
            "profile": f"{CROSS_BAR_W:g}x{CROSS_BAR_H:g}",
            "span": cross_bar.support_span(),
            "overhang": cross_bar.overhang(),
            "underside_z": cross_bar.underside_z(),
            "gantry_rise": GANTRY_RISE,
            "plate_len": GANTRY_PLATE_LEN,
            "travel": cross_bar.x_travel(),
            "travel_half": cross_bar.x_travel() / 2,
            "sag_self": round(d["self_weight"], 3),
            "sag_load": round(d["payload"], 3),
            "sag_total": round(d["total"], 3),
            "ix": round(d["ix"]),
        },
        "deck": {
            "t": DECK_T,
            "x": DECK_X,
            "y": DECK_Y,
            "holes": len(deck_mod.hole_positions()),
            "hole_d": DECK_HOLE_D,
            "mass": round(deck_mod.mass(), 2),
            "sag": {str(t): round(deck_mod.plate_sag(t), 1) for t in (1.0, 1.5, 2.0, 3.0)},
        },
        "table": {
            "x": table_mod.TABLE_X,
            "y": table_mod.TABLE_Y,
            "t": table_mod.TABLE_T,
            "free": [round(v) for v in table_mod.free_zone()],
        },
        "cut_list": [
            {"qty": q, "len": l, "label": lb}
            for q, l, lb in (frame.cut_list() + cross_bar.cut_list())
        ],
        "sections": sections,
    }


if __name__ == "__main__":
    data = build_data()
    blob = json.dumps(data, separators=(",", ":"))
    print(f"payload {len(blob)/1024:.0f} KB")
    for name, p in data["parts"].items():
        print(f"  {name:10s} {p['geom']['tris']:5d} tris  {len(p['geom']['b64'])/1024:6.0f} KB b64")
