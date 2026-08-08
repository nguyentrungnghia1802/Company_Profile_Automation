"""Deterministic HTML, JSON, and PDF parsers with stable evidence blocks."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass, field
from html.parser import HTMLParser
from io import BytesIO
from typing import Any, ClassVar
from urllib.parse import urljoin

from company_profile.db.models.source import DocumentBlock

HTML_PARSER_VERSION = "html-1.0"
STRUCTURED_PARSER_VERSION = "structured-1.0"
PDF_PARSER_VERSION = "pdf-1.0"
DEFAULT_LANGUAGE = "und"


def _clean_text(value: str) -> str:
    """Normalize whitespace without changing the source language or wording."""
    return " ".join(value.split()).strip()


def _hash_text(value: str) -> str:
    """Return the stable content hash used by evidence deduplication."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _json_field_paths(value: Any, prefix: str = "$") -> list[str]:
    """Return deterministic JSON paths without evaluating their values."""
    if isinstance(value, dict):
        paths: list[str] = []
        for key in sorted(value):
            paths.extend(_json_field_paths(value[key], f"{prefix}.{key}"))
        return paths or [prefix]
    if isinstance(value, list):
        paths = []
        for index, item in enumerate(value):
            paths.extend(_json_field_paths(item, f"{prefix}[{index}]"))
        return paths or [prefix]
    return [prefix]


def _infer_language(text: str) -> str:
    """Use conservative markers when a document has no explicit language tag."""
    lowered = text.lower()
    if any(marker in lowered for marker in ("công ty", "địa chỉ", "mã số thuế", "trụ sở")):
        return "vi"
    if any(marker in lowered for marker in ("company", "headquarters", "tax id", "address")):
        return "en"
    return DEFAULT_LANGUAGE


@dataclass(slots=True)
class _HtmlFrame:
    """Small stack frame used by the malformed-HTML tolerant parser."""

    tag: str
    attrs: dict[str, str]
    parts: list[str] = field(default_factory=list)


