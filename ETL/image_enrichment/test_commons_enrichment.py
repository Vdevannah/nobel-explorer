from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock, patch

import requests

from ETL.image_enrichment.commons import CommonsClient, CommonsError
from ETL.image_enrichment.enrichment import (
    enrich_commons_for_identity,
    run_commons_dry_run,
)
from ETL.image_enrichment.validation import (
    decide_commons_validation,
    normalize_attribution,
    normalize_license,
    validate_media_type,
)


def extmetadata(**overrides):
    base = {
        "License": None,
        "LicenseShortName": None,
        "LicenseUrl": None,
        "UsageTerms": None,
        "AttributionRequired": None,
        "Attribution": None,
        "Artist": None,
        "Credit": None,
        "Copyrighted": None,
        "Restrictions": None,
        "ImageDescription": None,
    }
    base.update(overrides)
    return base


def file_info(**overrides):
    base = {
        "filename": "Example.jpg",
        "canonical_source_url": "https://commons.wikimedia.org/wiki/File:Example.jpg",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/e/e0/Example.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/Example.jpg/800px-Example.jpg",
        "thumbnail_width": 800,
        "thumbnail_height": 600,
        "width": 3000,
        "height": 2250,
        "mime": "image/jpeg",
        "extmetadata": extmetadata(),
    }
    base.update(overrides)
    return base


def identity(**overrides):
    base = {
        "nobel_laureate_id": "26",
        "full_name": "Albert Einstein",
        "selected_entity_id": "Q937",
        "proposed_action": "ACCEPT",
        "p18_filename": "Einstein 1921 by F Schmutzer - restoration.jpg",
    }
    base.update(overrides)
    return base


def evaluate(info):
    license_info = normalize_license(info["extmetadata"])
    attribution_info = normalize_attribution(info["extmetadata"])
    media_info = validate_media_type(info["mime"])
    return decide_commons_validation(
        identity_action="ACCEPT",
        p18_filename="Example.jpg",
        commons_lookup_status="found",
        file_info=info,
        license_info=license_info,
        attribution_info=attribution_info,
        media_info=media_info,
    )


# 1. CC BY image is acceptable when metadata is complete.
def test_cc_by_image_is_accepted_when_metadata_complete():
    info = file_info(
        extmetadata=extmetadata(
            LicenseShortName="CC BY 4.0",
            UsageTerms="Creative Commons Attribution 4.0",
            AttributionRequired="true",
            Artist="Jane Photographer",
        )
    )
    decision = evaluate(info)

    assert decision["decision"] == "ACCEPT"
    assert decision["skip_reasons"] == []
    assert decision["review_reasons"] == []


# 2. CC BY-SA image is acceptable when metadata is complete.
def test_cc_by_sa_image_is_accepted_when_metadata_complete():
    info = file_info(
        extmetadata=extmetadata(
            LicenseShortName="CC BY-SA 3.0",
            Artist="Jane Photographer",
        )
    )
    decision = evaluate(info)

    assert decision["decision"] == "ACCEPT"
    license_info = normalize_license(info["extmetadata"])
    assert license_info["normalized"] == "CC BY-SA 3.0"


# 3. Public Domain image is acceptable.
def test_public_domain_image_is_accepted():
    info = file_info(
        extmetadata=extmetadata(
            LicenseShortName="Public domain",
            Credit="Library of Congress",
        )
    )
    decision = evaluate(info)
    license_info = normalize_license(info["extmetadata"])

    assert decision["decision"] == "ACCEPT"
    assert license_info["normalized"] == "Public Domain"
    assert license_info["reusable"] is True


def test_public_domain_from_copyrighted_false_without_cc_license():
    info = file_info(extmetadata=extmetadata(Copyrighted="False"))
    license_info = normalize_license(info["extmetadata"])

    assert license_info["normalized"] == "Public Domain"
    assert license_info["status"] == "reusable"


