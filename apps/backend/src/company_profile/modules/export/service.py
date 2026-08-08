"""Export service for structured JSON and PDF generation with evidence appendix."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from company_profile.config.settings import get_settings
from company_profile.db.models.export import ExportJob
from company_profile.modules.publication.service import PublicationService

if TYPE_CHECKING:
    from collections.abc import Sequence


class ExportService:
    """Service for managing ExportJob creation, JSON/PDF generation, and download retrieval."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settings = get_settings()

    async def create_export_job(
        self,
        workspace_id: uuid.UUID,
        profile_version_id: uuid.UUID,
        requested_by: uuid.UUID | None,
        export_format: str = "pdf",
        locale: str = "vi",
        include_source_appendix: bool = True,
        include_internal_notes: bool = False,
    ) -> ExportJob:
        """Create and execute an ExportJob."""
        job = ExportJob(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            profile_version_id=profile_version_id,
            requested_by=requested_by,
            export_format=export_format,
            locale=locale,
            status="processing",
            include_source_appendix=include_source_appendix,
            include_internal_notes=include_internal_notes,
            storage_provider="local",
        )
        self._session.add(job)
        await self._session.flush()

        try:
            pub_svc = PublicationService(self._session)
            pv = await pub_svc.get_profile_version(workspace_id, profile_version_id)
            if not pv:
                raise ValueError(f"ProfileVersion '{profile_version_id}' not found.")

            export_dir = Path(self._settings.local_storage_root) / "exports" / str(workspace_id)
            export_dir.mkdir(parents=True, exist_ok=True)

            if export_format == "json":
                filename = f"profile_v{pv.version_number}_{job.id}.json"
                file_path = export_dir / filename
                payload = self._build_json_payload(pv, include_source_appendix)
                content_bytes = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
                file_path.write_bytes(content_bytes)

            else:  # pdf
                filename = f"profile_v{pv.version_number}_{job.id}.pdf"
                file_path = export_dir / filename
                content_bytes = self._build_pdf_bytes(pv, locale, include_source_appendix)
                file_path.write_bytes(content_bytes)

            checksum = hashlib.sha256(content_bytes).hexdigest()
            file_size = len(content_bytes)

            job.mark_completed(
                object_key=str(file_path.relative_to(self._settings.local_storage_root)),
                checksum=checksum,
                file_size=file_size,
            )
            await self._session.flush()
        except Exception as exc:
            job.mark_failed(str(exc))
            await self._session.flush()

        return job

    async def get_export_job(
        self, workspace_id: uuid.UUID, export_id: uuid.UUID
    ) -> ExportJob | None:
        """Get ExportJob by ID."""
        stmt = select(ExportJob).where(
            ExportJob.workspace_id == workspace_id,
            ExportJob.id == export_id,
        )
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    def get_export_file_path(self, job: ExportJob) -> Path:
        """Get absolute Path to exported file."""
        if not job.object_key:
            raise ValueError("Export file has no object key.")
        return Path(self._settings.local_storage_root) / job.object_key

    def _build_json_payload(self, pv: Any, include_source_appendix: bool) -> dict[str, Any]:
        fields = []
        for fv in pv.field_values:
            evs = []
            if include_source_appendix:
                evs = [
                    {
                        "excerpt": e.original_excerpt,
                        "translation": e.translated_excerpt,
                        "url": e.source_canonical_url,
                        "tier": e.source_authority_tier,
                    }
                    for e in fv.evidences
                ]
            fields.append(
                {
                    "field_key": fv.field_key,
                    "value": fv.get_value(),
                    "display_value": fv.display_value,
                    "status": fv.display_status,
                    "confidence": fv.confidence_score,
                    "evidences": evs,
                }
            )

        return {
            "title": pv.title,
            "version_number": pv.version_number,
            "published_at": pv.published_at.isoformat(),
            "content_hash": pv.content_hash,
            "overall_confidence": pv.overall_confidence,
            "executive_summary": pv.executive_summary,
            "fields": fields,
        }

    def _build_pdf_bytes(self, pv: Any, locale: str, include_source_appendix: bool) -> bytes:
        """Generate structured PDF document bytes with header, summary, fields, and appendix."""
        title = f"VERIFIED COMPANY PROFILE — v{pv.version_number}"
        header = f"{pv.title} (Published: {pv.published_at.strftime('%Y-%m-%d')})"
        summary = f"Executive Summary:\n{pv.executive_summary}\n\n"

        field_rows = []
        for fv in pv.field_values:
            val_str = fv.display_value or str(fv.value)
            field_rows.append(f"• {fv.field_key}: {val_str} (Confidence: {int(fv.confidence_score * 100)}%)")

        appendix_str = ""
        if include_source_appendix:
            appendix_rows = []
            for fv in pv.field_values:
                for e in fv.evidences:
                    appendix_rows.append(f"  - [{fv.field_key}] Excerpt: \"{e.original_excerpt}\" (URL: {e.source_canonical_url or 'N/A'})")
            if appendix_rows:
                appendix_str = "\n\nSource Evidence Appendix:\n" + "\n".join(appendix_rows)

        text_doc = f"{title}\n{'=' * len(title)}\n{header}\nHash: {pv.content_hash}\n\n{summary}Fields:\n" + "\n".join(field_rows) + appendix_str

        # Return mock PDF / formatted document bytes with PDF header marker
        pdf_content = f"%PDF-1.4\n%VERIFIED_PROFILE_EXPORT\n{text_doc}\n%%EOF".encode("utf-8")
        return pdf_content
