"""
Creates sample PDF files for the TenderEval AI demo.
Run from the sample_data/ directory or the project root:
    python sample_data/create_sample_pdfs.py
"""

import os
import sys
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_CENTER

OUTPUT_DIR = Path(__file__).parent

SAMPLE_FILES = [
    "sample_tender.txt",
    "sample_bidder_1.txt",
    "sample_bidder_2.txt",
    "sample_bidder_3.txt",
]


def txt_to_pdf(txt_path: Path, pdf_path: Path):
    print(f"  Converting {txt_path.name} → {pdf_path.name}")
    text = txt_path.read_text(encoding="utf-8")

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    normal = ParagraphStyle("n", parent=styles["Normal"], fontSize=10, leading=14, spaceAfter=4)
    heading = ParagraphStyle("h", parent=styles["Normal"], fontSize=12, leading=16,
                              fontName="Helvetica-Bold", spaceAfter=6, spaceBefore=8,
                              textColor=colors.HexColor("#1e3a5f"))
    hr_style = ParagraphStyle("hr", parent=styles["Normal"], fontSize=8, textColor=colors.grey)

    story = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            story.append(Spacer(1, 0.15 * cm))
        elif stripped.startswith("---"):
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=4))
        elif (stripped.isupper() and len(stripped) > 10) or stripped.startswith("SECTION "):
            story.append(Paragraph(stripped, heading))
        else:
            story.append(Paragraph(stripped.replace("&", "&amp;"), normal))

    doc.build(story)


def main():
    print("TenderEval AI — Creating sample PDFs")
    print("=" * 40)

    created = []
    for fname in SAMPLE_FILES:
        txt_path = OUTPUT_DIR / fname
        if not txt_path.exists():
            print(f"  WARNING: {fname} not found, skipping")
            continue
        pdf_name = fname.replace(".txt", ".pdf")
        pdf_path = OUTPUT_DIR / pdf_name
        txt_to_pdf(txt_path, pdf_path)
        created.append(pdf_path)

    print("\nCreated PDFs:")
    for p in created:
        size_kb = p.stat().st_size // 1024
        print(f"  {p.name} ({size_kb} KB)")

    print(f"\nSample PDFs are in: {OUTPUT_DIR}")
    print("\nUpload order for demo:")
    print("  1. sample_tender.pdf  → Upload as tender")
    print("  2. sample_bidder_1.pdf → Clearly ELIGIBLE")
    print("  3. sample_bidder_2.pdf → NOT ELIGIBLE (fails turnover + ISO + EPF/ESIC)")
    print("  4. sample_bidder_3.pdf → NEEDS REVIEW (ambiguous turnover, expiring ISO, CPWD class mismatch)")


if __name__ == "__main__":
    main()
