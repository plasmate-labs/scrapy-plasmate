"""Tests for scrapy-plasmate middleware and utilities."""

import json
from unittest.mock import MagicMock, patch

import pytest
from scrapy.http import HtmlResponse, Request
from scrapy.utils.test import get_crawler

from scrapy_plasmate.middleware import PlasmateDownloaderMiddleware
from scrapy_plasmate.utils import (
    extract_by_role,
    extract_headings,
    extract_images,
    extract_links,
    extract_tables,
    extract_text,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_SOM = {
    "url": "https://example.com",
    "title": "Example Domain",
    "regions": [
        {
            "role": "navigation",
            "elements": [
                {
                    "role": "link",
                    "text": "Home",
                    "attrs": {"href": "/"},
                },
                {
                    "role": "link",
                    "text": "About",
                    "attrs": {"href": "/about"},
                },
            ],
        },
        {
            "role": "main",
            "elements": [
                {
                    "role": "heading",
                    "text": "Example Domain",
                    "attrs": {"level": 1},
                },
                {
                    "role": "text",
                    "text": "This domain is for use in illustrative examples.",
                },
                {
                    "role": "link",
                    "text": "More information...",
                    "attrs": {"href": "https://www.iana.org/domains/example"},
                },
                {
                    "role": "image",
                    "attrs": {"src": "/logo.png", "alt": "Example logo"},
                },
            ],
        },
        {
            "role": "table",
            "elements": [
                {"role": "row", "text": "Header1 | Header2"},
                {"role": "row", "text": "Cell1 | Cell2"},
            ],
        },
    ],
}

SAMPLE_SOM_JSON = json.dumps(SAMPLE_SOM)


@pytest.fixture
def middleware():
    """Create a middleware instance with default settings."""
    crawler = get_crawler(settings_dict={})
    return PlasmateDownloaderMiddleware.from_crawler(crawler)


@pytest.fixture
def spider():
    return MagicMock()


# ---------------------------------------------------------------------------
# Middleware tests
# ---------------------------------------------------------------------------


class TestPlasmateDownloaderMiddleware:
    def test_from_crawler_defaults(self):
        crawler = get_crawler(settings_dict={})
        mw = PlasmateDownloaderMiddleware.from_crawler(crawler)
        assert mw.enabled is True
        assert mw.timeout == 30
        assert mw.javascript is True
        assert mw.format == "json"
        assert mw.binary == "plasmate"

    def test_from_crawler_custom_settings(self):
        crawler = get_crawler(
            settings_dict={
                "PLASMATE_ENABLED": False,
                "PLASMATE_TIMEOUT": 60,
                "PLASMATE_JAVASCRIPT": False,
                "PLASMATE_FORMAT": "text",
                "PLASMATE_BINARY": "/usr/local/bin/plasmate",
                "PLASMATE_EXTRA_ARGS": ["--verbose"],
            }
        )
        mw = PlasmateDownloaderMiddleware.from_crawler(crawler)
        assert mw.enabled is False
        assert mw.timeout == 60
        assert mw.javascript is False
        assert mw.format == "text"
        assert mw.binary == "/usr/local/bin/plasmate"
        assert mw.extra_args == ["--verbose"]

    def test_disabled_returns_none(self, middleware, spider):
        middleware.enabled = False
        request = Request("https://example.com")
        assert middleware.process_request(request, spider) is None

    def test_skip_meta_returns_none(self, middleware, spider):
        request = Request("https://example.com", meta={"plasmate_skip": True})
        assert middleware.process_request(request, spider) is None

    @patch("scrapy_plasmate.middleware.subprocess.run")
    def test_successful_fetch(self, mock_run, middleware, spider):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=SAMPLE_SOM_JSON,
            stderr="",
        )

        request = Request("https://example.com")
        response = middleware.process_request(request, spider)

        assert response is not None
        assert isinstance(response, HtmlResponse)
        assert response.url == "https://example.com"
        assert request.meta["plasmate_som"] == SAMPLE_SOM

        # Verify CLI command
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "plasmate"
        assert cmd[1] == "fetch"
        assert "https://example.com" in cmd

    @patch("scrapy_plasmate.middleware.subprocess.run")
    def test_nonzero_exit_falls_back(self, mock_run, middleware, spider):
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="error: network failure",
        )

        request = Request("https://example.com")
        assert middleware.process_request(request, spider) is None

    @patch("scrapy_plasmate.middleware.subprocess.run")
    def test_timeout_falls_back(self, mock_run, middleware, spider):
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="plasmate", timeout=30)

        request = Request("https://example.com")
        assert middleware.process_request(request, spider) is None

    @patch("scrapy_plasmate.middleware.subprocess.run")
    def test_binary_not_found_falls_back(self, mock_run, middleware, spider):
        mock_run.side_effect = FileNotFoundError()

        request = Request("https://example.com")
        assert middleware.process_request(request, spider) is None

    @patch("scrapy_plasmate.middleware.subprocess.run")
    def test_invalid_json_still_returns_response(self, mock_run, middleware, spider):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="not valid json {{{",
            stderr="",
        )

        request = Request("https://example.com")
        response = middleware.process_request(request, spider)

        # Should still return a response (body has the raw output)
        assert response is not None
        assert "plasmate_som" not in request.meta

    def test_build_command_default(self, middleware):
        cmd = middleware._build_command("https://example.com")
        assert cmd == ["plasmate", "fetch", "https://example.com"]

    def test_build_command_text_format(self, middleware):
        middleware.format = "text"
        cmd = middleware._build_command("https://example.com")
        assert "--format=text" in cmd

    def test_build_command_no_js(self, middleware):
        middleware.javascript = False
        cmd = middleware._build_command("https://example.com")
        assert "--no-js" in cmd

    def test_build_command_extra_args(self, middleware):
        middleware.extra_args = ["--verbose", "--cache"]
        cmd = middleware._build_command("https://example.com")
        assert "--verbose" in cmd
        assert "--cache" in cmd


