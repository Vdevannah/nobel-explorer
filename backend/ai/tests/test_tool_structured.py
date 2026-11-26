"""search_laureates and get_laureate_details against the isolated fixture DB."""

import json

import pytest

pytest.importorskip("langchain_core")
pytest.importorskip("chromadb")


def _names(result):
    return [l["full_name"] for l in result["data"]["laureates"]]


# ---------------------------------------------------------------- search_laureates

def test_exact_year_and_category_returns_all_2022_chemistry_laureates(tools):
    result = tools["search_laureates"].invoke({"year": 2022, "category": "Chemistry"})
    assert result["ok"] is True
    data = result["data"]
    assert data["total_matches"] == 3 and data["returned"] == 3 and data["truncated"] is False
    assert _names(result) == ["Carolyn R. Bertozzi", "K. Barry Sharpless", "Morten Meldal"]
    assert [l["laureate_id"] for l in data["laureates"]] == [356, 766, 886]  # stable ids, id order
    for laureate in data["laureates"]:
        assert [(a["year"], a["category"]) for a in laureate["matched_awards"]] == [(2022, "Chemistry")]
        assert "click chemistry" in laureate["matched_awards"][0]["motivation"]


def test_other_awards_are_separated_from_matched_awards(tools):
    sharpless = tools["search_laureates"].invoke({"year": 2022, "category": "Chemistry"})["data"]["laureates"][1]
    assert [(a["year"], a["category"]) for a in sharpless["other_awards"]] == [(2001, "Chemistry")]


def test_category_alias_is_applied(tools):
    result = tools["search_laureates"].invoke({"year": 2023, "category": "medicine"})
    assert result["data"]["filters"]["category"] == "Physiology or Medicine"
    assert _names(result) == ["Katalin Karikó", "Drew Weissman"]


def test_name_ambiguity_is_flagged(tools):
    result = tools["search_laureates"].invoke({"name": "Curie"})
    data = result["data"]
    assert data["ambiguous_name"] is True and data["total_matches"] == 3
    assert set(_names(result)) == {"Marie Curie, née Skłodowska", "Pierre Curie", "Irène Joliot-Curie"}
    assert "Choose a laureate_id" in data["message"]


def test_unique_name_is_not_ambiguous(tools):
    data = tools["search_laureates"].invoke({"name": "einstein"})["data"]
    assert data["ambiguous_name"] is False and data["laureates"][0]["laureate_id"] == 249


def test_birth_country_semantics_and_alias(tools):
    result = tools["search_laureates"].invoke({"birth_country": "United States"})
    data = result["data"]
    assert data["filters"]["birth_country"] == "USA"
    assert _names(result) == ["Carolyn R. Bertozzi", "K. Barry Sharpless", "Drew Weissman"]
    assert "birth_country is the country of birth" in data["country_semantics"]
    # Bertozzi's affiliation country is reported separately from her birth country.
    award = data["laureates"][0]["matched_awards"][0]
    assert award["affiliations"][0]["affiliation_country"] == "USA"


def test_historical_birth_country_is_not_remapped(tools):
    assert _names(tools["search_laureates"].invoke({"birth_country": "Russian Empire"})) == [
        "Marie Curie, née Skłodowska"]
    assert tools["search_laureates"].invoke({"birth_country": "Poland"})["data"]["total_matches"] == 0


def test_gender_filter(tools):
    result = tools["search_laureates"].invoke({"gender": "female", "category": "Chemistry"})
    assert _names(result) == ["Carolyn R. Bertozzi", "Irène Joliot-Curie", "Marie Curie, née Skłodowska"]


def test_limit_truncates_and_reports_total(tools):
    data = tools["search_laureates"].invoke({"gender": "male", "limit": 2})["data"]
    assert data["returned"] == 2 and data["total_matches"] == 7 and data["truncated"] is True
    assert [l["laureate_id"] for l in data["laureates"]] == [1, 249]
    assert "Showing 2 of 7" in data["message"]


def test_results_are_deterministic(tools):
    first = tools["search_laureates"].invoke({"gender": "male"})
    second = tools["search_laureates"].invoke({"gender": "male"})
    assert first == second
    ids = [l["laureate_id"] for l in first["data"]["laureates"]]
    assert ids == sorted(ids)


def test_empty_result_is_explicit_with_category_coverage(tools):
    data = tools["search_laureates"].invoke({"year": 1950, "category": "Economics"})["data"]
    assert data["total_matches"] == 0 and data["laureates"] == []
    assert "No laureates matched" in data["message"]
    assert data["coverage"]["category_first_year"] == 1969
    assert "Economic Sciences prizes in the database run from 1969" in data["message"]


