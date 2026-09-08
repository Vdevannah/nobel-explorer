from __future__ import annotations

import random
import re
import time
from email.utils import parsedate_to_datetime
from time import monotonic
from typing import Any

import requests

from ETL.image_enrichment.commons import CommonsClient
from ETL.image_enrichment.enrichment import build_laureate_evidence, enrich_commons_for_identity
from ETL.image_enrichment.matching import select_candidate
from ETL.image_enrichment.sources import WikidataClient, WikidataError
from backend.repositories import laureate_repository


WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
USER_AGENT = (
    "NobelExplorer/1.0 "
    "(educational project; Wikipedia PageImage fallback prototype)"
)
REQUEST_TIMEOUT = 15
DEFAULT_REQUEST_DELAY = 0.5
DEFAULT_MAX_ATTEMPTS = 3
TRANSIENT_STATUS_CODES = {429, 502, 503, 504}

# Article-image-list fallback (section 5): conservative blocklist for
# obviously non-portrait content. Substring match, case-insensitive.
_IMAGE_BLOCKLIST_MARKERS = (
    "flag of", "flag_of", "coat of arms", "seal of", "locator", "map of",
    "orthographic", "signature", "autograph", "medal", "logo", "-logo",
    "symbol", "icon", "ooui", "edit-ltr", "edit-rtl", "wikisource",
    "wikiquote", "commons-logo", "nobel prize.png", "nobel medal",
    ".svg",
)

# Section 9: formal/titled Nobel full_name strings often bury the actual
# searchable name behind honorifics, parentheticals, or trailing style.
# These are additional Wikipedia *search query* variants, never a lowered
# matching confidence -- select_candidate still decides ACCEPT/REVIEW/SKIP
# from the same evidence either way.
_TITLE_PREFIX_PATTERN = re.compile(
    r"^(lord|lady|sir|dame|dr\.?|prof\.?|baron|baroness|count|countess|"
    r"earl|viscount|the)\s+",
    re.IGNORECASE,
)
_PARENTHETICAL_PATTERN = re.compile(r"\(([^)]+)\)")


class WikipediaError(RuntimeError):
    """Raised when structured Wikipedia data cannot be retrieved."""


class WikipediaClient:
    def __init__(
        self,
        session: requests.Session | None = None,
        request_delay: float = DEFAULT_REQUEST_DELAY,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        sleep_func=time.sleep,
        monotonic_func=monotonic,
        jitter_func=random.uniform,
    ):
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.request_delay = request_delay
        self.max_attempts = max_attempts
        self._sleep = sleep_func
        self._monotonic = monotonic_func
        self._jitter = jitter_func
        self._last_request_at: float | None = None

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
                    WIKIPEDIA_API_URL,
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
        raise WikipediaError(f"Wikipedia request failed: {last_error}") from last_error

    def search_articles(self, query: str, limit: int = 3) -> list[dict[str, Any]]:
        data = self._request({
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "format": "json",
        })
        return [
            {"title": item["title"], "pageid": item.get("pageid")}
            for item in data.get("query", {}).get("search", [])
            if item.get("title")
        ]

    def resolve_article(self, title: str) -> dict[str, Any] | None:
        """Resolve a title to its canonical article, Wikidata sitelink
        (if any), and PageImages candidate in one call. Returns None if
        the title does not resolve to an existing page.
        """
        data = self._request({
            "action": "query",
            "titles": title,
            "prop": "pageprops|pageimages",
            "piprop": "name",
            "redirects": 1,
            "format": "json",
        })
        pages = data.get("query", {}).get("pages", {})
        page = next(iter(pages.values()), None)
        if not page or "missing" in page:
            return None
        pageprops = page.get("pageprops", {}) or {}
        return {
            "title": page.get("title"),
            "pageid": page.get("pageid"),
            "wikibase_item": pageprops.get("wikibase_item"),
            # page_image_free is Wikipedia's own free-licensed lead-image
            # pick; pageimage may include non-free fallbacks, so prefer
            # the former per Phase 7.5H section 4.
            "pageimage_free": pageprops.get("page_image_free"),
            "pageimage": page.get("pageimage"),
        }

    def list_article_images(self, title: str, limit: int = 50) -> list[str]:
        data = self._request({
            "action": "query",
            "titles": title,
            "prop": "images",
            "imlimit": limit,
            "redirects": 1,
            "format": "json",
        })
        pages = data.get("query", {}).get("pages", {})
        page = next(iter(pages.values()), None)
        if not page or "missing" in page:
            return []
        return [
            image["title"]
            for image in page.get("images", [])
            if image.get("title")
        ]


