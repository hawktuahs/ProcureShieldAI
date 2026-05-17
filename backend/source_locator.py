"""
Source Locator — link extracted text back to its physical location in the PDF.

Provides two main functions:
1. locate_source()  — find which page and bounding box a text snippet lives on
2. render_page_with_highlight() — render a PDF page as PNG with a highlighted region

Works for both digital PDFs (precise text search) and scanned/OCR PDFs
(fuzzy text matching with word-level position reconstruction).
"""

import io
import logging
import re
from difflib import SequenceMatcher
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import fitz  # pymupdf
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False


# ---------------------------------------------------------------------------
# Text search helpers
# ---------------------------------------------------------------------------

def _normalise(text: str) -> str:
    """Collapse whitespace and lowercase for fuzzy matching."""
    return re.sub(r"\s+", " ", text.strip().lower())


def _similarity(a: str, b: str) -> float:
    """Quick similarity ratio between two strings."""
    return SequenceMatcher(None, _normalise(a), _normalise(b)).ratio()


def _search_page_fitz(page, query: str) -> Optional[dict]:
    """
    Search for query text on a PyMuPDF page.
    Returns bounding box dict {x0, y0, x1, y1} or None.
    Uses page.search_for() for exact matching, falling back to
    progressively shorter substrings for fuzzy matching.
    """
    # Try exact search first
    results = page.search_for(query, quads=False)
    if results:
        # Merge all matching rects into one bounding box
        x0 = min(r.x0 for r in results)
        y0 = min(r.y0 for r in results)
        x1 = max(r.x1 for r in results)
        y1 = max(r.y1 for r in results)
        return {"x0": round(x0, 1), "y0": round(y0, 1),
                "x1": round(x1, 1), "y1": round(y1, 1)}

    # Try progressively shorter prefixes (fuzzy fallback)
    words = query.split()
    for length in range(min(len(words), 12), 2, -1):
        sub = " ".join(words[:length])
        results = page.search_for(sub, quads=False)
        if results:
            x0 = min(r.x0 for r in results)
            y0 = min(r.y0 for r in results)
            x1 = max(r.x1 for r in results)
            y1 = max(r.y1 for r in results)
            # Expand the box slightly to account for the missing suffix
            return {"x0": round(x0, 1), "y0": round(max(0, y0 - 2), 1),
                    "x1": round(min(page.rect.width, x1 + 40), 1),
                    "y1": round(min(page.rect.height, y1 + 2), 1)}

    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def locate_source(
    filepath: str,
    source_text: str,
    page_hint: Optional[int] = None,
) -> dict:
    """
    Find the page and bounding box for a source text snippet.

    Args:
        filepath: Path to the PDF file
        source_text: The text snippet to locate (from raw_source_text)
        page_hint: Optional 1-indexed page number hint from LLM extraction

    Returns:
        {
            "page": int (1-indexed),
            "bbox": {"x0": float, "y0": float, "x1": float, "y1": float} or None,
            "confidence": float (0-1),
            "found": bool
        }
    """
    if not FITZ_AVAILABLE:
        return {"page": page_hint or 1, "bbox": None, "confidence": 0.0, "found": False}

    if not source_text or len(source_text.strip()) < 5:
        return {"page": page_hint or 1, "bbox": None, "confidence": 0.0, "found": False}

    try:
        doc = fitz.open(filepath)
    except Exception as e:
        logger.error(f"Cannot open PDF for source location: {e}")
        return {"page": page_hint or 1, "bbox": None, "confidence": 0.0, "found": False}

    clean_query = source_text.strip()

    # Strategy 1: Search the hinted page first
    if page_hint and 1 <= page_hint <= len(doc):
        page = doc[page_hint - 1]
        bbox = _search_page_fitz(page, clean_query)
        if bbox:
            doc.close()
            return {"page": page_hint, "bbox": bbox, "confidence": 0.95, "found": True}

    # Strategy 2: Search all pages using fitz text search
    for page_num in range(len(doc)):
        page = doc[page_num]
        bbox = _search_page_fitz(page, clean_query)
        if bbox:
            doc.close()
            return {"page": page_num + 1, "bbox": bbox, "confidence": 0.9, "found": True}

    # Strategy 3: Fuzzy match against page text content
    best_page = page_hint or 1
    best_sim = 0.0
    normalised_query = _normalise(clean_query)

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_text = page.get_text()
        if not page_text.strip():
            continue

        # Check if the query text appears as a substring (case-insensitive)
        if normalised_query in _normalise(page_text):
            # Found it — try to get a bbox from a shorter substring
            words = clean_query.split()
            for length in range(min(len(words), 8), 1, -1):
                sub = " ".join(words[:length])
                bbox = _search_page_fitz(page, sub)
                if bbox:
                    doc.close()
                    return {"page": page_num + 1, "bbox": bbox, "confidence": 0.8, "found": True}
            # Substring found but no bbox — still return the page
            doc.close()
            return {"page": page_num + 1, "bbox": None, "confidence": 0.7, "found": True}

        # Compute similarity
        # Compare against sliding windows of similar length
        sim = _similarity(clean_query, page_text[:len(clean_query) * 3])
        if sim > best_sim:
            best_sim = sim
            best_page = page_num + 1

    doc.close()

    if best_sim > 0.4:
        return {"page": best_page, "bbox": None, "confidence": round(best_sim, 2), "found": True}

    return {"page": page_hint or 1, "bbox": None, "confidence": 0.0, "found": False}


