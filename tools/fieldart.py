#!/usr/bin/env python3
"""fieldart.py - generate dense interference-field plots.

The look: a few hundred near-parallel lines snaking across a square, each one
displaced by a smooth wave field.  Where the field folds, the lines bunch and
cross and the flat scan reads as a three-dimensional surface.  Plot two or three
of these in different inks on the same sheet and the layers moire against each
other.

Two properties matter on this machine:

  * ONE continuous stroke, no pen lifts.  The servo is unreliable while moving
    (docs/FINDINGS.md section 7), so the pen is taped down and never leaves the
    paper.  The turns at the end of each row are part of the drawing.
  * Every layer STARTS AND ENDS AT THE SAME POINT.  Swap the pen in the holder
    without touching the carriage and the next colour registers exactly.  That
    is the only registration method that works with a fixed pen.

    python3 fieldart.py --name bloom --layers 2
    python3 fieldart.py --name dense --spacing 0.8 --amp 3.5 --seed 7
    python3 fieldart.py --name quick --spacing 2.0 --preview-only

Writes gcode/art/field_<name>_L<n>.gcode plus a matching .svg preview.
Look at the SVG before committing an hour of plotting to it.
"""

import argparse, math, os, random, sys

TAU = 2.0 * math.pi


# ---------------------------------------------------------------- the field

def make_field(seed, n_sources, n_waves, size, scale=1.0):
    """Build a deterministic wave field: radial sources plus plane waves.

    `scale` stretches every wavelength: bigger scale, bigger and calmer features.
    """
    rng = random.Random(seed)
    sources, waves = [], []
    for _ in range(n_sources):
        sources.append((
            rng.uniform(-0.25, 1.25) * size,      # centre x, may sit off-sheet
            rng.uniform(-0.25, 1.25) * size,      # centre y
            rng.uniform(0.10, 0.35) * size * scale,   # wavelength
            rng.uniform(0.6, 1.2),                # weight
            rng.uniform(0.6, 1.6) * size,         # decay distance
            rng.uniform(0, TAU),                  # phase
        ))
    for _ in range(n_waves):
        waves.append((
            rng.uniform(0, math.pi),              # direction
            rng.uniform(0.25, 0.9) * size * scale,    # wavelength
            rng.uniform(0.3, 0.7),                # weight
            rng.uniform(0, TAU),                  # phase
        ))
    return sources, waves


def displacement(x, y, sources, waves, amp, phase, fold=1.0):
    """Perpendicular offset of the scan line at (x, y), in mm.

    The inner sum is folded through a sine so the field wraps: that fold is
    what turns a smooth hill into the closed contour bands you can see.
    """
    u = 0.0
    for cx, cy, lam, w, rho, ph in sources:
        r = math.hypot(x - cx, y - cy)
        u += w * math.sin(TAU * r / lam + ph) * math.exp(-r / rho)
    for ang, lam, w, ph in waves:
        u += w * math.sin(TAU * (x * math.cos(ang) + y * math.sin(ang)) / lam + ph)
    return amp * math.sin(math.pi * fold * u + phase)


# ----------------------------------------------------------------- the path

def build_path(size, spacing, step, amp, sources, waves, phase, row_shift, fold=1.0):
    """Serpentine up the square, then serpentine back down between the rows.

    The return sweep sits half a row-space off the outward one, so it doubles
    the density AND brings the pen back to where it started - which is what
    makes multi-colour registration possible.
    """
    n = max(2, int(round(size / spacing)))
    ys = [i * spacing + row_shift for i in range(n)]                    # going up
    ys += [(n - 1 - j) * spacing + spacing / 2.0 + row_shift for j in range(n)]

    pts = [(0.0, 0.0)]
    for k, y in enumerate(ys):
        left_to_right = (k % 2 == 0)
        m = max(2, int(round(size / step)))
        for i in range(m + 1):
            t = i / float(m)
            x = t * size if left_to_right else (1.0 - t) * size
            pts.append((x, y + displacement(x, y, sources, waves, amp, phase, fold)))
    pts.append((0.0, 0.0))          # close the loop, exactly
    return pts


