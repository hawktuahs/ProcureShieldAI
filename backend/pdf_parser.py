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
import re
from pathlib import Path
from typing import List, Tuple, Optional

# Imaging and OCR
try:
    import fitz  # PyMuPDF
    from PIL import Image, ImageEnhance, ImageOps
    import pytesseract
    FITZ_AVAILABLE = True
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
                break
except ImportError:
    FITZ_AVAILABLE = False
    TESSERACT_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

logger = logging.getLogger(__name__)


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
                # layout=True helps preserve table structure in digital text
                text = page.extract_text(layout=True) or ""
                try:
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            if not table or not any(table[0]): continue
                            lines = []
                            for i, row in enumerate(table):
                                cleaned_row = [" ".join(str(cell).split()) if cell else "" for cell in row]
                                if not any(cleaned_row): continue
                                lines.append("| " + " | ".join(cleaned_row) + " |")
                                if i == 0:
                                    lines.append("|" + "|".join(["---"] * len(cleaned_row)) + "|")
                            if lines:
                                text += "\n\n### Table Data ###\n" + "\n".join(lines) + "\n"
                except Exception:
                    pass
                pages.append(text)
        return pages
    except Exception as e:
        logger.debug(f"pdfplumber extraction failed: {e}")
        return []


def _ocr_pages_via_fitz(filepath: str) -> list[str]:
    """
    Render each PDF page to PNG with PyMuPDF, enhance for OCR, then run Tesseract.
    """
    if not FITZ_AVAILABLE or not TESSERACT_AVAILABLE:
        return []
    try:
        doc = fitz.open(filepath)
        ocr_pages = []
        langs = "eng+hin"
        for page_num, page in enumerate(doc):
            # High resolution for better table detail
            mat = fitz.Matrix(3.5, 3.5)
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)
            img_bytes = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_bytes))
            
            # Image Preprocessing for better OCR on blurry/small table text
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2.0)
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.5)
            
            # Use PSM 6 (Assume a single uniform block of text) for table-heavy pages
            # or PSM 3 for general layout. 6 is often better for tabular data OCR.
            page_text = pytesseract.image_to_string(img, lang=langs, config="--psm 6")
            
            ocr_pages.append(page_text)
            logger.debug(f"OCR page {page_num + 1}/{len(doc)}: {len(page_text)} chars")
        doc.close()
        return ocr_pages
    except Exception as e:
        logger.error(f"OCR processing failed: {e}")
        return []


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

def extract_text_from_pdf(filepath: str) -> Tuple[str, str, int]:
    """
    Extract text from PDF using a hybrid strategy:
    1. Try pdfplumber for digital text and tables.
    2. If text is sparse or missing on key pages, use OCR.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"PDF not found: {filepath}")

    digital_pages = []
    if PDFPLUMBER_AVAILABLE:
        digital_pages = _pdfplumber_pages(filepath)

    page_count = len(digital_pages) if digital_pages else get_page_count(filepath)
    
    # Hybrid Check: Many tenders have digital headers but image-based tables.
    total_digital_len = sum(len(p) for p in digital_pages)
    
    use_ocr = False
    if total_digital_len < 300:
        use_ocr = True
        logger.info(f"PDF seems to be an image ({total_digital_len} chars). Using OCR.")
    
    if not use_ocr and FITZ_AVAILABLE and TESSERACT_AVAILABLE:
        sparse_pages = [i for i, p in enumerate(digital_pages) if len(p.strip()) < 200]
        if len(sparse_pages) > 0:
            logger.info(f"Found {len(sparse_pages)} sparse pages. Running hybrid OCR.")
            ocr_pages = _ocr_pages_via_fitz(filepath)
            
            final_pages = []
            for i in range(max(len(digital_pages), len(ocr_pages))):
                d_text = digital_pages[i] if i < len(digital_pages) else ""
                o_text = ocr_pages[i] if i < len(ocr_pages) else ""
                
                if len(d_text.strip()) < 200 and len(o_text.strip()) > len(d_text.strip()):
                    final_pages.append(f"--- PAGE {i+1} ---\n{o_text}")
                else:
                    final_pages.append(f"--- PAGE {i+1} ---\n{d_text}")
            
            return "\n\n".join(final_pages), "hybrid-ocr", page_count

    if use_ocr and FITZ_AVAILABLE and TESSERACT_AVAILABLE:
        ocr_pages = _ocr_pages_via_fitz(filepath)
        final_text = ""
        for i, p in enumerate(ocr_pages):
            final_text += f"--- PAGE {i+1} ---\n{p}\n\n"
        return final_text.strip(), "ocr", len(ocr_pages)

    final_text = ""
    for i, p in enumerate(digital_pages):
        final_text += f"--- PAGE {i+1} ---\n{p}\n\n"
    return final_text.strip(), "digital", page_count


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
