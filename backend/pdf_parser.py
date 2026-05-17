"""
PDF text extraction pipeline — page-aware edition.

Strategy (in order):
1. PyMuPDF digital text  — works for text-layer PDFs, no system deps
2. pdfplumber             — cross-check / fallback for digital
3. Tesseract OCR via PyMuPDF page rendering  — for scanned/image PDFs
   * PyMuPDF renders pages to PNG in-process; NO poppler/pdf2image needed
   * On Windows, auto-detects the standard Tesseract-OCR install path

All extraction functions now embed page markers:
    --- PAGE 1 ---
    ... text from page 1 ...
    --- PAGE 2 ---
    ... text from page 2 ...

This lets the LLM report page numbers in its extractions, and lets us
trace every extracted criterion back to its exact source page.
"""

import io
import logging
import os
import platform
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional imports
# ---------------------------------------------------------------------------

try:
    import fitz  # pymupdf
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
    # Auto-detect Windows Tesseract install path
    if platform.system() == "Windows":
        win_candidates = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
        ]
        for candidate in win_candidates:
            if os.path.exists(candidate):
                pytesseract.pytesseract.tesseract_cmd = candidate
                logger.info(f"Tesseract found at: {candidate}")
                break
except ImportError:
    TESSERACT_AVAILABLE = False


# ---------------------------------------------------------------------------
# Per-page extraction helpers
# ---------------------------------------------------------------------------

def _fitz_pages(filepath: str) -> list[str]:
    """Extract embedded text per page using PyMuPDF. Returns list indexed by page (0-based)."""
    if not FITZ_AVAILABLE:
        return []
    try:
        doc = fitz.open(filepath)
        pages = [page.get_text() for page in doc]
        doc.close()
        return pages
    except Exception as e:
        logger.debug(f"fitz digital extraction failed: {e}")
        return []


def _pdfplumber_pages(filepath: str) -> list[str]:
    """Extract embedded text per page using pdfplumber."""
    if not PDFPLUMBER_AVAILABLE:
        return []
    try:
        pages = []
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        if not table or not table[0]: continue
                        lines = []
                        for i, row in enumerate(table):
                            cleaned_row = [" ".join(str(cell).split()) if cell else "" for cell in row]
                            lines.append("| " + " | ".join(cleaned_row) + " |")
                            if i == 0:
                                lines.append("|" + "|".join(["---"] * len(cleaned_row)) + "|")
                        text += "\n\n" + "\n".join(lines) + "\n"
                pages.append(text)
        return pages
    except Exception as e:
        logger.debug(f"pdfplumber extraction failed: {e}")
        return []


def _ocr_pages_via_fitz(filepath: str) -> list[str]:
    """
    Render each PDF page to PNG with PyMuPDF, then run Tesseract.
    Returns list of page texts (0-indexed).
    """
    if not FITZ_AVAILABLE:
        raise RuntimeError("PyMuPDF (pymupdf) is not installed. Run: pip install pymupdf")
    if not TESSERACT_AVAILABLE:
        raise RuntimeError(
            "pytesseract or Pillow not installed.\n"
            "Run: pip install pytesseract Pillow\n"
            "Also install Tesseract OCR engine:\n"
            "  Windows: https://github.com/UB-Mannheim/tesseract/wiki\n"
            "  Linux:   sudo apt install tesseract-ocr\n"
            "  macOS:   brew install tesseract"
        )
    try:
        doc = fitz.open(filepath)
        ocr_pages = []
        for page_num, page in enumerate(doc):
            # 2× zoom → ~150 dpi, good balance of speed vs accuracy
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)
            img_bytes = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_bytes))
            page_text = pytesseract.image_to_string(img, lang="eng", config="--psm 6")
            ocr_pages.append(page_text)
            logger.debug(f"OCR page {page_num + 1}/{len(doc)}: {len(page_text)} chars")
        doc.close()
        return ocr_pages
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"OCR processing failed: {e}") from e


def _pages_to_text_with_markers(pages: list[str]) -> str:
    """Combine per-page text into a single string with page markers."""
    parts = []
    for i, page_text in enumerate(pages):
        parts.append(f"\n--- PAGE {i + 1} ---\n")
        parts.append(page_text.strip())
    return "\n".join(parts)


def _total_text_length(pages: list[str]) -> int:
    return sum(len(p.strip()) for p in pages)


def get_page_count(filepath: str) -> int:
    """Return total number of pages in a PDF."""
    if not FITZ_AVAILABLE:
        return 0
    try:
        doc = fitz.open(filepath)
        count = len(doc)
        doc.close()
        return count
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_text_from_pdf(filepath: str) -> tuple[str, str, int]:
    """
    Returns (text_with_page_markers, method, page_count).
    method is 'digital' or 'ocr'.

    Text includes page markers like:
        --- PAGE 1 ---
        ... text ...
        --- PAGE 2 ---
        ... text ...
    """
    # 1. Try pdfplumber first (best for tables)
    pages = _pdfplumber_pages(filepath)

    # 2. Try PyMuPDF digital if pdfplumber failed or gave nothing
    if _total_text_length(pages) < 100:
        pages = _fitz_pages(filepath)

    page_count = len(pages) if pages else get_page_count(filepath)

    if _total_text_length(pages) >= 100:
        text = _pages_to_text_with_markers(pages)
        logger.info(f"Digital extraction: {len(text)} chars, {page_count} pages from {Path(filepath).name}")
        return text.strip(), "digital", page_count

    # 3. OCR fallback
    logger.info(f"Switching to OCR for {Path(filepath).name} (digital text < 100 chars)")
    try:
        ocr_pages = _ocr_pages_via_fitz(filepath)
        page_count = len(ocr_pages)
        text = _pages_to_text_with_markers(ocr_pages)
        if _total_text_length(ocr_pages) < 50:
            logger.warning("OCR produced very little text — document may be blank or unreadable")
        logger.info(f"OCR extraction: {len(text)} chars, {page_count} pages from {Path(filepath).name}")
        return text.strip(), "ocr", page_count
    except RuntimeError as e:
        msg = str(e)
        logger.error(f"OCR unavailable: {msg}")
        return f"[OCR required but unavailable: {msg}]", "ocr", page_count


def extract_text_from_txt(filepath: str) -> tuple[str, str, int]:
    """Read plain text files (used for sample data testing)."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    # Wrap in a single page marker for consistency
    text = f"\n--- PAGE 1 ---\n{content}"
    return text, "digital", 1


def extract_text(filepath: str) -> tuple[str, str, int]:
    """
    Dispatch based on file extension.
    Returns (text_with_page_markers, method, page_count).
    """
    path = Path(filepath)
    ext = path.suffix.lower()
    if ext in (".pdf",):
        return extract_text_from_pdf(filepath)
    elif ext in (".txt",):
        return extract_text_from_txt(filepath)
    else:
        return extract_text_from_pdf(filepath)
