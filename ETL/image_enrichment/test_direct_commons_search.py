from unittest.mock import Mock

from ETL.image_enrichment.direct_commons_search import (
    search_organization_candidates,
    search_person_candidates,
    validate_candidate,
)


# 1. Person search filters out non-portrait content (flags/logos/etc.)
# even when Commons returns it as a hit.
def test_person_search_filters_blocklisted_files():
    commons_client = Mock()
    commons_client.search_files.return_value = [
        "Flag of Germany.svg",
        "Albert Einstein 1921.jpg",
        "Commons-logo.svg",
    ]

    results = search_person_candidates(commons_client, "Albert Einstein")

    assert results == ["Albert Einstein 1921.jpg"]


# 2. Person search stops after the first query variant that yields any
# plausible candidate, rather than exhausting every variant needlessly.
def test_person_search_stops_after_first_successful_query():
    commons_client = Mock()
    commons_client.search_files.return_value = ["Some Person Photo.jpg"]

    search_person_candidates(commons_client, "Lord Rayleigh (John William Strutt)")

    # candidate_search_queries generates multiple variants; only the
    # first should actually be searched once results are found.
    assert commons_client.search_files.call_count == 1


# 3. Person search with zero plausible hits across all variants returns
# an empty list rather than a decorative fallback.
def test_person_search_returns_empty_when_nothing_plausible():
    commons_client = Mock()
    commons_client.search_files.return_value = ["Flag of Germany.svg", "Commons-logo.svg"]

    results = search_person_candidates(commons_client, "Some Obscure Laureate")

    assert results == []


# 4. Organization search allows logos/buildings through, unlike the
# person path.
def test_organization_search_allows_logo():
    commons_client = Mock()
    commons_client.search_files.return_value = ["Amnesty International logo.svg"]

    results = search_organization_candidates(commons_client, "Amnesty International")

    assert results == ["Amnesty International logo.svg"]


# 5. Organization search still rejects clearly unrelated decorative
# content that isn't a logo/building/emblem/photo of the org.
def test_organization_search_rejects_unrelated_flag():
    commons_client = Mock()
    commons_client.search_files.return_value = ["Flag of Germany.svg"]

    results = search_organization_candidates(commons_client, "Some Organization")

    assert results == []


# 6. validate_candidate reuses the exact same Commons validation used
# everywhere else -- no second, weaker validator.
def test_validate_candidate_reuses_shared_commons_validation():
    commons_client = Mock()
    commons_client.get_file_info.return_value = {
        "filename": "File:Example.jpg",
        "canonical_source_url": "https://commons.wikimedia.org/wiki/File:Example.jpg",
        "image_url": "https://upload.wikimedia.org/example.jpg",
        "thumbnail_url": "https://upload.wikimedia.org/thumb/example.jpg",
        "width": 800,
        "height": 600,
        "mime": "image/jpeg",
        "extmetadata": {
            "License": None,
            "LicenseShortName": "CC BY 4.0",
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
    }

    result = validate_candidate(commons_client, 1001, "26", "Albert Einstein", "Example.jpg")

    assert result["commons_decision"] == "ACCEPT"
    assert result["license_normalized"] == "CC BY 4.0"