# Phase 7.5I-A: five specific, named license families identified by the
# Commons policy audit as reusable-but-previously-unrecognized. Each is
# checked to (a) now register as reusable and (b) preserve Commons' own
# license label verbatim in `normalized`, never rewritten.
def test_gfdl_license_is_reusable_and_preserved_verbatim():
    info = file_info(
        extmetadata=extmetadata(
            LicenseShortName="GFDL 1.2",
            UsageTerms="GNU Free Documentation License 1.2",
            LicenseUrl="http://www.gnu.org/licenses/old-licenses/fdl-1.2.html",
            Copyrighted="True",
            Artist="Jane Photographer",
        )
    )
    decision = evaluate(info)
    license_info = normalize_license(info["extmetadata"])

    assert license_info["status"] == "reusable"
    assert license_info["normalized"] == "GFDL 1.2"
    assert decision["decision"] == "ACCEPT"


def test_copyrighted_free_use_is_reusable():
    info = file_info(
        extmetadata=extmetadata(
            LicenseShortName="Copyrighted free use",
            UsageTerms="Copyrighted free use",
            Copyrighted="True",
        )
    )
    license_info = normalize_license(info["extmetadata"])

    assert license_info["status"] == "reusable"
    assert license_info["normalized"] == "Copyrighted free use"


def test_no_restrictions_is_reusable():
    info = file_info(
        extmetadata=extmetadata(
            LicenseShortName="No restrictions",
            UsageTerms="No known copyright restrictions",
            LicenseUrl="https://www.flickr.com/commons/usage/",
            Copyrighted="True",
        )
    )
    license_info = normalize_license(info["extmetadata"])

    assert license_info["status"] == "reusable"
    assert license_info["normalized"] == "No restrictions"


def test_licence_ouverte_is_reusable():
    info = file_info(
        extmetadata=extmetadata(
            LicenseShortName="Licence Ouverte",
            UsageTerms="Licence Ouverte",
            LicenseUrl="https://www.etalab.gouv.fr/licence-ouverte-open-licence",
            Copyrighted="True",
        )
    )
    license_info = normalize_license(info["extmetadata"])

    assert license_info["status"] == "reusable"
    assert license_info["normalized"] == "Licence Ouverte"


def test_kogl_is_reusable():
    info = file_info(
        extmetadata=extmetadata(
            LicenseShortName="KOGL Type 1",
            LicenseUrl="http://www.kogl.or.kr/info/licenseType1.do",
            Copyrighted="True",
        )
    )
    license_info = normalize_license(info["extmetadata"])

    assert license_info["status"] == "reusable"
    assert license_info["normalized"] == "KOGL Type 1"


# Phase 7.5M-A: UK Open Government Licence v3.0 only, verified against
# nationalarchives.gov.uk and Commons:UK_Open_Government_Licence policy
# (David W. C. MacMillan's North Lanarkshire Council portrait).
def test_ogl_v3_is_reusable_and_preserved_verbatim():
    info = file_info(
        extmetadata=extmetadata(
            LicenseShortName="OGL 3",
            UsageTerms="Open Government License 3",
            LicenseUrl="http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3",
            AttributionRequired="true",
            Artist="North Lanarkshire Council",
            Copyrighted="True",
        )
    )
    decision = evaluate(info)
    license_info = normalize_license(info["extmetadata"])

    assert license_info["status"] == "reusable"
    assert license_info["reusable"] is True
    # Preserved verbatim -- never rewritten as "CC BY" or similar.
    assert license_info["normalized"] == "OGL 3"
    assert decision["decision"] == "ACCEPT"


def test_ogl_v3_requires_and_preserves_attribution():
    info = file_info(
        extmetadata=extmetadata(
            LicenseShortName="OGL 3",
            LicenseUrl="http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3",
            AttributionRequired="true",
            Artist="North Lanarkshire Council",
            Credit="https://www.northlanarkshire.gov.uk/news/message-hope-scotlands-newest-nobel-prizewinner",
        )
    )
    decision = evaluate(info)
    attribution_info = normalize_attribution(info["extmetadata"])

    assert decision["decision"] == "ACCEPT"
    assert attribution_info["normalized"] is not None
    assert "North Lanarkshire Council" in attribution_info["normalized"]
    assert any("attribution" in reason for reason in decision["reasons"])


