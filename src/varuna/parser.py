"""HTML parsing and data extraction for Varuna.

Provides regex-based parsing of HTML-like strings for link extraction,
text extraction, table parsing, and selector-based element extraction.
No external dependencies required.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ParsedLink:
    """A link extracted from HTML content.

    Attributes:
        href: The URL from the href attribute.
        text: The anchor text.
        attrs: Additional attributes on the anchor tag.
    """

    href: str
    text: str = ""
    attrs: Dict[str, str] = field(default_factory=dict)

    def is_absolute(self) -> bool:
        """Return True if the href is an absolute URL."""
        return self.href.startswith(("http://", "https://", "//"))

    def resolve(self, base_url: str) -> str:
        """Resolve a relative URL against a base URL."""
        if self.is_absolute():
            return self.href
        if self.href.startswith("/"):
            # Extract scheme + host from base
            match = re.match(r"(https?://[^/]+)", base_url)
            if match:
                return match.group(1) + self.href
        # Relative path
        if base_url.endswith("/"):
            return base_url + self.href
        return base_url.rsplit("/", 1)[0] + "/" + self.href


@dataclass
class ParsedTable:
    """A table extracted from HTML content.

    Attributes:
        headers: Column header names.
        rows: List of row data (each row is a list of cell values).
    """

    headers: List[str] = field(default_factory=list)
    rows: List[List[str]] = field(default_factory=list)

    def to_dicts(self) -> List[Dict[str, str]]:
        """Convert table rows to a list of dictionaries keyed by headers."""
        if not self.headers:
            return []
        return [
            dict(zip(self.headers, row))
            for row in self.rows
            if len(row) == len(self.headers)
        ]

    @property
    def row_count(self) -> int:
        """Return the number of data rows."""
        return len(self.rows)


class HTMLParser:
    """Regex-based HTML parser for extracting structured data.

    Extracts links, text content, tables, and elements matching
    CSS-like selectors from HTML strings.
    """

    # Regex patterns for HTML parsing
    _LINK_PATTERN = re.compile(
        r'<a\s+[^>]*href=["\']([^"\']*)["\'][^>]*>(.*?)</a>',
        re.IGNORECASE | re.DOTALL,
    )
    _TAG_PATTERN = re.compile(r"<[^>]+>")
    _TITLE_PATTERN = re.compile(
        r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL
    )
    _META_PATTERN = re.compile(
        r'<meta\s+[^>]*name=["\']([^"\']*)["\'][^>]*content=["\']([^"\']*)["\']',
        re.IGNORECASE,
    )
    _TABLE_PATTERN = re.compile(
        r"<table[^>]*>(.*?)</table>", re.IGNORECASE | re.DOTALL
    )
    _TR_PATTERN = re.compile(r"<tr[^>]*>(.*?)</tr>", re.IGNORECASE | re.DOTALL)
    _TH_PATTERN = re.compile(r"<th[^>]*>(.*?)</th>", re.IGNORECASE | re.DOTALL)
    _TD_PATTERN = re.compile(r"<td[^>]*>(.*?)</td>", re.IGNORECASE | re.DOTALL)
    _HEADING_PATTERN = re.compile(
        r"<h([1-6])[^>]*>(.*?)</h\1>", re.IGNORECASE | re.DOTALL
    )

    def __init__(self, html: str):
        self._html = html

    @property
    def html(self) -> str:
        """Return the raw HTML content."""
        return self._html

    def extract_links(self) -> List[ParsedLink]:
        """Extract all anchor links from the HTML."""
        links = []
        for match in self._LINK_PATTERN.finditer(self._html):
            href = match.group(1).strip()
            text = self._strip_tags(match.group(2)).strip()
            links.append(ParsedLink(href=href, text=text))
        return links

    def extract_text(self) -> str:
        """Extract all visible text content, stripping HTML tags."""
        text = self._TAG_PATTERN.sub(" ", self._html)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def extract_title(self) -> Optional[str]:
        """Extract the page title."""
        match = self._TITLE_PATTERN.search(self._html)
        if match:
            return self._strip_tags(match.group(1)).strip()
        return None

    def extract_meta(self) -> Dict[str, str]:
        """Extract meta tag name/content pairs."""
        meta = {}
        for match in self._META_PATTERN.finditer(self._html):
            meta[match.group(1)] = match.group(2)
        return meta

    def extract_tables(self) -> List[ParsedTable]:
        """Extract all tables from the HTML as structured data."""
        tables = []
        for table_match in self._TABLE_PATTERN.finditer(self._html):
            table_html = table_match.group(1)
            parsed = ParsedTable()

            rows = self._TR_PATTERN.findall(table_html)
            for i, row_html in enumerate(rows):
                headers = self._TH_PATTERN.findall(row_html)
                cells = self._TD_PATTERN.findall(row_html)

                if headers and not parsed.headers:
                    parsed.headers = [self._strip_tags(h).strip() for h in headers]
                elif cells:
                    parsed.rows.append([self._strip_tags(c).strip() for c in cells])

            tables.append(parsed)
        return tables

    def extract_headings(self) -> List[Tuple[int, str]]:
        """Extract all headings with their level (1-6)."""
        headings = []
        for match in self._HEADING_PATTERN.finditer(self._html):
            level = int(match.group(1))
            text = self._strip_tags(match.group(2)).strip()
            headings.append((level, text))
        return headings

    def select(self, selector: str) -> List[str]:
        """Select elements by a simple CSS-like selector.

        Supports:
            - Tag names: 'p', 'div', 'span'
            - Classes: '.classname'
            - IDs: '#idname'

        Returns the inner content of matched elements.
        """
        if selector.startswith("#"):
            id_val = selector[1:]
            pattern = re.compile(
                rf'<\w+[^>]*id=["\']{ re.escape(id_val) }["\'][^>]*>(.*?)</\w+>',
                re.IGNORECASE | re.DOTALL,
            )
        elif selector.startswith("."):
            class_val = selector[1:]
            pattern = re.compile(
                rf'<\w+[^>]*class=["\'][^"\']*\b{ re.escape(class_val) }\b[^"\']*["\'][^>]*>(.*?)</\w+>',
                re.IGNORECASE | re.DOTALL,
            )
        else:
            tag = re.escape(selector)
            pattern = re.compile(
                rf"<{tag}[^>]*>(.*?)</{tag}>",
                re.IGNORECASE | re.DOTALL,
            )

        return [self._strip_tags(m.group(1)).strip() for m in pattern.finditer(self._html)]

    def _strip_tags(self, text: str) -> str:
        """Remove HTML tags from a string."""
        return self._TAG_PATTERN.sub("", text)


class DataExtractor:
    """Extract structured data from crawl responses.

    Combines parsing capabilities to extract specific data structures
    from pages based on configurable extraction rules.
    """

    def __init__(self):
        self._rules: List[Dict[str, Any]] = []

    def add_rule(
        self,
        name: str,
        selector: str,
        transform: Optional[str] = None,
    ) -> None:
        """Add an extraction rule.

        Args:
            name: Field name for the extracted data.
            selector: CSS-like selector to find the element.
            transform: Optional transform ('lower', 'upper', 'strip', 'int').
        """
        self._rules.append({
            "name": name,
            "selector": selector,
            "transform": transform,
        })

    def extract(self, html: str) -> Dict[str, Any]:
        """Apply all extraction rules to an HTML string.

        Returns a dictionary of field names to extracted values.
        """
        parser = HTMLParser(html)
        result: Dict[str, Any] = {}

        for rule in self._rules:
            matches = parser.select(rule["selector"])
            value = matches[0] if matches else None

            if value and rule.get("transform"):
                value = self._apply_transform(value, rule["transform"])

            result[rule["name"]] = value

        return result

    def extract_all(self, html: str) -> Dict[str, List[Any]]:
        """Apply all rules and return all matches (not just the first)."""
        parser = HTMLParser(html)
        result: Dict[str, List[Any]] = {}

        for rule in self._rules:
            matches = parser.select(rule["selector"])
            if rule.get("transform"):
                matches = [self._apply_transform(m, rule["transform"]) for m in matches]
            result[rule["name"]] = matches

        return result

    @staticmethod
    def _apply_transform(value: str, transform: str) -> Any:
        """Apply a named transform to a value."""
        if transform == "lower":
            return value.lower()
        if transform == "upper":
            return value.upper()
        if transform == "strip":
            return value.strip()
        if transform == "int":
            try:
                return int(value)
            except ValueError:
                return None
        return value

    @property
    def rule_count(self) -> int:
        """Return the number of registered extraction rules."""
        return len(self._rules)
