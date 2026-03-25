"""Tests for varuna.core — crawler, session, strategy, and URL filtering."""

from varuna.core import (
    CrawlMethod,
    CrawlRequest,
    CrawlResponse,
    CrawlSession,
    CrawlStrategy,
    RetryPolicy,
    TraversalStrategy,
    URLFilter,
)


class TestCrawlRequest:
    def test_default_method(self):
        req = CrawlRequest(url="https://example.com")
        assert req.method == CrawlMethod.GET

    def test_fingerprint_deterministic(self):
        req = CrawlRequest(url="https://example.com", params={"a": "1", "b": "2"})
        assert req.fingerprint() == req.fingerprint()

    def test_fingerprint_differs_by_method(self):
        r1 = CrawlRequest(url="https://example.com", method=CrawlMethod.GET)
        r2 = CrawlRequest(url="https://example.com", method=CrawlMethod.POST)
        assert r1.fingerprint() != r2.fingerprint()

    def test_full_url_no_params(self):
        req = CrawlRequest(url="https://example.com/path")
        assert req.full_url() == "https://example.com/path"

    def test_full_url_with_params(self):
        req = CrawlRequest(url="https://example.com", params={"q": "test"})
        assert "q=test" in req.full_url()


class TestCrawlResponse:
    def test_ok_status(self):
        resp = CrawlResponse(status=200, body="ok")
        assert resp.ok is True
        assert resp.is_error is False

    def test_error_status(self):
        resp = CrawlResponse(status=500, body="error")
        assert resp.ok is False
        assert resp.is_error is True

    def test_redirect_status(self):
        resp = CrawlResponse(status=301, body="")
        assert resp.is_redirect is True
        assert resp.ok is False

    def test_json_parsing(self):
        resp = CrawlResponse(status=200, body='{"name": "varuna", "version": "1"}')
        data = resp.json()
        assert data["name"] == "varuna"


class TestRetryPolicy:
    def test_should_retry_on_matching_status(self):
        policy = RetryPolicy(max_retries=3)
        assert policy.should_retry(500, attempt=0) is True

    def test_should_not_retry_on_success(self):
        policy = RetryPolicy(max_retries=3)
        assert policy.should_retry(200, attempt=0) is False

    def test_should_not_retry_past_max(self):
        policy = RetryPolicy(max_retries=2)
        assert policy.should_retry(500, attempt=2) is False

    def test_backoff_delay(self):
        policy = RetryPolicy(backoff_factor=0.5)
        assert policy.get_delay(0) == 0.5
        assert policy.get_delay(1) == 1.0
        assert policy.get_delay(2) == 2.0


class TestCrawlSession:
    def test_default_session_crawls(self):
        session = CrawlSession()
        req = CrawlRequest(url="https://example.com")
        resp = session.execute(req)
        assert resp.ok is True
        assert resp.status == 200

    def test_session_tracks_cookies(self):
        session = CrawlSession()
        req = CrawlRequest(url="https://example.com")
        session.execute(req)
        assert session.get_cookie("session_id") == "abc123"

    def test_session_request_count(self):
        session = CrawlSession()
        session.execute(CrawlRequest(url="https://example.com"))
        session.execute(CrawlRequest(url="https://example.com/page2"))
        assert session.request_count == 2

    def test_custom_response_handler(self):
        def handler(req):
            return CrawlResponse(status=418, body="I'm a teapot")

        session = CrawlSession(response_handler=handler)
        resp = session.execute(CrawlRequest(url="https://example.com"))
        assert resp.status == 418

    def test_error_url_simulation(self):
        session = CrawlSession()
        resp = session.execute(CrawlRequest(url="https://example.com/error"))
        assert resp.status == 500

    def test_cookie_management(self):
        session = CrawlSession()
        session.set_cookie("token", "xyz")
        assert session.get_cookie("token") == "xyz"
        session.clear_cookies()
        assert session.get_cookie("token") is None

    def test_user_agent_in_headers(self):
        session = CrawlSession(user_agent="TestBot/1.0")
        req = CrawlRequest(url="https://example.com")
        session.execute(req)
        assert req.headers["User-Agent"] == "TestBot/1.0"


class TestURLFilter:
    def test_accept_all_by_default(self):
        f = URLFilter()
        assert f.accepts("https://anything.com") is True

    def test_exclude_pattern(self):
        f = URLFilter(exclude_patterns=[r"\.pdf$"])
        assert f.accepts("https://example.com/doc.pdf") is False
        assert f.accepts("https://example.com/page") is True

    def test_include_pattern(self):
        f = URLFilter(include_patterns=[r"example\.com"])
        assert f.accepts("https://example.com/page") is True
        assert f.accepts("https://other.com/page") is False

    def test_exclude_overrides_include(self):
        f = URLFilter(
            include_patterns=[r"example\.com"],
            exclude_patterns=[r"/admin"],
        )
        assert f.accepts("https://example.com/admin") is False


class TestCrawlStrategy:
    def test_bfs_order(self):
        strategy = CrawlStrategy(strategy=TraversalStrategy.BFS)
        strategy.add_url("https://a.com")
        strategy.add_url("https://b.com")
        first = strategy.next_url()
        assert first is not None
        assert first.url == "https://a.com"

    def test_dfs_order(self):
        strategy = CrawlStrategy(strategy=TraversalStrategy.DFS)
        strategy.add_url("https://a.com")
        strategy.add_url("https://b.com")
        first = strategy.next_url()
        assert first is not None
        assert first.url == "https://b.com"

    def test_deduplication(self):
        strategy = CrawlStrategy()
        assert strategy.add_url("https://a.com") is True
        assert strategy.add_url("https://a.com") is False

    def test_depth_limit(self):
        strategy = CrawlStrategy(max_depth=1)
        assert strategy.add_url("https://a.com", depth=2) is False

    def test_max_urls_limit(self):
        strategy = CrawlStrategy(max_urls=2)
        strategy.add_url("https://a.com")
        strategy.add_url("https://b.com")
        assert strategy.add_url("https://c.com") is False

    def test_reset(self):
        strategy = CrawlStrategy()
        strategy.add_url("https://a.com")
        strategy.reset()
        assert strategy.visited_count == 0
        assert strategy.pending_count == 0
