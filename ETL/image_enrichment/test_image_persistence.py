from types import SimpleNamespace
from unittest.mock import Mock, patch

from ETL.image_enrichment.persistence import (
    apply_persistence,
    build_persistence_payload,
    cleanup_attribution,
    plan_persistence,
    run_persistence,
    strip_tracking_params,
)


PATCH_TARGET_GET = "ETL.image_enrichment.persistence.laureate_repository.get_by_nobel_id"
PATCH_TARGET_UPDATE = "ETL.image_enrichment.persistence.laureate_repository.update_image_metadata"


def commons_result(**overrides):
    base = {
        "nobel_laureate_id": "26",
        "full_name": "Albert Einstein",
        "identity_decision": "ACCEPT",
        "commons_decision": "ACCEPT",
        "image_url_candidate": (
            "https://thumb.wikimedia.org/wikipedia/commons/thumb/3/3e/"
            "Einstein.jpg/960px-Einstein.jpg"
            "?utm_source=commons.wikimedia.org&utm_campaign=imageinfo"
        ),
        "canonical_source_url": (
            "https://commons.wikimedia.org/wiki/File:Einstein.jpg"
        ),
        "license_normalized": "Public Domain",
        "attribution_normalized": "Ferdinand Schmutzer",
    }
    base.update(overrides)
    return base


def fake_laureate(nobel_laureate_id="26", image_url=None, **extra_fields):
    fields = {
        "nobel_laureate_id": nobel_laureate_id,
        "full_name": "Albert Einstein",
        "laureate_type": "Person",
        "gender": "male",
        "featured": False,
        "image_url": image_url,
        "image_source_url": None,
        "image_attribution": None,
        "image_license": None,
    }
    fields.update(extra_fields)
    return SimpleNamespace(**fields)


# 1. ACCEPT + missing image -> update.
def test_accept_with_missing_image_plans_an_update():
    laureate = fake_laureate(image_url=None)
    db = Mock()

    with patch(PATCH_TARGET_GET, return_value=laureate):
        plans = plan_persistence(db, [commons_result()])

    assert plans[0]["action"] == "update"
    assert plans[0]["payload"]["image_license"] == "Public Domain"


# 2. REVIEW -> no update.
def test_review_decision_never_plans_an_update():
    result = commons_result(commons_decision="REVIEW")
    db = Mock()

    with patch(PATCH_TARGET_GET, return_value=fake_laureate()):
        plans = plan_persistence(db, [result])

    assert plans[0]["action"] == "review"
    assert build_persistence_payload(result) is None


# 3. SKIP -> no update.
def test_skip_decision_never_plans_an_update():
    result = commons_result(commons_decision="SKIP")
    db = Mock()

    with patch(PATCH_TARGET_GET, return_value=fake_laureate()):
        plans = plan_persistence(db, [result])

    assert plans[0]["action"] == "skip"
    assert build_persistence_payload(result) is None


def test_identity_not_accepted_is_never_planned_for_update():
    result = commons_result(identity_decision="REVIEW", commons_decision="SKIP")

    assert build_persistence_payload(result) is None


# 4. Existing image_url -> skipped by default (missing-only).
def test_existing_image_is_skipped_by_default():
    laureate = fake_laureate(image_url="https://example.org/existing.jpg")
    db = Mock()

    with patch(PATCH_TARGET_GET, return_value=laureate):
        plans = plan_persistence(db, [commons_result()], force=False)

    assert plans[0]["action"] == "skipped_existing"
    assert plans[0]["existing_image_url"] == "https://example.org/existing.jpg"


# 5. Force mode can update when explicitly requested.
def test_force_mode_updates_existing_image():
    laureate = fake_laureate(image_url="https://example.org/existing.jpg")
    db = Mock()

    with patch(PATCH_TARGET_GET, return_value=laureate):
        plans = plan_persistence(db, [commons_result()], force=True)

    assert plans[0]["action"] == "update"
    assert plans[0]["force_applied"] is True


