"""Deterministic URL classification and relevance ranking for source discovery."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import unquote, urlparse

PAGE_GROUP_TOKENS: dict[str, tuple[str, ...]] = {
    "about_company_history": (
        "about",
        "company",
        "gioi thieu",
        "gioithieu",
        "ve chung toi",
        "vechungtoi",
        "history",
        "lich su",
        "lichsu",
        "overview",
        "profile",
    ),
    "products_services_solutions": (
        "product",
        "products",
        "service",
        "services",
        "solution",
        "solutions",
        "san pham",
        "sanpham",
        "dich vu",
        "dichvu",
        "giai phap",
        "giaiphap",
    ),
    "leadership": (
        "leadership",
        "management",
        "executive",
        "board",
        "team",
        "lanh dao",
        "lanhdao",
        "ban dieu hanh",
        "bandieuhanh",
    ),
    "markets_customers_partners": (
        "market",
        "markets",
        "customer",
        "customers",
        "partner",
        "partners",
        "thi truong",
        "thitruong",
        "khach hang",
        "khachhang",
        "doi tac",
        "doitac",
    ),
    "investor_relations": (
        "investor",
        "investors",
        "investor relations",
        "ir",
        "quan he co dong",
        "quanhecodong",
    ),
    "annual_reports": (
        "annual report",
        "annual-report",
        "annualreports",
        "report",
        "reports",
        "bao cao",
        "baocao",
        "tai chinh",
        "taichinh",
    ),
    "news": (
        "news",
        "press",
        "media",
        "tin tuc",
        "tintuc",
        "bao chi",
        "baochi",
    ),
    "careers": (
        "career",
        "careers",
        "jobs",
        "job",
        "recruit",
        "recruitment",
        "tuyen dung",
        "tuyendung",
        "viec lam",
        "vieclam",
    ),
    "contact": (
        "contact",
        "contacts",
        "lien he",
        "lienhe",
        "head office",
        "dia chi",
        "diachi",
    ),
}

EXCLUDED_PATH_TOKENS: tuple[str, ...] = (
    "login",
    "signin",
    "sign-in",
    "account",
    "register",
    "privacy",
    "cookie",
    "cart",
    "checkout",
    "admin",
    "wp-admin",
    "password",
)


@dataclass(frozen=True, slots=True)
class UrlRanking:
    """Explainable deterministic classification result for one URL."""

    page_group: str | None
    relevance_score: float
    excluded: bool
    reason: str


def normalize_domain(value: str) -> str:
    """Return a comparison-safe hostname, treating ``www`` as an alias."""
    candidate = value.strip()
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    hostname = (urlparse(candidate).hostname or "").strip().lower().rstrip(".")
    if hostname.startswith("www."):
        hostname = hostname[4:]
    try:
        return hostname.encode("idna").decode("ascii")
    except UnicodeError:
        return hostname


def _fold_text(value: str) -> str:
    """Fold accents and punctuation for multilingual token matching."""
    folded = unicodedata.normalize("NFKD", value.lower())
    ascii_text = "".join(char for char in folded if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", ascii_text).strip()


def _matches_token(text: str, token: str) -> bool:
    """Match a token in both separated and concatenated Vietnamese paths."""
    folded_text = _fold_text(text)
    folded_token = _fold_text(token)
    if not folded_token:
        return False
    return folded_token in folded_text or folded_token.replace(" ", "") in folded_text.replace(
        " ", ""
    )


def _path_has_excluded_token(path: str) -> str | None:
    """Return the first sensitive path token that makes a URL unsuitable."""
    folded_path = _fold_text(unquote(path))
    for token in EXCLUDED_PATH_TOKENS:
        if _matches_token(folded_path, token):
            return token
    return None


def classify_and_rank_url(
    url: str,
    *,
    title: str = "",
    snippet: str = "",
    official_domain: str = "",
    discovered_via: str = "",
    crawl_depth: int = 0,
) -> UrlRanking:
    """Classify and score a URL without relying on exact path names.

    Scores are discovery priorities only. They never turn a snippet into
    evidence or replace entity/source policy checks.
    """
    parsed = urlparse(url)
    path_and_query = unquote(f"{parsed.path} {parsed.query}")
    excluded_token = _path_has_excluded_token(path_and_query)
    if excluded_token is not None:
        return UrlRanking(
            page_group=None,
            relevance_score=0.0,
            excluded=True,
            reason=f"excluded_path_token:{excluded_token}",
        )

    path_text = _fold_text(path_and_query)
    title_text = _fold_text(f"{title} {snippet}")
    group: str | None = None
    path_match_count = 0
    title_match_count = 0
    for group_name, tokens in PAGE_GROUP_TOKENS.items():
        path_matches = sum(1 for token in tokens if _matches_token(path_text, token))
        title_matches = sum(1 for token in tokens if _matches_token(title_text, token))
        if path_matches > path_match_count or (
            path_matches == path_match_count and title_matches > title_match_count
        ):
            group = group_name
            path_match_count = path_matches
            title_match_count = title_matches

    score = 0.28
    reason_parts: list[str] = []
    if group is not None:
        score += 0.28
        reason_parts.append(f"page_group:{group}")
    if title_match_count:
        score += 0.12
        reason_parts.append("title_token_match")
    if parsed.path.lower().endswith((".pdf", ".xlsx", ".xls")) and group == "annual_reports":
        score += 0.12
        reason_parts.append("report_document")
    if official_domain and normalize_domain(parsed.hostname or "") == normalize_domain(
        official_domain
    ):
        score += 0.16
        reason_parts.append("official_domain")
    if discovered_via == "official_website":
        score += 0.08
        reason_parts.append("official_website")
    elif discovered_via == "internal_link":
        score += 0.06
        reason_parts.append("internal_link")
    elif discovered_via == "sitemap":
        score += 0.04
        reason_parts.append("sitemap")

    score -= min(max(crawl_depth, 0) * 0.04, 0.2)
    score = round(max(0.0, min(1.0, score)), 4)
    if not reason_parts:
        reason_parts.append("general_public_page")
    return UrlRanking(
        page_group=group,
        relevance_score=score,
        excluded=False,
        reason=";".join(reason_parts),
    )
