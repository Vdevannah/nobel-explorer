from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock, patch

import requests

from ETL.image_enrichment.enrichment import run_dry_run
from ETL.image_enrichment.matching import evaluate_candidate, select_candidate
from ETL.image_enrichment.sources import WikidataClient, WikidataError


def person_evidence(
    name="Albert Einstein",
    birth_date="1879-03-14",
):
    return {
        "nobel_laureate_id": "26",
        "full_name": name,
        "laureate_type": "Person",
        "birth_date": birth_date,
        "birth_city": "Ulm",
        "birth_state": None,
        "birth_country": "Germany",
    }


def person_candidate(
    entity_id="Q937",
    label="Albert Einstein",
    aliases=None,
    birth_date="1879-03-14T00:00:00Z",
    instance_of_ids=None,
    award_labels=None,
    p18_filename=None,
):
    return {
        "entity_id": entity_id,
        "label": label,
        "aliases": aliases or [],
        "description": "German-born theoretical physicist",
        "instance_of_ids": ["Q5"] if instance_of_ids is None else instance_of_ids,
        "birth_date": birth_date,
        "birthplace_labels": ["Ulm"],
        "country_labels": ["Germany"],
        "occupation_labels": ["physicist"],
        "award_labels": (
            ["Nobel Prize in Physics"]
            if award_labels is None
            else award_labels
        ),
        "has_p18": p18_filename is not None,
        "p18_filename": p18_filename,
    }


def test_exact_person_match_is_high_confidence():
    result = select_candidate(person_evidence(), [person_candidate()])

    assert result["matched"] is True
    assert result["confidence"] == "high"
    assert result["selected_entity_id"] == "Q937"
    assert result["proposed_action"] == "ACCEPT"


def test_alias_and_initial_name_variations_are_supported():
    alias_result = evaluate_candidate(
        person_evidence(name="Marie Curie, née Skłodowska", birth_date="1867-11-07"),
        person_candidate(
            label="Marie Curie",
            aliases=["Marie Curie, née Skłodowska"],
            birth_date="1867-11-07T00:00:00Z",
        ),
    )
    initials_result = evaluate_candidate(
        person_evidence(name="A. Michael Spence", birth_date="1943-11-07"),
        person_candidate(
            label="Michael Spence",
            birth_date="1943-11-07T00:00:00Z",
        ),
    )

    assert alias_result["confidence"] == "high"
    assert initials_result["confidence"] == "high"
    assert "name variation or initials relationship matched" in initials_result["reasons"]


def test_birth_date_support_and_conflict_are_explainable():
    supported = evaluate_candidate(person_evidence(), person_candidate())
    rejected = evaluate_candidate(
        person_evidence(),
        person_candidate(birth_date="1979-03-14T00:00:00Z"),
    )

    assert "birth date matched" in supported["reasons"]
    assert rejected["confidence"] == "rejected"
    assert "birth year conflicts (1879 != 1979)" in rejected["conflicts"]


def test_wrong_entity_type_is_rejected():
    result = evaluate_candidate(
        person_evidence(),
        person_candidate(instance_of_ids=["Q43229"]),
    )

    assert result["confidence"] == "rejected"
    assert "candidate is not identified as a human" in result["conflicts"]


def test_missing_birth_or_nobel_evidence_does_not_fabricate_it():
    missing_birth = evaluate_candidate(
        person_evidence(),
        person_candidate(birth_date=None),
    )
    missing_nobel = evaluate_candidate(
        person_evidence(),
        person_candidate(award_labels=[]),
    )

    assert not any("birth date matched" == reason for reason in missing_birth["reasons"])
    assert not any("Nobel" in reason for reason in missing_nobel["reasons"])
    assert missing_birth["confidence"] == "high"
    assert missing_nobel["confidence"] == "high"


def test_similarly_plausible_candidates_are_ambiguous():
    candidates = [
        person_candidate(entity_id="Q1"),
        person_candidate(entity_id="Q2"),
    ]

    result = select_candidate(person_evidence(), candidates)

    assert result["matched"] is False
    assert result["confidence"] == "ambiguous"
    assert result["selected_entity_id"] is None
    assert result["proposed_action"] == "REVIEW"


def test_organization_uses_non_person_matching_path():
    organization = {
        "nobel_laureate_id": "1043",
        "full_name": "Nihon Hidankyo",
        "laureate_type": "Organization",
        "birth_date": None,
        "birth_city": None,
        "birth_state": None,
        "birth_country": None,
    }
    candidate = person_candidate(
        label="Nihon Hidankyo",
        birth_date=None,
        instance_of_ids=["Q43229"],
        award_labels=["Nobel Peace Prize"],
    )

    result = select_candidate(organization, [candidate])

    assert result["confidence"] == "high"
    assert result["matched"] is True


def test_p18_presence_and_absence_are_reported_only():
    without_image = select_candidate(person_evidence(), [person_candidate()])
    with_image = select_candidate(
        person_evidence(),
        [person_candidate(p18_filename="Albert Einstein Head.jpg")],
    )

    assert without_image["has_p18"] is False
    assert without_image["p18_filename"] is None
    assert with_image["has_p18"] is True
    assert with_image["p18_filename"] == "Albert Einstein Head.jpg"


