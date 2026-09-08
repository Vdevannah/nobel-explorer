from __future__ import annotations

import random
import time
from email.utils import parsedate_to_datetime
from time import monotonic
from typing import Any

import requests


COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = (
    "NobelExplorer/1.0 "
    "(educational project; Commons metadata validation prototype)"
)
REQUEST_TIMEOUT = 15
DEFAULT_REQUEST_DELAY = 0.5
DEFAULT_MAX_ATTEMPTS = 3
TRANSIENT_STATUS_CODES = {429, 502, 503, 504}
DEFAULT_THUMBNAIL_WIDTH = 800

EXTMETADATA_FIELDS = (
    "License",
    "LicenseShortName",
    "LicenseUrl",
    "UsageTerms",
    "AttributionRequired",
    "Attribution",
    "Artist",
    "Credit",
    "Copyrighted",
    "Restrictions",
    "ImageDescription",
)


class CommonsError(RuntimeError):
    """Raised when structured Commons data cannot be retrieved."""


class CommonsClient:
    def __init__(
        self,
        session: requests.Session | None = None,
        request_delay: float = DEFAULT_REQUEST_DELAY,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        sleep_func=time.sleep,
        monotonic_func=monotonic,
        jitter_func=random.uniform,
        thumbnail_width: int = DEFAULT_THUMBNAIL_WIDTH,
    ):
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.request_delay = request_delay
        self.max_attempts = max_attempts
        self._sleep = sleep_func
        self._monotonic = monotonic_func
        self._jitter = jitter_func
        self._last_request_at: float | None = None
        self.thumbnail_width = thumbnail_width
        self._file_cache: dict[str, dict[str, Any] | None] = {}

    def _pace_request(self) -> None:
        if self._last_request_at is None or self.request_delay <= 0:
            return
        elapsed = self._monotonic() - self._last_request_at
        remaining_delay = self.request_delay - elapsed
        if remaining_delay > 0:
            self._sleep(remaining_delay)

    @staticmethod
    def _retry_after_seconds(response: requests.Response) -> float | None:
        value = response.headers.get("Retry-After")
        if not value:
            return None
        try:
            return max(0.0, float(value))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(value)
                return max(0.0, retry_at.timestamp() - time.time())
            except (TypeError, ValueError, OverflowError):
                return None

    def _retry_delay(
        self,
        attempt: int,
        response: requests.Response | None = None,
    ) -> float:
        if response is not None:
            retry_after = self._retry_after_seconds(response)
            if retry_after is not None:
                return retry_after
        return (0.5 * (2 ** (attempt - 1))) + self._jitter(0.0, 0.25)

    def _request(self, params: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            response = None
            try:
                self._pace_request()
                response = self.session.get(
                    COMMONS_API_URL,
                    params=params,
                    timeout=REQUEST_TIMEOUT,
                )
                self._last_request_at = self._monotonic()
                response.raise_for_status()
                return response.json()
            except requests.HTTPError as error:
                last_error = error
                status_code = (
                    error.response.status_code
                    if error.response is not None
                    else None
                )
                if (
                    status_code not in TRANSIENT_STATUS_CODES
                    or attempt == self.max_attempts
                ):
                    break
                self._sleep(self._retry_delay(attempt, error.response))
            except requests.Timeout as error:
                last_error = error
                self._last_request_at = self._monotonic()
                if attempt == self.max_attempts:
                    break
                self._sleep(self._retry_delay(attempt))
            except (requests.RequestException, ValueError) as error:
                last_error = error
                break
        raise CommonsError(f"Commons request failed: {last_error}") from last_error

    @staticmethod
    def _extmetadata_value(extmetadata: dict[str, Any], field: str) -> str | None:
        entry = extmetadata.get(field)
        if not isinstance(entry, dict):
            return None
        value = entry.get("value")
        if value is None:
            return None
        return str(value)

    def get_file_info(self, filename: str) -> dict[str, Any] | None:
        """Look up official Commons imageinfo/extmetadata for a P18 filename.

        Returns None when the file does not resolve on Commons. Raises
        CommonsError only for network/transport failures, never for a
        missing file (that is a normal, expected outcome to report).
        """
        if filename in self._file_cache:
            return self._file_cache[filename]

        title = filename if filename.startswith("File:") else f"File:{filename}"
        data = self._request({
            "action": "query",
            "format": "json",
            "titles": title,
            "prop": "imageinfo",
            "iiprop": "url|size|mime|extmetadata",
            "iiurlwidth": self.thumbnail_width,
        })

        pages = data.get("query", {}).get("pages", {})
        page = next(iter(pages.values()), None)
        if not page or "missing" in page or not page.get("imageinfo"):
            self._file_cache[filename] = None
            return None

        info = page["imageinfo"][0]
        extmetadata = info.get("extmetadata", {}) or {}
        result = {
            "filename": filename,
            "canonical_source_url": info.get("descriptionurl"),
            "image_url": info.get("url"),
            "thumbnail_url": info.get("thumburl"),
            "thumbnail_width": info.get("thumbwidth"),
            "thumbnail_height": info.get("thumbheight"),
            "width": info.get("width"),
            "height": info.get("height"),
            "mime": info.get("mime"),
            "extmetadata": {
                field: self._extmetadata_value(extmetadata, field)
                for field in EXTMETADATA_FIELDS
            },
        }
        self._file_cache[filename] = result
        return result

    def search_files(self, query: str, limit: int = 8) -> list[str]:
        """Search the Commons File namespace directly (Phase 7.5J step 3)
        -- an independent discovery path from Wikidata P18 or Wikipedia
        PageImages. Returns bare filenames (no "File:" prefix), ready to
        pass to get_file_info(). Read-only; never validates identity or
        suitability -- callers must still do that.
        """
        data = self._request({
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srnamespace": 6,  # File namespace
            "srlimit": limit,
            "format": "json",
        })
        return [
            item["title"].removeprefix("File:")
            for item in data.get("query", {}).get("search", [])
            if item.get("title")
        ]
