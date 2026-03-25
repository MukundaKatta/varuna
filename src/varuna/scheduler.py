"""Crawl scheduling and rate limiting for Varuna.

Provides a priority-based crawl queue with deduplication, politeness delays,
and token bucket rate limiting.
"""

from __future__ import annotations

import heapq
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from varuna.core import CrawlRequest


@dataclass(order=True)
class PriorityItem:
    """Wrapper for priority queue ordering.

    Lower priority values are dequeued first.
    """

    priority: int
    sequence: int = field(compare=True)
    request: CrawlRequest = field(compare=False)


class RateLimiter:
    """Token bucket rate limiter.

    Controls the rate of requests using a token bucket algorithm.
    Tokens are added at a fixed rate, and each request consumes one token.

    Attributes:
        rate: Tokens added per second.
        capacity: Maximum number of tokens in the bucket.
    """

    def __init__(self, rate: float = 1.0, capacity: int = 10):
        self.rate = rate
        self.capacity = capacity
        self._tokens: float = float(capacity)
        self._last_refill: float = time.monotonic()

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
        self._last_refill = now

    def acquire(self) -> bool:
        """Try to acquire a token. Returns True if successful."""
        self._refill()
        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return True
        return False

    def wait_time(self) -> float:
        """Return the seconds to wait before a token is available."""
        self._refill()
        if self._tokens >= 1.0:
            return 0.0
        deficit = 1.0 - self._tokens
        return deficit / self.rate if self.rate > 0 else float("inf")

    @property
    def available_tokens(self) -> float:
        """Return the current number of available tokens."""
        self._refill()
        return self._tokens

    def reset(self) -> None:
        """Reset the limiter to full capacity."""
        self._tokens = float(self.capacity)
        self._last_refill = time.monotonic()


class CrawlScheduler:
    """Manages the crawl queue with priority, deduplication, and politeness.

    The scheduler maintains a priority queue of URLs to crawl, deduplicates
    requests by fingerprint, and enforces per-domain politeness delays.

    Attributes:
        rate_limiter: Token bucket rate limiter for global rate control.
        politeness_delay: Minimum seconds between requests to the same domain.
    """

    def __init__(
        self,
        rate_limiter: Optional[RateLimiter] = None,
        politeness_delay: float = 1.0,
    ):
        self.rate_limiter = rate_limiter or RateLimiter()
        self.politeness_delay = politeness_delay
        self._heap: List[PriorityItem] = []
        self._seen: Set[str] = set()
        self._domain_last_access: Dict[str, float] = {}
        self._sequence: int = 0
        self._total_scheduled: int = 0

    def enqueue(self, request: CrawlRequest) -> bool:
        """Add a request to the crawl queue.

        Returns True if the request was enqueued, False if it was
        a duplicate or otherwise rejected.
        """
        fingerprint = request.fingerprint()
        if fingerprint in self._seen:
            return False

        self._seen.add(fingerprint)
        item = PriorityItem(
            priority=request.priority,
            sequence=self._sequence,
            request=request,
        )
        heapq.heappush(self._heap, item)
        self._sequence += 1
        self._total_scheduled += 1
        return True

    def dequeue(self) -> Optional[CrawlRequest]:
        """Remove and return the highest-priority request.

        Returns None if the queue is empty.
        """
        if not self._heap:
            return None
        item = heapq.heappop(self._heap)
        return item.request

    def is_polite(self, domain: str) -> bool:
        """Check whether enough time has passed since the last request to a domain."""
        last_access = self._domain_last_access.get(domain)
        if last_access is None:
            return True
        elapsed = time.monotonic() - last_access
        return elapsed >= self.politeness_delay

    def record_access(self, domain: str) -> None:
        """Record the time of a request to a domain."""
        self._domain_last_access[domain] = time.monotonic()

    @property
    def pending_count(self) -> int:
        """Return the number of requests in the queue."""
        return len(self._heap)

    @property
    def total_scheduled(self) -> int:
        """Return the total number of requests that have been scheduled."""
        return self._total_scheduled

    @property
    def seen_count(self) -> int:
        """Return the number of unique request fingerprints seen."""
        return len(self._seen)

    def clear(self) -> None:
        """Clear the queue and all tracking state."""
        self._heap.clear()
        self._seen.clear()
        self._domain_last_access.clear()
        self._sequence = 0
        self._total_scheduled = 0
