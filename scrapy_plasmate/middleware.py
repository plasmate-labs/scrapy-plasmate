"""Scrapy downloader middleware that uses Plasmate for content extraction."""

import json
import logging
import subprocess

from scrapy.http import HtmlResponse, TextResponse

logger = logging.getLogger(__name__)


class PlasmateDownloaderMiddleware:
    """Use Plasmate's Semantic Object Model instead of raw HTML.

    Plasmate replaces the default Scrapy downloader for requests, returning
    structured SOM (Semantic Object Model) data instead of raw HTML. This
    dramatically reduces token counts for LLM pipelines and simplifies
    extraction logic.

    Enable in settings.py::

        DOWNLOADER_MIDDLEWARES = {
            'scrapy_plasmate.PlasmateDownloaderMiddleware': 543,
        }

    Settings:
        PLASMATE_ENABLED (bool): Enable/disable the middleware. Default: True.
        PLASMATE_TIMEOUT (int): Timeout in seconds for plasmate CLI. Default: 30.
        PLASMATE_JAVASCRIPT (bool): Enable JS rendering. Default: True.
        PLASMATE_FORMAT (str): Output format — 'json' or 'text'. Default: 'json'.
        PLASMATE_BINARY (str): Path to plasmate binary. Default: 'plasmate'.
        PLASMATE_EXTRA_ARGS (list): Additional CLI arguments. Default: [].

    Per-request meta keys:
        plasmate_skip (bool): Skip Plasmate for this request, use default downloader.
        plasmate_som (dict): After processing, contains the parsed SOM data.
    """

    def __init__(self):
        self.enabled = True
        self.timeout = 30
        self.javascript = True
        self.format = "json"
        self.binary = "plasmate"
        self.extra_args = []

    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls()
        settings = crawler.settings
        middleware.enabled = settings.getbool("PLASMATE_ENABLED", True)
        middleware.timeout = settings.getint("PLASMATE_TIMEOUT", 30)
        middleware.javascript = settings.getbool("PLASMATE_JAVASCRIPT", True)
        middleware.format = settings.get("PLASMATE_FORMAT", "json")
        middleware.binary = settings.get("PLASMATE_BINARY", "plasmate")
        middleware.extra_args = settings.getlist("PLASMATE_EXTRA_ARGS", [])
        return middleware

    def _build_command(self, url):
        """Build the plasmate CLI command."""
        cmd = [self.binary, "fetch"]

        if self.format == "text":
            cmd.append("--format=text")

        if not self.javascript:
            cmd.append("--no-js")

        cmd.extend(self.extra_args)
        cmd.append(url)
        return cmd

    def process_request(self, request, spider):
        """Intercept requests and fetch via Plasmate instead of default downloader."""
        if not self.enabled:
            return None

        if request.meta.get("plasmate_skip", False):
            return None

        cmd = self._build_command(request.url)
        logger.debug("Plasmate fetching: %s", request.url)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            if result.returncode != 0:
                logger.warning(
                    "Plasmate returned non-zero exit code %d for %s: %s",
                    result.returncode,
                    request.url,
                    result.stderr.strip(),
                )
                return None  # Fall back to default downloader

            body = result.stdout

            # Parse SOM and store in meta for easy access
            if self.format == "json":
                try:
                    request.meta["plasmate_som"] = json.loads(body)
                except json.JSONDecodeError:
                    logger.warning(
                        "Plasmate returned invalid JSON for %s, passing raw output",
                        request.url,
                    )

            # Return as a response so Scrapy skips the default downloader
            response_cls = HtmlResponse if self.format == "json" else TextResponse
            return response_cls(
                url=request.url,
                body=body.encode("utf-8"),
                encoding="utf-8",
                request=request,
            )

        except subprocess.TimeoutExpired:
            logger.warning(
                "Plasmate timed out after %ds for %s", self.timeout, request.url
            )
        except FileNotFoundError:
            logger.error(
                "Plasmate binary not found at '%s'. "
                "Install with: cargo install plasmate",
                self.binary,
            )
        except Exception:
            logger.exception("Unexpected error running Plasmate for %s", request.url)

        return None  # Fall back to default downloader

    def process_exception(self, request, exception, spider):
        """Handle download exceptions — no special handling needed."""
        return None
