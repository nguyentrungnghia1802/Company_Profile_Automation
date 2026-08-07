"""HTML and Document Parsers for extracting structured blocks, metadata, and PDF pages."""

from __future__ import annotations

import hashlib
import json
import re
import uuid

from company_profile.db.models.source import DocumentBlock


class DocumentParser:
    """Parser converting raw HTML or plain text into structured DocumentBlock items."""

    def parse_html_to_blocks(
        self,
        workspace_id: uuid.UUID,
        source_snapshot_id: uuid.UUID,
        html_content: str,
    ) -> list[DocumentBlock]:
        """Extract clean text blocks, JSON-LD metadata, and headings from HTML string."""
        blocks: list[DocumentBlock] = []
        if not html_content:
            return blocks

        # 1. Extract JSON-LD metadata blocks
        json_ld_matches = re.findall(
            r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html_content,
            flags=re.DOTALL | re.IGNORECASE,
        )
        for idx, json_str in enumerate(json_ld_matches):
            clean_json = json_str.strip()
            if clean_json:
                try:
                    parsed_json = json.loads(clean_json)
                    formatted_json = json.dumps(parsed_json, ensure_ascii=False)
                    bhash = hashlib.sha256(formatted_json.encode("utf-8")).hexdigest()
                    blocks.append(
                        DocumentBlock(
                            workspace_id=workspace_id,
                            source_snapshot_id=source_snapshot_id,
                            block_key=f"json_ld_{idx}",
                            block_type="table",
                            text_content=formatted_json,
                            block_hash=bhash,
                        )
                    )
                except json.JSONDecodeError:
                    pass

        # 2. Strip scripts and styles for HTML body parsing
        clean_html = re.sub(
            r"<(script|style)[^>]*>.*?</\1>", "", html_content, flags=re.DOTALL | re.IGNORECASE
        )

        # 3. Extract headings, paragraphs, and list items
        patterns = [
            (r"<h[1-6][^>]*>(.*?)</h[1-6]>", "heading"),
            (r"<p[^>]*>(.*?)</p>", "paragraph"),
            (r"<li[^>]*>(.*?)</li>", "list"),
            (r"<table[^>]*>(.*?)</table>", "table"),
        ]

        raw_blocks: list[tuple[str, str]] = []
        for pattern, btype in patterns:
            for match in re.finditer(pattern, clean_html, flags=re.DOTALL | re.IGNORECASE):
                text = re.sub(r"<[^>]+>", "", match.group(1)).strip()
                if text and len(text) > 5:
                    raw_blocks.append((btype, text))

        # Fallback if no HTML block tags found: split plain text paragraphs by double newlines
        if not raw_blocks:
            plain_text = re.sub(r"<[^>]+>", "", clean_html).strip()
            for line in plain_text.split("\n\n"):
                clean_line = line.strip()
                if clean_line and len(clean_line) > 5:
                    raw_blocks.append(("paragraph", clean_line))

        for idx, (btype, text) in enumerate(raw_blocks):
            block_key = f"block_{idx}"
            bhash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            blocks.append(
                DocumentBlock(
                    workspace_id=workspace_id,
                    source_snapshot_id=source_snapshot_id,
                    block_key=block_key,
                    block_type=btype,
                    text_content=text,
                    block_hash=bhash,
                )
            )

        return blocks


class PDFDocumentParser:
    """PDF Document Parser for extracting page-partitioned text blocks."""

    def parse_pdf_to_blocks(
        self,
        workspace_id: uuid.UUID,
        source_snapshot_id: uuid.UUID,
        pdf_bytes: bytes,
    ) -> list[DocumentBlock]:
        """Extract page-referenced document blocks from PDF bytes."""
        blocks: list[DocumentBlock] = []
        if not pdf_bytes:
            return blocks

        try:
            import pypdf  # type: ignore[import-not-found]

            reader = pypdf.PdfReader(stream=pdf_bytes)
            if reader.is_encrypted:
                return blocks

            for page_idx, page in enumerate(reader.pages, start=1):
                text = (page.extract_text() or "").strip()
                if text:
                    for line_idx, paragraph in enumerate(text.split("\n\n")):
                        clean_p = paragraph.strip()
                        if clean_p:
                            block_key = f"p{page_idx}_b{line_idx}"
                            bhash = hashlib.sha256(clean_p.encode("utf-8")).hexdigest()
                            blocks.append(
                                DocumentBlock(
                                    workspace_id=workspace_id,
                                    source_snapshot_id=source_snapshot_id,
                                    block_key=block_key,
                                    block_type="paragraph",
                                    text_content=clean_p,
                                    block_hash=bhash,
                                )
                            )
        except Exception:
            # Fallback for plain text or malformed PDF bytes
            text_str = pdf_bytes.decode("utf-8", errors="ignore").strip()
            if text_str and len(text_str) > 10:
                bhash = hashlib.sha256(text_str.encode("utf-8")).hexdigest()
                blocks.append(
                    DocumentBlock(
                        workspace_id=workspace_id,
                        source_snapshot_id=source_snapshot_id,
                        block_key="pdf_raw_0",
                        block_type="paragraph",
                        text_content=text_str,
                        block_hash=bhash,
                    )
                )

        return blocks
