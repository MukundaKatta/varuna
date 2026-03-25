# Architecture

## Overview

Varuna is structured as a modular web scraping framework with three core layers:

```
CLI / Entry Point
       |
   [core.py]         -- Crawl engine: requests, responses, sessions, strategies
   [parser.py]       -- HTML parsing and structured data extraction
   [scheduler.py]    -- Priority queue, deduplication, rate limiting
   [config.py]       -- Environment-based configuration
```

## Core (`core.py`)

- **CrawlRequest / CrawlResponse** — Value objects for HTTP request/response cycle
- **CrawlSession** — Manages cookies, headers, rate limiting, and retry logic
- **CrawlStrategy** — BFS/DFS URL traversal with depth limits and URL filtering
- **URLFilter** — Regex-based include/exclude URL filtering
- **RetryPolicy** — Configurable exponential backoff retry logic

## Parser (`parser.py`)

- **HTMLParser** — Regex-based extraction of links, text, tables, headings, and meta tags
- **DataExtractor** — Rule-based structured data extraction with transforms

## Scheduler (`scheduler.py`)

- **CrawlScheduler** — Priority heap queue with fingerprint-based deduplication
- **RateLimiter** — Token bucket algorithm for global rate control

## Design Decisions

- **No external dependencies** — All HTTP and HTML operations are simulated
- **Python 3.9+ compatible** — Uses `from __future__ import annotations`
- **Simulated responses** — Pluggable response handlers for testing and extension
