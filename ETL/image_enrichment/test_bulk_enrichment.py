from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models.laureate import Laureate
from ETL.image_enrichment.bulk import (
    chunked,
    classify_result,
    run_bulk_enrichment,
    select_missing_image_nobel_ids,
)


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Laureate.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    for index in range(1, 11):
        has_image = index in (2, 5, 8)  # a few already-enriched rows
        session.add(Laureate(
            laureate_id=index,
            nobel_laureate_id=str(index),
            full_name=f"Laureate {index}",
            laureate_type="Person",
            featured=False,
            image_url="https://example.org/existing.jpg" if has_image else None,
        ))
    session.commit()

    yield session
    session.close()
    engine.dispose()


def commons_result(nobel_id, **overrides):
    base = {
        "laureate_id": int(nobel_id),
        "nobel_laureate_id": nobel_id,
        "full_name": f"Laureate {nobel_id}",
        "wikidata_entity_id": f"Q{nobel_id}",
        "identity_confidence": "high",
        "identity_decision": "ACCEPT",
        "commons_lookup_status": "found",
        "p18_filename": f"Photo{nobel_id}.jpg",
        "commons_decision": "ACCEPT",
        "image_url_candidate": f"https://upload.wikimedia.org/photo{nobel_id}.jpg",
        "canonical_source_url": f"https://commons.wikimedia.org/wiki/File:Photo{nobel_id}.jpg",
        "license_normalized": "Public Domain",
        "attribution_normalized": "Some Author",
        "warnings": [],
        "skip_reasons": [],
        "review_reasons": [],
    }
    base.update(overrides)
    return base


def fake_enrich_laureate_dry_run(db, nobel_id, wikidata_client=None):
    return {"nobel_laureate_id": nobel_id}


def fake_enrich_commons_for_identity_factory(results_by_id):
    def fake(identity, commons_client=None):
        return results_by_id[identity["nobel_laureate_id"]]
    return fake


PATCH_TARGET_IDENTITY = "ETL.image_enrichment.bulk.enrich_laureate_dry_run"
PATCH_TARGET_COMMONS = "ETL.image_enrichment.bulk.enrich_commons_for_identity"


# 1. limit works.
def test_limit_caps_selection(db_session):
    ids = select_missing_image_nobel_ids(db_session, limit=3)

    assert len(ids) == 3


# 2. offset works.
def test_offset_skips_leading_rows(db_session):
    first_three = select_missing_image_nobel_ids(db_session, limit=3, offset=0)
    next_three = select_missing_image_nobel_ids(db_session, limit=3, offset=3)

    assert first_three != next_three
    assert set(first_three).isdisjoint(next_three)


# 3. missing-only selection works.
def test_missing_only_excludes_rows_with_existing_image(db_session):
    ids = select_missing_image_nobel_ids(db_session)

    assert "2" not in ids
    assert "5" not in ids
    assert "8" not in ids
    assert len(ids) == 7  # 10 total - 3 already enriched


def test_force_includes_rows_with_existing_image(db_session):
    ids = select_missing_image_nobel_ids(db_session, force=True)

    assert "2" in ids
    assert len(ids) == 10


# 4. Deterministic ordering.
def test_selection_is_ordered_by_laureate_id(db_session):
    ids = select_missing_image_nobel_ids(db_session, force=True)

    assert ids == [str(i) for i in range(1, 11)]


def test_selection_ordering_is_repeatable(db_session):
    first = select_missing_image_nobel_ids(db_session)
    second = select_missing_image_nobel_ids(db_session)

    assert first == second


# 5. Chunking works.
def test_chunked_splits_into_expected_sizes():
    items = [str(i) for i in range(1, 11)]

    chunks = list(chunked(items, 4))

    assert chunks == [
        ["1", "2", "3", "4"],
        ["5", "6", "7", "8"],
        ["9", "10"],
    ]


def test_bulk_run_processes_in_configured_chunk_size(db_session):
    ids = [str(i) for i in range(1, 11)]
    results_by_id = {nid: commons_result(nid) for nid in ids}

    with patch(PATCH_TARGET_IDENTITY, side_effect=fake_enrich_laureate_dry_run), \
         patch(PATCH_TARGET_COMMONS, side_effect=fake_enrich_commons_for_identity_factory(results_by_id)):
        report = run_bulk_enrichment(db_session, ids, mode="dry-run", batch_size=4)

    assert len(report["chunks"]) == 3
    assert [chunk["size"] for chunk in report["chunks"]] == [4, 4, 2]