def path_length(pts):
    return sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
               for i in range(len(pts) - 1))


def bbox(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


# ------------------------------------------------------------------- output

def write_gcode(path, pts, feed, header, origin=(0.0, 0.0)):
    """Emit G91 relative moves, accumulating exactly so the loop really closes."""
    lines = [";" + h for h in header]
    lines += ["G21", "G90", "G94", "G91"]
    cur = (round(origin[0], 3), round(origin[1], 3))
    first = True
    for tx, ty in pts[1:]:
        tx, ty = round(tx, 3), round(ty, 3)
        dx, dy = round(tx - cur[0], 3), round(ty - cur[1], 3)
        if dx == 0.0 and dy == 0.0:
            continue
        lines.append("G1 %sX%.3f Y%.3f" % ("F%d " % feed if first else "", dx, dy))
        first = False
        cur = (round(cur[0] + dx, 3), round(cur[1] + dy, 3))
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return len(lines), cur


def write_svg(path, pts, stroke="#1f4fd8"):
    x0, y0, x1, y1 = bbox(pts)
    pad = 4.0
    w, h = (x1 - x0) + 2 * pad, (y1 - y0) + 2 * pad
    # SVG y grows downward; flip so the preview matches the paper.
    d = " ".join("%.2f,%.2f" % (p[0] - x0 + pad, (y1 - p[1]) + pad) for p in pts)
    with open(path, "w") as f:
        f.write('<svg xmlns="http://www.w3.org/2000/svg" width="%.1fmm" height="%.1fmm" '
                'viewBox="0 0 %.2f %.2f">\n' % (w, h, w, h))
        f.write('<rect width="100%%" height="100%%" fill="#fdfdfb"/>\n')
        f.write('<polyline fill="none" stroke="%s" stroke-width="0.28" '
                'stroke-linecap="round" stroke-linejoin="round" points="%s"/>\n' % (stroke, d))
        f.write('</svg>\n')


INKS = ["#1f4fd8", "#c2308c", "#111111", "#0e9b8a"]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", default="field", help="output name stem")
    ap.add_argument("--size", type=float, default=150.0, help="square side, mm")
    ap.add_argument("--spacing", type=float, default=1.2,
                    help="row spacing of the outward sweep, mm (the return sweep "
                         "halves it). 1.0-1.5 gives the dense look; 2.5 is a quick test.")
    ap.add_argument("--amp", type=float, default=3.0,
                    help="peak displacement, mm. Must exceed the spacing or the "
                         "lines never cross and the 3D illusion does not appear.")
    ap.add_argument("--step", type=float, default=0.8, help="segment length along a row, mm")
    ap.add_argument("--feed", type=int, default=500, help="feed rate, mm/min (keep <= $110)")
    ap.add_argument("--seed", type=int, default=3, help="field seed - change for a new design")
    ap.add_argument("--sources", type=int, default=3, help="radial wave sources")
    ap.add_argument("--waves", type=int, default=2, help="plane waves")
    ap.add_argument("--scale", type=float, default=1.0,
                    help="stretch every wavelength. >1 gives bigger, calmer features; "
                         "<1 packs more incident into the same square.")
    ap.add_argument("--fold", type=float, default=1.0,
                    help="how many times the field folds back on itself - the number of "
                         "contour bands. 0.4-0.6 is a calm surface, 1.0 is turbulent.")
    ap.add_argument("--layers", type=int, default=1, help="colour passes (one file each)")
    ap.add_argument("--layer-phase", type=float, default=0.45,
                    help="radians of field phase between layers - how far the "
                         "colours drift apart")
    ap.add_argument("--outdir", default=None, help="default: <repo>/gcode/art")
    ap.add_argument("--split", type=int, default=1,
                    help="cut each layer into N consecutive files. The machine does "
                         "not move between them, so this is a safe place to refill "
                         "ink or stop for the night - and a reset only costs one part.")
    ap.add_argument("--preview-only", action="store_true", help="write the SVG, skip the G-code")
    args = ap.parse_args()

    if args.amp <= args.spacing / 2.0:
        print("note: amp %.1f is small next to spacing %.1f - expect gentle waves, "
              "not crossings." % (args.amp, args.spacing))

    outdir = args.outdir or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gcode", "art")
    os.makedirs(outdir, exist_ok=True)

    sources, waves = make_field(args.seed, args.sources, args.waves, args.size, args.scale)
    total_minutes = 0.0

    for k in range(args.layers):
        phase = k * args.layer_phase
        shift = (k * args.spacing / args.layers) if args.layers > 1 else 0.0
        pts = build_path(args.size, args.spacing, args.step, args.amp,
                         sources, waves, phase, shift, args.fold)
        length = path_length(pts)
        minutes = length / args.feed
        total_minutes += minutes
        x0, y0, x1, y1 = bbox(pts)
        sx = 0.0 if abs(x0) < 0.05 else -x0          # avoid printing "-0.0"
        sy = 0.0 if abs(y0) < 0.05 else -y0
        stem = "field_%s" % args.name + ("_L%d" % (k + 1) if args.layers > 1 else "")

        svg = os.path.join(outdir, stem + ".svg")
        write_svg(svg, pts, INKS[k % len(INKS)])

        if args.preview_only:
            print("%-28s preview only   %.1f m, ~%d min" % (stem, length / 1000.0, minutes))
            continue

        header = [
            " Interference field - dense serpentine scan warped by a wave field.",
            " ONE continuous stroke. NO pen lifts, NO Z words, NO M2/M5.",
            "",
            " Layer %d of %d.  seed=%d spacing=%.2f amp=%.2f scale=%.2f fold=%.2f"
            " step=%.2f F%d" % (k + 1, args.layers, args.seed, args.spacing, args.amp,
                                args.scale, args.fold, args.step, args.feed),
            " %d rows over %.0f mm, effective line pitch %.2f mm." % (
                2 * max(2, int(round(args.size / args.spacing))), args.size,
                args.spacing / 2.0),
            " Path length %.1f m, about %d minutes at F%d." % (
                length / 1000.0, round(minutes), args.feed),
            "",
            " >>> START POINT: %.1f mm right of, and %.1f mm up from, the" % (sx, sy),
            "     bottom-left corner of the drawn area.  Put the pen there. <<<",
            " The stroke returns to that exact point when it finishes.  For the next",
            " colour, swap the pen in the holder WITHOUT MOVING THE CARRIAGE and run",
            " the next layer - that is the whole registration method.",
            "",
            " Drawn area: %.1f x %.1f mm  (x %.1f..%.1f, y %.1f..%.1f from the start)" % (
                x1 - x0, y1 - y0, x0, x1, y0, y1),
        ]
        n_parts = max(1, args.split)
        edges = [round(i * (len(pts) - 1) / float(n_parts)) for i in range(n_parts + 1)]
        for part in range(n_parts):
            chunk = pts[edges[part]:edges[part + 1] + 1]
            name = stem + ("_p%d" % (part + 1) if n_parts > 1 else "")
            h = list(header)
            if n_parts > 1:
                h.insert(2, " PART %d of %d - run them in order, and DO NOT MOVE THE"
                            " CARRIAGE between parts." % (part + 1, n_parts))
            gc = os.path.join(outdir, name + ".gcode")
            nlines, endpos = write_gcode(gc, chunk, args.feed, h, origin=chunk[0])
            if n_parts == 1 and endpos != (0.0, 0.0):
                sys.exit("BUG: layer %d does not return to its start (%s)" % (k + 1, endpos))
            print("%-28s %6d lines  %.1f m  ~%3d min  bbox %.1f x %.1f mm" % (
                name, nlines, path_length(chunk) / 1000.0,
                round(path_length(chunk) / args.feed), x1 - x0, y1 - y0))

    if not args.preview_only:
        print("\nTotal plotting time for all layers: about %d h %d min." % (
            int(total_minutes // 60), int(total_minutes % 60)))
        print("Preview the .svg files before you start.")


if __name__ == "__main__":
    main()
