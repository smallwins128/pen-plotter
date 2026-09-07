#!/usr/bin/env python3
"""Build the interactive 3D viewer.

    python3 hardware/viewer.py

Injects the current model geometry and numbers into hardware/web/viewer.html
and writes a self-contained page to hardware/out/viewer.html. Open it in a
browser, or publish it. Re-run after changing anything in params.py -- the
viewer carries no hard-coded dimensions of its own.
"""

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from export_web import build_data  # noqa: E402

TEMPLATE = HERE / "web" / "viewer.html"
OUT = HERE / "out" / "viewer.html"
PLACEHOLDER = "__VIEWER_DATA__"


def main():
    template = TEMPLATE.read_text()
    if PLACEHOLDER not in template:
        print(f"{PLACEHOLDER} missing from {TEMPLATE}", file=sys.stderr)
        return 1

    # Escape "<" so the payload can never close the surrounding <script> tag.
    blob = json.dumps(build_data(), separators=(",", ":")).replace("<", "\\u003c")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(template.replace(PLACEHOLDER, blob))
    print(f"wrote {OUT.relative_to(HERE.parent)}  ({OUT.stat().st_size/1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