# 6. ACCEPT persists.
def test_accept_records_are_persisted(db_session):
    ids = ["1"]
    results_by_id = {"1": commons_result("1")}

    with patch(PATCH_TARGET_IDENTITY, side_effect=fake_enrich_laureate_dry_run), \
         patch(PATCH_TARGET_COMMONS, side_effect=fake_enrich_commons_for_identity_factory(results_by_id)):
        report = run_bulk_enrichment(db_session, ids, mode="persist")

    assert report["counts"]["persisted"] == 1
    laureate = db_session.get(Laureate, 1)
    assert laureate.image_url == "https://upload.wikimedia.org/photo1.jpg"
    assert laureate.image_license == "Public Domain"


# 7. REVIEW does not persist.
def test_review_records_are_never_persisted(db_session):
    ids = ["1"]
    results_by_id = {"1": commons_result("1", commons_decision="REVIEW")}

    with patch(PATCH_TARGET_IDENTITY, side_effect=fake_enrich_laureate_dry_run), \
         patch(PATCH_TARGET_COMMONS, side_effect=fake_enrich_commons_for_identity_factory(results_by_id)):
        report = run_bulk_enrichment(db_session, ids, mode="persist")

    assert report["counts"]["persisted"] == 0
    laureate = db_session.get(Laureate, 1)
    assert laureate.image_url is None


# 8. SKIP does not persist.
def test_skip_records_are_never_persisted(db_session):
    ids = ["1"]
    results_by_id = {"1": commons_result("1", identity_decision="SKIP", commons_decision="SKIP")}

    with patch(PATCH_TARGET_IDENTITY, side_effect=fake_enrich_laureate_dry_run), \
         patch(PATCH_TARGET_COMMONS, side_effect=fake_enrich_commons_for_identity_factory(results_by_id)):
        report = run_bulk_enrichment(db_session, ids, mode="persist")

    assert report["counts"]["persisted"] == 0
    laureate = db_session.get(Laureate, 1)
    assert laureate.image_url is None


# 9. Rerun skips already-enriched (existing) rows.
def test_rerun_in_missing_only_mode_skips_persisted_rows(db_session):
    ids = ["1"]
    results_by_id = {"1": commons_result("1")}

    with patch(PATCH_TARGET_IDENTITY, side_effect=fake_enrich_laureate_dry_run), \
         patch(PATCH_TARGET_COMMONS, side_effect=fake_enrich_commons_for_identity_factory(results_by_id)):
        first_report = run_bulk_enrichment(db_session, ids, mode="persist")
        assert first_report["counts"]["persisted"] == 1

        # A fresh selection now correctly excludes the just-persisted row.
        remaining_ids = select_missing_image_nobel_ids(db_session)
        assert "1" not in remaining_ids

        second_report = run_bulk_enrichment(db_session, ids, mode="persist")

    assert second_report["counts"]["persisted"] == 0
    assert second_report["counts"]["skipped_existing"] == 1


# 10. Systemic network failure stops safely.
def test_systemic_network_failure_stops_the_run(db_session):
    ids = [str(i) for i in range(1, 7)]
    results_by_id = {
        nid: commons_result(nid, commons_lookup_status="error", commons_decision="SKIP")
        for nid in ids
    }

    with patch(PATCH_TARGET_IDENTITY, side_effect=fake_enrich_laureate_dry_run), \
         patch(PATCH_TARGET_COMMONS, side_effect=fake_enrich_commons_for_identity_factory(results_by_id)):
        report = run_bulk_enrichment(db_session, ids, mode="dry-run", batch_size=6)

    assert report["stopped_early"] is True
    assert "systemic network failure" in report["stop_reason"]
    assert report["counts"]["persisted"] == 0


def test_partial_network_failure_does_not_trigger_systemic_stop(db_session):
    ids = [str(i) for i in range(1, 5)]
    results_by_id = {
        "1": commons_result("1", commons_lookup_status="error", commons_decision="SKIP"),
        "2": commons_result("2"),
        "3": commons_result("3"),
        "4": commons_result("4"),
    }

    with patch(PATCH_TARGET_IDENTITY, side_effect=fake_enrich_laureate_dry_run), \
         patch(PATCH_TARGET_COMMONS, side_effect=fake_enrich_commons_for_identity_factory(results_by_id)):
        report = run_bulk_enrichment(db_session, ids, mode="dry-run", batch_size=4)

    assert report["stopped_early"] is False
    assert report["counts"]["network_failed"] == 1


