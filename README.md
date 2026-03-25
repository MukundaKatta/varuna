# 🔱 Varuna — Adaptive Web Scraping

> **Hindu Mythology**: God of Cosmic Order | Adaptive crawling with rate limiting and URL management

[![CI](https://github.com/MukundaKatta/varuna/actions/workflows/ci.yml/badge.svg)](https://github.com/MukundaKatta/varuna/actions/workflows/ci.yml)
[![GitHub Pages](https://img.shields.io/badge/🌐_Live_Demo-Visit_Site-blue?style=for-the-badge)](https://MukundaKatta.github.io/varuna/)
[![GitHub](https://img.shields.io/github/license/MukundaKatta/varuna?style=flat-square)](LICENSE)
[![Stars](https://img.shields.io/github/stars/MukundaKatta/varuna?style=flat-square)](https://github.com/MukundaKatta/varuna/stargazers)

## Overview

Varuna is an adaptive web scraping framework that scales from single requests to full-scale crawls, handling dynamic sites and anti-bot measures. Built with zero external dependencies, it provides configurable crawling with BFS/DFS traversal, session management, rate limiting, and structured data extraction.

**Tech Stack:** Python 3.9+ | No external dependencies

## Quick Start

```bash
git clone https://github.com/MukundaKatta/varuna.git
cd varuna

# Run tests
PYTHONPATH=src python3 -m pytest tests/ -v --tb=short

# CLI usage
PYTHONPATH=src python3 -m varuna https://example.com --depth 2 --strategy bfs
```

## Features

- **Configurable Crawler** — GET/POST with custom headers, params, and cookies
- **Session Management** — Persistent cookies, automatic rate limiting, retry with backoff
- **BFS/DFS Traversal** — Choose breadth-first or depth-first URL discovery
- **URL Filtering** — Regex-based include/exclude patterns
- **HTML Parsing** — Extract links, tables, headings, and meta tags (regex-based, no deps)
- **Data Extraction** — Rule-based structured extraction with transforms
- **Crawl Scheduler** — Priority queue with deduplication and politeness delays
- **Rate Limiting** — Token bucket algorithm for controlled request rates

## Project Structure

```
varuna/
├── src/varuna/
│   ├── __init__.py          # Package metadata
│   ├── __main__.py          # Module entry point
│   ├── core.py              # Crawler engine, sessions, strategies
│   ├── parser.py            # HTML parsing and data extraction
│   ├── scheduler.py         # Priority queue and rate limiting
│   ├── config.py            # Environment-based configuration
│   └── cli.py               # Command-line interface
├── tests/
│   ├── test_core.py         # Crawler and strategy tests
│   ├── test_parser.py       # Parser and extractor tests
│   └── test_scheduler.py    # Scheduler and rate limiter tests
├── pyproject.toml
├── Makefile
├── .env.example
├── ARCHITECTURE.md
└── CONTRIBUTING.md
```

## Configuration

Copy `.env.example` to `.env` and adjust:

| Variable | Default | Description |
|----------|---------|-------------|
| `VARUNA_MAX_DEPTH` | 3 | Maximum crawl depth |
| `VARUNA_MAX_URLS` | 100 | Maximum URLs to crawl |
| `VARUNA_RPS` | 2.0 | Requests per second |
| `VARUNA_POLITENESS` | 1.0 | Per-domain delay (seconds) |
| `VARUNA_STRATEGY` | bfs | Traversal strategy (bfs/dfs) |

## Live Demo

Visit the landing page: **https://MukundaKatta.github.io/varuna/**

## License

MIT License — 2026 Officethree Technologies

## Part of the Mythological Portfolio

This is project **#varuna** in the [100-project Mythological Portfolio](https://github.com/MukundaKatta) by Officethree Technologies.
