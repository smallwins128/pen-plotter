#!/usr/bin/env python3
"""svg2gcode.py - layered SVG to this machine's G-code dialect.

Takes an SVG written by vpype or vsketch (or anything that puts each pen on
its own Inkscape layer) and writes one G-code file per layer, in the dialect
docs/SETUP.md phase 7.2 requires:

    G21 / G90 / G94, M3 S<n> for the pen, no Z words, no M2, no mid-file M5,
    servo soft-start preamble, dwell after every pen change.

One file per layer is deliberate: you plot a layer, swap the pen, plot the
next.  plot2.py streams one file at a time, so that is the natural seam.

    python3 svg2gcode.py drawing.svg                 -> drawing_L1.gcode, ...
    python3 svg2gcode.py drawing.svg --out-dir plots
    python3 svg2gcode.py drawing.svg --layer 2       just one layer
    python3 svg2gcode.py drawing.svg --dry-run       report, write nothing

Run the SVG through vpype first - it is what makes a plot finish this side of
lunchtime:

    vpype read drawing.svg linemerge linesimplify reloop linesort write out.svg

No dependencies.

WHAT THIS REFUSES TO DO
-----------------------
It will not write a file whose extents fall outside the usable area, because
soft limits (`$20=1`) abort the job mid-plot with ALARM:2 rather than
clipping.  Better to find out here than 40 minutes in.
"""

import argparse, math, os, re, sys, xml.etree.ElementTree as ET

# --- the machine ----------------------------------------------------------
PEN_UP, PEN_DOWN = 120, 60      # MEASURE: re-run tools/servo_sweep.py after
                                # any mechanical change to the pen lift
MAX_X, MAX_Y = 150.0, 150.0     # usable area, mm, from README
FEED_DRAW = 1000                # <= $110/$111.  Those are 500 while the
FEED_TRAVEL = 1000              # servo resets are unresolved - see HANDOFF 7
PEN_DWELL = 0.30                # seconds after every pen change
SOFT_START = [90, 100, 110]     # walk the servo out from centre before the
                                # first real move; the jump from limp to an
                                # extreme is its largest current draw

SVG_NS = "{http://www.w3.org/2000/svg}"
INK_NS = "{http://www.inkscape.org/namespaces/inkscape}"
PX_PER_MM = 96.0 / 25.4         # SVG user units are px at 96 dpi


def parse_length(s, default=None):
    """'15.0cm' or '150mm' or '566.9' -> millimetres."""
    if s is None:
        return default
    m = re.match(r"^\s*([-+0-9.eE]+)\s*([a-z%]*)\s*$", s)
    if not m:
        return default
    v, unit = float(m.group(1)), m.group(2)
    return {"mm": v, "cm": v * 10.0, "in": v * 25.4, "px": v / PX_PER_MM,
            "pt": v * 25.4 / 72.0, "": v / PX_PER_MM}.get(unit, default)


def parse_points(s):
    """'x,y x,y ...' -> [(x, y), ...].  Commas and spaces both separate."""
    nums = [float(t) for t in re.split(r"[,\s]+", s.strip()) if t]
    return list(zip(nums[0::2], nums[1::2]))


def read_svg(path):
    """-> (layers, width_mm, height_mm).

    layers is {index: {"label": str, "colour": str, "paths": [[(x, y), ...]]}}
    with coordinates still in SVG user units, y still pointing down.
    """
    root = ET.parse(path).getroot()

    vb = root.get("viewBox")
    if vb:
        _, _, vw, vh = [float(t) for t in re.split(r"[,\s]+", vb.strip())]
    else:
        vw = vh = None
    w_mm = parse_length(root.get("width"), vw / PX_PER_MM if vw else None)
    h_mm = parse_length(root.get("height"), vh / PX_PER_MM if vh else None)
    if w_mm is None or h_mm is None:
        sys.exit("%s: no usable width/height/viewBox" % path)

    # user units -> mm, honouring a viewBox that is not 1:1 with width/height
    sx = w_mm / vw if vw else 1.0 / PX_PER_MM
    sy = h_mm / vh if vh else 1.0 / PX_PER_MM

    layers, loose = {}, []
    for i, g in enumerate(root.iter(SVG_NS + "g")):
        if g.get(INK_NS + "groupmode") != "layer":
            continue
        label = g.get(INK_NS + "label") or g.get("id") or str(i + 1)
        try:
            idx = int(re.sub(r"\D", "", label) or (i + 1))
        except ValueError:
            idx = i + 1
        paths = []
        for el in g.iter():
            tag = el.tag.replace(SVG_NS, "")
            if tag not in ("polyline", "polygon") or not el.get("points"):
                continue
            pts = parse_points(el.get("points"))
            if tag == "polygon" and len(pts) > 1 and pts[0] != pts[-1]:
                pts.append(pts[0])          # a polygon's closing edge is implicit
            if len(pts) >= 2:
                paths.append([(x * sx, y * sy) for x, y in pts])
        if paths:
            layers.setdefault(idx, {"label": label,
                                    "colour": g.get("stroke") or "?",
                                    "paths": []})["paths"] += paths

    # Anything outside a layer group would silently vanish; say so instead.
    for el in root.iter():
        tag = el.tag.replace(SVG_NS, "")
        if tag in ("path", "circle", "rect", "ellipse", "line"):
            loose.append(tag)
    return layers, w_mm, h_mm, loose