def candidate_search_queries(full_name: str) -> list[str]:
    """Generate Wikipedia search-query variants for a formal/titled Nobel
    full_name, without ever lowering identity-matching confidence -- each
    variant is just an alternate way to *find* a candidate; select_candidate
    still scores whatever is found against the same evidence.
    """
    queries: list[str] = [full_name]

    comma_prefix = full_name.split(",", 1)[0].strip()
    if comma_prefix and comma_prefix != full_name:
        queries.append(comma_prefix)

    for parenthetical in _PARENTHETICAL_PATTERN.findall(full_name):
        cleaned = parenthetical.strip()
        if cleaned:
            queries.append(cleaned)

    for base in list(queries):
        stripped = _TITLE_PREFIX_PATTERN.sub("", base).strip()
        if stripped and stripped != base:
            queries.append(stripped)
        # Also drop a bracketed alternate name to get a bare "First Last".
        bare = _PARENTHETICAL_PATTERN.sub("", base).strip()
        bare = re.sub(r"\s+", " ", bare)
        if bare and bare != base:
            queries.append(bare)

    seen: set[str] = set()
    unique_queries = []
    for query in queries:
        if query not in seen:
            seen.add(query)
            unique_queries.append(query)
    return unique_queries


def is_plausible_portrait_filename(filename: str) -> bool:
    lowered = filename.lower()
    return not any(marker in lowered for marker in _IMAGE_BLOCKLIST_MARKERS)


def pick_article_image_candidate(
    image_titles: list[str],
    full_name: str,
) -> str | None:
    """Best-effort, conservative pick from a raw (alphabetically ordered,
    unranked) article image list. Never treated as identity-confirmed --
    callers must still cap this path at REVIEW regardless of Commons
    outcome (Phase 7.5H section 5/16).
    """
    survivors = [title for title in image_titles if is_plausible_portrait_filename(title)]
    if not survivors:
        return None

    name_tokens = [
        token.lower()
        for token in re.split(r"[^A-Za-z]+", full_name)
        if len(token) > 2
    ]
    name_matches = [
        title for title in survivors
        if any(token in title.lower() for token in name_tokens)
    ]
    if name_matches:
        return name_matches[0]
    return survivors[0]


def _resolve_identity_via_wikipedia(
    evidence: dict[str, Any],
    wikipedia_client: WikipediaClient,
    wikidata_client: WikidataClient,
) -> dict[str, Any]:
    """OTHER / IDENTITY_AMBIGUOUS path: search Wikipedia under several
    name variants, resolve each hit's linked Wikidata entity, and score
    every candidate with the exact same select_candidate() used by the
    primary Wikidata pipeline -- no second, weaker validator.
    """
    qid_to_title: dict[str, str] = {}
    candidates: list[dict[str, Any]] = []
    seen_qids: set[str] = set()

    for query in candidate_search_queries(evidence["full_name"]):
        try:
            hits = wikipedia_client.search_articles(query, limit=3)
        except WikipediaError:
            continue
        for hit in hits:
            try:
                article = wikipedia_client.resolve_article(hit["title"])
            except WikipediaError:
                continue
            qid = article and article.get("wikibase_item")
            if not qid or qid in seen_qids:
                continue
            seen_qids.add(qid)
            qid_to_title[qid] = article["title"]
            try:
                entities = wikidata_client.get_wikidata_entities([qid])
            except WikidataError:
                continue
            candidates.extend(entities)
        if candidates:
            # Found at least one linked-entity candidate; still let
            # select_candidate weigh everything gathered so far rather
            # than stopping after the very first query variant, but no
            # need to keep burning additional Wikipedia searches once we
            # have real candidates in hand.
            break

    selection = select_candidate(evidence, candidates)
    selection["article_title"] = (
        qid_to_title.get(selection.get("selected_entity_id"))
        if selection.get("selected_entity_id")
        else None
    )
    return selection


