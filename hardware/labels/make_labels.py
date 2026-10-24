"""Room R05 Harbor: print sheets for bin, SAMLA and location labels.

Fonts in fonts/ are Barlow Condensed and IBM Plex Mono (SIL Open Font License, Google Fonts).

Reads labels.csv, writes labels.pdf (true size) and labels_plus7.pdf (scaled up
15/14 for a print shop that shrinks to fit). Each sheet carries a 100 mm check bar.

    python3 make_labels.py
"""
import csv
import os

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

HERE = os.path.dirname(os.path.abspath(__file__))
PW, PH = A4
MARGIN = 12 * mm
GAP = 3 * mm

# label sizes in mm (w, h); change here when the real slots are measured
SIZE = {"bin": (60, 12), "samla": (90, 45), "loc": (88, 38)}
# screw sizes use the resistor colour code, so the digit is the colour (M3 = orange = 3);
# other parts get a black block with a shape icon instead
FAMILY = {"m2": ("#D32F2F", "M2 red"), "m3": ("#EF6C00", "M3 orange"), "m4": ("#F9C80E", "M4 yellow"),
          "m5": ("#2E7D32", "M5 green"), "m6": ("#1565C0", "M6 blue"),
          "nut": ("#1C1C1C", "nuts"), "washer": ("#1C1C1C", "washers"), "rivet": ("#1C1C1C", "rivets")}
DARK_TEXT = {"m4"}
# SAMLA boxes carry a band for the overarching category
CATEGORY = {"electronics": ("#00838F", "ELECTRONICS"), "electricals": ("#B71C1C", "ELECTRICALS"),
            "plumbing": ("#1565C0", "PLUMBING"), "woodworking": ("#795548", "WOODWORKING"),
            "sewing": ("#C2185B", "SEWING"), "art": ("#6A1B9A", "ART SUPPLIES"),
            "hardware": ("#455A64", "HARDWARE"), "mechanical": ("#212121", "MECHANICAL"),
            "fasteners": ("#9E7C0C", "FASTENERS")}
# a spot inside another spot passes its contents up (rack B stands in A3)
PARENT = {"RB-1": "A3", "RB-2": "A3"}
# what this print run includes; spot cards and box homes wait until storage is final
PRINT = ("bin", "samla")
PRINT_HOMES = False
# condensed display face for names, mono for codes and field labels (both OFL, in fonts/)
for _f in ("BarlowCondensed-ExtraBold", "BarlowCondensed-Medium", "IBMPlexMono-Regular", "IBMPlexMono-SemiBold"):
    pdfmetrics.registerFont(TTFont(_f, os.path.join(HERE, "fonts", _f + ".ttf")))
DISPLAY, MONO, MONO_B = "BarlowCondensed-ExtraBold", "IBMPlexMono-Regular", "IBMPlexMono-SemiBold"
SHEET = {"bin": "Grey bins", "samla": "SAMLA boxes", "loc": "Cupboard and rack spots"}


def qr(c, text, x, y, size):
    w = QrCodeWidget(text, barLevel="M", barBorder=0)
    x0, y0, x1, y1 = w.getBounds()
    d = Drawing(size, size, transform=[size / (x1 - x0), 0, 0, size / (y1 - y0), 0, 0])
    d.add(w)
    renderPDF.draw(d, c, x, y)


def fit(c, text, font, size, maxw):
    while size > 5 and c.stringWidth(text, font, size) > maxw:
        size -= 0.25
    return size


def code_block(c, code, x, y, w, h, size, fill="#000000"):
    c.setFillColor(HexColor(fill))
    c.rect(x, y, w, h, stroke=0, fill=1)
    c.setFillGray(1)
    s = fit(c, code, "Helvetica-Bold", size, w - 2 * mm)
    c.setFont("Helvetica-Bold", s)
    c.drawCentredString(x + w / 2, y + h / 2 - s * 0.35, code)
    c.setFillGray(0)


