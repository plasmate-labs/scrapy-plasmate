# scrapy-plasmate

**Scrapy downloader middleware powered by [Plasmate](https://plasmate.dev)'s Semantic Object Model.**

Stop writing fragile CSS selectors. Let Plasmate parse pages into clean, structured data — then use simple Python to extract what you need.

## The Problem

Scraping Hacker News with vanilla Scrapy means fighting table-based HTML:

```python
# Without Plasmate — brittle, verbose, breaks when HN changes layout
def parse(self, response):
    for row in response.css('tr.athing'):
        title_el = row.css('td.title > span.titleline > a')
        yield {
            'title': title_el.css('::text').get(),
            'url': title_el.attrib.get('href', ''),
            'rank': row.css('td.title > span.rank::text').get('').strip('.'),
        }
```

**Raw HTML from HN**: ~42 KB → ~11,000 tokens  
**Plasmate SOM output**: ~6 KB → ~1,500 tokens (86% reduction)

## The Solution

```python
# With Plasmate — clean, structural, resilient
from scrapy_plasmate import extract_links

def parse(self, response):
    som = response.meta['plasmate_som']
    for link in extract_links(som):
        yield {'title': link['text'], 'url': link['url']}
```

## Installation

```bash
pip install scrapy-plasmate
```

You also need the Plasmate CLI:

```bash
# macOS
brew install nicholasgasior/plasmate/plasmate

# From source
cargo install plasmate

# Or download from https://github.com/nicholasgasior/plasmate/releases
```

## Quick Start

### 1. Enable the middleware

In your Scrapy project's `settings.py`:

```python
DOWNLOADER_MIDDLEWARES = {
    'scrapy_plasmate.PlasmateDownloaderMiddleware': 543,
}
```

### 2. Use SOM in your spider

```python
import scrapy
from scrapy_plasmate import extract_text, extract_links, extract_headings

class MySpider(scrapy.Spider):
    name = 'example'
    start_urls = ['https://example.com']

    def parse(self, response):
        som = response.meta['plasmate_som']

        # Extract all text
        text = extract_text(som)

        # Extract all links
        links = extract_links(som)

        # Extract headings
        headings = extract_headings(som)

        yield {
            'url': response.url,
            'title': som.get('title', ''),
            'text': text,
            'links': links,
            'headings': headings,
        }
```

## Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `PLASMATE_ENABLED` | bool | `True` | Enable/disable the middleware |
| `PLASMATE_TIMEOUT` | int | `30` | Timeout in seconds |
| `PLASMATE_JAVASCRIPT` | bool | `True` | Enable JS rendering |
| `PLASMATE_FORMAT` | str | `'json'` | Output format: `'json'` or `'text'` |
| `PLASMATE_BINARY` | str | `'plasmate'` | Path to plasmate binary |
| `PLASMATE_EXTRA_ARGS` | list | `[]` | Additional CLI arguments |

## Per-Request Control

Skip Plasmate for specific requests:

```python
yield scrapy.Request(url, meta={'plasmate_skip': True})
```

Access the SOM after the middleware runs:

```python
def parse(self, response):
    som = response.meta.get('plasmate_som')
    if som is None:
        # Plasmate was skipped or failed — response is raw HTML
        pass
```

## Utility Functions

All utilities work with the parsed SOM dict from `response.meta['plasmate_som']`:

```python
from scrapy_plasmate import (
    extract_text,      # All text content as a string
    extract_links,     # [{'url': '...', 'text': '...'}]
    extract_headings,  # [{'level': 1, 'text': '...'}]
    extract_tables,    # Table regions/elements from the SOM
)
from scrapy_plasmate.utils import (
    extract_images,    # [{'src': '...', 'alt': '...'}]
    extract_by_role,   # Filter elements by SOM role
)
```

## Comparison

| Feature | Raw Scrapy | scrapy-plasmate |
|---------|-----------|-----------------|
| Setup | CSS/XPath per site | Same utils everywhere |
| Resilience | Breaks on layout changes | Semantic = stable |
| Token efficiency | Full HTML (~11K tokens/page) | SOM (~1.5K tokens/page) |
| JS rendering | Needs scrapy-splash or playwright | Built-in |
| Learning curve | CSS selectors, XPath | `extract_text(som)` |

## Examples

See [`examples/example_spider.py`](examples/example_spider.py) for a complete Hacker News spider.

```bash
# Run the example
scrapy runspider examples/example_spider.py -o stories.json
```

## Fallback Behavior

If Plasmate fails (timeout, binary not found, non-zero exit), the middleware returns `None` and Scrapy falls back to its default downloader. Your spider still works — it just gets raw HTML instead of a SOM.

## License

Apache 2.0 — see [LICENSE](LICENSE).