def test_ogl_unverified_version_does_not_auto_accept():
    # Only OGL v3 was verified this phase. A bare "OGL" or an OGL v1/v2
    # string must NOT be swept in by a generic "contains open" rule.
    for short_name in ("OGL", "OGL 1", "OGL 2", "OGL v2.0"):
        info = file_info(extmetadata=extmetadata(LicenseShortName=short_name))
        license_info = normalize_license(info["extmetadata"])
        assert license_info["status"] == "unclear", short_name


def test_ogl_v3_with_unknown_restriction_is_still_review():
    info = file_info(
        extmetadata=extmetadata(
            LicenseShortName="OGL 3",
            LicenseUrl="http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3",
            AttributionRequired="true",
            Artist="North Lanarkshire Council",
            Restrictions="trademark",
        )
    )
    decision = evaluate(info)
    license_info = normalize_license(info["extmetadata"])

    assert license_info["status"] == "reusable"
    assert decision["copyright_decision"] == "ACCEPT"
    # Non-copyright restriction (not the narrow personality-only exemption)
    # still forces overall REVIEW -- unchanged from existing 7.5I-C behavior.
    assert decision["decision"] == "REVIEW"
    assert decision["non_copyright_restrictions"] == []


def test_unrelated_unclear_license_is_still_unclear_not_swept_in():
    # Guards against a generic "accept unknown license" regression: a
    # made-up/unrecognized license string must remain "unclear", not
    # accidentally reusable just because *some* new branch was added.
    info = file_info(extmetadata=extmetadata(LicenseShortName="Some Made Up License 9.9"))
    license_info = normalize_license(info["extmetadata"])

    assert license_info["status"] == "unclear"


# 4. Missing license metadata leads to REVIEW (not an automatic ACCEPT).
def test_missing_license_is_review():
    info = file_info(extmetadata=extmetadata(Artist="Jane Photographer"))
    decision = evaluate(info)
    license_info = normalize_license(info["extmetadata"])

    assert license_info["status"] == "missing"
    assert decision["decision"] == "REVIEW"
    assert any("license" in reason for reason in decision["review_reasons"])


# 5. Unsupported/restrictive license leads to SKIP.
def test_restrictive_license_is_skipped():
    info = file_info(
        extmetadata=extmetadata(LicenseShortName="CC BY-NC-ND 4.0")
    )
    decision = evaluate(info)
    license_info = normalize_license(info["extmetadata"])

    assert license_info["status"] == "restrictive"
    assert decision["decision"] == "SKIP"
    assert any("restrictive" in reason for reason in decision["skip_reasons"])


def test_all_rights_reserved_is_restrictive():
    info = file_info(extmetadata=extmetadata(License="All rights reserved"))
    license_info = normalize_license(info["extmetadata"])

    assert license_info["status"] == "restrictive"
    assert license_info["reusable"] is False


# 6. Missing Commons file leads to SKIP.
def test_missing_commons_file_is_skipped():
    decision = decide_commons_validation(
        identity_action="ACCEPT",
        p18_filename="Does Not Exist.jpg",
        commons_lookup_status="missing",
        file_info=None,
        license_info=None,
        attribution_info=None,
        media_info=None,
    )

    assert decision["decision"] == "SKIP"
    assert any("does not resolve" in reason for reason in decision["skip_reasons"])


# 7. Missing image URL leads to REVIEW (metadata present but unusable).
def test_missing_image_url_is_review():
    info = file_info(
        image_url=None,
        thumbnail_url=None,
        extmetadata=extmetadata(
            LicenseShortName="CC0",
        ),
    )
    decision = evaluate(info)

    assert decision["decision"] == "REVIEW"
    assert any(
        "image URL" in reason for reason in decision["review_reasons"]
    )


