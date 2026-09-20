#!/usr/bin/env python3
"""Build the interactive 3D viewers.

    python3 hardware/viewer.py

Writes two self-contained pages into hardware/out/:

    viewer.html        the machine -- frame, deck, gantry, bench. The
                       electronics case appears as a black box with ports,
                       because at this scale that is all it is.
    case_viewer.html   the enclosure on its own -- shell, contents, fans,
                       panel and the routed harness.

They are separate because their payloads are: the deck mesh alone is 477 KB
and means nothing to the case page, and the harness means nothing to the
machine page. Both pages share `web/_common.html` -- the CSS and the scene,
orbit and theme plumbing -- so only what each page actually shows lives in its
own file.

Neither carries a hard-coded dimension: re-run after changing params.py.
"""

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from export_web import build_data, case_data  # noqa: E402

WEB = HERE / "web"
OUT = HERE / "out"

PAGES = [
    ("viewer.html", "machine.html", "Pen Plotter Machine", build_data),
    ("case_viewer.html", "case.html", "Plotter Electronics Case", case_data),
]


def _split(page):
    """A page file is a body and a script, divided by the SCRIPT marker."""
    text = (WEB / page).read_text()
    body, _, script = text.partition("<!--SCRIPT-->")
    return body.replace("<!--BODY-->", "").strip(), script.strip()


def build(out_name, page, title, data_fn):
    common = (WEB / "_common.html").read_text()
    body, script = _split(page)

    # Escape "<" so the payload can never close the surrounding <script> tag.
    blob = json.dumps(data_fn(), separators=(",", ":")).replace("<", "\\u003c")

    html = (common
            .replace("__TITLE__", title)
            .replace("__BODY__", body)
            .replace("__PAGE_SCRIPT__", script)
            .replace("__DATA__", blob))

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / out_name
    path.write_text(html)
    return path


def main():
    for out_name, page, title, data_fn in PAGES:
        path = build(out_name, page, title, data_fn)
        print(f"wrote {path.relative_to(HERE.parent)}  ({path.stat().st_size/1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
