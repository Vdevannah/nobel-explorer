from collections import Counter

from backend.ai.config import (
    CITATION_SOURCE_LINKED,
    CITATION_STRUCTURED_RECORD,
    CITATION_UNVERIFIED_EDUCATIONAL,
    CITATION_STATUSES,
    DOC_TYPES,
)
from backend.ai.documents import build_all_documents


def _by_id(documents):
    return {d.doc_id: d for d in documents}


def test_extracts_every_record_type(documents):
    counts = Counter(d.doc_type for d in documents)
    assert counts == {"laureate_record": 4, "contribution": 2, "explanation": 5, "connection": 2}
    assert set(counts) <= set(DOC_TYPES)


def test_document_ids_are_deterministic(db_session):
    first = build_all_documents(db_session)
    second = build_all_documents(db_session)
    assert [d.doc_id for d in first] == [d.doc_id for d in second]
    assert [d.content_hash for d in first] == [d.content_hash for d in second]
    assert len({d.doc_id for d in first}) == len(first)


def test_document_id_formats(documents):
    ids = set(_by_id(documents))
    assert {"laureate:nobel-26", "laureate:nobel-482", "contribution:38", "contribution:779",
            "explanation:38:simple", "explanation:38:expert", "connection:24", "connection:29"} <= ids


def test_laureate_record_contains_prize_motivation_and_affiliation(documents):
    einstein = _by_id(documents)["laureate:nobel-26"]
    assert "Albert Einstein" in einstein.text
    assert "Nobel Prize in Physics 1921" in einstein.text
    assert "photoelectric effect" in einstein.text
    assert einstein.metadata["laureate_ids"] == [249]
    assert einstein.metadata["prize_years"] == [1921]
    assert einstein.metadata["categories"] == ["Physics"]

    bertozzi = _by_id(documents)["laureate:nobel-1015"]
    assert "Affiliation at time of award: Stanford University" in bertozzi.text


def test_laureate_without_prizes_or_birth_data_has_no_empty_metadata(documents):
    red_cross = _by_id(documents)["laureate:nobel-482"]
    assert "organization" in red_cross.text
    assert "prize_years" not in red_cross.metadata
    assert all(v not in (None, "", []) for v in red_cross.metadata.values())


def test_structured_records_have_no_invented_source_url(documents):
    for doc in documents:
        if doc.doc_type == "laureate_record":
            assert doc.metadata["citation_status"] == CITATION_STRUCTURED_RECORD
            assert "source_url" not in doc.metadata
            assert doc.metadata["source_name"].startswith("Nobel Prize API")


def test_explanations_are_marked_unverified_and_never_cited(documents):
    explanations = [d for d in documents if d.doc_type == "explanation"]
    assert explanations
    for doc in explanations:
        assert doc.metadata["citation_status"] == CITATION_UNVERIFIED_EDUCATIONAL
        assert "source_url" not in doc.metadata
        assert "source_name" not in doc.metadata
        # Parent source is exposed as context only.
        assert doc.metadata["related_source_url"].startswith("https://www.nobelprize.org/")
        assert doc.metadata["level"] in {"Simple", "Explore", "Advanced", "Expert"}


def test_source_linked_documents_carry_stored_urls(documents):
    docs = _by_id(documents)
    contribution = docs["contribution:38"]
    assert contribution.metadata["citation_status"] == CITATION_SOURCE_LINKED
    assert contribution.metadata["source_url"] == "https://www.nobelprize.org/prizes/physics/1921/summary/"
    connection = docs["connection:24"]
    assert connection.metadata["source_name"] == "U.S. Department of Energy"
    assert connection.metadata["citation_status"] == CITATION_SOURCE_LINKED


def test_connection_without_url_is_not_source_linked(documents):
    legacy = _by_id(documents)["connection:29"]
    assert legacy.metadata["citation_status"] == CITATION_UNVERIFIED_EDUCATIONAL
    assert "source_url" not in legacy.metadata
    assert legacy.metadata["related_prize_year"] == 2017
    assert "Related Nobel Prize: Physics 2017" in legacy.text


def test_shared_contribution_lists_all_credited_laureates(documents):
    click = _by_id(documents)["contribution:779"]
    assert click.metadata["laureate_ids"] == [766, 886]
    assert "Carolyn R. Bertozzi" in click.text and "K. Barry Sharpless" in click.text
    assert click.metadata["prize_years"] == [2022]


def test_key_concepts_are_appended(documents):
    simple = _by_id(documents)["explanation:38:simple"]
    assert "Key concepts: Light has photons; Photons knock out electrons." in simple.text


def test_all_citation_statuses_are_known(documents):
    assert {d.metadata["citation_status"] for d in documents} <= set(CITATION_STATUSES)