# ---------------------------------------------------------------------------
# Utils tests
# ---------------------------------------------------------------------------


class TestExtractText:
    def test_extracts_all_text(self):
        text = extract_text(SAMPLE_SOM)
        assert "Home" in text
        assert "Example Domain" in text
        assert "This domain is for use in illustrative examples." in text
        assert "More information..." in text

    def test_empty_som(self):
        assert extract_text({}) == ""
        assert extract_text({"regions": []}) == ""


class TestExtractLinks:
    def test_extracts_all_links(self):
        links = extract_links(SAMPLE_SOM)
        urls = [l["url"] for l in links]
        assert "/" in urls
        assert "/about" in urls
        assert "https://www.iana.org/domains/example" in urls

    def test_link_text(self):
        links = extract_links(SAMPLE_SOM)
        link_map = {l["url"]: l["text"] for l in links}
        assert link_map["/"] == "Home"
        assert link_map["/about"] == "About"

    def test_empty_som(self):
        assert extract_links({}) == []


class TestExtractHeadings:
    def test_extracts_headings(self):
        headings = extract_headings(SAMPLE_SOM)
        assert len(headings) == 1
        assert headings[0]["level"] == 1
        assert headings[0]["text"] == "Example Domain"

    def test_empty_som(self):
        assert extract_headings({}) == []


class TestExtractTables:
    def test_extracts_tables(self):
        tables = extract_tables(SAMPLE_SOM)
        assert len(tables) == 1
        assert tables[0]["role"] == "table"

    def test_empty_som(self):
        assert extract_tables({}) == []


class TestExtractImages:
    def test_extracts_images(self):
        images = extract_images(SAMPLE_SOM)
        assert len(images) == 1
        assert images[0]["src"] == "/logo.png"
        assert images[0]["alt"] == "Example logo"

    def test_empty_som(self):
        assert extract_images({}) == []


class TestExtractByRole:
    def test_extracts_navigation(self):
        navs = extract_by_role(SAMPLE_SOM, "navigation")
        assert len(navs) == 1

    def test_extracts_links(self):
        links = extract_by_role(SAMPLE_SOM, "link")
        assert len(links) == 3  # Home, About, More information

    def test_no_matches(self):
        assert extract_by_role(SAMPLE_SOM, "nonexistent") == []

    def test_empty_som(self):
        assert extract_by_role({}, "link") == []