# 11. Report aggregation is correct.
def test_report_aggregation_counts_every_bucket_exactly_once(db_session):
    ids = ["1", "2", "3", "4", "5"]
    results_by_id = {
        "1": commons_result("1"),  # commons_accept
        "2": commons_result("2", commons_decision="REVIEW"),
        "3": commons_result("3", identity_decision="SKIP", commons_decision="SKIP"),
        "4": commons_result("4", identity_decision="REVIEW", commons_decision="SKIP"),
        "5": commons_result("5", p18_filename=None, commons_decision="SKIP"),
    }

    with patch(PATCH_TARGET_IDENTITY, side_effect=fake_enrich_laureate_dry_run), \
         patch(PATCH_TARGET_COMMONS, side_effect=fake_enrich_commons_for_identity_factory(results_by_id)):
        report = run_bulk_enrichment(db_session, ids, mode="dry-run")

    counts = report["counts"]
    assert counts["total_processed"] == 5
    assert counts["commons_accept"] == 1
    assert counts["commons_review"] == 1
    assert counts["identity_skip"] == 1
    assert counts["identity_review"] == 1
    assert counts["no_image"] == 1
    # No double counting: every record lands in exactly one bucket.
    bucketed_total = (
        counts["commons_accept"] + counts["commons_review"] + counts["commons_skip"]
        + counts["identity_skip"] + counts["identity_review"]
        + counts["no_image"] + counts["network_failed"]
    )
    assert bucketed_total == counts["total_processed"]


def test_classify_result_buckets():
    assert classify_result(commons_result("1", identity_decision="REVIEW")) == "identity_review"
    assert classify_result(commons_result("1", identity_decision="SKIP")) == "identity_skip"
    assert classify_result(
        commons_result("1", commons_lookup_status="error")
    ) == "network_failed"
    assert classify_result(commons_result("1", p18_filename=None)) == "no_image"
    assert classify_result(commons_result("1")) == "commons_accept"
    assert classify_result(commons_result("1", commons_decision="REVIEW")) == "commons_review"
    assert classify_result(commons_result("1", commons_decision="SKIP")) == "commons_skip"


# 12. Review queue contains only review-worthy records.
def test_review_queue_contains_only_review_decisions(db_session):
    ids = ["1", "2", "3", "4", "5"]
    results_by_id = {
        "1": commons_result("1"),  # accept - must NOT appear
        "2": commons_result("2", commons_decision="REVIEW"),  # must appear
        "3": commons_result("3", identity_decision="SKIP", commons_decision="SKIP"),  # must NOT
        "4": commons_result("4", identity_decision="REVIEW", commons_decision="SKIP"),  # must appear
        "5": commons_result("5", p18_filename=None, commons_decision="SKIP"),  # no_image, must NOT
    }

    with patch(PATCH_TARGET_IDENTITY, side_effect=fake_enrich_laureate_dry_run), \
         patch(PATCH_TARGET_COMMONS, side_effect=fake_enrich_commons_for_identity_factory(results_by_id)):
        report = run_bulk_enrichment(db_session, ids, mode="dry-run")

    review_ids = {entry["nobel_laureate_id"] for entry in report["review_queue"]}
    assert review_ids == {"2", "4"}
    assert len(report["review_queue"]) == 2


def test_records_report_includes_all_non_accept_cases(db_session):
    ids = ["1", "2"]
    results_by_id = {
        "1": commons_result("1"),  # accept - excluded from records
        "2": commons_result("2", commons_decision="SKIP"),  # included
    }

    with patch(PATCH_TARGET_IDENTITY, side_effect=fake_enrich_laureate_dry_run), \
         patch(PATCH_TARGET_COMMONS, side_effect=fake_enrich_commons_for_identity_factory(results_by_id)):
        report = run_bulk_enrichment(db_session, ids, mode="dry-run")

    record_ids = {entry["nobel_laureate_id"] for entry in report["records"]}
    assert record_ids == {"2"}
