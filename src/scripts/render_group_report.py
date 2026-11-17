"""Render the Markdown report as A4 PDF. Requires reportlab and pypdf.

Run from the repository root: python src/scripts/render_group_report.py
These optional authoring dependencies are not required by the lab runtime.
"""
from pathlib import Path
import html
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output/pdf/group_report.pdf"


def inline(text):
    text = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", text)
    text = html.escape(text)
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    return text.replace("`", "")


def main():
    fonts = Path("C:/Windows/Fonts")
    pdfmetrics.registerFont(TTFont("Arial", str(fonts / "arial.ttf")))
    pdfmetrics.registerFont(TTFont("Arial-Bold", str(fonts / "arialbd.ttf")))
    pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-Bold", italic="Arial", boldItalic="Arial-Bold")
    body = ParagraphStyle("body", fontName="Arial", fontSize=10.4, leading=15, spaceAfter=8, alignment=TA_LEFT)
    heading = ParagraphStyle("heading", parent=body, fontName="Arial-Bold", fontSize=13, leading=18, spaceBefore=8, keepWithNext=True)
    title = ParagraphStyle("title", parent=heading, fontSize=19, leading=24, spaceAfter=15)
    small = ParagraphStyle("small", parent=body, fontSize=9, leading=12, spaceAfter=0, wordWrap="CJK")
    code = ParagraphStyle("code", parent=small, fontSize=8.2, leading=11, spaceAfter=3, wordWrap="CJK")
    lines = (ROOT / "report/team/group_report.md").read_text(encoding="utf-8-sig").splitlines()
    story, paragraph, rows = [], [], []

    def flush():
        if paragraph:
            story.append(Paragraph(inline(" ".join(paragraph)), body))
            paragraph.clear()
        if rows:
            widths = [511 / len(rows[0])] * len(rows[0])
            data = [[Paragraph(inline(cell), small) for cell in row] for row in rows]
            table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e7edf5")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#bcc7d4")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.extend([table, Spacer(1, 9)])
            rows.clear()

    in_code = False
    for line in lines:
        if line.startswith("```"):
            flush()
            in_code = not in_code
        elif in_code:
            story.append(Paragraph(html.escape(line), code))
        elif line == "<!-- pagebreak -->":
            flush()
            story.append(PageBreak())
        elif line.startswith("|"):
            if paragraph:
                story.append(Paragraph(inline(" ".join(paragraph)), body))
                paragraph.clear()
            if not re.fullmatch(r"[| :\-]+", line):
                rows.append([x.strip() for x in line.strip("|").split("|")])
        elif line.startswith("#"):
            flush()
            story.append(Paragraph(inline(line.lstrip("# ")), title if line.startswith("# ") else heading))
        elif not line.strip():
            flush()
        elif line.startswith("- "):
            flush()
            story.append(Paragraph(inline(line[2:]), body, bulletText="-"))
        else:
            paragraph.append(line)
    flush()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    def footer(canvas, doc):
        canvas.setFont("Arial", 8)
        canvas.setFillColor(colors.HexColor("#566579"))
        canvas.drawString(42, 26, "DongDong | Lab 8 | From Workflows to Agents")
        canvas.drawRightString(A4[0] - 42, 26, str(doc.page))

    SimpleDocTemplate(str(OUTPUT), pagesize=A4, rightMargin=42, leftMargin=42, topMargin=38, bottomMargin=42,
                      title="DongDong - Lab 8 group report", author="DongDong").build(story, onFirstPage=footer, onLaterPages=footer)
    pages = len(PdfReader(OUTPUT).pages)
    print(f"{OUTPUT}: {pages} pages")
    if pages > 5:
        raise RuntimeError("Report exceeds five pages")


if __name__ == "__main__":
    main()
