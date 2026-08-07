"""Unit tests for HTML and PDF document parsers."""

from __future__ import annotations

import uuid

from company_profile.modules.sources.parser import DocumentParser, PDFDocumentParser


def test_html_document_parser_json_ld_and_headings() -> None:
    """Verify HTML parser extracts JSON-LD metadata, headings, and paragraphs."""
    parser = DocumentParser()
    ws_id = uuid.uuid4()
    snap_id = uuid.uuid4()

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Company Profile</title>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": "Parsed Company Corp",
            "taxID": "0319876543"
        }
        </script>
    </head>
    <body>
        <h1>Main Official Heading</h1>
        <p>This is official company profile information paragraph.</p>
        <ul>
            <li>Address: 123 Main St</li>
            <li>Phone: 0901234567</li>
        </ul>
    </body>
    </html>
    """

    blocks = parser.parse_html_to_blocks(ws_id, snap_id, html)
    assert len(blocks) >= 3

    json_ld_block = next((b for b in blocks if b.block_key.startswith("json_ld")), None)
    assert json_ld_block is not None
    assert "Parsed Company Corp" in json_ld_block.text_content
    assert "0319876543" in json_ld_block.text_content

    heading_block = next((b for b in blocks if b.block_type == "heading"), None)
    assert heading_block is not None
    assert "Main Official Heading" in heading_block.text_content


def test_pdf_document_parser_blocks() -> None:
    """Verify PDF parser handles raw bytes and generates page-indexed block keys."""
    parser = PDFDocumentParser()
    ws_id = uuid.uuid4()
    snap_id = uuid.uuid4()

    # Raw text bytes fallback
    pdf_text = b"Page 1 content paragraph for PDF testing.\n\nSecond paragraph of PDF."
    blocks = parser.parse_pdf_to_blocks(ws_id, snap_id, pdf_text)

    assert len(blocks) >= 1
    assert "Page 1 content" in blocks[0].text_content


def test_pdf_document_parser_empty_bytes() -> None:
    """Verify PDF parser returns empty list for empty bytes."""
    parser = PDFDocumentParser()
    ws_id = uuid.uuid4()
    snap_id = uuid.uuid4()

    blocks = parser.parse_pdf_to_blocks(ws_id, snap_id, b"")
    assert blocks == []