def icon(c, fam, cx, cy, r):
    """White part silhouette: hex nut, washer ring or rivet."""
    import math
    c.setFillGray(1)
    c.setStrokeGray(1)
    if fam in ("nut", "washer"):
        p = c.beginPath()
        if fam == "nut":
            for i in range(6):
                a = math.radians(60 * i)
                (p.moveTo if i == 0 else p.lineTo)(cx + r * math.cos(a), cy + r * math.sin(a))
            p.close()
        else:
            p.circle(cx, cy, r)
        p.circle(cx, cy, r * 0.45)
        c.drawPath(p, stroke=0, fill=1, fillMode=0)
    else:
        c.wedge(cx - r * 0.9, cy + r * 0.15, cx + r * 0.9, cy + r * 1.3, 180, 180, stroke=0, fill=1)
        c.rect(cx - r * 0.25, cy - r * 1.1, r * 0.5, r * 1.85, stroke=0, fill=1)
    c.setFillGray(0)


def write_line(c, x, y, w):
    c.setStrokeGray(0.6)
    c.setLineWidth(0.4)
    c.line(x, y, x + w, y)


def draw_label(c, row, x, y):
    kind = row["kind"]
    w, h = SIZE[kind][0] * mm, SIZE[kind][1] * mm
    if kind != "samla":
        c.setStrokeGray(0.8)
        c.setLineWidth(0.25)
        c.rect(x, y, w, h, stroke=1, fill=0)
    pad = 2 * mm
    q = h - 2 * pad
    if kind == "bin":
        draw_bin(c, row, x, y, w, h)
    elif kind == "samla":
        draw_samla(c, row, x, y, w, h)
    else:
        q = 22 * mm
        qr(c, row["code"], x + w - pad - q, y + h - pad - q, q)
        tw = w - q - 3 * pad
        c.setFont("Helvetica-Bold", fit(c, row["code"], "Helvetica-Bold", 28, tw))
        c.drawString(x + pad, y + h - 12 * mm, row["code"])
        c.setFont("Helvetica-Bold", fit(c, row["title"], "Helvetica-Bold", 10, tw))
        c.drawString(x + pad, y + h - 18 * mm, row["title"])
        c.setFont("Helvetica", fit(c, row["sub"], "Helvetica", 7, tw))
        c.drawString(x + pad, y + h - 22.5 * mm, row["sub"])
        chips(c, row.get("contains", []), x + pad, y + pad, w - 2 * pad)


def field(c, name, x, y):
    """Tiny field name, as in a drawing title block."""
    c.setFont(MONO, 4.6)
    c.setFillGray(0.4)
    c.drawString(x, y, name)
    c.setFillGray(0)


def draw_bin(c, row, x, y, w, h):
    bw = 15 * mm
    fam = row["family"]
    if fam:
        c.setFillColor(HexColor(FAMILY[fam][0]))
        c.rect(x, y, bw, h, stroke=0, fill=1)
        if row["size"]:
            c.setFillGray(0 if fam in DARK_TEXT else 1)
            sz = fit(c, row["size"], DISPLAY, 30, bw - 1.5 * mm)
            c.setFont(DISPLAY, sz)
            c.drawCentredString(x + bw / 2, y + h / 2 - sz * 0.34, row["size"])
        else:
            icon(c, fam, x + bw / 2, y + h / 2, h * 0.34)
    else:
        c.setStrokeGray(0)
        c.setLineWidth(0.8)
        c.rect(x, y, bw, h, stroke=1, fill=0)
    tx = x + bw + 1.4 * mm
    tw = w - bw - 2.4 * mm
    # top line: code and detail in mono
    c.setFillGray(0)
    c.setFont(MONO_B, 5)
    c.drawString(tx, y + h - 2.6 * mm, row["code"])
    if row["sub"]:
        c.setFont(MONO, 5)
        c.setFillGray(0.35)
        c.drawString(tx + c.stringWidth(row["code"] + "  ", MONO_B, 5), y + h - 2.6 * mm, row["sub"].upper())
        c.setFillGray(0)
    if row["title"]:
        c.setFont(DISPLAY, fit(c, row["title"], DISPLAY, 21, tw))
        c.drawString(tx, y + 3.1 * mm, row["title"])
    else:
        write_line(c, tx, y + 3.4 * mm, tw)
    # millimetre scale from the colour block's edge: butt a screw head against it to read its length
    c.setStrokeGray(0)
    for i in range(int(tw / mm) + 1):
        t = 1.9 if i % 10 == 0 else 1.25 if i % 5 == 0 else 0.7
        c.setLineWidth(0.35 if i % 5 == 0 else 0.2)
        c.line(x + bw + i * mm, y, x + bw + i * mm, y + t * mm)