# 8. HTML attribution is normalized to safe plain text.
def test_html_attribution_is_normalized_safely():
    result = normalize_attribution(
        extmetadata(
            Artist='<a href="//commons.wikimedia.org/wiki/User:Jane">'
            "Jane&nbsp;Doe</a>",
            Credit="<span class=\"int-own-work\">Own work</span>",
        )
    )

    assert result["normalized"] == "Jane Doe (Own work)"
    assert "<" not in result["normalized"]
    assert ">" not in result["normalized"]
    assert result["had_html"] is True


def test_attribution_is_never_fabricated_when_absent():
    result = normalize_attribution(extmetadata())

    assert result["normalized"] is None
    assert result["had_html"] is False


# 9. Canonical Commons page is distinct from the raw image URL.
def test_canonical_source_is_distinct_from_image_url():
    session = Mock()
    session.headers = {}
    response = Mock()
    response.status_code = 200
    response.headers = {}
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "query": {
            "pages": {
                "123": {
                    "imageinfo": [{
                        "url": "https://upload.wikimedia.org/wikipedia/commons/e/e0/Example.jpg",
                        "descriptionurl": "https://commons.wikimedia.org/wiki/File:Example.jpg",
                        "thumburl": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/Example.jpg/800px-Example.jpg",
                        "thumbwidth": 800,
                        "thumbheight": 600,
                        "width": 3000,
                        "height": 2250,
                        "mime": "image/jpeg",
                        "extmetadata": {},
                    }],
                }
            }
        }
    }
    session.get.return_value = response
    client = CommonsClient(session=session, request_delay=0)

    info = client.get_file_info("Example.jpg")

    assert info["canonical_source_url"] == (
        "https://commons.wikimedia.org/wiki/File:Example.jpg"
    )
    assert info["image_url"] != info["canonical_source_url"]
    assert info["canonical_source_url"].startswith(
        "https://commons.wikimedia.org/wiki/File:"
    )


def test_missing_commons_page_returns_none_not_error():
    session = Mock()
    session.headers = {}
    response = Mock()
    response.status_code = 200
    response.headers = {}
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "query": {"pages": {"-1": {"missing": ""}}}
    }
    session.get.return_value = response
    client = CommonsClient(session=session, request_delay=0)

    assert client.get_file_info("Does Not Exist.jpg") is None


# 10. Non-image media is rejected; uncommon image formats are reviewed.
def test_non_image_media_is_rejected():
    info = file_info(mime="application/pdf")
    decision = evaluate(info)

    assert decision["decision"] == "SKIP"
    assert any("not an image" in reason for reason in decision["skip_reasons"])


def test_uncommon_image_format_is_reviewed_not_accepted_silently():
    info = file_info(
        mime="image/tiff",
        extmetadata=extmetadata(LicenseShortName="CC0"),
    )
    decision = evaluate(info)

    assert decision["decision"] == "REVIEW"
    assert any("uncommon" in reason for reason in decision["review_reasons"])


def test_unknown_media_type_is_reviewed():
    result = validate_media_type(None)

    assert result["is_image"] is False
    assert result["status"] == "unknown"


# Phase 7.5H: an uncommon original format is still "supported" once
# Commons has already rendered a browser-safe thumbnail derivative -- the
# thumbnail, not the original, is what gets served/persisted.
def test_tiff_with_browser_thumbnail_is_supported():
    result = validate_media_type("image/tiff", has_browser_thumbnail=True)

    assert result["is_image"] is True
    assert result["status"] == "supported"


def test_tiff_without_thumbnail_is_still_reviewed():
    result = validate_media_type("image/tiff", has_browser_thumbnail=False)

    assert result["status"] == "unsupported_image"


# 11. Network transient retry behavior remains bounded for Commons calls.
def _commons_response(status_code, retry_after=None, payload=None):
    response = Mock()
    response.status_code = status_code
    response.headers = {}
    if retry_after is not None:
        response.headers["Retry-After"] = retry_after
    if status_code >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(
            f"status {status_code}", response=response,
        )
    else:
        response.raise_for_status.return_value = None
        response.json.return_value = payload or {
            "query": {"pages": {"-1": {"missing": ""}}}
        }
    return response


