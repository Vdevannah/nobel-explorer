from __future__ import annotations

import random
import time
from email.utils import parsedate_to_datetime
from time import monotonic
from typing import Any

import requests


WIKIDATA_API_URL = "https://www.wikidata.org/w/api.php"
USER_AGENT = (
    "NobelExplorer/1.0 "
    "(educational project; Wikidata identity matching prototype)"
)
REQUEST_TIMEOUT = 15
DEFAULT_REQUEST_DELAY = 0.5
DEFAULT_MAX_ATTEMPTS = 3
TRANSIENT_STATUS_CODES = {429, 502, 503, 504}
NOBEL_AWARD_LABELS = {
    "Q7191": "Nobel Prize",
    "Q38104": "Nobel Prize in Physics",
    "Q44585": "Nobel Prize in Chemistry",
    "Q80061": "Nobel Prize in Physiology or Medicine",
    "Q37922": "Nobel Prize in Literature",
    "Q35637": "Nobel Peace Prize",
    "Q47170": "Nobel Memorial Prize in Economic Sciences",
}


class WikidataError(RuntimeError):
    """Raised when structured Wikidata data cannot be retrieved."""


class WikidataClient:
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
        self._entity_cache: dict[str, dict[str, Any]] = {}
        self._label_cache: dict[str, str] = {}

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
                    WIKIDATA_API_URL,
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
        raise WikidataError(f"Wikidata request failed: {last_error}") from last_error

    def search_wikidata_entities(
        self,
        name: str,
        limit: int = 5
    ) -> list[dict[str, Any]]:
        data = self._request({
            "action": "wbsearchentities",
            "format": "json",
            "language": "en",
            "uselang": "en",
            "type": "item",
            "search": name,
            "limit": limit,
        })
        return [
            {
                "entity_id": item.get("id"),
                "label": item.get("label"),
                "description": item.get("description"),
                "aliases": item.get("aliases", []),
            }
            for item in data.get("search", [])
            if item.get("id")
        ]

    def _get_entities(
        self,
        entity_ids: list[str],
        props: str
    ) -> dict[str, dict[str, Any]]:
        if not entity_ids:
            return {}
        data = self._request({
            "action": "wbgetentities",
            "format": "json",
            "ids": "|".join(entity_ids),
            "languages": "en",
            "languagefallback": 1,
            "props": props,
        })
        return data.get("entities", {})

    def _labels_for(self, entity_ids: list[str]) -> dict[str, str]:
        missing_ids = [
            entity_id for entity_id in dict.fromkeys(entity_ids)
            if entity_id not in self._label_cache
        ]
        if missing_ids:
            entities = self._get_entities(missing_ids, "labels")
            for entity_id in missing_ids:
                label_data = entities.get(entity_id, {}).get("labels", {})
                self._label_cache[entity_id] = label_data.get(
                    "en",
                    {}
                ).get("value", entity_id)
        return {
            entity_id: self._label_cache.get(entity_id, entity_id)
            for entity_id in entity_ids
        }

    @staticmethod
    def _claim_entity_ids(claims: dict, property_id: str) -> list[str]:
        values = []
        for claim in claims.get(property_id, []):
            value = claim.get("mainsnak", {}).get("datavalue", {}).get(
                "value"
            )
            if isinstance(value, dict) and value.get("id"):
                values.append(value["id"])
        return values

    @staticmethod
    def _claim_time(claims: dict, property_id: str) -> str | None:
        for claim in claims.get(property_id, []):
            value = claim.get("mainsnak", {}).get("datavalue", {}).get(
                "value"
            )
            if isinstance(value, dict) and value.get("time"):
                return value["time"].lstrip("+")
        return None

    @staticmethod
    def _claim_string(claims: dict, property_id: str) -> str | None:
        for claim in claims.get(property_id, []):
            value = claim.get("mainsnak", {}).get("datavalue", {}).get(
                "value"
            )
            if isinstance(value, str):
                return value
        return None

    def _parse_entity(
        self,
        entity_id: str,
        raw_entity: dict[str, Any],
        labels: dict[str, str],
    ) -> dict[str, Any]:
        claims = raw_entity.get("claims", {})
        related = {
            "instance_of": self._claim_entity_ids(claims, "P31"),
            "birthplace": self._claim_entity_ids(claims, "P19"),
            "countries": self._claim_entity_ids(claims, "P27"),
            "occupations": self._claim_entity_ids(claims, "P106"),
            "awards": self._claim_entity_ids(claims, "P166"),
            "organization_country": self._claim_entity_ids(claims, "P17"),
            "organization_location": self._claim_entity_ids(claims, "P131"),
        }
        award_labels = [
            NOBEL_AWARD_LABELS[award_id]
            for award_id in related["awards"]
            if award_id in NOBEL_AWARD_LABELS
        ]

        entity = {
            "entity_id": entity_id,
            "label": raw_entity.get("labels", {}).get("en", {}).get("value"),
            "aliases": [
                alias.get("value")
                for alias in raw_entity.get("aliases", {}).get("en", [])
                if alias.get("value")
            ],
            "description": raw_entity.get("descriptions", {}).get(
                "en",
                {}
            ).get("value"),
            "instance_of_ids": related["instance_of"],
            "instance_of_labels": [labels.get(qid, qid) for qid in related["instance_of"]],
            "birth_date": self._claim_time(claims, "P569"),
            "birthplace_ids": related["birthplace"],
            "birthplace_labels": [labels.get(qid, qid) for qid in related["birthplace"]],
            "country_ids": related["countries"],
            "country_labels": [labels.get(qid, qid) for qid in related["countries"]],
            "occupation_ids": related["occupations"],
            "occupation_labels": [labels.get(qid, qid) for qid in related["occupations"]],
            "award_ids": related["awards"],
            "award_labels": award_labels,
            "inception_date": self._claim_time(claims, "P571"),
            "organization_country_ids": related["organization_country"],
            "organization_country_labels": [
                labels.get(qid, qid) for qid in related["organization_country"]
            ],
            "organization_location_ids": related["organization_location"],
            "organization_location_labels": [
                labels.get(qid, qid) for qid in related["organization_location"]
            ],
            "p18_filename": self._claim_string(claims, "P18"),
        }
        entity["has_p18"] = entity["p18_filename"] is not None
        self._entity_cache[entity_id] = entity
        return entity

    def get_wikidata_entities(
        self,
        entity_ids: list[str]
    ) -> list[dict[str, Any]]:
        unique_ids = list(dict.fromkeys(entity_ids))
        missing_ids = [
            entity_id for entity_id in unique_ids
            if entity_id not in self._entity_cache
        ]
        raw_entities = self._get_entities(
            missing_ids,
            "labels|aliases|descriptions|claims"
        )
        label_ids = []
        for raw_entity in raw_entities.values():
            claims = raw_entity.get("claims", {})
            for property_id in ("P31", "P19", "P27", "P17", "P131"):
                label_ids.extend(self._claim_entity_ids(claims, property_id))
            label_ids.extend(self._claim_entity_ids(claims, "P106")[:5])
        labels = self._labels_for(label_ids)
        for entity_id in missing_ids:
            raw_entity = raw_entities.get(entity_id)
            if not raw_entity or raw_entity.get("missing") is not None:
                continue
            self._parse_entity(entity_id, raw_entity, labels)
        return [
            self._entity_cache[entity_id]
            for entity_id in unique_ids
            if entity_id in self._entity_cache
        ]

    def get_wikidata_entity(self, entity_id: str) -> dict[str, Any]:
        entities = self.get_wikidata_entities([entity_id])
        if not entities:
            raise WikidataError(f"Wikidata entity not found: {entity_id}")
        return entities[0]

    def get_enwiki_sitelink(self, entity_id: str) -> str | None:
        """Look up the English Wikipedia article title linked from a
        Wikidata entity, for laureates whose identity is already
        Wikidata-ACCEPTed but who are missing a P18 image (Phase 7.5H
        fallback). Returns None when no enwiki sitelink exists.
        """
        data = self._request({
            "action": "wbgetentities",
            "format": "json",
            "ids": entity_id,
            "props": "sitelinks",
            "sitefilter": "enwiki",
        })
        entity = data.get("entities", {}).get(entity_id, {})
        sitelink = entity.get("sitelinks", {}).get("enwiki", {})
        return sitelink.get("title")