def to_machine(paths, h_mm):
    """SVG space (y down, origin top-left) -> work space (y up, origin at the
    paper's bottom-left), which is the Quadrant I convention in README."""
    return [[(x, h_mm - y) for x, y in p] for p in paths]


def extents(paths):
    xs = [x for p in paths for x, _ in p]
    ys = [y for p in paths for _, y in p]
    return min(xs), min(ys), max(xs), max(ys)


def path_length(paths):
    """(drawn, travelled) mm, assuming we travel between consecutive paths."""
    drawn = travel = 0.0
    cur = (0.0, 0.0)
    for p in paths:
        travel += math.dist(cur, p[0])
        for a, b in zip(p, p[1:]):
            drawn += math.dist(a, b)
        cur = p[-1]
    travel += math.dist(cur, (0.0, 0.0))
    return drawn, travel


def emit(paths, pen_up, pen_down, feed_draw, feed_travel):
    g = ["G21", "G90", "G94"]
    for s in SOFT_START:                    # wake the servo near centre
        g += ["M3 S%d" % s, "G4 P0.30"]
    g += ["M3 S%d" % pen_up, "G4 P0.30"]

    for p in paths:
        g.append("G0 X%.3f Y%.3f F%d" % (p[0][0], p[0][1], feed_travel))
        g += ["M3 S%d" % pen_down, "G4 P%.2f" % PEN_DWELL]
        for x, y in p[1:]:
            g.append("G1 X%.3f Y%.3f F%d" % (x, y, feed_draw))
        g += ["M3 S%d" % pen_up, "G4 P%.2f" % PEN_DWELL]

    g += ["M3 S%d" % pen_up, "G4 P0.30", "G0 X0 Y0"]
    return g                                # no M2: it drops the pen and
                                            # zeroes the feed rate


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("svg")
    ap.add_argument("--out-dir", default=".")
    ap.add_argument("--layer", type=int, action="append",
                    help="only this layer; repeatable")
    ap.add_argument("--pen-up", type=int, default=PEN_UP)
    ap.add_argument("--pen-down", type=int, default=PEN_DOWN)
    ap.add_argument("--feed", type=int, default=FEED_DRAW)
    ap.add_argument("--travel-feed", type=int, default=FEED_TRAVEL)
    ap.add_argument("--max-x", type=float, default=MAX_X)
    ap.add_argument("--max-y", type=float, default=MAX_Y)
    ap.add_argument("--origin", default="0,0",
                    help="shift the drawing in work coordinates, mm")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="write even if the drawing leaves the usable area")
    args = ap.parse_args()

    layers, w_mm, h_mm, loose = read_svg(args.svg)
    if not layers:
        sys.exit("%s: no Inkscape layer groups found. If this came from "
                 "vsketch use vsk.stroke(n) to put each pen on its own layer; "
                 "otherwise run it through `vpype read ... write`." % args.svg)
    if loose:
        print("note: %d element(s) outside any layer were ignored (%s). "
              "Run the file through vpype to normalise it."
              % (len(loose), ", ".join(sorted(set(loose)))))

    ox, oy = [float(t) for t in args.origin.split(",")]
    print("%s  %.1f x %.1f mm  %d layer(s)" % (args.svg, w_mm, h_mm, len(layers)))

    total_t, bad = 0.0, []
    for idx in sorted(layers):
        if args.layer and idx not in args.layer:
            continue
        lay = layers[idx]
        paths = [[(x + ox, y + oy) for x, y in p]
                 for p in to_machine(lay["paths"], h_mm)]
        x0, y0, x1, y1 = extents(paths)
        drawn, travel = path_length(paths)
        mins = (drawn / args.feed + travel / args.travel_feed) * 60.0 / 60.0
        # each pen change costs two dwells plus the servo's own travel
        mins += len(paths) * 2 * PEN_DWELL / 60.0
        total_t += mins

        fits = x0 >= -0.001 and y0 >= -0.001 and x1 <= args.max_x and y1 <= args.max_y
        flag = "" if fits else "   *** OUTSIDE THE USABLE AREA ***"
        print("  layer %-3d %-9s %4d paths  X %6.1f..%-6.1f  Y %6.1f..%-6.1f  "
              "%6.0f mm drawn  ~%.0f min%s"
              % (idx, lay["colour"], len(paths), x0, x1, y0, y1, drawn, mins, flag))
        if not fits:
            bad.append(idx)
            if not args.force:
                continue

        if args.dry_run:
            continue
        os.makedirs(args.out_dir, exist_ok=True)
        stem = os.path.splitext(os.path.basename(args.svg))[0]
        path = os.path.join(args.out_dir, "%s_L%d.gcode" % (stem, idx))
        body = emit(paths, args.pen_up, args.pen_down, args.feed, args.travel_feed)
        with open(path, "w") as fh:
            fh.write("(%s layer %d - %s - %d paths, %.0f mm)\n"
                     % (stem, idx, lay["colour"], len(paths), drawn))
            fh.write("(pen up S%d, down S%d)\n" % (args.pen_up, args.pen_down))
            fh.write("\n".join(body) + "\n")
        print("        -> %s" % path)

    print("\ntotal ~%.0f min across %d layer(s), pen swap between each"
          % (total_t, len(args.layer or layers)))
    if bad:
        print("\nlayer(s) %s fall outside %.0f x %.0f mm. Soft limits abort the "
              "job with ALARM:2 rather than clipping, so these were not written."
              % (", ".join(map(str, bad)), args.max_x, args.max_y))
        print("Scale the drawing down in the sketch, or pass --origin to shift it.")
        return 1 if not args.force else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