def test_commons_transient_errors_are_retried_within_limit():
    session = Mock()
    session.headers = {}
    session.get.side_effect = [
        _commons_response(503),
        _commons_response(429),
        _commons_response(200),
    ]
    sleep = Mock()
    client = CommonsClient(
        session=session,
        request_delay=0,
        sleep_func=sleep,
        jitter_func=lambda _start, _end: 0,
    )

    assert client.get_file_info("Example.jpg") is None
    assert session.get.call_count == 3
    assert sleep.call_count == 2


def test_commons_permanent_404_is_not_retried():
    session = Mock()
    session.headers = {}
    session.get.return_value = _commons_response(404)
    client = CommonsClient(session=session, request_delay=0)

    try:
        client.get_file_info("Example.jpg")
    except CommonsError:
        pass
    else:
        raise AssertionError("Expected CommonsError")

    assert session.get.call_count == 1


def test_commons_retries_stop_at_configured_limit():
    session = Mock()
    session.headers = {}
    session.get.return_value = _commons_response(503)
    client = CommonsClient(
        session=session,
        request_delay=0,
        max_attempts=3,
        sleep_func=Mock(),
        jitter_func=lambda _start, _end: 0,
    )

    try:
        client.get_file_info("Example.jpg")
    except CommonsError:
        pass
    else:
        raise AssertionError("Expected CommonsError")

    assert session.get.call_count == 3


def test_commons_retry_after_is_honored():
    session = Mock()
    session.headers = {}
    session.get.side_effect = [
        _commons_response(429, retry_after="2"),
        _commons_response(200),
    ]
    sleep = Mock()
    client = CommonsClient(session=session, request_delay=0, sleep_func=sleep)

    client.get_file_info("Example.jpg")

    sleep.assert_called_once_with(2.0)


def test_commons_file_cache_prevents_duplicate_requests():
    session = Mock()
    session.headers = {}
    session.get.return_value = _commons_response(
        200,
        payload={"query": {"pages": {"-1": {"missing": ""}}}},
    )
    client = CommonsClient(session=session, request_delay=0)

    first = client.get_file_info("Example.jpg")
    second = client.get_file_info("Example.jpg")

    assert first is second is None
    assert session.get.call_count == 1


# 12. No database writes occur anywhere in the Commons dry-run path.
# Phase 7.5J: direct Commons File-namespace search, independent of
# Wikidata P18 / Wikipedia PageImages.
def test_search_files_returns_bare_filenames():
    session = Mock()
    session.headers = {}
    session.get.return_value = _commons_response(
        200,
        payload={
            "query": {
                "search": [
                    {"title": "File:Example Portrait.jpg"},
                    {"title": "File:Example Portrait 2.jpg"},
                ]
            }
        },
    )
    client = CommonsClient(session=session, request_delay=0)

    results = client.search_files("Example Portrait", limit=5)

    assert results == ["Example Portrait.jpg", "Example Portrait 2.jpg"]
    call_kwargs = session.get.call_args
    assert call_kwargs.kwargs["params"]["srnamespace"] == 6


def test_search_files_returns_empty_list_for_no_hits():
    session = Mock()
    session.headers = {}
    session.get.return_value = _commons_response(200, payload={"query": {"search": []}})
    client = CommonsClient(session=session, request_delay=0)

    assert client.search_files("Nonexistent Person Xyz") == []


def test_commons_dry_run_performs_no_database_writes():
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

    wikidata_client = Mock()
    wikidata_client.search_wikidata_entities.return_value = [
        {"entity_id": "Q937"}
    ]
    wikidata_client.get_wikidata_entities.return_value = [{
        "entity_id": "Q937",
        "label": "Albert Einstein",
        "aliases": [],
        "description": "German-born theoretical physicist",
        "instance_of_ids": ["Q5"],
        "birth_date": "1879-03-14T00:00:00Z",
        "award_labels": ["Nobel Prize in Physics"],
        "has_p18": True,
        "p18_filename": "Einstein 1921 by F Schmutzer - restoration.jpg",
    }]

    commons_client = Mock()
    commons_client.get_file_info.return_value = file_info(
        extmetadata=extmetadata(
            LicenseShortName="Public domain",
            Credit="Ferdinand Schmutzer",
        )
    )

    with patch(
        "ETL.image_enrichment.enrichment.laureate_repository.get_by_nobel_id",
        return_value=laureate,
    ):
        report = run_commons_dry_run(
            db, ["26"],
            wikidata_client=wikidata_client,
            commons_client=commons_client,
        )

    assert report["database_writes"] == 0
    assert report["results"][0]["database_write"] is False
    db.add.assert_not_called()
    db.delete.assert_not_called()
    db.flush.assert_not_called()
    db.commit.assert_not_called()
    db.execute.assert_not_called()