def draw_samla(c, row, x, y, w, h):
    strip, qcol, low = 8 * mm, 25 * mm, 11 * mm
    cat = CATEGORY.get(row["category"])
    # category strip down the left edge, name reading upwards
    if cat:
        c.setFillColor(HexColor(cat[0]))
        c.rect(x, y, strip, h, stroke=0, fill=1)
        c.saveState()
        c.translate(x + strip / 2 + 2.3 * mm, y + h / 2)
        c.rotate(90)
        c.setFillGray(1)
        c.setFont(DISPLAY, fit(c, cat[1], DISPLAY, 15, h - 4 * mm))
        c.drawCentredString(0, 0, cat[1])
        c.restoreState()
    # title-block frame and cells
    c.setStrokeGray(0)
    c.setLineWidth(0.7)
    c.rect(x, y, w, h, stroke=1, fill=0)
    c.setLineWidth(0.35)
    mx, mw = x + strip, w - strip - qcol
    c.line(mx, y, mx, y + h)
    c.line(mx + mw, y, mx + mw, y + h)
    c.line(mx, y + low, mx + mw, y + low)
    cells = [("CODE", 22 * mm), ("SIZE", 14 * mm), ("HOME", mw - 36 * mm)]
    cx = mx
    for name, cw in cells:
        if cx > mx:
            c.line(cx, y, cx, y + low)
        field(c, name, cx + 1.2 * mm, y + low - 2.2 * mm)
        cx += cw
    c.setFont(DISPLAY, 17)
    c.drawString(mx + 1.2 * mm, y + 1.6 * mm, row["code"])
    c.setFont(MONO_B, 9)
    c.drawString(mx + 22 * mm + 1.2 * mm, y + 2.2 * mm, row["sub"])
    if PRINT_HOMES and row["home"]:
        c.setFont(MONO_B, 9)
        c.drawString(mx + 36 * mm + 1.2 * mm, y + 2.2 * mm, row["home"])
    # contents cell
    field(c, "CONTENTS", mx + 1.2 * mm, y + h - 2.8 * mm)
    tw = mw - 2.4 * mm
    if row["title"]:
        c.setFont(DISPLAY, fit(c, row["title"], DISPLAY, 30, tw))
        c.drawString(mx + 1.2 * mm, y + low + 11 * mm, row["title"])
    else:
        write_line(c, mx + 1.2 * mm, y + low + 14 * mm, tw)
        write_line(c, mx + 1.2 * mm, y + low + 5 * mm, tw)
    # QR column
    q = 21 * mm
    field(c, "SCAN", mx + mw + 1.2 * mm, y + h - 2.8 * mm)
    qr(c, row["code"], mx + mw + (qcol - q) / 2, y + (h - q) / 2 - 1.5 * mm, q)


def chips(c, cats, x, y, maxw):
    """Row of category colour chips along the bottom of a spot card."""
    c.setStrokeGray(0.6)
    c.setLineWidth(0.4)
    c.line(x, y + 7.5 * mm, x + maxw, y + 7.5 * mm)
    if not cats:
        c.setFont("Helvetica", 7)
        c.setFillGray(0.45)
        c.drawString(x, y + 2 * mm, "CONTAINS")
        write_line(c, x + 15 * mm, y + 1.8 * mm, maxw - 15 * mm)
        c.setFillGray(0)
        return
    cx, ch = x, 5.5 * mm
    for k in cats:
        col, name = CATEGORY[k]
        size = 7
        cw = c.stringWidth(name, "Helvetica-Bold", size) + 3 * mm
        if cx + cw > x + maxw:
            break
        c.setFillColor(HexColor(col))
        c.roundRect(cx, y, cw, ch, 1 * mm, stroke=0, fill=1)
        c.setFillGray(1)
        c.setFont("Helvetica-Bold", size)
        c.drawString(cx + 1.5 * mm, y + 1.8 * mm, name)
        cx += cw + 1.5 * mm
    c.setFillGray(0)


