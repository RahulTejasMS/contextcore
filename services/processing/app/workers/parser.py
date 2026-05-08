# ============================================================
# parser.py — Extracts raw text from different file types
# ============================================================
import io
from pypdf import PdfReader


def parse_document(file_bytes: bytes, file_type: str) -> str:
    """
    Takes raw file bytes and returns plain text.
    Supports: pdf, txt, md, html
    """
    if file_type == "pdf":
        return _parse_pdf(file_bytes)
    elif file_type in ("txt", "md"):
        return file_bytes.decode("utf-8", errors="ignore")
    elif file_type == "html":
        return _parse_html(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")


def _parse_pdf(file_bytes: bytes) -> str:
    """Extracts text from all pages of a PDF."""
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text and text.strip():
            pages.append(f"[Page {i+1}]\n{text.strip()}")
    return "\n\n".join(pages)


def _parse_html(file_bytes: bytes) -> str:
    """Strips HTML tags and returns plain text."""
    import re
    html = file_bytes.decode("utf-8", errors="ignore")
    # Remove script and style blocks
    html = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.DOTALL)
    # Remove all HTML tags
    text = re.sub(r'<[^>]+>', ' ', html)
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text