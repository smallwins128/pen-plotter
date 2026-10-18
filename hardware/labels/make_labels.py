"""Room R05 Harbor: print sheets for bin, SAMLA and location labels.

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
from reportlab.pdfgen import canvas

HERE = os.path.dirname(os.path.abspath(__file__))
PW, PH = A4
MARGIN = 12 * mm
GAP = 3 * mm

# label sizes in mm (w, h); change here when the real slots are measured
SIZE = {"bin": (60, 12), "samla": (90, 45), "loc": (70, 30)}
# bin colour by family: screws by diameter, the rest by part type
FAMILY = {"m2": ("#E0B000", "M2 · M2.5"), "m3": ("#1F5FAD", "M3"), "m4": ("#2E8540", "M4"),
          "m5": ("#E06A10", "M5"), "nut": ("#C62828", "nuts"), "washer": ("#5A5A5A", "washers · spacers"),
          "rivet": ("#6A3FA0", "rivets")}
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


def write_line(c, x, y, w):
    c.setStrokeGray(0.6)
    c.setLineWidth(0.4)
    c.line(x, y, x + w, y)


def draw_label(c, row, x, y):
    kind = row["kind"]
    w, h = SIZE[kind][0] * mm, SIZE[kind][1] * mm
    c.setStrokeGray(0.75)
    c.setLineWidth(0.3)
    c.rect(x, y, w, h, stroke=1, fill=0)
    pad = 2 * mm
    q = h - 2 * pad
    if kind == "bin":
        bw = 13 * mm
        if row["family"]:
            code_block(c, row["code"], x, y, bw, h, 12, FAMILY[row["family"]][0])
        else:
            c.setStrokeGray(0)
            c.setLineWidth(0.8)
            c.rect(x, y, bw, h, stroke=1, fill=0)
            c.setFont("Helvetica-Bold", 12)
            c.drawCentredString(x + bw / 2, y + h / 2 - 4.2, row["code"])
        tx, tw = x + bw + 1.5 * mm, w - bw - 2.5 * mm
        if row["title"] and row["sub"]:
            c.setFont("Helvetica-Bold", fit(c, row["title"], "Helvetica-Bold", 15, tw))
            c.drawString(tx, y + 4.6 * mm, row["title"])
            c.setFont("Helvetica", fit(c, row["sub"], "Helvetica", 6.5, tw))
            c.drawString(tx, y + 1.4 * mm, row["sub"])
        elif row["title"]:
            sz = fit(c, row["title"], "Helvetica-Bold", 18, tw)
            c.setFont("Helvetica-Bold", sz)
            c.drawString(tx, y + h / 2 - sz * 0.35, row["title"])
        else:
            write_line(c, tx, y + 3 * mm, tw - 1 * mm)
    elif kind == "samla":
        code_block(c, row["code"], x, y + h - 14 * mm, 22 * mm, 14 * mm, 18)
        q = 24 * mm
        qr(c, row["code"], x + w - pad - q, y + pad, q)
        tw = w - q - 3 * pad
        c.setFont("Helvetica-Bold", fit(c, row["title"], "Helvetica-Bold", 15, tw))
        c.drawString(x + pad, y + h - 22 * mm, row["title"])
        c.setFont("Helvetica", 8)
        c.drawString(x + pad, y + h - 28 * mm, row["sub"])
        c.setFont("Helvetica", 7)
        c.setFillGray(0.35)
        c.drawString(x + pad, y + pad + 1 * mm, "HOME")
        c.setFillGray(0)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x + pad + 9 * mm, y + pad + 1 * mm, row["home"])
    else:
        q = 20 * mm
        qr(c, row["code"], x + w - pad - q, y + (h - q) / 2, q)
        tw = w - q - 3 * pad
        c.setFont("Helvetica-Bold", fit(c, row["code"], "Helvetica-Bold", 24, tw))
        c.drawString(x + pad, y + h - 12 * mm, row["code"])
        c.setFont("Helvetica-Bold", fit(c, row["title"], "Helvetica-Bold", 9, tw))
        c.drawString(x + pad, y + 9 * mm, row["title"])
        c.setFont("Helvetica", fit(c, row["sub"], "Helvetica", 7, tw))
        c.drawString(x + pad, y + 4 * mm, row["sub"])


def check_bar(c, scaled):
    y = MARGIN
    c.setStrokeGray(0)
    c.setLineWidth(0.8)
    c.line(MARGIN, y, MARGIN + 100 * mm, y)
    for i in range(11):
        t = 3 * mm if i % 5 == 0 else 1.5 * mm
        c.line(MARGIN + i * 10 * mm, y, MARGIN + i * 10 * mm, y + t)
    c.setFont("Helvetica", 7)
    note = "this bar must measure 100 mm after printing" if not scaled else \
        "pre-scaled +7%: this bar must measure 100 mm after printing"
    c.drawString(MARGIN + 104 * mm, y, note)


def sheet(c, kind, rows, scaled):
    if scaled:
        c.translate(PW / 2, PH / 2)
        c.scale(15 / 14, 15 / 14)
        c.translate(-PW / 2, -PH / 2)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(MARGIN, PH - MARGIN - 4 * mm, f"R05 Harbor · {SHEET[kind]}")
    c.setFont("Helvetica", 7)
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
    c.setFont("Helvetica", 8)
    c.setFillGray(0)
    c.drawString(x, y, "Colour key:")
    x += 18 * mm
    for col, name in FAMILY.values():
        c.setFillColor(HexColor(col))
        c.rect(x, y - 1, 4 * mm, 3.2 * mm, stroke=0, fill=1)
        c.setFillGray(0)
        c.drawString(x + 5 * mm, y, name)
        x += 5 * mm + c.stringWidth(name, "Helvetica", 8) + 5 * mm


def main():
    with open(os.path.join(HERE, "labels.csv"), newline="") as f:
        rows = list(csv.DictReader(f))
    for name, scaled in (("labels.pdf", False), ("labels_plus7.pdf", True)):
        c = canvas.Canvas(os.path.join(HERE, name), pagesize=A4)
        c.setTitle("Harbor labels")
        for kind in ("bin", "samla", "loc"):
            picked = [r for r in rows if r["kind"] == kind]
            # bins are small and cheap to misplace: print two of each
            sheet(c, kind, picked * 2 if kind == "bin" else picked, scaled)
        c.save()


if __name__ == "__main__":
    main()