def contents(rows):
    """Categories held at each spot, from where each box lives."""
    held = {}
    for r in rows:
        if r["kind"] == "samla" and r["home"] and r["category"]:
            spot = r["home"]
            while spot:
                held.setdefault(spot, [])
                if r["category"] not in held[spot]:
                    held[spot].append(r["category"])
                spot = PARENT.get(spot) or (spot.split("-")[0] if "-" in spot else None)
    return held


def check_bar(c, scaled):
    y = MARGIN
    c.setStrokeGray(0)
    c.setLineWidth(0.8)
    c.line(MARGIN, y, MARGIN + 100 * mm, y)
    for i in range(11):
        t = 3 * mm if i % 5 == 0 else 1.5 * mm
        c.line(MARGIN + i * 10 * mm, y, MARGIN + i * 10 * mm, y + t)
    c.setFont(MONO, 7)
    note = "this bar must measure 100 mm after printing" if not scaled else \
        "pre-scaled +7%: this bar must measure 100 mm after printing"
    c.drawString(MARGIN + 104 * mm, y, note)


def sheet(c, kind, rows, scaled):
    h = SIZE[kind][1] * mm
    per_row = int((PW - 2 * MARGIN + GAP) // (SIZE[kind][0] * mm + GAP))
    fit_rows = int((PH - 2 * MARGIN - 10 * mm - 20 * mm + GAP) // (h + GAP))
    n = per_row * fit_rows
    for i in range(0, len(rows), n):
        page(c, kind, rows[i:i + n], scaled)


def page(c, kind, rows, scaled):
    if scaled:
        c.translate(PW / 2, PH / 2)
        c.scale(15 / 14, 15 / 14)
        c.translate(-PW / 2, -PH / 2)
    c.setFont(DISPLAY, 13)
    c.drawString(MARGIN, PH - MARGIN - 4 * mm, f"R05 HARBOR · {SHEET[kind].upper()}")
    c.setFont(MONO, 7)
    c.drawRightString(PW - MARGIN, PH - MARGIN - 4 * mm,
                      "Print at 100% / actual size. Do not use fit to page.")
    w, h = SIZE[kind][0] * mm, SIZE[kind][1] * mm
    cols = int((PW - 2 * MARGIN + GAP) // (w + GAP))
    x0 = (PW - (cols * w + (cols - 1) * GAP)) / 2
    top = PH - MARGIN - 10 * mm
    for i, row in enumerate(rows):
        r, k = divmod(i, cols)
        draw_label(c, row, x0 + k * (w + GAP), top - (r + 1) * h - r * GAP)
    if kind == "bin":
        legend(c, top - (r + 1) * h - r * GAP - 12 * mm)
    check_bar(c, scaled)
    c.showPage()


def legend(c, y):
    x = MARGIN
    c.setFont(MONO, 8)
    c.setFillGray(0)
    c.drawString(x, y, "Resistor colour code:")
    x += c.stringWidth("Resistor colour code:", MONO, 8) + 4 * mm
    for col, name in [v for k, v in FAMILY.items() if k.startswith("m")]:
        c.setFillColor(HexColor(col))
        c.rect(x, y - 1, 4 * mm, 3.2 * mm, stroke=0, fill=1)
        c.setFillGray(0)
        c.drawString(x + 5 * mm, y, name)
        x += 5 * mm + c.stringWidth(name, MONO, 8) + 4 * mm
    c.drawString(MARGIN, y - 5 * mm, "Black with a shape: nuts, washers, rivets. Bottom edge is a mm scale from the colour block.")


def main():
    with open(os.path.join(HERE, "labels.csv"), newline="") as f:
        rows = list(csv.DictReader(f))
    held = contents(rows)
    for r in rows:
        if r["kind"] == "loc":
            r["contains"] = held.get(r["code"], [])
    for name, scaled in (("labels.pdf", False), ("labels_plus7.pdf", True)):
        c = canvas.Canvas(os.path.join(HERE, name), pagesize=A4)
        c.setTitle("Harbor labels")
        for kind in PRINT:
            picked = [r for r in rows if r["kind"] == kind]
            # bins are small and cheap to misplace: print two of each
            sheet(c, kind, picked * 2 if kind == "bin" else picked, scaled)
        c.save()


if __name__ == "__main__":
    main()
