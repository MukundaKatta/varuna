"""Configuration management for Varuna.

Loads settings from environment variables with sensible defaults.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class VarunaConfig:
    """Global configuration for a Varuna crawl session.

    Attributes:
        max_depth: Maximum crawl depth from seed URLs.
        max_urls: Maximum total URLs to crawl.
        requests_per_second: Global rate limit.
        politeness_delay: Per-domain delay in seconds.
        user_agent: User-Agent header value.
        respect_robots: Whether to respect robots.txt.
        strategy: Traversal strategy ('bfs' or 'dfs').
        retry_max: Maximum retry attempts per request.
        retry_backoff: Backoff multiplier for retries.
    """

    max_depth: int = 3
    max_urls: int = 100
    requests_per_second: float = 2.0
    politeness_delay: float = 1.0
    user_agent: str = "Varuna/0.1.0"
    respect_robots: bool = True
    strategy: str = "bfs"
    retry_max: int = 3
    retry_backoff: float = 1.0

    @classmethod
    def from_env(cls) -> "VarunaConfig":
        """Load configuration from environment variables."""
        return cls(
            max_depth=int(os.environ.get("VARUNA_MAX_DEPTH", "3")),
            max_urls=int(os.environ.get("VARUNA_MAX_URLS", "100")),
            requests_per_second=float(os.environ.get("VARUNA_RPS", "2.0")),
            politeness_delay=float(os.environ.get("VARUNA_POLITENESS", "1.0")),
            user_agent=os.environ.get("VARUNA_USER_AGENT", "Varuna/0.1.0"),
            respect_robots=os.environ.get("VARUNA_RESPECT_ROBOTS", "true").lower() == "true",
            strategy=os.environ.get("VARUNA_STRATEGY", "bfs"),
            retry_max=int(os.environ.get("VARUNA_RETRY_MAX", "3")),
            retry_backoff=float(os.environ.get("VARUNA_RETRY_BACKOFF", "1.0")),
        )