def enrich_one_fallback(
    db: Any,
    nobel_laureate_id: str,
    original_category: str,
    wikidata_client: WikidataClient,
    wikipedia_client: WikipediaClient,
    commons_client: CommonsClient,
    candidate_wikidata_id: str | None = None,
    existing_p18_filename: str | None = None,
) -> dict[str, Any]:
    """Run the Phase 7.5H fallback for one already-unresolved laureate.

    Returns a compact, report-ready record. Never touches Commons-license
    review cases (callers must not pass those in), never lowers matching
    confidence, and never persists -- persistence is a separate, later
    step reusing plan_persistence/apply_persistence unchanged.
    """
    laureate = laureate_repository.get_by_nobel_id(db, nobel_laureate_id)
    base: dict[str, Any] = {
        "nobel_laureate_id": nobel_laureate_id,
        "laureate_id": laureate.laureate_id if laureate else None,
        "full_name": laureate.full_name if laureate else None,
        "original_category": original_category,
        "wikipedia_article": None,
        "identity_decision": "SKIP",
        "pageimage_candidate": None,
        "commons_filename": None,
        "commons_decision": None,
        "final_action": "skip",
        "reason": None,
        "database_write": False,
        "image_url_candidate": None,
        "canonical_source_url": None,
        "attribution_normalized": None,
        "license_normalized": None,
        "warnings": [],
    }

    if laureate is None:
        base["reason"] = "laureate not found in Nobel Explorer"
        return base

    if laureate.image_url:
        base["identity_decision"] = "ACCEPT"
        base["final_action"] = "skipped_existing"
        base["reason"] = "image_url already populated (missing-only mode)"
        return base

    evidence = build_laureate_evidence(laureate)
    article_title: str | None = None
    p18_filename: str | None = None

    if original_category == "REVIEW":
        # Identity was already Wikidata-ACCEPTed in the primary pipeline;
        # this path only needs to re-validate the existing Commons file
        # with the thumbnail-aware media check, no Wikipedia involved.
        base["identity_decision"] = "ACCEPT"
        if not existing_p18_filename:
            base["reason"] = "TIFF fallback requires the original run's p18_filename"
            return base
        p18_filename = existing_p18_filename
    elif original_category == "NO_P18":
        base["identity_decision"] = "ACCEPT"
        if not candidate_wikidata_id:
            base["reason"] = "NO_P18 fallback requires the original run's accepted Wikidata QID"
            return base
        try:
            article_title = wikidata_client.get_enwiki_sitelink(candidate_wikidata_id)
        except WikidataError as error:
            base["reason"] = f"Wikidata sitelink lookup failed: {error}"
            return base
        if not article_title:
            base["reason"] = "no English Wikipedia sitelink for the already-accepted Wikidata entity"
            return base
        base["wikipedia_article"] = article_title
    elif original_category in ("OTHER", "IDENTITY_AMBIGUOUS"):
        try:
            selection = _resolve_identity_via_wikipedia(evidence, wikipedia_client, wikidata_client)
        except WikidataError as error:
            base["reason"] = f"Wikidata lookup failed during Wikipedia fallback: {error}"
            return base
        base["identity_decision"] = selection["proposed_action"]
        base["reason"] = selection.get("review_reason")
        if selection["proposed_action"] != "ACCEPT":
            base["final_action"] = "review" if selection["proposed_action"] == "REVIEW" else "skip"
            return base
        article_title = selection.get("article_title")
        base["wikipedia_article"] = article_title
        if not article_title:
            base["reason"] = "identity accepted but no Wikipedia article title recovered"
            base["final_action"] = "review"
            return base
    else:
        base["reason"] = f"unsupported original_category for fallback: {original_category!r}"
        return base

    image_source = None
    if original_category != "REVIEW":
        try:
            article = wikipedia_client.resolve_article(article_title)
        except WikipediaError as error:
            base["reason"] = f"Wikipedia article resolution failed: {error}"
            base["final_action"] = "review"
            return base

        pageimage = (article or {}).get("pageimage_free") or (article or {}).get("pageimage")
        if pageimage:
            p18_filename = pageimage
            image_source = "pageimages"
        else:
            try:
                image_titles = wikipedia_client.list_article_images(article_title)
            except WikipediaError:
                image_titles = []
            fallback_choice = pick_article_image_candidate(image_titles, evidence["full_name"])
            if fallback_choice:
                p18_filename = fallback_choice.removeprefix("File:")
                image_source = "article_image_list"

    if not p18_filename:
        base["reason"] = "no PageImage or suitable article image found"
        base["final_action"] = "skip"
        return base

    base["pageimage_candidate"] = p18_filename
    base["commons_filename"] = p18_filename

    fake_identity = {
        "proposed_action": "ACCEPT",
        "p18_filename": p18_filename,
        "laureate_id": laureate.laureate_id,
        "nobel_laureate_id": nobel_laureate_id,
        "full_name": laureate.full_name,
    }
    commons_result = enrich_commons_for_identity(fake_identity, commons_client)
    base["commons_decision"] = commons_result.get("commons_decision")
    base["image_url_candidate"] = commons_result.get("image_url_candidate")
    base["canonical_source_url"] = commons_result.get("canonical_source_url")
    base["attribution_normalized"] = commons_result.get("attribution_normalized")
    base["license_normalized"] = commons_result.get("license_normalized")
    base["warnings"] = commons_result.get("warnings", [])
    reasons = commons_result.get("skip_reasons", []) + commons_result.get("review_reasons", [])
    if reasons:
        base["reason"] = "; ".join(reasons)

    if image_source == "article_image_list" and commons_result.get("commons_decision") == "ACCEPT":
        # Weakest-provenance path (section 5/16): never auto-persist even
        # on a clean Commons ACCEPT -- the identity-of-the-*image*, not
        # the laureate, is unranked/unverified here.
        commons_result = {**commons_result, "commons_decision": "REVIEW"}
        base["commons_decision"] = "REVIEW"
        base["reason"] = (
            (base["reason"] + "; " if base["reason"] else "")
            + "article-image fallback candidate requires manual confirmation before use"
        )

    base["_commons_result"] = commons_result  # internal: consumed by the persistence step only

    if base["identity_decision"] == "ACCEPT" and base["commons_decision"] == "ACCEPT":
        base["final_action"] = "accept"
    elif base["commons_decision"] in ("REVIEW", None):
        base["final_action"] = "review"
    else:
        base["final_action"] = "skip"

    return base