def test_commons_lookup_is_skipped_when_identity_not_accepted():
    result = enrich_commons_for_identity(
        identity(proposed_action="REVIEW"),
        commons_client=Mock(),
    )

    assert result["commons_lookup_status"] == "skipped"
    assert result["commons_decision"] == "SKIP"
    assert result["database_write"] is False


def test_commons_lookup_is_skipped_when_no_p18():
    result = enrich_commons_for_identity(
        identity(p18_filename=None),
        commons_client=Mock(),
    )

    assert result["commons_lookup_status"] == "skipped"
    assert result["commons_decision"] == "SKIP"
    assert any("P18" in reason for reason in result["skip_reasons"])


def test_commons_network_error_is_reported_as_skip():
    commons_client = Mock()
    commons_client.get_file_info.side_effect = CommonsError("offline")

    result = enrich_commons_for_identity(identity(), commons_client)

    assert result["commons_lookup_status"] == "error"
    assert result["commons_decision"] == "SKIP"
    assert result["lookup_error"] == "offline"


# Phase 7.5I-C: personality-rights policy. A single, exact "personality"
# restriction does not block an otherwise-reusable copyright license;
# any other restriction pattern continues through the prior, more
# conservative REVIEW behavior unchanged.

# 1. Reusable CC BY + personality -> copyright acceptable.
def test_cc_by_with_personality_only_is_accepted():
    info = file_info(
        extmetadata=extmetadata(
            LicenseShortName="CC BY 4.0",
            Artist="Jane Photographer",
            Restrictions="personality",
        )
    )
    decision = evaluate(info)

    assert decision["decision"] == "ACCEPT"
    assert decision["copyright_decision"] == "ACCEPT"
    assert decision["non_copyright_restrictions"] == ["personality"]
    assert decision["skip_reasons"] == []
    assert decision["review_reasons"] == []


# 2. Reusable CC BY-SA + personality -> acceptable.
def test_cc_by_sa_with_personality_only_is_accepted():
    info = file_info(
        extmetadata=extmetadata(
            LicenseShortName="CC BY-SA 3.0",
            Artist="Jane Photographer",
            Restrictions="personality",
        )
    )
    decision = evaluate(info)

    assert decision["decision"] == "ACCEPT"
    assert decision["copyright_decision"] == "ACCEPT"
    assert decision["non_copyright_restrictions"] == ["personality"]


# 3. Unclear license + personality -> REVIEW. The exemption never fires
# when the copyright side hasn't independently reached ACCEPT.
def test_unclear_license_with_personality_remains_review():
    info = file_info(
        extmetadata=extmetadata(
            LicenseShortName="Some Ambiguous Tag",
            Restrictions="personality",
        )
    )
    decision = evaluate(info)

    assert decision["decision"] == "REVIEW"
    assert decision["copyright_decision"] == "REVIEW"
    assert decision["non_copyright_restrictions"] == []


# 4. personality + an unfamiliar second restriction -> REVIEW. The
# exemption requires the restriction list to be *exactly* ["personality"].
def test_personality_combined_with_unknown_restriction_remains_review():
    info = file_info(
        extmetadata=extmetadata(
            LicenseShortName="CC BY 4.0",
            Artist="Jane Photographer",
            Restrictions="personality|trademark",
        )
    )
    decision = evaluate(info)

    assert decision["decision"] == "REVIEW"
    assert decision["non_copyright_restrictions"] == []
    assert any("additional recorded restrictions" in reason for reason in decision["review_reasons"])


