"""Core crawling engine for Varuna.

Provides configurable web crawling with session management, rate limiting,
retry logic, and URL traversal strategies. All HTTP operations are simulated
for safe, dependency-free usage.
"""

from __future__ import annotations

import hashlib
import re
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class CrawlMethod(Enum):
    """HTTP methods supported by the crawler."""

    GET = "GET"
    POST = "POST"
    HEAD = "HEAD"
    PUT = "PUT"
    DELETE = "DELETE"


@dataclass
class CrawlRequest:
    """Represents a single crawl request.

    Attributes:
        url: Target URL to crawl.
        method: HTTP method to use.
        headers: Optional request headers.
        params: Optional query parameters.
        body: Optional request body for POST/PUT.
        priority: Priority level (lower = higher priority).
        depth: Current crawl depth from the seed URL.
        parent_url: URL that linked to this request.
    """

    url: str
    method: CrawlMethod = CrawlMethod.GET
    headers: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, str] = field(default_factory=dict)
    body: Optional[str] = None
    priority: int = 0
    depth: int = 0
    parent_url: Optional[str] = None

    def fingerprint(self) -> str:
        """Generate a unique fingerprint for deduplication."""
        raw = f"{self.method.value}:{self.url}:{sorted(self.params.items())}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def full_url(self) -> str:
        """Return URL with query parameters appended."""
        if not self.params:
            return self.url
        query = "&".join(f"{k}={v}" for k, v in sorted(self.params.items()))
        sep = "&" if "?" in self.url else "?"
        return f"{self.url}{sep}{query}"


@dataclass
class CrawlResponse:
    """Represents a crawl response.

    Attributes:
        status: HTTP status code.
        body: Response body content.
        headers: Response headers.
        elapsed_ms: Time taken for the request in milliseconds.
        url: The URL that was requested.
        request: The original request object.
    """

    status: int
    body: str
    headers: Dict[str, str] = field(default_factory=dict)
    elapsed_ms: float = 0.0
    url: str = ""
    request: Optional[CrawlRequest] = None

    @property
    def ok(self) -> bool:
        """Return True if the response status indicates success."""
        return 200 <= self.status < 300

    @property
    def is_redirect(self) -> bool:
        """Return True if the response is a redirect."""
        return 300 <= self.status < 400

    @property
    def is_error(self) -> bool:
        """Return True if the response indicates an error."""
        return self.status >= 400

    def json(self) -> Dict[str, Any]:
        """Attempt to parse the body as JSON-like structure (simulated)."""
        # Simple simulated JSON parsing for demonstration
        result = {}
        body = self.body.strip()
        if body.startswith("{") and body.endswith("}"):
            inner = body[1:-1].strip()
            for pair in inner.split(","):
                if ":" in pair:
                    key, val = pair.split(":", 1)
                    key = key.strip().strip('"')
                    val = val.strip().strip('"')
                    result[key] = val
        return result


class RetryPolicy:
    """Configurable retry policy for failed requests.

    Attributes:
        max_retries: Maximum number of retry attempts.
        backoff_factor: Multiplier for exponential backoff.
        retry_on_statuses: Set of HTTP status codes that trigger a retry.
    """

    def __init__(
        self,
        max_retries: int = 3,
        backoff_factor: float = 1.0,
        retry_on_statuses: Optional[Set[int]] = None,
    ):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.retry_on_statuses = retry_on_statuses or {429, 500, 502, 503, 504}

    def should_retry(self, status: int, attempt: int) -> bool:
        """Determine whether the request should be retried."""
        if attempt >= self.max_retries:
            return False
        return status in self.retry_on_statuses

    def get_delay(self, attempt: int) -> float:
        """Calculate the delay before the next retry attempt."""
        return self.backoff_factor * (2 ** attempt)


