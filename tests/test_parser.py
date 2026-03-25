"""Tests for varuna.parser — HTML parsing and data extraction."""

from varuna.parser import DataExtractor, HTMLParser, ParsedLink, ParsedTable


SAMPLE_HTML = (
    '<html><head><title>Test Page</title>'
    '<meta name="description" content="A test page">'
    '</head><body>'
    '<h1>Main Heading</h1>'
    '<h2>Sub Heading</h2>'
    '<p class="intro">Welcome to the test page.</p>'
    '<p id="special">Special paragraph.</p>'
    '<a href="https://example.com/page1">Page 1</a>'
    '<a href="/page2">Page 2</a>'
    '<a href="relative.html">Relative</a>'
    '<table><tr><th>Name</th><th>Value</th></tr>'
    '<tr><td>alpha</td><td>100</td></tr>'
    '<tr><td>beta</td><td>200</td></tr></table>'
    '</body></html>'
)


class TestHTMLParser:
    def test_extract_title(self):
        parser = HTMLParser(SAMPLE_HTML)
        assert parser.extract_title() == "Test Page"

    def test_extract_links(self):
        parser = HTMLParser(SAMPLE_HTML)
        links = parser.extract_links()
        assert len(links) == 3
        assert links[0].href == "https://example.com/page1"
        assert links[0].text == "Page 1"

    def test_extract_text_strips_tags(self):
        parser = HTMLParser(SAMPLE_HTML)
        text = parser.extract_text()
        assert "Main Heading" in text
        assert "<h1>" not in text

    def test_extract_meta(self):
        parser = HTMLParser(SAMPLE_HTML)
        meta = parser.extract_meta()
        assert meta.get("description") == "A test page"

    def test_extract_tables(self):
        parser = HTMLParser(SAMPLE_HTML)
        tables = parser.extract_tables()
        assert len(tables) == 1
        assert tables[0].headers == ["Name", "Value"]
        assert tables[0].row_count == 2

    def test_table_to_dicts(self):
        parser = HTMLParser(SAMPLE_HTML)
        tables = parser.extract_tables()
        dicts = tables[0].to_dicts()
        assert dicts[0] == {"Name": "alpha", "Value": "100"}

    def test_extract_headings(self):
        parser = HTMLParser(SAMPLE_HTML)
        headings = parser.extract_headings()
        assert (1, "Main Heading") in headings
        assert (2, "Sub Heading") in headings

    def test_select_by_tag(self):
        parser = HTMLParser(SAMPLE_HTML)
        results = parser.select("h1")
        assert "Main Heading" in results

    def test_select_by_class(self):
        parser = HTMLParser(SAMPLE_HTML)
        results = parser.select(".intro")
        assert len(results) == 1
        assert "Welcome" in results[0]

    def test_select_by_id(self):
        parser = HTMLParser(SAMPLE_HTML)
        results = parser.select("#special")
        assert len(results) == 1
        assert "Special paragraph" in results[0]


class TestParsedLink:
    def test_absolute_url(self):
        link = ParsedLink(href="https://example.com/page")
        assert link.is_absolute() is True

    def test_relative_url(self):
        link = ParsedLink(href="/page")
        assert link.is_absolute() is False

    def test_resolve_absolute(self):
        link = ParsedLink(href="https://other.com/page")
        assert link.resolve("https://example.com") == "https://other.com/page"

    def test_resolve_root_relative(self):
        link = ParsedLink(href="/page2")
        resolved = link.resolve("https://example.com/dir/page1")
        assert resolved == "https://example.com/page2"

    def test_resolve_relative(self):
        link = ParsedLink(href="sibling.html")
        resolved = link.resolve("https://example.com/dir/page1")
        assert resolved == "https://example.com/dir/sibling.html"


class TestDataExtractor:
    def test_extract_single(self):
        extractor = DataExtractor()
        extractor.add_rule("heading", "h1")
        result = extractor.extract(SAMPLE_HTML)
        assert result["heading"] == "Main Heading"

    def test_extract_with_transform(self):
        extractor = DataExtractor()
        extractor.add_rule("heading", "h1", transform="upper")
        result = extractor.extract(SAMPLE_HTML)
        assert result["heading"] == "MAIN HEADING"

    def test_extract_all(self):
        extractor = DataExtractor()
        extractor.add_rule("paras", "p")
        result = extractor.extract_all(SAMPLE_HTML)
        assert len(result["paras"]) == 2

    def test_rule_count(self):
        extractor = DataExtractor()
        extractor.add_rule("a", "h1")
        extractor.add_rule("b", "h2")
        assert extractor.rule_count == 2

    def test_missing_selector_returns_none(self):
        extractor = DataExtractor()
        extractor.add_rule("missing", ".nonexistent")
        result = extractor.extract(SAMPLE_HTML)
        assert result["missing"] is None

    def test_int_transform(self):
        html = '<span class="count">42</span>'
        extractor = DataExtractor()
        extractor.add_rule("count", ".count", transform="int")
        result = extractor.extract(html)
        assert result["count"] == 42
