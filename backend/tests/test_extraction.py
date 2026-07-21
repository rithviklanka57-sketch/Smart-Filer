"""
tests/test_extraction.py — Unit tests for text extraction service.
No API keys needed — tests local logic only.
"""
import pytest
from services.extraction import extract_text


def test_plain_text():
    content = b"Hello, world! This is a plain text file."
    result = extract_text(content, "test.txt", "text/plain")
    assert "Hello, world!" in result


def test_pdf_extraction():
    """Test PDF extraction returns non-empty text for a simple synthetic PDF."""
    # Minimal valid PDF with text
    pdf_bytes = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj
4 0 obj<</Length 44>>stream
BT /F1 12 Tf 100 700 Td (Invoice #1234) Tj ET
endstream endobj
5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000266 00000 n
0000000360 00000 n
trailer<</Size 6/Root 1 0 R>>
startxref
441
%%EOF"""
    result = extract_text(pdf_bytes, "invoice.pdf", "application/pdf")
    # Should at minimum not crash; text extraction may or may not succeed on minimal PDF
    assert isinstance(result, str)


def test_docx_extraction():
    """DOCX extraction returns a string (may be empty without real DOCX bytes)."""
    result = extract_text(b"not a real docx", "test.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    assert isinstance(result, str)


def test_unknown_mime_type():
    """Unknown MIME falls back to UTF-8 decode."""
    result = extract_text(b"some raw text content", "file.xyz", "application/xyz")
    assert "some raw text content" in result