def test_force_is_never_implied_by_default():
    laureate = fake_laureate(image_url="https://example.org/existing.jpg")
    db = Mock()

    with patch(PATCH_TARGET_GET, return_value=laureate):
        plans = plan_persistence(db, [commons_result()])  # force omitted

    assert plans[0]["action"] == "skipped_existing"


# 6. Only the four image fields are modified.
def test_only_four_image_fields_are_modified():
    laureate = fake_laureate(
        image_url=None,
        full_name="Albert Einstein",
        gender="male",
        featured=True,
    )
    db = Mock()

    with patch(PATCH_TARGET_GET, return_value=laureate):
        plans = plan_persistence(db, [commons_result()])
        report = apply_persistence(db, plans)

    assert report["committed"] is True
    assert laureate.image_url == (
        "https://thumb.wikimedia.org/wikipedia/commons/thumb/3/3e/"
        "Einstein.jpg/960px-Einstein.jpg"
    )
    assert laureate.image_source_url == (
        "https://commons.wikimedia.org/wiki/File:Einstein.jpg"
    )
    assert laureate.image_attribution == "Ferdinand Schmutzer"
    assert laureate.image_license == "Public Domain"
    # Untouched fields.
    assert laureate.full_name == "Albert Einstein"
    assert laureate.gender == "male"
    assert laureate.featured is True


# 7 & 8. UTM/tracking params stripped; functional params preserved.
def test_utm_tracking_params_are_stripped():
    url = (
        "https://upload.wikimedia.org/wikipedia/commons/e/e0/Example.jpg"
        "?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail"
    )

    cleaned = strip_tracking_params(url)

    assert cleaned == "https://upload.wikimedia.org/wikipedia/commons/e/e0/Example.jpg"
    assert "utm_" not in cleaned


def test_functional_query_params_are_preserved():
    url = "https://upload.wikimedia.org/wikipedia/commons/e/e0/Example.jpg?width=800"

    cleaned = strip_tracking_params(url)

    assert cleaned == url


def test_mixed_tracking_and_functional_params():
    url = (
        "https://example.org/img.jpg"
        "?width=800&utm_source=commons.wikimedia.org&format=jpg"
    )

    cleaned = strip_tracking_params(url)

    assert "utm_source" not in cleaned
    assert "width=800" in cleaned
    assert "format=jpg" in cleaned


def test_url_without_query_string_is_unchanged():
    url = "https://commons.wikimedia.org/wiki/File:Example.jpg"

    assert strip_tracking_params(url) == url


def test_strip_tracking_params_handles_falsy_input():
    assert strip_tracking_params(None) is None
    assert strip_tracking_params("") == ""


# 9. Attribution duplicate cleanup.
def test_exact_repeated_attribution_phrase_is_deduped():
    raw = (
        "Unknown author Unknown author "
        "(http://jasminkellner.com/wp-content/uploads/2015/03/Marie-Curie.jpg)"
    )

    cleaned = cleanup_attribution(raw)

    assert cleaned == (
        "Unknown author "
        "(http://jasminkellner.com/wp-content/uploads/2015/03/Marie-Curie.jpg)"
    )


def test_non_repeated_attribution_is_preserved_unchanged():
    raw = "Bengt Oberger (Own work)"

    assert cleanup_attribution(raw) == raw


def test_cleanup_never_fabricates_when_attribution_missing():
    assert cleanup_attribution(None) is None
    assert cleanup_attribution("") == ""


def test_cleanup_does_not_dedupe_dissimilar_repeated_words():
    raw = "John Smith and Jane Smith (Own work)"

    assert cleanup_attribution(raw) == raw