class CrawlSession:
    """Manages cookies, rate limiting, and retry logic for a crawl session.

    A session persists state across multiple requests, maintaining cookies,
    enforcing rate limits, and applying retry policies.
    """

    def __init__(
        self,
        default_headers: Optional[Dict[str, str]] = None,
        retry_policy: Optional[RetryPolicy] = None,
        requests_per_second: float = 2.0,
        respect_robots: bool = True,
        user_agent: str = "Varuna/0.1.0",
        response_handler: Optional[Callable[[CrawlRequest], CrawlResponse]] = None,
    ):
        self.default_headers = default_headers or {}
        self.retry_policy = retry_policy or RetryPolicy()
        self.requests_per_second = requests_per_second
        self.respect_robots = respect_robots
        self.user_agent = user_agent
        self.cookies: Dict[str, str] = {}
        self._request_log: List[Tuple[float, str]] = []
        self._response_handler = response_handler
        self._last_request_time: float = 0.0
        self._min_interval = 1.0 / requests_per_second if requests_per_second > 0 else 0.0

    def set_cookie(self, name: str, value: str) -> None:
        """Set a cookie for the session."""
        self.cookies[name] = value

    def get_cookie(self, name: str) -> Optional[str]:
        """Retrieve a cookie by name."""
        return self.cookies.get(name)

    def clear_cookies(self) -> None:
        """Clear all session cookies."""
        self.cookies.clear()

    def _enforce_rate_limit(self) -> float:
        """Enforce the rate limit and return wait time in seconds."""
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval:
            wait_time = self._min_interval - elapsed
            return wait_time
        return 0.0

    def _merge_headers(self, request: CrawlRequest) -> Dict[str, str]:
        """Merge default headers with request-specific headers."""
        merged = {"User-Agent": self.user_agent}
        merged.update(self.default_headers)
        merged.update(request.headers)
        if self.cookies:
            cookie_str = "; ".join(f"{k}={v}" for k, v in self.cookies.items())
            merged["Cookie"] = cookie_str
        return merged

    def execute(self, request: CrawlRequest) -> CrawlResponse:
        """Execute a crawl request with rate limiting and retry logic.

        Args:
            request: The crawl request to execute.

        Returns:
            CrawlResponse from the simulated or provided handler.
        """
        wait_time = self._enforce_rate_limit()
        # In real usage, we would sleep here; we track it instead
        merged_headers = self._merge_headers(request)
        request.headers = merged_headers

        attempt = 0
        response = None

        while True:
            start = time.monotonic()

            if self._response_handler:
                response = self._response_handler(request)
            else:
                response = self._simulate_response(request)

            elapsed = (time.monotonic() - start) * 1000
            response.elapsed_ms = elapsed + (wait_time * 1000)
            response.url = request.full_url()
            response.request = request

            self._last_request_time = time.monotonic()
            self._request_log.append((self._last_request_time, request.url))

            # Extract cookies from response headers
            if "Set-Cookie" in response.headers:
                cookie_parts = response.headers["Set-Cookie"].split("=", 1)
                if len(cookie_parts) == 2:
                    self.set_cookie(cookie_parts[0].strip(), cookie_parts[1].strip())

            if response.ok or not self.retry_policy.should_retry(response.status, attempt):
                break

            attempt += 1

        return response

    def _simulate_response(self, request: CrawlRequest) -> CrawlResponse:
        """Generate a simulated response for testing purposes."""
        url = request.url.lower()

        if "error" in url or "500" in url:
            return CrawlResponse(
                status=500,
                body="Internal Server Error",
                headers={"Content-Type": "text/plain"},
            )
        if "notfound" in url or "404" in url:
            return CrawlResponse(
                status=404,
                body="Not Found",
                headers={"Content-Type": "text/plain"},
            )
        if "redirect" in url:
            return CrawlResponse(
                status=301,
                body="",
                headers={"Location": "https://example.com/redirected"},
            )

        body = (
            "<html><head><title>Test Page</title></head>"
            "<body><h1>Hello Varuna</h1>"
            '<a href="/page1">Page 1</a>'
            '<a href="/page2">Page 2</a>'
            "<p>Sample content for crawling.</p>"
            '<table><tr><th>Name</th><th>Value</th></tr>'
            "<tr><td>alpha</td><td>100</td></tr>"
            "<tr><td>beta</td><td>200</td></tr></table>"
            "</body></html>"
        )
        return CrawlResponse(
            status=200,
            body=body,
            headers={
                "Content-Type": "text/html",
                "Set-Cookie": "session_id=abc123",
            },
        )

    @property
    def request_count(self) -> int:
        """Return the total number of requests made in this session."""
        return len(self._request_log)


class TraversalStrategy(Enum):
    """URL traversal strategy for crawling."""

    BFS = "bfs"
    DFS = "dfs"


class URLFilter:
    """Filter URLs based on include/exclude patterns.

    Uses regex patterns to determine which URLs should be crawled.
    """

    def __init__(
        self,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
    ):
        self._include = [re.compile(p) for p in (include_patterns or [])]
        self._exclude = [re.compile(p) for p in (exclude_patterns or [])]

    def accepts(self, url: str) -> bool:
        """Return True if the URL passes the filter rules.

        Logic:
        - If exclude patterns match, reject.
        - If include patterns are set, at least one must match.
        - If no include patterns, accept by default.
        """
        for pattern in self._exclude:
            if pattern.search(url):
                return False
        if self._include:
            return any(p.search(url) for p in self._include)
        return True


class CrawlStrategy:
    """Manages BFS/DFS URL traversal for a crawl.

    Tracks visited URLs, enforces depth limits, and applies URL filtering.
    """

    def __init__(
        self,
        strategy: TraversalStrategy = TraversalStrategy.BFS,
        max_depth: int = 3,
        max_urls: int = 100,
        url_filter: Optional[URLFilter] = None,
    ):
        self.strategy = strategy
        self.max_depth = max_depth
        self.max_urls = max_urls
        self.url_filter = url_filter or URLFilter()
        self._visited: Set[str] = set()
        self._queue: deque = deque()

    def add_url(self, url: str, depth: int = 0, priority: int = 0) -> bool:
        """Add a URL to the crawl queue if it passes filters.

        Returns True if the URL was added, False if rejected or already visited.
        """
        if url in self._visited:
            return False
        if len(self._visited) >= self.max_urls:
            return False
        if depth > self.max_depth:
            return False
        if not self.url_filter.accepts(url):
            return False

        request = CrawlRequest(url=url, depth=depth, priority=priority)

        if self.strategy == TraversalStrategy.DFS:
            self._queue.appendleft(request)
        else:
            self._queue.append(request)

        self._visited.add(url)
        return True

    def next_url(self) -> Optional[CrawlRequest]:
        """Return the next URL to crawl, or None if the queue is empty."""
        if not self._queue:
            return None
        return self._queue.popleft()

    @property
    def visited_count(self) -> int:
        """Return the number of visited URLs."""
        return len(self._visited)

    @property
    def pending_count(self) -> int:
        """Return the number of URLs still in the queue."""
        return len(self._queue)

    def is_visited(self, url: str) -> bool:
        """Check whether a URL has already been visited."""
        return url in self._visited

    def reset(self) -> None:
        """Reset the crawl state."""
        self._visited.clear()
        self._queue.clear()
