"""Example spider: Scrape Hacker News front page using Plasmate.

Run with:
    scrapy runspider examples/example_spider.py -o items.json

Requires:
    pip install scrapy-plasmate
    cargo install plasmate
"""

import scrapy

from scrapy_plasmate import extract_links, extract_text


class HackerNewsSpider(scrapy.Spider):
    """Scrape Hacker News stories using Plasmate's Semantic Object Model.

    With Plasmate, you get clean structured data instead of parsing
    raw HTML tables. The SOM automatically identifies story titles,
    links, scores, and metadata.
    """

    name = "hackernews"
    start_urls = ["https://news.ycombinator.com"]

    custom_settings = {
        # Enable the Plasmate middleware
        "DOWNLOADER_MIDDLEWARES": {
            "scrapy_plasmate.PlasmateDownloaderMiddleware": 543,
        },
        # Plasmate settings
        "PLASMATE_ENABLED": True,
        "PLASMATE_TIMEOUT": 30,
        "PLASMATE_JAVASCRIPT": False,  # HN doesn't need JS
    }

    def parse(self, response):
        """Parse the Hacker News front page.

        With Plasmate, response.meta['plasmate_som'] contains the
        structured SOM — no need to write fragile CSS selectors
        against HN's table-based layout.
        """
        som = response.meta.get("plasmate_som")

        if som is None:
            self.logger.warning("No SOM data — Plasmate may not be installed")
            return

        # Extract all links from the SOM
        links = extract_links(som)

        # Filter for story links (HN stories link to external sites or item pages)
        for link in links:
            url = link["url"]
            text = link["text"]

            # Skip navigation/meta links
            if not text or len(text) < 5:
                continue
            if url.startswith(("login", "submit", "newest", "threads")):
                continue

            yield {
                "title": text,
                "url": response.urljoin(url),
            }

        # Follow "More" link to next page
        for link in links:
            if link["text"].strip().lower() == "more":
                next_url = response.urljoin(link["url"])
                yield scrapy.Request(next_url, callback=self.parse)
                break


class HackerNewsDetailSpider(scrapy.Spider):
    """Advanced example: scrape story + comments using SOM text extraction."""

    name = "hackernews_detail"
    start_urls = ["https://news.ycombinator.com"]

    custom_settings = {
        "DOWNLOADER_MIDDLEWARES": {
            "scrapy_plasmate.PlasmateDownloaderMiddleware": 543,
        },
        "DEPTH_LIMIT": 2,
    }

    def parse(self, response):
        som = response.meta.get("plasmate_som", {})
        links = extract_links(som)

        for link in links:
            url = link["url"]
            if "item?id=" in url:
                yield scrapy.Request(
                    response.urljoin(url),
                    callback=self.parse_comments,
                    meta={"story_title": link["text"]},
                )

    def parse_comments(self, response):
        som = response.meta.get("plasmate_som", {})
        text = extract_text(som)

        yield {
            "title": response.meta.get("story_title", ""),
            "url": response.url,
            "content": text[:2000],  # First 2000 chars of discussion
        }