# 10. Rollback / error handling: all-or-nothing, no partial success.
def test_persistence_rolls_back_entire_batch_on_error():
    laureate_one = fake_laureate(nobel_laureate_id="26", image_url=None)
    laureate_two = fake_laureate(nobel_laureate_id="6", image_url=None)
    db = Mock()

    plans = [
        {
            "nobel_laureate_id": "26",
            "full_name": "Albert Einstein",
            "action": "update",
            "payload": {
                "image_url": "https://example.org/a.jpg",
                "image_source_url": "https://commons.wikimedia.org/wiki/File:A.jpg",
                "image_attribution": "A",
                "image_license": "Public Domain",
            },
        },
        {
            "nobel_laureate_id": "6",
            "full_name": "Marie Curie",
            "action": "update",
            "payload": {
                "image_url": "https://example.org/b.jpg",
                "image_source_url": "https://commons.wikimedia.org/wiki/File:B.jpg",
                "image_attribution": "B",
                "image_license": "Public Domain",
            },
        },
    ]

    with patch(
        PATCH_TARGET_GET, side_effect=[laureate_one, laureate_two]
    ), patch(
        PATCH_TARGET_UPDATE,
        side_effect=[None, RuntimeError("boom")],
    ):
        report = apply_persistence(db, plans)

    assert report["committed"] is False
    assert report["updated_ids"] == []
    assert "boom" in report["error"]
    db.commit.assert_not_called()
    db.rollback.assert_called_once()


def test_run_persistence_reports_failure_without_writes():
    result = commons_result()
    db = Mock()

    with patch(PATCH_TARGET_GET, return_value=fake_laureate(image_url=None)), patch(
        PATCH_TARGET_UPDATE, side_effect=RuntimeError("boom")
    ):
        report = run_persistence(db, [result], mode="persist")

    assert report["updated"] == 0
    assert report["failed"] == 1
    assert report["database_writes"] == 0
    db.commit.assert_not_called()
    db.rollback.assert_called_once()


# 11. Dry-run performs zero writes.
def test_dry_run_performs_zero_writes():
    db = Mock()

    with patch(PATCH_TARGET_GET, return_value=fake_laureate(image_url=None)):
        report = run_persistence(db, [commons_result()], mode="dry-run")

    assert report["database_writes"] == 0
    assert report["updated"] == 1  # would-update count, not an actual write
    db.commit.assert_not_called()
    db.flush.assert_not_called()
    db.execute.assert_not_called()


def test_dry_run_does_not_mutate_laureate_objects():
    laureate = fake_laureate(image_url=None)
    db = Mock()

    with patch(PATCH_TARGET_GET, return_value=laureate):
        run_persistence(db, [commons_result()], mode="dry-run")

    assert laureate.image_url is None


# 12. Second missing-only run is idempotent.
def test_second_missing_only_run_makes_zero_additional_updates():
    db = Mock()
    laureate_before = fake_laureate(image_url=None)

    with patch(PATCH_TARGET_GET, return_value=laureate_before):
        first_report = run_persistence(db, [commons_result()], mode="persist")

    assert first_report["updated"] == 1

    # Simulate the row now having image metadata, as it would after a
    # real commit, and run persistence again in default missing-only mode.
    laureate_after = fake_laureate(
        image_url=laureate_before.image_url or "https://example.org/persisted.jpg"
    )
    with patch(PATCH_TARGET_GET, return_value=laureate_after):
        second_report = run_persistence(db, [commons_result()], mode="persist")

    assert second_report["updated"] == 0
    assert second_report["skipped_existing"] == 1


def test_load_and_end_to_end_summary_counts():
    results = [
        commons_result(nobel_laureate_id="26"),
        commons_result(nobel_laureate_id="6", commons_decision="REVIEW"),
        commons_result(nobel_laureate_id="217", identity_decision="SKIP"),
    ]
    db = Mock()

    def fake_get(_db, nobel_id):
        return fake_laureate(nobel_laureate_id=nobel_id, image_url=None)

    with patch(PATCH_TARGET_GET, side_effect=fake_get):
        report = run_persistence(db, results, mode="dry-run")

    assert report["updated"] == 1
    assert report["review"] == 1
    assert report["skip"] == 1
    assert report["database_writes"] == 0
