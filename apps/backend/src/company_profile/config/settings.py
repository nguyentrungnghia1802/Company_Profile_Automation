"""Typed application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration.

    All settings are loaded from environment variables.
    See .env.example for documentation of each variable.
    """

    # --- Application ---
    environment: str = "development"
    app_name: str = "Verified Company Profile"
    web_origin: str = "http://localhost:3000"
    api_origin: str = "http://localhost:8000"
    log_level: str = "INFO"
    default_locale: str = "vi"

    # --- CORS ---
    cors_origins: list[str] = ["http://localhost:3000"]

    # --- Database ---
    database_url: str = "postgresql+asyncpg://vcps:vcps_dev@localhost:5432/vcps"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_echo: bool = False

    # --- Authentication ---
    auth_mode: str = "mock"  # mock | firebase
    auth_project_id: str = ""
    auth_audience: str = ""

    # --- AI Provider ---
    ai_provider: str = "mock"  # disabled | mock | gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    ai_timeout: int = 60
    ai_max_retries: int = 3
    ai_budget_usd_per_job: float = 1.0  # Maximum AI spend per research job in USD
    ai_kill_switch_enabled: bool = False  # Emergency kill switch to disable all AI calls

    # --- Search Provider ---
    search_provider: str = "fixture"  # fixture | google
    search_api_key: str = ""
    search_engine_id: str = ""

    # --- Fetch ---
    fetch_user_agent: str = "VCPS-Bot/0.1 (+https://example.com/bot)"
    fetch_timeout: int = 30
    fetch_max_response_bytes: int = 10_000_000  # 10 MB
    fetch_max_decompressed_bytes: int = 10_000_000  # 10 MB after content decoding
    fetch_max_redirects: int = 5
    fetch_max_retries: int = 2
    fetch_rate_limit_seconds: float = 0.25
    fetch_max_concurrency_per_domain: int = 2
    fetch_browser_fallback_max_pages: int = 2
    fetch_browser_fallback_enabled: bool = False
    crawl_max_depth: int = 1
    crawl_max_pages_per_domain: int = 25
    crawl_max_pages_per_job: int = 50
    crawl_max_sitemaps: int = 3
    crawl_max_sitemap_urls: int = 100

    # --- Object Storage ---
    object_storage_provider: str = "local"  # local | gcs
    local_storage_root: str = "./data/storage"
    gcs_bucket: str = ""
    signed_url_expiry_seconds: int = 300

    # --- Malware Scanner ---
    malware_scanner_mode: str = "mock"  # mock | production

    # --- Worker ---
    task_dispatcher: str = "postgres"  # postgres | cloud_tasks
    worker_id: str = "worker-local-1"
    worker_poll_interval: int = 5
    worker_claim_lease_seconds: int = 300
    worker_batch_size: int = 5
    worker_retry_base_delay: int = 10
    worker_retry_max_delay: int = 600

    model_config = {
        "env_prefix": "",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
