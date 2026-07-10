"""
PDF text extraction with OCR fallback.

Handles both digitally-native PDFs (text layer present) and scanned
PDFs (image-only pages) by falling back to Tesseract OCR on a
per-page basis. Returns a page-indexed structure so downstream
chunking can retain accurate page references for evidence citations.
"""

from dataclasses import dataclass
import io

import fitz  # PyMuPDF


@dataclass
class PageText:
    page_number: int  # 1-indexed, for user-facing citations
    text: str
    used_ocr: bool


def _ocr_page(page: "fitz.Page", zoom: float = 2.0) -> str:
    """Render a page to an image and run OCR on it.

    Imports are done lazily so the app can still run (with reduced
    functionality) if pytesseract / Pillow / a Tesseract binary are
    not available in the deployment environment.
    """
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return ""

    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img = Image.open(io.BytesIO(pix.tobytes("png")))

    try:
        return pytesseract.image_to_string(img)
    except Exception:
        # Tesseract binary missing/misconfigured - fail soft.
        return ""


def extract_pages(file_bytes: bytes, min_chars_for_text_layer: int = 20) -> list[PageText]:
    """Extract text from every page of a PDF.

    If a page's native text layer is empty or near-empty (typical of
    scanned documents), falls back to OCR for that page only.
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages: list[PageText] = []

    for i, page in enumerate(doc):
        native_text = page.get_text().strip()
        used_ocr = False

        if len(native_text) < min_chars_for_text_layer:
            ocr_text = _ocr_page(page)
            if len(ocr_text.strip()) > len(native_text):
                native_text = ocr_text.strip()
                used_ocr = True

        pages.append(PageText(page_number=i + 1, text=native_text, used_ocr=used_ocr))

    doc.close()
    return pages


def full_text(pages: list[PageText]) -> str:
    """Concatenate all page text (useful for quick previews / fallbacks)."""
    return "\n\n".join(p.text for p in pages)


def any_ocr_used(pages: list[PageText]) -> bool:
    return any(p.used_ocr for p in pages)
