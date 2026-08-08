"""Public import boundary for the bounded crawl coordinator."""

from company_profile.modules.sources.fetcher import CrawlCoordinator, CrawledPage

__all__ = ["CrawlCoordinator", "CrawledPage"]