def test_future_year_inside_range_is_empty_not_error(tools):
    data = tools["search_laureates"].invoke({"year": 2024})["data"]
    assert data["total_matches"] == 0 and "covers prizes awarded 1901-2023" in data["message"]


def test_unsupported_category_returns_validation_error(tools):
    result = tools["search_laureates"].invoke({"category": "Mathematics", "year": 1950})
    assert result["ok"] is False
    assert result["error"]["type"] == "validation_error"
    assert "There is no Nobel Prize in Mathematics" in result["error"]["message"]


def test_search_provenance_never_invents_urls(tools):
    data = tools["search_laureates"].invoke({"year": 2022})["data"]
    assert data["provenance"]["citation_status"] == "structured_record"
    assert set(data["provenance"]) == {"source_name", "citation_status", "note"}
    assert "http" not in json.dumps(data["provenance"])
    assert "http" not in json.dumps(data["laureates"])  # no invented per-laureate URLs


# ---------------------------------------------------------------- get_laureate_details

def test_details_full_record(tools):
    data = tools["get_laureate_details"].invoke({"laureate_id": 249})["data"]
    laureate = data["laureate"]
    assert laureate["full_name"] == "Albert Einstein" and laureate["birth_date"] == "1879-03-14"
    assert laureate["birth_city"] == "Ulm" and laureate["birth_country"] == "Germany"
    assert data["awards"][0]["year"] == 1921 and "photoelectric" in data["awards"][0]["motivation"]
    assert data["awards"][0]["affiliations"][0]["institution"] == "Kaiser-Wilhelm-Institut für Physik"
    contribution = data["contributions"][0]
    assert contribution["title"] == "Photoelectric Effect"
    assert contribution["explanation_levels_available"] == ["Simple", "Expert"]
    assert contribution["citation_status"] == "source_linked"
    assert contribution["source"]["url"].startswith("https://www.nobelprize.org/")
    assert "explanation" not in contribution  # only when a level is requested


def test_details_connection_provenance(tools):
    connections = tools["get_laureate_details"].invoke({"laureate_id": 249})["data"]["contributions"][0]["connections"]
    by_id = {c["connection_id"]: c for c in connections}
    assert by_id[24]["citation_status"] == "source_linked" and by_id[24]["source"]["name"] == "U.S. Department of Energy"
    assert by_id[25]["citation_status"] == "unverified_educational" and by_id[25]["source"] is None


def test_details_with_explanation_level(tools):
    contribution = tools["get_laureate_details"].invoke(
        {"laureate_id": 249, "include_explanation_level": "simple"})["data"]["contributions"][0]
    explanation = contribution["explanation"]
    assert explanation["level"] == "Simple" and explanation["text"].startswith("Light is made of photons")
    assert explanation["citation_status"] == "unverified_educational"
    assert explanation["related_source"]["url"].startswith("https://www.nobelprize.org/")
    assert explanation["key_concepts"] == ["Light has photons", "Photons knock out electrons"]


def test_details_missing_level_is_reported_honestly(tools):
    contribution = tools["get_laureate_details"].invoke(
        {"laureate_id": 249, "include_explanation_level": "Advanced"})["data"]["contributions"][0]
    assert contribution["explanation"] is None
    assert "No Advanced explanation is stored" in contribution["explanation_message"]


def test_details_shared_contribution(tools):
    data = tools["get_laureate_details"].invoke({"laureate_id": 886})["data"]
    assert [c["contribution_id"] for c in data["contributions"]] == [779]


def test_details_without_educational_content(tools):
    data = tools["get_laureate_details"].invoke({"laureate_id": 1})["data"]
    assert data["contributions"] == [] and data["educational_content_available"] is False
    assert "only structured prize data is available" in data["message"]


def test_details_organization(tools):
    data = tools["get_laureate_details"].invoke({"laureate_id": 648})["data"]
    assert data["laureate"]["laureate_type"] == "Organization" and data["laureate"]["gender"] is None
    assert [a["year"] for a in data["awards"]] == [1917, 1944]


def test_details_missing_laureate(tools):
    result = tools["get_laureate_details"].invoke({"laureate_id": 999999})
    assert result == {"tool": "get_laureate_details", "ok": False,
                      "error": {"type": "not_found", "message": "Laureate not found: 999999"}}


def test_details_invalid_id(tools):
    result = tools["get_laureate_details"].invoke({"laureate_id": -3})
    assert result["ok"] is False and result["error"]["type"] == "validation_error"
