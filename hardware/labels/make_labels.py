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
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

HERE = os.path.dirname(os.path.abspath(__file__))
PW, PH = A4
MARGIN = 12 * mm
GAP = 3 * mm

# label sizes in mm (w, h); change here when the real slots are measured
SIZE = {"bin": (80, 22), "samla": (90, 45), "loc": (70, 30)}
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


def code_block(c, code, x, y, w, h, size):
    c.setFillGray(0)
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
        code_block(c, row["code"], x, y, 17 * mm, h, 13)
        qr(c, row["code"], x + w - pad - q, y + pad, q)
        tx, tw = x + 17 * mm + pad, w - 17 * mm - q - 3 * pad
        if row["title"]:
            c.setFont("Helvetica-Bold", fit(c, row["title"], "Helvetica-Bold", 11, tw))
            c.drawString(tx, y + h - 9 * mm, row["title"])
            c.setFont("Helvetica", fit(c, row["sub"], "Helvetica", 7, tw))
            c.drawString(tx, y + 4.5 * mm, row["sub"])
        else:
            write_line(c, tx, y + h - 10 * mm, tw)
            write_line(c, tx, y + 4 * mm, tw)
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
    check_bar(c, scaled)
    c.showPage()


def main():
    with open(os.path.join(HERE, "labels.csv"), newline="") as f:
        rows = list(csv.DictReader(f))
    for name, scaled in (("labels.pdf", False), ("labels_plus7.pdf", True)):
        c = canvas.Canvas(os.path.join(HERE, name), pagesize=A4)
        c.setTitle("Harbor labels")
        for kind in ("bin", "samla", "loc"):
            sheet(c, kind, [r for r in rows if r["kind"] == kind], scaled)
        c.save()


if __name__ == "__main__":
    main()