def render_page_image(
    filepath: str,
    page_num: int,
    zoom: float = 2.0,
    highlight_bbox: Optional[dict] = None,
) -> bytes:
    """
    Render a PDF page as a PNG image.

    Args:
        filepath: Path to the PDF file
        page_num: 1-indexed page number
        zoom: Rendering zoom factor (2.0 = ~144 dpi)
        highlight_bbox: Optional {x0, y0, x1, y1} to draw a highlight rectangle.
                        Coordinates are in PDF points (72 dpi), same as returned by locate_source.

    Returns:
        PNG image bytes
    """
    if not FITZ_AVAILABLE:
        raise RuntimeError("PyMuPDF is required for page rendering")

    doc = fitz.open(filepath)
    if page_num < 1 or page_num > len(doc):
        doc.close()
        raise ValueError(f"Page {page_num} out of range (1-{len(doc)})")

    page = doc[page_num - 1]
    mat = fitz.Matrix(zoom, zoom)

    # Draw highlight annotation if bbox provided
    if highlight_bbox:
        try:
            x0 = float(highlight_bbox.get("x0", 0))
            y0 = float(highlight_bbox.get("y0", 0))
            x1 = float(highlight_bbox.get("x1", 100))
            y1 = float(highlight_bbox.get("y1", 100))
            rect = fitz.Rect(x0, y0, x1, y1)

            # Add a highlight annotation (yellow, semi-transparent)
            annot = page.add_highlight_annot(rect)
            annot.set_colors(stroke=(1, 0.8, 0))  # golden yellow
            annot.set_opacity(0.35)
            annot.update()

            # Also draw a colored rectangle border for extra visibility
            shape = page.new_shape()
            shape.draw_rect(rect)
            shape.finish(color=(0.2, 0.5, 1.0), width=2)  # blue border
            shape.commit()
        except Exception as e:
            logger.warning(f"Could not draw highlight annotation: {e}")

    pix = page.get_pixmap(matrix=mat)
    img_bytes = pix.tobytes("png")

    # Clean up annotations we added (so they don't persist in the file)
    doc.close()

    return img_bytes


def get_pdf_page_count(filepath: str) -> int:
    """Return total number of pages."""
    if not FITZ_AVAILABLE:
        return 0
    try:
        doc = fitz.open(filepath)
        count = len(doc)
        doc.close()
        return count
    except Exception:
        return 0
