"""Deterministic multilingual discovery query generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from company_profile.db.models.company import CompanyProfile


@dataclass(frozen=True, slots=True)
class DiscoveryQuery:
    """One provider-neutral discovery query and its audit metadata."""

    query: str
    language_code: str
    purpose: str
    requested_section: str
    generated_by: str = "deterministic_template"


SECTION_TERMS: dict[str, dict[str, str]] = {
    "official": {"en": "official company website", "vi": "website chính thức công ty"},
    "about_company_history": {
        "en": "about company history",
        "vi": "giới thiệu công ty lịch sử",
    },
    "products_services_solutions": {
        "en": "products services solutions",
        "vi": "sản phẩm dịch vụ giải pháp",
    },
    "leadership": {"en": "leadership management", "vi": "lãnh đạo ban điều hành"},
    "markets_customers_partners": {
        "en": "markets customers partners",
        "vi": "thị trường khách hàng đối tác",
    },
    "investor_relations": {
        "en": "investor relations",
        "vi": "quan hệ nhà đầu tư",
    },
    "annual_reports": {"en": "annual reports", "vi": "báo cáo thường niên"},
    "news": {"en": "company news", "vi": "tin tức công ty"},
    "careers": {"en": "careers recruitment", "vi": "tuyển dụng việc làm"},
    "contact": {"en": "contact headquarters", "vi": "liên hệ trụ sở"},
}


def _unique(values: Sequence[str]) -> list[str]:
    """Keep non-empty query terms in stable first-seen order."""
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        clean = " ".join(value.split()).strip()
        key = clean.casefold()
        if clean and key not in seen:
            seen.add(key)
            result.append(clean)
    return result


def _website_domain(scope: Mapping[str, Any], company: CompanyProfile) -> str:
    """Extract a hostname from the explicit or persisted company website."""
    values: list[str] = []
    for key in ("website_url", "website"):
        value = scope.get(key)
        if isinstance(value, str):
            values.append(value)
    if company.website_url:
        values.append(company.website_url)
    for value in values:
        candidate = value if "://" in value else f"https://{value}"
        hostname = urlparse(candidate).hostname
        if hostname:
            return hostname.lower().removeprefix("www.")
    return ""


def _requested_sections(scope: Mapping[str, Any]) -> list[str]:
    """Read requested sections while accepting singular and list forms."""
    raw: list[Any] = []
    for key in ("requested_section", "requested_sections", "sections"):
        value = scope.get(key)
        if isinstance(value, str):
            raw.append(value)
        elif isinstance(value, list):
            raw.extend(value)
    sections = _unique([str(value) for value in raw])
    return sections or ["official"]


def _section_key(section: str) -> str:
    """Map user-facing section names to the stable query-template key."""
    normalized = section.casefold().replace("-", "_").replace(" ", "_")
    aliases = {
        "about": "about_company_history",
        "company": "about_company_history",
        "history": "about_company_history",
        "products": "products_services_solutions",
        "services": "products_services_solutions",
        "solutions": "products_services_solutions",
        "markets": "markets_customers_partners",
        "customers": "markets_customers_partners",
        "partners": "markets_customers_partners",
        "investors": "investor_relations",
        "annual_report": "annual_reports",
        "report": "annual_reports",
    }
    return aliases.get(normalized, normalized)


class DiscoveryQueryBuilder:
    """Build bounded, vendor-neutral queries from canonical company fields."""

    def build(
        self,
        company: CompanyProfile,
        scope: Mapping[str, Any],
        *,
        default_locale: str = "vi",
    ) -> list[DiscoveryQuery]:
        """Generate deterministic English/Vietnamese query templates."""
        canonical_name = company.legal_name or company.company_name
        aliases = [
            alias.alias_name
            for alias in company.__dict__.get("aliases", [])
            if getattr(alias, "alias_name", "")
        ]
        aliases.extend(
            value for value in scope.get("aliases", []) if isinstance(value, str)
        ) if isinstance(scope.get("aliases"), list) else None
        names = _unique([canonical_name, company.company_name, *aliases])[:4]
        country_values = [
            value
            for key in ("country", "country_name", "country_code")
            if isinstance((value := scope.get(key)), str)
        ]
        if not country_values and str(scope.get("country_code", "")).upper() == "VN":
            country_values = ["Vietnam"]
        identifiers = _unique(
            [
                value
                for value in (company.registration_number, company.tax_id)
                if isinstance(value, str)
            ]
        )
        domain = _website_domain(scope, company)
        languages = scope.get("search_languages")
        if isinstance(languages, list):
            language_codes = _unique([str(value).lower() for value in languages])
        else:
            primary = default_locale.lower() if default_locale.lower() in {"en", "vi"} else "en"
            language_codes = [primary, "en" if primary == "vi" else "vi"]

        queries: list[DiscoveryQuery] = []
        explicit_query = scope.get("search_query")
        if isinstance(explicit_query, str) and explicit_query.strip():
            queries.append(
                DiscoveryQuery(
                    query=" ".join(explicit_query.split()),
                    language_code=default_locale.lower(),
                    purpose="user_requested",
                    requested_section="official",
                    generated_by="user_input",
                )
            )

        for section in _requested_sections(scope):
            section_key = _section_key(section)
            section_terms = SECTION_TERMS.get(section_key, SECTION_TERMS["official"])
            for language_code in language_codes:
                tokens = [f'"{names[0]}"']
                if len(names) > 1:
                    tokens.append("aliases " + " ".join(f'"{name}"' for name in names[1:]))
                if country_values:
                    tokens.append("country " + " ".join(country_values))
                if domain:
                    tokens.append(f"site:{domain}")
                if identifiers:
                    tokens.append("registration " + " ".join(identifiers))
                tokens.append(section_terms.get(language_code, section_terms["en"]))
                queries.append(
                    DiscoveryQuery(
                        query=" ".join(tokens),
                        language_code=language_code,
                        purpose="source_discovery",
                        requested_section=section_key,
                    )
                )

        unique_queries: list[DiscoveryQuery] = []
        seen: set[str] = set()
        for query in queries:
            key = query.query.casefold()
            if key not in seen:
                seen.add(key)
                unique_queries.append(query)
        return unique_queries