# 5. Trademark alone remains REVIEW even with a reusable license.
def test_trademark_restriction_remains_review():
    info = file_info(
        extmetadata=extmetadata(
            LicenseShortName="CC BY-SA 4.0",
            Artist="Jane Photographer",
            Restrictions="trademark",
        )
    )
    decision = evaluate(info)

    assert decision["decision"] == "REVIEW"
    assert decision["non_copyright_restrictions"] == []


# 6. An unrecognized restriction string also remains REVIEW -- no generic
# "ignore restrictions" rule was introduced.
def test_unknown_restriction_remains_review():
    info = file_info(
        extmetadata=extmetadata(
            LicenseShortName="CC BY 4.0",
            Artist="Jane Photographer",
            Restrictions="some_unrecognized_flag",
        )
    )
    decision = evaluate(info)

    assert decision["decision"] == "REVIEW"
    assert decision["non_copyright_restrictions"] == []


# 7. The restriction metadata is retained (never silently discarded) in
# the enrichment result, even when it doesn't block acceptance.
def test_restriction_metadata_is_retained_in_enrichment_result():
    commons_client = Mock()
    commons_client.get_file_info.return_value = file_info(
        extmetadata=extmetadata(
            LicenseShortName="CC BY 4.0",
            Artist="Jane Photographer",
            Restrictions="personality",
        )
    )

    result = enrich_commons_for_identity(identity(), commons_client)

    assert result["commons_decision"] == "ACCEPT"
    assert result["copyright_decision"] == "ACCEPT"
    assert result["non_copyright_restrictions"] == ["personality"]
    assert any("personality" in warning for warning in result["warnings"])


# 8. A laureate that already has an image_url is never overwritten, even
# for a personality-exempted ACCEPT.
def test_existing_image_is_never_overwritten_by_personality_exemption():
    from ETL.image_enrichment.persistence import plan_persistence

    commons_client = Mock()
    commons_client.get_file_info.return_value = file_info(
        extmetadata=extmetadata(
            LicenseShortName="CC BY 4.0",
            Artist="Jane Photographer",
            Restrictions="personality",
        )
    )
    result = enrich_commons_for_identity(identity(), commons_client)

    laureate = SimpleNamespace(
        laureate_id=1001,
        nobel_laureate_id="26",
        full_name="Albert Einstein",
        image_url="https://upload.wikimedia.org/existing.jpg",
    )
    db = Mock()
    with patch(
        "ETL.image_enrichment.persistence.laureate_repository.get_by_nobel_id",
        return_value=laureate,
    ):
        plans = plan_persistence(db, [result], force=False)

    assert plans[0]["action"] == "skipped_existing"


# 9. Dry-run (plan only, never apply) makes zero database writes for a
# personality-exempted ACCEPT.
def test_personality_exempted_accept_dry_run_makes_zero_writes():
    from ETL.image_enrichment.persistence import plan_persistence

    commons_client = Mock()
    commons_client.get_file_info.return_value = file_info(
        extmetadata=extmetadata(
            LicenseShortName="CC BY-SA 4.0",
            Artist="Jane Photographer",
            Restrictions="personality",
        )
    )
    result = enrich_commons_for_identity(identity(), commons_client)

    laureate = SimpleNamespace(laureate_id=1001, nobel_laureate_id="26", full_name="Albert Einstein", image_url=None)
    db = Mock()
    with patch(
        "ETL.image_enrichment.persistence.laureate_repository.get_by_nobel_id",
        return_value=laureate,
    ):
        plans = plan_persistence(db, [result], force=False)

    assert plans[0]["action"] == "update"
    db.commit.assert_not_called()
    db.add.assert_not_called()


# 10. A made-up/unrecognized license string is still "unclear" -- the new
# personality-exemption branch never widens what counts as reusable.
def test_made_up_license_remains_unclear_with_or_without_restrictions():
    info = file_info(extmetadata=extmetadata(LicenseShortName="Totally Fictional License 7.0"))
    assert normalize_license(info["extmetadata"])["status"] == "unclear"

    info_with_restriction = file_info(
        extmetadata=extmetadata(
            LicenseShortName="Totally Fictional License 7.0",
            Restrictions="personality",
        )
    )
    decision = evaluate(info_with_restriction)
    assert decision["decision"] == "REVIEW"
    assert decision["copyright_decision"] == "REVIEW"


