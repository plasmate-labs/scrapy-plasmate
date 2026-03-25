"""Helper utilities for working with Plasmate SOM in Scrapy spiders."""

from __future__ import annotations

from typing import Any


def extract_text(som: dict[str, Any]) -> str:
    """Extract all text content from a SOM.

    Args:
        som: Parsed Plasmate SOM dictionary.

    Returns:
        All text content joined by newlines.

    Example::

        som = response.meta['plasmate_som']
        text = extract_text(som)
        print(text[:200])
    """
    parts: list[str] = []
    for region in som.get("regions", []):
        for el in region.get("elements", []):
            text = el.get("text", "")
            if text:
                parts.append(text)
    return "\n".join(parts)


def extract_links(som: dict[str, Any]) -> list[dict[str, str]]:
    """Extract all links from a SOM.

    Args:
        som: Parsed Plasmate SOM dictionary.

    Returns:
        List of dicts with 'url' and 'text' keys.

    Example::

        links = extract_links(som)
        for link in links:
            print(f"{link['text']} -> {link['url']}")
    """
    links: list[dict[str, str]] = []
    for region in som.get("regions", []):
        for el in region.get("elements", []):
            href = el.get("attrs", {}).get("href", "")
            text = el.get("text", "")
            if href:
                links.append({"url": href, "text": text})
    return links


def extract_headings(som: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract all headings from a SOM.

    Args:
        som: Parsed Plasmate SOM dictionary.

    Returns:
        List of dicts with 'level' (int) and 'text' (str) keys.

    Example::

        headings = extract_headings(som)
        for h in headings:
            print(f"{'#' * h['level']} {h['text']}")
    """
    headings: list[dict[str, Any]] = []
    for region in som.get("regions", []):
        for el in region.get("elements", []):
            if el.get("role") == "heading":
                level = el.get("attrs", {}).get("level", 2)
                headings.append({"level": level, "text": el.get("text", "")})
    return headings


def extract_tables(som: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract tables from a SOM.

    Args:
        som: Parsed Plasmate SOM dictionary.

    Returns:
        List of table region/element dicts from the SOM.
    """
    tables: list[dict[str, Any]] = []
    for region in som.get("regions", []):
        if region.get("role") == "table":
            tables.append(region)
        for el in region.get("elements", []):
            if el.get("role") == "table":
                tables.append(el)
    return tables


def extract_images(som: dict[str, Any]) -> list[dict[str, str]]:
    """Extract image references from a SOM.

    Args:
        som: Parsed Plasmate SOM dictionary.

    Returns:
        List of dicts with 'src' and 'alt' keys.
    """
    images: list[dict[str, str]] = []
    for region in som.get("regions", []):
        for el in region.get("elements", []):
            if el.get("role") == "image":
                src = el.get("attrs", {}).get("src", "")
                alt = el.get("attrs", {}).get("alt", "")
                if src:
                    images.append({"src": src, "alt": alt})
    return images


def extract_by_role(som: dict[str, Any], role: str) -> list[dict[str, Any]]:
    """Extract all elements with a specific role from a SOM.

    Args:
        som: Parsed Plasmate SOM dictionary.
        role: The role to filter by (e.g., 'button', 'input', 'navigation').

    Returns:
        List of matching element dicts.
    """
    results: list[dict[str, Any]] = []
    for region in som.get("regions", []):
        if region.get("role") == role:
            results.append(region)
        for el in region.get("elements", []):
            if el.get("role") == role:
                results.append(el)
    return results
