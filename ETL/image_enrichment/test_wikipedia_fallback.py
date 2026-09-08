from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock, patch

from ETL.image_enrichment.wikipedia_fallback import (
    candidate_search_queries,
    enrich_one_fallback,
    pick_article_image_candidate,
)


PATCH_TARGET = "ETL.image_enrichment.wikipedia_fallback.laureate_repository.get_by_nobel_id"


def laureate(**overrides):
    base = dict(
        laureate_id=1001,
        nobel_laureate_id="26",
        full_name="Albert Einstein",
        laureate_type="Person",
        birth_date=date(1879, 3, 14),
        birth_city="Ulm",
        birth_state=None,
        birth_country="Germany",
        image_url=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def wikidata_person(
    entity_id="Q937",
    label="Albert Einstein",
    birth_date="1879-03-14T00:00:00Z",
    instance_of_ids=None,
    award_labels=None,
):
    return {
        "entity_id": entity_id,
        "label": label,
        "aliases": [],
        "description": "German-born theoretical physicist",
        "instance_of_ids": ["Q5"] if instance_of_ids is None else instance_of_ids,
        "birth_date": birth_date,
        "birthplace_labels": ["Ulm"],
        "country_labels": ["Germany"],
        "occupation_labels": ["physicist"],
        "award_labels": ["Nobel Prize in Physics"] if award_labels is None else award_labels,
        "has_p18": False,
        "p18_filename": None,
    }


def commons_file_info(**overrides):
    base = dict(
        filename="File:Example.jpg",
        canonical_source_url="https://commons.wikimedia.org/wiki/File:Example.jpg",
        image_url="https://upload.wikimedia.org/wikipedia/commons/e/e0/Example.jpg",
        thumbnail_url="https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/Example.jpg/800px-Example.jpg",
        thumbnail_width=800,
        thumbnail_height=600,
        width=3000,
        height=2250,
        mime="image/jpeg",
        extmetadata={
            "License": None,
            "LicenseShortName": "CC BY-SA 4.0",
            "LicenseUrl": None,
            "UsageTerms": None,
            "AttributionRequired": "true",
            "Attribution": None,
            "Artist": "Jane Photographer",
            "Credit": None,
            "Copyrighted": "True",
            "Restrictions": None,
            "ImageDescription": None,
        },
    )
    base.update(overrides)
    return base


def build_clients(
    resolve_article_return=None,
    search_articles_return=None,
    list_images_return=None,
    entities_return=None,
    sitelink_return=None,
    file_info_return=None,
):
    wikidata_client = Mock()
    wikidata_client.get_enwiki_sitelink.return_value = sitelink_return
    wikidata_client.get_wikidata_entities.return_value = entities_return or []

    wikipedia_client = Mock()
    wikipedia_client.resolve_article.return_value = resolve_article_return
    wikipedia_client.search_articles.return_value = search_articles_return or []
    wikipedia_client.list_article_images.return_value = list_images_return or []

    commons_client = Mock()
    commons_client.get_file_info.return_value = file_info_return

    return wikidata_client, wikipedia_client, commons_client


# 1. Verified Wikipedia article resolves to a high-confidence Wikidata
# identity via the shared select_candidate() -- no second validator.
def test_verified_wikipedia_article_resolves_identity():
    person = laureate()
    wikidata_client, wikipedia_client, commons_client = build_clients(
        search_articles_return=[{"title": "Albert Einstein", "pageid": 1}],
        resolve_article_return={
            "title": "Albert Einstein",
            "wikibase_item": "Q937",
            "pageimage_free": "Einstein_1921.jpg",
            "pageimage": None,
        },
        entities_return=[wikidata_person()],
        file_info_return=commons_file_info(),
    )

    with patch(PATCH_TARGET, return_value=person):
        result = enrich_one_fallback(
            Mock(), "26", "OTHER", wikidata_client, wikipedia_client, commons_client,
        )

    assert result["identity_decision"] == "ACCEPT"
    assert result["wikipedia_article"] == "Albert Einstein"
    assert result["commons_decision"] == "ACCEPT"
    assert result["final_action"] == "accept"


# 2. A Wikipedia hit whose linked Wikidata entity conflicts on birth year
# is rejected, not force-matched.
def test_wrong_article_candidate_is_rejected():
    person = laureate(nobel_laureate_id="964", full_name="George P. Smith", birth_date=date(1941, 3, 10))
    wikidata_client, wikipedia_client, commons_client = build_clients(
        search_articles_return=[{"title": "George Smith (disambiguation)", "pageid": 2}],
        resolve_article_return={
            "title": "George Smith (disambiguation)",
            "wikibase_item": "Q123456",
            "pageimage_free": None,
            "pageimage": None,
        },
        entities_return=[wikidata_person(entity_id="Q123456", label="George Smith", birth_date="1873-01-01T00:00:00Z")],
    )

    with patch(PATCH_TARGET, return_value=person):
        result = enrich_one_fallback(
            Mock(), "964", "OTHER", wikidata_client, wikipedia_client, commons_client,
        )

    assert result["identity_decision"] in ("SKIP", "REVIEW")
    assert result["final_action"] in ("skip", "review")
    assert result["commons_filename"] is None


# 3. PageImages success: the free page image is used directly, no need
# to fall back to the raw article image list.
def test_pageimage_success_is_used_directly():
    person = laureate()
    wikidata_client, wikipedia_client, commons_client = build_clients(
        sitelink_return="Albert Einstein",
        resolve_article_return={
            "title": "Albert Einstein",
            "wikibase_item": "Q937",
            "pageimage_free": "Einstein_1921.jpg",
            "pageimage": None,
        },
        file_info_return=commons_file_info(filename="File:Einstein_1921.jpg"),
    )

    with patch(PATCH_TARGET, return_value=person):
        result = enrich_one_fallback(
            Mock(), "26", "NO_P18", wikidata_client, wikipedia_client, commons_client,
            candidate_wikidata_id="Q937",
        )

    assert result["pageimage_candidate"] == "Einstein_1921.jpg"
    wikipedia_client.list_article_images.assert_not_called()
    assert result["final_action"] == "accept"


# 4. No PageImage available -> falls back to the article image list.
def test_no_pageimage_falls_back_to_article_image_list():
    person = laureate()
    wikidata_client, wikipedia_client, commons_client = build_clients(
        sitelink_return="Albert Einstein",
        resolve_article_return={
            "title": "Albert Einstein",
            "wikibase_item": "Q937",
            "pageimage_free": None,
            "pageimage": None,
        },
        list_images_return=["File:Flag of Germany.svg", "File:Albert Einstein Head.jpg"],
        file_info_return=commons_file_info(filename="File:Albert Einstein Head.jpg"),
    )

    with patch(PATCH_TARGET, return_value=person):
        result = enrich_one_fallback(
            Mock(), "26", "NO_P18", wikidata_client, wikipedia_client, commons_client,
            candidate_wikidata_id="Q937",
        )

    wikipedia_client.list_article_images.assert_called_once()
    assert result["commons_filename"] == "Albert Einstein Head.jpg"
    # Weakest-provenance path: never auto-persisted even on Commons ACCEPT.
    assert result["final_action"] != "accept"


# 5. A non-portrait-only article image list (flags/logos/signature) never
# produces a candidate.
def test_non_portrait_only_images_are_rejected():
    survivors = pick_article_image_candidate(
        [
            "File:Flag of Germany.svg",
            "File:Commons-logo.svg",
            "File:Autograph of Someone.png",
            "File:Nobel Prize.png",
        ],
        "Someone Nobody",
    )
    assert survivors is None


# 6. Commons ACCEPT is eligible for persistence via the unchanged
# plan_persistence/apply_persistence pipeline.
def test_commons_accept_is_planned_for_persistence():
    from ETL.image_enrichment.persistence import plan_persistence

    person = laureate()
    wikidata_client, wikipedia_client, commons_client = build_clients(
        sitelink_return="Albert Einstein",
        resolve_article_return={
            "title": "Albert Einstein",
            "wikibase_item": "Q937",
            "pageimage_free": "Einstein_1921.jpg",
            "pageimage": None,
        },
        file_info_return=commons_file_info(),
    )

    db = Mock()
    with patch(PATCH_TARGET, return_value=person):
        result = enrich_one_fallback(
            db, "26", "NO_P18", wikidata_client, wikipedia_client, commons_client,
            candidate_wikidata_id="Q937",
        )
        with patch(
            "ETL.image_enrichment.persistence.laureate_repository.get_by_nobel_id",
            return_value=person,
        ):
            plans = plan_persistence(db, [result["_commons_result"]])

    assert plans[0]["action"] == "update"
    assert plans[0]["payload"]["image_url"]


# 7. Commons REVIEW never reaches an "update" persistence plan.
def test_commons_review_does_not_persist():
    from ETL.image_enrichment.persistence import plan_persistence

    person = laureate()
    wikidata_client, wikipedia_client, commons_client = build_clients(
        sitelink_return="Albert Einstein",
        resolve_article_return={
            "title": "Albert Einstein",
            "wikibase_item": "Q937",
            "pageimage_free": "Einstein_1921.jpg",
            "pageimage": None,
        },
        file_info_return=commons_file_info(
            extmetadata={
                "License": None, "LicenseShortName": "Unclear license", "LicenseUrl": None,
                "UsageTerms": None, "AttributionRequired": None, "Attribution": None,
                "Artist": None, "Credit": None, "Copyrighted": None, "Restrictions": None,
                "ImageDescription": None,
            }
        ),
    )

    db = Mock()
    with patch(PATCH_TARGET, return_value=person):
        result = enrich_one_fallback(
            db, "26", "NO_P18", wikidata_client, wikipedia_client, commons_client,
            candidate_wikidata_id="Q937",
        )
        plans = plan_persistence(db, [result["_commons_result"]])

    assert result["commons_decision"] == "REVIEW"
    assert result["final_action"] == "review"
    assert plans[0]["action"] in ("review", "skip")


# 8. A laureate that already has an image_url is skipped without any
# Wikipedia/Wikidata/Commons calls.
def test_existing_image_is_skipped_without_network_calls():
    person = laureate(image_url="https://upload.wikimedia.org/existing.jpg")
    wikidata_client, wikipedia_client, commons_client = build_clients()

    with patch(PATCH_TARGET, return_value=person):
        result = enrich_one_fallback(
            Mock(), "26", "NO_P18", wikidata_client, wikipedia_client, commons_client,
            candidate_wikidata_id="Q937",
        )

    assert result["final_action"] == "skipped_existing"
    wikidata_client.get_enwiki_sitelink.assert_not_called()
    wikipedia_client.resolve_article.assert_not_called()
    commons_client.get_file_info.assert_not_called()


# 9. A TIFF original with a resolved browser-safe thumbnail is accepted,
# not rejected solely for its original media type.
def test_tiff_with_browser_thumbnail_is_accepted():
    person = laureate(nobel_laureate_id="353", full_name="Selman Abraham Waksman")
    wikidata_client, wikipedia_client, commons_client = build_clients(
        file_info_return=commons_file_info(
            mime="image/tiff",
            thumbnail_url="https://thumb.wikimedia.org/.../lossy-page1-960px-Example.tif.jpg",
        ),
    )

    with patch(PATCH_TARGET, return_value=person):
        result = enrich_one_fallback(
            Mock(), "353", "REVIEW", wikidata_client, wikipedia_client, commons_client,
            existing_p18_filename="Example.tif",
        )

    wikipedia_client.resolve_article.assert_not_called()
    assert result["commons_decision"] == "ACCEPT"
    assert result["final_action"] == "accept"


# 10. Ambiguous identity (multiple similarly plausible Wikidata
# candidates found via Wikipedia) stays REVIEW; no image lookup happens.
def test_ambiguous_identity_remains_review():
    person = laureate(nobel_laureate_id="706", full_name="William F. Sharpe")
    wikidata_client, wikipedia_client, commons_client = build_clients(
        search_articles_return=[{"title": "William Sharpe", "pageid": 3}],
        resolve_article_return={
            "title": "William Sharpe",
            "wikibase_item": "Q1",
            "pageimage_free": None,
            "pageimage": None,
        },
        entities_return=[
            wikidata_person(entity_id="Q1", label="William Sharpe", birth_date="1934-06-16T00:00:00Z"),
            wikidata_person(entity_id="Q2", label="William F. Sharpe", birth_date="1934-06-16T00:00:00Z"),
        ],
    )

    with patch(PATCH_TARGET, return_value=person):
        result = enrich_one_fallback(
            Mock(), "706", "IDENTITY_AMBIGUOUS", wikidata_client, wikipedia_client, commons_client,
        )

    assert result["final_action"] in ("review", "skip")
    commons_client.get_file_info.assert_not_called()


# 11. No viable Wikidata-linked candidate found via any Wikipedia search
# variant -> identity stays SKIP, no image lookup.
def test_article_identity_mismatch_remains_skip():
    person = laureate(nobel_laureate_id="819", full_name="Albert Arnold (Al) Gore  Jr.")
    wikidata_client, wikipedia_client, commons_client = build_clients(
        search_articles_return=[],
    )

    with patch(PATCH_TARGET, return_value=person):
        result = enrich_one_fallback(
            Mock(), "819", "OTHER", wikidata_client, wikipedia_client, commons_client,
        )

    assert result["identity_decision"] == "SKIP"
    assert result["final_action"] == "skip"
    commons_client.get_file_info.assert_not_called()


# 12. enrich_one_fallback performs zero database writes itself --
# persistence is a separate, later step, so a dry-run naturally writes
# nothing regardless of outcome.
def test_fallback_step_never_writes_to_database():
    person = laureate()
    wikidata_client, wikipedia_client, commons_client = build_clients(
        sitelink_return="Albert Einstein",
        resolve_article_return={
            "title": "Albert Einstein", "wikibase_item": "Q937",
            "pageimage_free": "Einstein_1921.jpg", "pageimage": None,
        },
        file_info_return=commons_file_info(),
    )
    db = Mock()

    with patch(PATCH_TARGET, return_value=person):
        enrich_one_fallback(
            db, "26", "NO_P18", wikidata_client, wikipedia_client, commons_client,
            candidate_wikidata_id="Q937",
        )

    db.add.assert_not_called()
    db.commit.assert_not_called()
    db.execute.assert_not_called()


# 13. Idempotent rerun: once a laureate has image_url populated, running
# the fallback again is a stable no-op with no repeated network calls.
def test_rerun_after_persistence_is_idempotent():
    person = laureate(image_url="https://upload.wikimedia.org/existing.jpg")
    wikidata_client, wikipedia_client, commons_client = build_clients()

    with patch(PATCH_TARGET, return_value=person):
        first = enrich_one_fallback(
            Mock(), "26", "NO_P18", wikidata_client, wikipedia_client, commons_client,
            candidate_wikidata_id="Q937",
        )
        second = enrich_one_fallback(
            Mock(), "26", "NO_P18", wikidata_client, wikipedia_client, commons_client,
            candidate_wikidata_id="Q937",
        )

    assert first["final_action"] == second["final_action"] == "skipped_existing"
    wikidata_client.get_enwiki_sitelink.assert_not_called()


# Name-normalization helper coverage for formal/titled Nobel names
# (section 9) -- variants only, never a confidence change.
def test_candidate_search_queries_handles_titled_names():
    queries = candidate_search_queries("Lord (Alexander R.) Todd")
    assert "Lord (Alexander R.) Todd" in queries
    assert "Alexander R." in queries
    assert "(Alexander R.) Todd" in queries or "Todd" in " ".join(queries)


def test_candidate_search_queries_handles_comma_style_titles():
    queries = candidate_search_queries(
        "John Boyd Orr, Baron Boyd-Orr of Brechin Mearn"
    )
    assert "John Boyd Orr" in queries