# Phase 7.5N: ordinary trademark-only policy. A single, exact
# "trademarked" restriction (Commons' actual token for e.g. organization
# logos) does not block an otherwise-reusable copyright license, mirroring
# the existing personality-only exemption -- but any other combination
# (notably the Red Cross/IFRC "ihl|trademarked|insignia" case) must
# continue to force REVIEW unchanged.

def test_trademarked_only_restriction_is_accepted_like_personality():
    info = file_info(
        extmetadata=extmetadata(
            LicenseShortName="Public domain",
            Copyrighted="False",
            Restrictions="trademarked",
        )
    )
    decision = evaluate(info)

    assert decision["decision"] == "ACCEPT"
    assert decision["copyright_decision"] == "ACCEPT"
    assert decision["non_copyright_restrictions"] == ["trademarked"]
    assert decision["review_reasons"] == []


def test_trademarked_combined_with_other_restrictions_remains_review():
    # This is exactly the League of Red Cross Societies / IFRC pattern --
    # the protected emblem's IHL/insignia status must never be swept
    # aside by the ordinary trademark-only exemption.
    info = file_info(
        extmetadata=extmetadata(
            LicenseShortName="Public domain",
            Copyrighted="False",
            Restrictions="ihl|trademarked|insignia",
        )
    )
    decision = evaluate(info)

    assert decision["decision"] == "REVIEW"
    assert decision["non_copyright_restrictions"] == []
    assert any("additional recorded restrictions" in reason for reason in decision["review_reasons"])


def test_trademarked_only_without_copyright_accept_remains_review():
    info = file_info(
        extmetadata=extmetadata(
            LicenseShortName="Some Ambiguous Tag",
            Restrictions="trademarked",
        )
    )
    decision = evaluate(info)

    assert decision["decision"] == "REVIEW"
    assert decision["copyright_decision"] == "REVIEW"
    assert decision["non_copyright_restrictions"] == []


# Phase 7.5N: Commons' formally-templated "Attribution only license" --
# an exact, whole-string match only, never a generic "contains
# attribution" rule. Verified against the template's own displayed terms.

def test_attribution_only_license_is_reusable_and_preserved_verbatim():
    info = file_info(
        extmetadata=extmetadata(
            LicenseShortName="Attribution",
            Artist="AIP Emilio Segre Visual Archives",
            Attribution="American Institute of Physics (AIP)",
            Credit="https://repository.aip.org/example-item",
        )
    )
    decision = evaluate(info)
    license_info = normalize_license(info["extmetadata"])

    assert license_info["status"] == "reusable"
    assert license_info["normalized"] == "Attribution"
    assert decision["decision"] == "ACCEPT"
    assert decision["copyright_decision"] == "ACCEPT"


def test_attribution_only_license_without_usable_attribution_is_review():
    info = file_info(extmetadata=extmetadata(LicenseShortName="Attribution"))
    decision = evaluate(info)

    assert decision["decision"] == "REVIEW"
    assert any("attribution" in reason for reason in decision["review_reasons"])


def test_real_cc_by_attribution_is_not_swept_into_attribution_only_rule():
    # A genuine CC BY license whose UsageTerms happens to say
    # "Creative Commons Attribution 4.0" must still be recognized as CC BY
    # (via the earlier, more specific pattern) -- the exact-match
    # Attribution-only rule must never intercept it or relabel it.
    info = file_info(
        extmetadata=extmetadata(
            LicenseShortName="CC BY 4.0",
            UsageTerms="Creative Commons Attribution 4.0",
            Artist="Jane Photographer",
        )
    )
    license_info = normalize_license(info["extmetadata"])

    assert license_info["normalized"] == "CC BY 4.0"
    assert license_info["status"] == "reusable"
