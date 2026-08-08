"""Deterministic fact extraction from trusted structured and labelled content.

This module deliberately handles a small, high-precision field set. It never
uses broad text heuristics to infer industry, market, business model, or other
semantic fields. Every emitted candidate is linked to the exact document block
from which it was read.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from company_profile.db.models.company import CompanyProfile
from company_profile.db.models.source import DocumentBlock, Source, SourceSnapshot
from company_profile.modules.facts.confidence import ConfidenceCalculator
from company_profile.modules.facts.repository import FactCandidateRepository
from company_profile.modules.sources.policy import calculate_entity_match_score

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(slots=True)
class DeterministicExtractionSummary:
    """Persisted output summary for one deterministic extraction step."""

    candidate_ids: list[str] = field(default_factory=list)
    fact_count: int = 0
    warnings: list[str] = field(default_factory=list)


_LABEL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "identity.legal_name",
        re.compile(
            r"^(?:legal\s+name|company\s+name|tên\s+(?:pháp\s+lý|công\s+ty))\s*[:\-]\s*(.+)$",
            re.IGNORECASE,
        ),
    ),
    (
        "identity.tax_id",
        re.compile(
            r"^(?:tax\s+id|tax\s+identification\s*(?:number|no\.)?|mã\s+số\s+thuế)\s*[:\-]\s*([A-Z0-9\-]+)$",
            re.IGNORECASE,
        ),
    ),
    (
        "identity.registration_number",
        re.compile(
            r"^(?:registration\s+(?:number|no\.)|business\s+registration\s+(?:number|no\.)|số\s+đăng\s+ký)\s*[:\-]\s*(.+)$",
            re.IGNORECASE,
        ),
    ),
    (
        "identity.address",
        re.compile(r"^(?:address|headquarters|trụ\s+sở|địa\s+chỉ)\s*[:\-]\s*(.+)$", re.IGNORECASE),
    ),
    (
        "identity.telephone",
        re.compile(r"^(?:telephone|phone|tel|điện\s+thoại|hotline)\s*[:\-]\s*(.+)$", re.IGNORECASE),
    ),
    (
        "identity.email",
        re.compile(r"^(?:email|e-mail)\s*[:\-]\s*([^\s]+@[^\s]+)$", re.IGNORECASE),
    ),
    (
        "identity.founding_date",
        re.compile(
            r"^(?:founding|founded|incorporation)\s+(?:date|day)?\s*[:\-]\s*(.+)$",
            re.IGNORECASE,
        ),
    ),
)


class DeterministicFactExtractor:
    """Extract direct facts from DocumentBlocks without calling AI."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.fact_repo = FactCandidateRepository(session)
        self.confidence = ConfidenceCalculator()

    async def extract(
        self,
        workspace_id: uuid.UUID,
        company_id: uuid.UUID,
        research_job_id: uuid.UUID,
        snapshot_ids: list[uuid.UUID],
    ) -> DeterministicExtractionSummary:
        """Create idempotent candidates and evidence for supplied snapshots."""
        company = await self.session.get(CompanyProfile, company_id)
        if company is None or company.workspace_id != workspace_id:
            raise ValueError("COMPANY_NOT_FOUND_FOR_DETERMINISTIC_EXTRACTION")

        summary = DeterministicExtractionSummary()
        for snapshot_id in snapshot_ids:
            snapshot = await self.session.get(SourceSnapshot, snapshot_id)
            if snapshot is None or snapshot.workspace_id != workspace_id:
                summary.warnings.append(f"SNAPSHOT_NOT_FOUND:{snapshot_id}")
                continue

            source = await self.session.get(Source, snapshot.source_id)
            if source is None or source.workspace_id != workspace_id:
                summary.warnings.append(f"SOURCE_NOT_FOUND:{snapshot.source_id}")
                continue

            blocks_stmt = (
                select(DocumentBlock)
                .where(
                    DocumentBlock.workspace_id == workspace_id,
                    DocumentBlock.source_snapshot_id == snapshot.id,
                )
                .order_by(DocumentBlock.block_key.asc())
            )
            blocks_result = await self.session.execute(blocks_stmt)
            blocks = list(blocks_result.scalars().all())

            for block in blocks:
                facts = self._facts_from_block(company, block)
                for field_key, value, support_type in facts:
                    candidate = await self.fact_repo.create_candidate(
                        workspace_id=workspace_id,
                        company_id=company_id,
                        field_key=field_key,
                        value=value,
                        origin_type="deterministic",
                        value_type=self.value_type_for(value),
                        research_job_id=research_job_id,
                        confidence_score=self.confidence.calculate(
                            field_key=field_key,
                            authority_tier=source.authority_for_field(field_key),
                            support_type=support_type,
                            observed_at=self._observed_at(snapshot),
                            origin_type="deterministic",
                        ).total_score,
                        confidence_components=self.confidence.calculate(
                            field_key=field_key,
                            authority_tier=source.authority_for_field(field_key),
                            support_type=support_type,
                            observed_at=self._observed_at(snapshot),
                            origin_type="deterministic",
                        ).to_dict(),
                        confidence_explanation=self.confidence.calculate(
                            field_key=field_key,
                            authority_tier=source.authority_for_field(field_key),
                            support_type=support_type,
                            observed_at=self._observed_at(snapshot),
                            origin_type="deterministic",
                        ).explanation,
                        observed_at=self._observed_at(snapshot),
                    )
                    await self.fact_repo.add_evidence(
                        workspace_id=workspace_id,
                        fact_candidate_id=candidate.id,
                        source_snapshot_id=snapshot.id,
                        document_block_id=block.id,
                        original_excerpt=block.text_content,
                        start_offset=0,
                        end_offset=len(block.text_content),
                        support_type=support_type,
                        extraction_method="deterministic",
                    )
                    if str(candidate.id) not in summary.candidate_ids:
                        summary.candidate_ids.append(str(candidate.id))
                        summary.fact_count += 1

        await self.session.flush()
        return summary

    def _facts_from_block(
        self,
        company: CompanyProfile,
        block: DocumentBlock,
    ) -> list[tuple[str, Any, str]]:
        """Return high-precision facts from one block."""
        facts: list[tuple[str, Any, str]] = []
        if block.block_type in {"table", "structured"} or block.block_metadata.get("format") in {
            "json",
            "json-ld",
        }:
            try:
                payload = json.loads(block.text_content)
            except (TypeError, json.JSONDecodeError):
                payload = None
            if payload is not None:
                entity_text = json.dumps(payload, ensure_ascii=False)
                match_score = calculate_entity_match_score(
                    company.company_name, company.tax_id, entity_text
                )
                if match_score >= 0.3:
                    facts.extend(self._facts_from_structured_payload(payload))

        for line in block.text_content.splitlines():
            clean_line = " ".join(line.split()).strip()
            for field_key, pattern in _LABEL_PATTERNS:
                match = pattern.match(clean_line)
                if match:
                    value = match.group(1).strip()
                    if value:
                        facts.append((field_key, value, "direct"))
                    break
        return facts

    def _facts_from_structured_payload(self, payload: Any) -> list[tuple[str, Any, str]]:
        """Extract only direct schema/API fields with an explicit JSON path."""
        facts: list[tuple[str, Any, str]] = []
        for item in self._walk_dicts(payload):
            name = item.get("legalName") or item.get("name")
            if isinstance(name, str) and name.strip():
                facts.append(("identity.legal_name", name.strip(), "structured"))

            website = item.get("url")
            if isinstance(website, str) and website.startswith(("http://", "https://")):
                facts.append(("identity.website", website.strip(), "structured"))

            tax_id = item.get("taxID") or item.get("taxId") or item.get("tax_id")
            if isinstance(tax_id, (str, int)) and str(tax_id).strip():
                facts.append(("identity.tax_id", str(tax_id).strip(), "structured"))

            telephone = item.get("telephone")
            if isinstance(telephone, str) and telephone.strip():
                facts.append(("identity.telephone", telephone.strip(), "structured"))

            email = item.get("email")
            if isinstance(email, str) and email.strip():
                facts.append(("identity.email", email.strip(), "structured"))

            address = self._address_value(item.get("address"))
            if address:
                facts.append(("identity.address", address, "structured"))
                address_value = item.get("address")
                country = (
                    address_value.get("addressCountry") if isinstance(address_value, dict) else None
                )
                if isinstance(country, str) and country.strip():
                    facts.append(("identity.country", country.strip(), "structured"))

            identifier = item.get("identifier")
            if isinstance(identifier, str) and identifier.strip():
                facts.append(("identity.registration_number", identifier.strip(), "structured"))
            elif isinstance(identifier, dict):
                identifier_value = identifier.get("value")
                if isinstance(identifier_value, str) and identifier_value.strip():
                    property_id = str(identifier.get("propertyID", "")).lower()
                    identifier_key = (
                        "identity.tax_id"
                        if "tax" in property_id
                        else "identity.registration_number"
                    )
                    facts.append((identifier_key, identifier_value.strip(), "structured"))

            founding_date = item.get("foundingDate") or item.get("founding_date")
            if isinstance(founding_date, (str, int, float)) and str(founding_date).strip():
                facts.append(("identity.founding_date", str(founding_date).strip(), "structured"))

            ticker = item.get("ticker")
            if isinstance(ticker, str) and ticker.strip():
                facts.append(("identity.ticker", ticker.strip(), "structured"))
            exchange = item.get("exchange") or item.get("stockExchange")
            if isinstance(exchange, str) and exchange.strip():
                facts.append(("identity.exchange", exchange.strip(), "structured"))

            social_links = item.get("sameAs")
            if isinstance(social_links, str):
                social_links = [social_links]
            if isinstance(social_links, list):
                links = [
                    value.strip()
                    for value in social_links
                    if isinstance(value, str) and value.startswith(("http://", "https://"))
                ]
                if links:
                    facts.append(("identity.official_social_links", links, "structured"))

            ceo = item.get("ceo")
            if isinstance(ceo, dict):
                person = self._person_value(ceo)
                if person is not None:
                    facts.append(("leadership.ceo", person, "structured"))

            founders = item.get("founders", item.get("founder"))
            if isinstance(founders, dict):
                founders = [founders]
            if isinstance(founders, list):
                people = [
                    person
                    for value in founders
                    if isinstance(value, dict)
                    for person in [self._person_value(value)]
                    if person is not None
                ]
                if people:
                    facts.append(("leadership.founders", people, "structured"))

            employees = item.get("employee")
            if isinstance(employees, dict):
                employees = [employees]
            if isinstance(employees, list):
                board_members = [
                    person
                    for value in employees
                    if isinstance(value, dict)
                    for person in [self._person_value(value)]
                    if person is not None
                    and str(value.get("jobTitle", value.get("role", ""))).lower()
                    in {"ceo", "chief executive officer", "director", "board member"}
                ]
                if board_members:
                    facts.append(("leadership.board_members", board_members, "structured"))
        return facts

    @staticmethod
    def _person_value(value: dict[str, Any]) -> dict[str, str] | None:
        """Keep only a named person and directly supplied role/title labels."""
        name = value.get("name")
        if not isinstance(name, str) or not name.strip():
            return None
        result = {"name": name.strip()}
        for key in ("role", "jobTitle", "title"):
            role = value.get(key)
            if isinstance(role, str) and role.strip():
                result["role" if key == "jobTitle" else key] = role.strip()
        return result

    @staticmethod
    def _walk_dicts(value: Any) -> list[dict[str, Any]]:
        if isinstance(value, dict):
            dict_items = [value]
            for child in value.values():
                dict_items.extend(DeterministicFactExtractor._walk_dicts(child))
            return dict_items
        if isinstance(value, list):
            list_items: list[dict[str, Any]] = []
            for child in value:
                list_items.extend(DeterministicFactExtractor._walk_dicts(child))
            return list_items
        return []

    @staticmethod
    def _address_value(value: Any) -> str | None:
        if isinstance(value, str):
            return value.strip() or None
        if not isinstance(value, dict):
            return None
        parts = [
            value.get("streetAddress"),
            value.get("addressLocality"),
            value.get("addressRegion"),
            value.get("postalCode"),
            value.get("addressCountry"),
        ]
        cleaned = [str(part).strip() for part in parts if part]
        return ", ".join(cleaned) if cleaned else None

    @staticmethod
    def value_type_for(value: Any) -> str:
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int):
            return "integer"
        if isinstance(value, float):
            return "number"
        if isinstance(value, list):
            return "list"
        if isinstance(value, dict):
            return "object"
        return "string"

    @staticmethod
    def _observed_at(snapshot: SourceSnapshot) -> datetime | None:
        observed_at = snapshot.retrieved_at
        if observed_at is not None and observed_at.tzinfo is None:
            return observed_at.replace(tzinfo=UTC)
        return observed_at
