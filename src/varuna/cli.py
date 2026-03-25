"""Command-line interface for Varuna.

Provides a simple CLI for running crawl jobs from the terminal.
"""

from __future__ import annotations

import argparse
import sys

from varuna.config import VarunaConfig
from varuna.core import (
    CrawlRequest,
    CrawlSession,
    CrawlStrategy,
    RetryPolicy,
    TraversalStrategy,
    URLFilter,
)
from varuna.parser import HTMLParser


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="varuna",
        description="Varuna - Adaptive Web Scraping Framework",
    )
    parser.add_argument("url", help="Seed URL to start crawling")
    parser.add_argument(
        "--depth", type=int, default=None, help="Maximum crawl depth"
    )
    parser.add_argument(
        "--max-urls", type=int, default=None, help="Maximum URLs to crawl"
    )
    parser.add_argument(
        "--strategy",
        choices=["bfs", "dfs"],
        default=None,
        help="Traversal strategy",
    )
    parser.add_argument(
        "--rps", type=float, default=None, help="Requests per second"
    )
    parser.add_argument(
        "--user-agent", default=None, help="Custom User-Agent string"
    )
    parser.add_argument(
        "--include", nargs="*", default=None, help="URL include patterns (regex)"
    )
    parser.add_argument(
        "--exclude", nargs="*", default=None, help="URL exclude patterns (regex)"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the Varuna CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    config = VarunaConfig.from_env()

    if args.depth is not None:
        config.max_depth = args.depth
    if args.max_urls is not None:
        config.max_urls = args.max_urls
    if args.strategy is not None:
        config.strategy = args.strategy
    if args.rps is not None:
        config.requests_per_second = args.rps
    if args.user_agent is not None:
        config.user_agent = args.user_agent

    strategy_enum = (
        TraversalStrategy.DFS if config.strategy == "dfs" else TraversalStrategy.BFS
    )
    url_filter = URLFilter(
        include_patterns=args.include,
        exclude_patterns=args.exclude,
    )

    retry_policy = RetryPolicy(
        max_retries=config.retry_max,
        backoff_factor=config.retry_backoff,
    )
    session = CrawlSession(
        requests_per_second=config.requests_per_second,
        user_agent=config.user_agent,
        respect_robots=config.respect_robots,
        retry_policy=retry_policy,
    )
    crawl = CrawlStrategy(
        strategy=strategy_enum,
        max_depth=config.max_depth,
        max_urls=config.max_urls,
        url_filter=url_filter,
    )

    crawl.add_url(args.url, depth=0)
    crawled = 0

    print(f"Varuna starting crawl: {args.url}")
    print(f"Strategy: {config.strategy.upper()} | Max depth: {config.max_depth}")
    print("-" * 60)

    while True:
        request = crawl.next_url()
        if request is None:
            break

        response = session.execute(request)
        crawled += 1

        status_mark = "OK" if response.ok else f"ERR({response.status})"
        print(f"[{crawled}] {status_mark} {request.url} ({response.elapsed_ms:.1f}ms)")

        if response.ok and response.headers.get("Content-Type", "").startswith("text/html"):
            parser = HTMLParser(response.body)
            links = parser.extract_links()
            for link in links:
                resolved = link.resolve(request.url)
                crawl.add_url(resolved, depth=request.depth + 1)

    print("-" * 60)
    print(f"Crawl complete: {crawled} pages, {crawl.visited_count} URLs discovered")
    return 0


if __name__ == "__main__":
    sys.exit(main())
