"""Tests for varuna.scheduler — crawl queue, deduplication, and rate limiting."""

import time

from varuna.core import CrawlRequest
from varuna.scheduler import CrawlScheduler, RateLimiter


class TestRateLimiter:
    def test_acquire_within_capacity(self):
        limiter = RateLimiter(rate=10.0, capacity=5)
        for _ in range(5):
            assert limiter.acquire() is True

    def test_acquire_exhausts_tokens(self):
        limiter = RateLimiter(rate=0.01, capacity=1)
        assert limiter.acquire() is True
        assert limiter.acquire() is False

    def test_wait_time_when_empty(self):
        limiter = RateLimiter(rate=1.0, capacity=1)
        limiter.acquire()
        wait = limiter.wait_time()
        assert wait > 0

    def test_reset(self):
        limiter = RateLimiter(rate=1.0, capacity=5)
        for _ in range(5):
            limiter.acquire()
        limiter.reset()
        assert limiter.available_tokens == 5.0


class TestCrawlScheduler:
    def test_enqueue_and_dequeue(self):
        sched = CrawlScheduler()
        req = CrawlRequest(url="https://example.com")
        assert sched.enqueue(req) is True
        result = sched.dequeue()
        assert result is not None
        assert result.url == "https://example.com"

    def test_deduplication(self):
        sched = CrawlScheduler()
        req = CrawlRequest(url="https://example.com")
        assert sched.enqueue(req) is True
        assert sched.enqueue(req) is False
        assert sched.seen_count == 1

    def test_priority_ordering(self):
        sched = CrawlScheduler()
        sched.enqueue(CrawlRequest(url="https://low.com", priority=10))
        sched.enqueue(CrawlRequest(url="https://high.com", priority=1))
        first = sched.dequeue()
        assert first is not None
        assert first.url == "https://high.com"

    def test_politeness_check(self):
        sched = CrawlScheduler(politeness_delay=0.5)
        assert sched.is_polite("example.com") is True
        sched.record_access("example.com")
        assert sched.is_polite("example.com") is False

    def test_clear(self):
        sched = CrawlScheduler()
        sched.enqueue(CrawlRequest(url="https://a.com"))
        sched.enqueue(CrawlRequest(url="https://b.com"))
        sched.clear()
        assert sched.pending_count == 0
        assert sched.seen_count == 0

    def test_empty_dequeue_returns_none(self):
        sched = CrawlScheduler()
        assert sched.dequeue() is None

    def test_total_scheduled(self):
        sched = CrawlScheduler()
        sched.enqueue(CrawlRequest(url="https://a.com"))
        sched.enqueue(CrawlRequest(url="https://b.com"))
        assert sched.total_scheduled == 2