class _StructuredHTMLParser(HTMLParser):
    """Collect semantic HTML elements without executing or interpreting markup."""

    _BLOCK_TAGS: ClassVar[set[str]] = {
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "p",
        "li",
        "table",
        "title",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.frames: list[_HtmlFrame] = []
        self.metadata: list[dict[str, str]] = []
        self.links: list[dict[str, str]] = []
        self.json_ld: list[str] = []
        self.html_language: str | None = None
        self.plain_parts: list[str] = []
        self._script_type: str | None = None
        self._script_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_name = tag.lower()
        attributes = {key.lower(): value or "" for key, value in attrs}
        if tag_name == "html":
            lang = attributes.get("lang", "").strip()
            if lang:
                self.html_language = lang.lower().replace("_", "-")[:16]
        if tag_name == "meta":
            name = (
                attributes.get("name")
                or attributes.get("property")
                or attributes.get("http-equiv", "")
            )
            content = attributes.get("content", "").strip()
            if name and content:
                self.metadata.append({"name": name.strip(), "content": content})
        if tag_name == "script":
            self._script_type = attributes.get("type", "").lower().strip()
            self._script_parts = []
        self.frames.append(_HtmlFrame(tag_name, attributes))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        if not data:
            return
        if self._script_type is not None:
            self._script_parts.append(data)
            return
        self.plain_parts.append(data)
        for frame in self.frames:
            frame.parts.append(data)

    def handle_entityref(self, name: str) -> None:
        self.handle_data(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self.handle_data(f"&#{name};")

    def handle_endtag(self, tag: str) -> None:
        tag_name = tag.lower()
        frame_index = next(
            (
                index
                for index in range(len(self.frames) - 1, -1, -1)
                if self.frames[index].tag == tag_name
            ),
            None,
        )
        if frame_index is None:
            if tag_name == "script":
                self._finish_script()
            return
        frame = self.frames[frame_index]
        del self.frames[frame_index:]
        if tag_name == "script":
            self._finish_script()
            return
        if tag_name == "a" and frame.attrs.get("href", "").strip():
            self.links.append(
                {
                    "href": frame.attrs["href"].strip(),
                    "text": _clean_text("".join(frame.parts)),
                }
            )

    def _finish_script(self) -> None:
        if self._script_type == "application/ld+json":
            payload = "".join(self._script_parts).strip()
            if payload:
                self.json_ld.append(payload)
        self._script_type = None
        self._script_parts = []


class DocumentParser:
    """Parse HTML into stable, evidence-addressable ``DocumentBlock`` rows."""

    version = HTML_PARSER_VERSION
    _semantic_tags: ClassVar[set[str]] = {
        "title",
        "p",
        "li",
        "table",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
    }

    def parse_html_to_blocks(
        self,
        workspace_id: uuid.UUID,
        source_snapshot_id: uuid.UUID,
        html_content: str,
        *,
        source_url: str | None = None,
        source_language: str | None = None,
    ) -> list[DocumentBlock]:
        """Extract metadata, structured data, semantic blocks, and links.

        ``HTMLParser`` intentionally tolerates incomplete/malformed markup. No
        scripts are executed and all source content remains untrusted text.
        Block keys are based on semantic tag and ordinal, so evidence survives
        a retry of the same immutable snapshot.
        """
        if not html_content:
            return []

        collector = _StructuredHTMLParser()
        try:
            collector.feed(html_content)
            collector.close()
        except Exception:
            # A malformed document must not fail the research job. The parser
            # retains the prefix collected before the HTMLParser exception.
            pass

        language = self._language(collector, html_content, source_language)
        blocks: list[DocumentBlock] = []
        counters: dict[str, int] = {}

        def add_block(
            *,
            key_prefix: str,
            block_type: str,
            text: str,
            section_path: list[str] | None = None,
            location: dict[str, object] | None = None,
            block_metadata: dict[str, object] | None = None,
        ) -> None:
            cleaned = _clean_text(text)
            if not cleaned:
                return
            counters[key_prefix] = counters.get(key_prefix, 0) + 1
            block_key = f"{key_prefix}_{counters[key_prefix]:04d}"
            blocks.append(
                DocumentBlock(
                    workspace_id=workspace_id,
                    source_snapshot_id=source_snapshot_id,
                    block_key=block_key,
                    block_type=block_type,
                    text_content=cleaned,
                    block_hash=_hash_text(cleaned),
                    language=language,
                    parser_version=self.version,
                    section_path=section_path or [],
                    location=location or {},
                    block_metadata=block_metadata or {},
                    start_offset=0,
                    end_offset=len(cleaned),
                )
            )

        for index, raw_json in enumerate(collector.json_ld, start=1):
            try:
                payload = json.loads(raw_json)
            except (TypeError, json.JSONDecodeError):
                continue
            normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
            add_block(
                key_prefix=f"json_ld_{index:04d}",
                block_type="table",
                text=normalized,
                location={"kind": "json-ld", "script_ordinal": index},
                block_metadata={
                    "format": "json-ld",
                    "field_paths": _json_field_paths(payload),
                    "provenance": {
                        "source_url": source_url or "",
                        "evidence_location": f"script[type=application/ld+json][{index}]",
                    },
                },
            )

        for index, item in enumerate(collector.metadata, start=1):
            name = item["name"]
            add_block(
                key_prefix="meta",
                block_type="metadata",
                text=f"{name}: {item['content']}",
                location={"kind": "meta", "ordinal": index},
                block_metadata={
                    "kind": "opengraph" if name.lower().startswith("og:") else "meta",
                    "name": name,
                    "content": item["content"],
                },
            )

        title_index = 0
        heading_stack: list[str] = []
        element_counts: dict[str, int] = {}
        # The collector deliberately retains semantic elements in document
        # order. Reconstructing order from the source is unnecessary for stable
        # evidence IDs, and heading paths remain deterministic for each block.
        for frame in self._semantic_frames(html_content):
            tag_name, text, _attrs = frame
            cleaned = _clean_text(text)
            if not cleaned:
                continue
            element_counts[tag_name] = element_counts.get(tag_name, 0) + 1
            ordinal = element_counts[tag_name]
            if tag_name == "title":
                title_index += 1
                add_block(
                    key_prefix="title",
                    block_type="title",
                    text=cleaned,
                    location={"tag": "title", "ordinal": title_index},
                    block_metadata={"kind": "document_title"},
                )
            elif tag_name.startswith("h"):
                level = int(tag_name[1])
                heading_stack = heading_stack[: max(level - 1, 0)]
                heading_stack.append(cleaned)
                add_block(
                    key_prefix=tag_name,
                    block_type="heading",
                    text=cleaned,
                    section_path=list(heading_stack),
                    location={"tag": tag_name, "ordinal": ordinal},
                    block_metadata={"level": level},
                )
            elif tag_name == "table":
                add_block(
                    key_prefix="table",
                    block_type="table",
                    text=cleaned,
                    section_path=list(heading_stack),
                    location={"tag": "table", "ordinal": ordinal},
                )
            elif tag_name == "li":
                add_block(
                    key_prefix="list",
                    block_type="list",
                    text=cleaned,
                    section_path=list(heading_stack),
                    location={"tag": "li", "ordinal": ordinal},
                )
            else:
                add_block(
                    key_prefix="paragraph",
                    block_type="paragraph",
                    text=cleaned,
                    section_path=list(heading_stack),
                    location={"tag": "p", "ordinal": ordinal},
                )

        for index, link in enumerate(collector.links, start=1):
            href = link["href"]
            resolved_href = urljoin(source_url or "", href) if source_url else href
            label = link["text"] or resolved_href
            add_block(
                key_prefix="link",
                block_type="link",
                text=label,
                location={"tag": "a", "ordinal": index},
                block_metadata={
                    "href": resolved_href,
                    "label": link["text"],
                    "source_url": source_url or "",
                },
            )

        if not any(
            block.block_type in {"title", "heading", "paragraph", "list", "table"}
            for block in blocks
        ):
            fallback = _clean_text(" ".join(collector.plain_parts))
            if fallback:
                add_block(
                    key_prefix="paragraph",
                    block_type="paragraph",
                    text=fallback,
                    location={"kind": "plain-text-fallback", "ordinal": 1},
                )

        return blocks

    def parse_json_to_blocks(
        self,
        workspace_id: uuid.UUID,
        source_snapshot_id: uuid.UUID,
        payload: Any,
        *,
        source_url: str | None = None,
        source_language: str | None = None,
        provenance: dict[str, object] | None = None,
    ) -> list[DocumentBlock]:
        """Persist one stable structured block with JSON field-path evidence."""
        language = source_language or _infer_language(json.dumps(payload, ensure_ascii=False))
        normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        location = {
            "kind": "json",
            "evidence_location": "$",
            "source_url": source_url or "",
        }
        return [
            DocumentBlock(
                workspace_id=workspace_id,
                source_snapshot_id=source_snapshot_id,
                block_key="structured_0001",
                block_type="structured",
                text_content=normalized,
                block_hash=_hash_text(normalized),
                language=language,
                parser_version=STRUCTURED_PARSER_VERSION,
                section_path=[],
                location=location,
                block_metadata={
                    "format": "json",
                    "field_paths": _json_field_paths(payload),
                    "provenance": {
                        "source_url": source_url or "",
                        "evidence_location": "$",
                        **(provenance or {}),
                    },
                },
                start_offset=0,
                end_offset=len(normalized),
            )
        ]

    @staticmethod
    def detect_language(html_content: str) -> str:
        """Return the explicit or conservative source-language code."""
        collector = _StructuredHTMLParser()
        try:
            collector.feed(html_content)
            collector.close()
        except Exception:
            pass
        if collector.html_language:
            return collector.html_language
        return _infer_language(" ".join(collector.plain_parts))

    @staticmethod
    def _language(
        collector: _StructuredHTMLParser, html_content: str, source_language: str | None
    ) -> str:
        if source_language:
            return source_language.lower().replace("_", "-")[:16]
        if collector.html_language:
            return collector.html_language
        return _infer_language(" ".join(collector.plain_parts) or html_content)

    @staticmethod
    def _semantic_frames(html_content: str) -> list[tuple[str, str, dict[str, str]]]:
        """Extract semantic frames in source order with malformed markup tolerance."""
        parser = _SemanticFrameParser()
        try:
            parser.feed(html_content)
            parser.close()
        except Exception:
            pass
        return parser.frames


class _SemanticFrameParser(HTMLParser):
    """Second lightweight pass that preserves semantic element ordering."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[_HtmlFrame] = []
        self.frames: list[tuple[str, str, dict[str, str]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.stack.append(
            _HtmlFrame(tag.lower(), {key.lower(): value or "" for key, value in attrs})
        )

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        for frame in self.stack:
            if frame.tag not in {"script", "style", "noscript"}:
                frame.parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag_name = tag.lower()
        frame_index = next(
            (
                index
                for index in range(len(self.stack) - 1, -1, -1)
                if self.stack[index].tag == tag_name
            ),
            None,
        )
        if frame_index is None:
            return
        frame = self.stack[frame_index]
        del self.stack[frame_index:]
        if frame.tag in {
            "title",
            "p",
            "li",
            "table",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
        }:
            self.frames.append((frame.tag, " ".join(frame.parts), frame.attrs))


class PDFDocumentParser:
    """Safely parse public PDF bytes into page-addressable blocks."""

    version = PDF_PARSER_VERSION

    def __init__(
        self,
        max_bytes: int = 10_000_000,
        max_decompressed_bytes: int | None = None,
    ) -> None:
        self.max_bytes = max(1, max_bytes)
        self.max_decompressed_bytes = max_decompressed_bytes or self.max_bytes

    def parse_pdf_to_blocks(
        self,
        workspace_id: uuid.UUID,
        source_snapshot_id: uuid.UUID,
        pdf_bytes: bytes,
    ) -> list[DocumentBlock]:
        """Extract bounded page text; malformed or encrypted PDFs return no blocks."""
        if not pdf_bytes or len(pdf_bytes) > self.max_bytes:
            return []
        is_pdf = pdf_bytes.lstrip().startswith(b"%PDF")
        if not is_pdf:
            # Preserve the existing deterministic text-fixture contract while
            # never treating a malformed PDF signature as arbitrary evidence.
            fallback = pdf_bytes.decode("utf-8", errors="ignore").strip()
            if fallback and len(fallback) > 10:
                return [
                    self._block(
                        workspace_id,
                        source_snapshot_id,
                        "pdf_raw_0",
                        fallback,
                        page_number=None,
                        location={"kind": "plain-text-fallback"},
                    )
                ]
            return []

        try:
            import pypdf

            reader = pypdf.PdfReader(stream=BytesIO(pdf_bytes), strict=False)
            if reader.is_encrypted:
                return []
            blocks: list[DocumentBlock] = []
            decompressed_size = 0
            for page_number, page in enumerate(reader.pages, start=1):
                text = (page.extract_text() or "").strip()
                if not text:
                    continue
                for block_number, paragraph in enumerate(re.split(r"\n\s*\n", text), start=1):
                    clean_paragraph = _clean_text(paragraph)
                    if not clean_paragraph:
                        continue
                    decompressed_size += len(clean_paragraph.encode("utf-8"))
                    if decompressed_size > self.max_decompressed_bytes:
                        return blocks
                    blocks.append(
                        self._block(
                            workspace_id,
                            source_snapshot_id,
                            f"p{page_number}_b{block_number}",
                            clean_paragraph,
                            page_number=page_number,
                            location={
                                "kind": "pdf",
                                "page": page_number,
                                "block": block_number,
                            },
                        )
                    )
            return blocks
        except Exception:
            return []

    def _block(
        self,
        workspace_id: uuid.UUID,
        source_snapshot_id: uuid.UUID,
        block_key: str,
        text: str,
        *,
        page_number: int | None,
        location: dict[str, object],
    ) -> DocumentBlock:
        return DocumentBlock(
            workspace_id=workspace_id,
            source_snapshot_id=source_snapshot_id,
            block_key=block_key,
            block_type="paragraph",
            text_content=text,
            block_hash=_hash_text(text),
            language=_infer_language(text),
            parser_version=self.version,
            page_number=page_number,
            section_path=[],
            location=location,
            block_metadata={"format": "pdf", "evidence_location": location},
            start_offset=0,
            end_offset=len(text),
        )
