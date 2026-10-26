"""Room R05 Harbor: build the two multi-page artifacts (Harbor Now, Harbor Plans).

Sub-pages ship as extra files of one artifact, so each needs its own document
shell and a link back to its index page.

    python3 build_harbor.py   # writes build/now/ and build/plans/
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LOFI = os.path.join(HERE, "lofi")
SHELL = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
         '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
         '<style>html,body{{margin:0}}</style></head><body>\n{body}\n</body></html>\n')
NAV = ('<p style="margin:0;font:500 .85rem \'IBM Plex Mono\',ui-monospace,monospace">'
       '<a href="./" style="color:inherit">← {back}</a></p>\n')
SETS = {
    "now": ("Harbor Now", ["room3d.html"]),
    "plans": ("Harbor Plans", ["printer_tower.html", "island_bench.html", "bench_power.html", "side_tower.html"]),
}

for folder, (back, pages) in SETS.items():
    out = os.path.join(HERE, "build", folder)
    os.makedirs(out, exist_ok=True)
    for name in pages:
        with open(os.path.join(LOFI, name), encoding="utf-8") as f:
            body = f.read()
        i = body.find("<main>")
        if i >= 0:
            body = body[:i + 6] + "\n" + NAV.format(back=back) + body[i + 6:]
        with open(os.path.join(out, name), "w", encoding="utf-8") as f:
            f.write(SHELL.format(body=body))
