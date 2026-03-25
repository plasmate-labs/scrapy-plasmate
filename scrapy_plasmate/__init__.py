"""Scrapy middleware powered by Plasmate's Semantic Object Model."""

from scrapy_plasmate.middleware import PlasmateDownloaderMiddleware
from scrapy_plasmate.utils import (
    extract_headings,
    extract_links,
    extract_tables,
    extract_text,
)

__version__ = "0.1.0"

__all__ = [
    "PlasmateDownloaderMiddleware",
    "extract_text",
    "extract_links",
    "extract_headings",
    "extract_tables",
]