def test_wikidata_search_failure_is_wrapped():
    session = Mock()
    session.headers = {}
    session.get.side_effect = requests.ConnectionError("offline")
    client = WikidataClient(session=session, request_delay=0)

    try:
        client.search_wikidata_entities("Albert Einstein")
    except WikidataError as error:
        assert "offline" in str(error)
    else:
        raise AssertionError("Expected WikidataError")


def test_wikidata_entity_retrieval_failure_is_wrapped():
    session = Mock()
    session.headers = {}
    session.get.side_effect = requests.Timeout("timed out")
    client = WikidataClient(session=session, request_delay=0)

    try:
        client.get_wikidata_entity("Q937")
    except WikidataError as error:
        assert "timed out" in str(error)
    else:
        raise AssertionError("Expected WikidataError")


def test_dry_run_does_not_write_to_database():
    laureate = SimpleNamespace(
        laureate_id=1001,
        nobel_laureate_id="26",
        full_name="Albert Einstein",
        laureate_type="Person",
        birth_date=date(1879, 3, 14),
        birth_city="Ulm",
        birth_state=None,
        birth_country="Germany",
    )
    db = Mock()
    client = Mock()
    client.search_wikidata_entities.return_value = [{"entity_id": "Q937"}]
    client.get_wikidata_entities.return_value = [person_candidate()]

    with patch(
        "ETL.image_enrichment.enrichment.laureate_repository.get_by_nobel_id",
        return_value=laureate,
    ):
        report = run_dry_run(db, ["26"], client=client)

    assert report["database_writes"] == 0
    db.add.assert_not_called()
    db.delete.assert_not_called()
    db.flush.assert_not_called()
    db.commit.assert_not_called()
    db.execute.assert_not_called()


def response_with_status(status_code, retry_after=None):
    response = Mock()
    response.status_code = status_code
    response.headers = {}
    if retry_after is not None:
        response.headers["Retry-After"] = retry_after
    if status_code >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(
            f"status {status_code}",
            response=response,
        )
    else:
        response.raise_for_status.return_value = None
        response.json.return_value = {"search": []}
    return response


def test_transient_429_and_503_are_retried():
    session = Mock()
    session.headers = {}
    session.get.side_effect = [
        response_with_status(429),
        response_with_status(503),
        response_with_status(200),
    ]
    sleep = Mock()
    client = WikidataClient(
        session=session,
        request_delay=0,
        sleep_func=sleep,
        jitter_func=lambda _start, _end: 0,
    )

    assert client.search_wikidata_entities("Albert Einstein") == []
    assert session.get.call_count == 3
    assert sleep.call_count == 2


def test_retry_after_is_honored():
    session = Mock()
    session.headers = {}
    session.get.side_effect = [
        response_with_status(429, retry_after="2"),
        response_with_status(200),
    ]
    sleep = Mock()
    client = WikidataClient(
        session=session,
        request_delay=0,
        sleep_func=sleep,
    )

    client.search_wikidata_entities("Albert Einstein")

    sleep.assert_called_once_with(2.0)


def test_permanent_404_is_not_retried():
    session = Mock()
    session.headers = {}
    session.get.return_value = response_with_status(404)
    client = WikidataClient(session=session, request_delay=0)

    try:
        client.search_wikidata_entities("missing")
    except WikidataError:
        pass
    else:
        raise AssertionError("Expected WikidataError")

    assert session.get.call_count == 1


def test_retries_stop_at_configured_limit():
    session = Mock()
    session.headers = {}
    session.get.return_value = response_with_status(503)
    client = WikidataClient(
        session=session,
        request_delay=0,
        max_attempts=3,
        sleep_func=Mock(),
        jitter_func=lambda _start, _end: 0,
    )

    try:
        client.search_wikidata_entities("Albert Einstein")
    except WikidataError:
        pass
    else:
        raise AssertionError("Expected WikidataError")

    assert session.get.call_count == 3


def test_entity_cache_prevents_duplicate_requests():
    client = WikidataClient(session=Mock(), request_delay=0)
    client._entity_cache["Q937"] = person_candidate()

    first = client.get_wikidata_entity("Q937")
    second = client.get_wikidata_entity("Q937")

    assert first is second
    client.session.get.assert_not_called()


def test_network_failure_reports_p18_as_unknown():
    laureate = SimpleNamespace(
        laureate_id=1001,
        nobel_laureate_id="26",
        full_name="Albert Einstein",
        laureate_type="Person",
        birth_date=date(1879, 3, 14),
        birth_city="Ulm",
        birth_state=None,
        birth_country="Germany",
    )
    db = Mock()
    client = Mock()
    client.search_wikidata_entities.side_effect = WikidataError("offline")

    with patch(
        "ETL.image_enrichment.enrichment.laureate_repository.get_by_nobel_id",
        return_value=laureate,
    ):
        result = run_dry_run(db, ["26"], client=client)["results"][0]

    assert result["has_p18"] is None
    assert result["p18_filename"] is None
    assert result["proposed_action"] == "SKIP"
