"""HTML Document Parser for splitting raw HTML into structured document blocks."""

from __future__ import annotations

import hashlib
import re
import uuid

from company_profile.db.models.source import DocumentBlock


class DocumentParser:
    """Parser converting raw HTML content into structured DocumentBlock items."""

    def parse_html_to_blocks(
        self,
        workspace_id: uuid.UUID,
        source_snapshot_id: uuid.UUID,
        html_content: str,
    ) -> list[DocumentBlock]:
        """Extract clean text blocks (headings, paragraphs) from HTML string."""
        blocks: list[DocumentBlock] = []
        if not html_content:
            return blocks

        # Strip scripts, styles, and tags
        clean_html = re.sub(
            r"<(script|style)[^>]*>.*?</\1>", "", html_content, flags=re.DOTALL | re.IGNORECASE
        )

        # Extract headings and paragraphs using regex block patterns
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
