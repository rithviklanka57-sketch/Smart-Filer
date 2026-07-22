"""
services/extraction.py — Text extraction from uploaded files.
Uses pdfplumber for native PDFs, Tesseract OCR fallback for scanned images.
Temp files are deleted after processing.
"""
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def extract_text(file_bytes: bytes, filename: str, mime_type: str) -> str:
    """
    Extract readable text from file_bytes.
    Returns extracted text (may be empty string if nothing extractable).
    Temp files are always cleaned up.
    """
    ext = Path(filename).suffix.lower()

    if mime_type == "application/pdf" or ext == ".pdf":
        return _extract_pdf(file_bytes)
    elif mime_type.startswith("image/") or ext in {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif"}:
        return _extract_image_ocr(file_bytes)
    elif mime_type in ("text/plain",) or ext in {".txt", ".md", ".csv"}:
        return _extract_plain_text(file_bytes)
    elif ext in {".docx", ".doc"}:
        return _extract_docx(file_bytes)
    else:
        # Try plain text as last resort
        try:
            return file_bytes.decode("utf-8", errors="ignore")
        except Exception:
            return ""


def _extract_pdf(file_bytes: bytes) -> str:
    try:
        import pdfplumber
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        try:
            with pdfplumber.open(tmp_path) as pdf:
                # Limit extraction to first 5 pages for ultra-fast performance
                target_pages = pdf.pages[:5]
                pages = [page.extract_text() or "" for page in target_pages]
            text = "\n".join(pages).strip()
            return text
        finally:
            os.unlink(tmp_path)
    except Exception as e:
        logger.warning("PDF extraction failed: %s", e)
        return ""


def _extract_image_ocr(file_bytes: bytes) -> str:
    try:
        import pytesseract
        from PIL import Image
        import io
        image = Image.open(io.BytesIO(file_bytes))
        return pytesseract.image_to_string(image).strip()
    except Exception as e:
        logger.warning("OCR failed: %s", e)
        return ""


def _extract_plain_text(file_bytes: bytes) -> str:
    return file_bytes.decode("utf-8", errors="ignore").strip()


def _extract_docx(file_bytes: bytes) -> str:
    try:
        import zipfile
        import xml.etree.ElementTree as ET
        import io

        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            if "word/document.xml" not in z.namelist():
                return ""
            xml_content = z.read("word/document.xml")

        root = ET.fromstring(xml_content)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs = []
        for para in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
            texts = [t.text or "" for t in para.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")]
            paragraphs.append("".join(texts))
        return "\n".join(p for p in paragraphs if p.strip())
    except Exception as e:
        logger.warning("DOCX extraction failed: %s", e)
        return ""
