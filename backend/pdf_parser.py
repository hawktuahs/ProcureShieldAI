"""
PDF text extraction pipeline.

Strategy (in order):
1. PyMuPDF digital text  — works for text-layer PDFs, no system deps
2. pdfplumber             — cross-check / fallback for digital
3. Tesseract OCR via PyMuPDF page rendering  — for scanned/image PDFs
   * PyMuPDF renders pages to PNG in-process; NO poppler/pdf2image needed
   * On Windows, auto-detects the standard Tesseract-OCR install path
"""

import io
import logging
import os
import platform
from pathlib import Path

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
# Helpers
# ---------------------------------------------------------------------------

def _fitz_digital_text(filepath: str) -> str:
    """Extract embedded text using PyMuPDF (fastest, no deps)."""
    if not FITZ_AVAILABLE:
        return ""
    try:
        doc = fitz.open(filepath)
        pages_text = []
        for page in doc:
            pages_text.append(page.get_text())
        doc.close()
        return "\n\n".join(pages_text)
    except Exception as e:
        logger.debug(f"fitz digital extraction failed: {e}")
        return ""


def _pdfplumber_text(filepath: str) -> str:
    """Extract embedded text using pdfplumber."""
    if not PDFPLUMBER_AVAILABLE:
        return ""
    try:
        text = ""
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n\n"
        return text
    except Exception as e:
        logger.debug(f"pdfplumber extraction failed: {e}")
        return ""


def _ocr_via_fitz(filepath: str) -> str:
    """
    Render each PDF page to PNG with PyMuPDF, then run Tesseract.
    Does NOT require poppler or pdf2image — fitz handles rendering.
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
        return "\n\n".join(ocr_pages)
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"OCR processing failed: {e}") from e


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_text_from_pdf(filepath: str) -> tuple[str, str]:
    """
    Returns (text, method) where method is 'digital' or 'ocr'.

    Tries digital extraction first (fast). Falls back to Tesseract OCR
    if extracted text is too short (scanned/image-based PDF).
    """
    # 1. Try PyMuPDF digital (best for mixed PDFs)
    text = _fitz_digital_text(filepath)

    # 2. Try pdfplumber if fitz gave little
    if len(text.strip()) < 100 and PDFPLUMBER_AVAILABLE:
        text = _pdfplumber_text(filepath)

    if len(text.strip()) >= 100:
        logger.info(f"Digital extraction: {len(text)} chars from {Path(filepath).name}")
        return text.strip(), "digital"

    # 3. OCR fallback
    logger.info(f"Switching to OCR for {Path(filepath).name} (digital text < 100 chars)")
    try:
        ocr_text = _ocr_via_fitz(filepath)
        if len(ocr_text.strip()) < 50:
            logger.warning("OCR produced very little text — document may be blank or unreadable")
        logger.info(f"OCR extraction: {len(ocr_text)} chars from {Path(filepath).name}")
        return ocr_text.strip(), "ocr"
    except RuntimeError as e:
        # Tesseract not installed — return a clear install message
        msg = str(e)
        logger.error(f"OCR unavailable: {msg}")
        return f"[OCR required but unavailable: {msg}]", "ocr"


def extract_text_from_txt(filepath: str) -> tuple[str, str]:
    """Read plain text files (used for sample data testing)."""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read(), "digital"


def extract_text(filepath: str) -> tuple[str, str]:
    """Dispatch based on file extension."""
    path = Path(filepath)
    ext = path.suffix.lower()
    if ext in (".pdf",):
        return extract_text_from_pdf(filepath)
    elif ext in (".txt",):
        return extract_text_from_txt(filepath)
    else:
        return extract_text_from_pdf(filepath)
