"""get_nobel_statistics: aggregation correctness against hand-counted fixture values.

Expected numbers are derived in backend/ai/tests/tool_fixture_data.py.
"""

import pytest

pytest.importorskip("langchain_core")
pytest.importorskip("chromadb")


def _stats(tools, **kwargs):
    result = tools["get_nobel_statistics"].invoke(kwargs)
    assert result["ok"] is True, result
    return result["data"]


def test_summary_distinguishes_laureates_prizes_and_awards(tools):
    data = _stats(tools, operation="summary")
    assert data["result"] == {
        "distinct_laureates": 12,
        "laureate_prize_awards": 15,
        "distinct_person_laureates": 11,
        "distinct_organization_laureates": 1,
        "prizes": 11,
        "distinct_birth_countries_of_persons": 7,
        "women_person_laureates": 4,
        "women_percentage_of_known_gender_persons": 36.4,
    }
    assert "distinct laureates" in data["metric_definition"] and data["applied_filters"] == {}


def test_summary_with_filters(tools):
    data = _stats(tools, operation="summary", category="Chemistry", start_year=2000, end_year=2025)
    # 2001 Sharpless; 2022 Bertozzi, Sharpless, Meldal -> 3 laureates, 4 awards, 2 prizes.
    assert data["result"]["distinct_laureates"] == 3
    assert data["result"]["laureate_prize_awards"] == 4
    assert data["result"]["prizes"] == 2
    assert data["applied_filters"] == {"category": "Chemistry", "start_year": 2000, "end_year": 2025}


def test_laureates_by_category_counts_distinct_laureates(tools):
    data = _stats(tools, operation="laureates_by_category")
    assert data["result"] == [
        {"category": "Chemistry", "laureate_count": 5},
        {"category": "Physics", "laureate_count": 4},
        {"category": "Physiology or Medicine", "laureate_count": 2},
        {"category": "Economic Sciences", "laureate_count": 1},
        {"category": "Peace", "laureate_count": 1},
    ]
    assert data["counting_unit"] == "distinct laureates (persons and organizations)"


def test_laureates_by_gender_excludes_organizations(tools):
    data = _stats(tools, operation="laureates_by_gender")
    assert data["result"] == [{"gender": "female", "laureate_count": 4}, {"gender": "male", "laureate_count": 7}]
    assert "Organizations are excluded" in data["metric_definition"]


def test_prizes_by_decade_counts_prizes_not_laureates(tools):
    rows = {r["decade"]: r["prize_count"] for r in _stats(tools, operation="prizes_by_decade")["result"]}
    assert rows == {1900: 2, 1910: 2, 1920: 1, 1930: 1, 1940: 1, 1960: 1, 2000: 1, 2020: 2}
    assert sum(rows.values()) == 11


def test_laureates_by_decade(tools):
    rows = {r["decade"]: r["laureate_count"] for r in _stats(tools, operation="laureates_by_decade")["result"]}
    # 1900s: Röntgen, Marie, Pierre; 2020s: Bertozzi, Sharpless, Meldal, Karikó, Weissman.
    assert rows[1900] == 3 and rows[2020] == 5


def test_top_birth_countries_breaks_ties_alphabetically(tools):
    data = _stats(tools, operation="top_birth_countries", limit=3)
    assert data["result"] == [
        {"birth_country": "USA", "laureate_count": 3},
        {"birth_country": "France", "laureate_count": 2},
        {"birth_country": "Germany", "laureate_count": 2},
    ]
    assert data["countries_with_laureates"] == 7
    assert "BIRTH country" in data["metric_definition"]


def test_women_by_era(tools):
    rows = {r["era"]: r for r in _stats(tools, operation="women_by_era")["result"]}
    assert rows["1901-1950"]["women_count"] == 2 and rows["1901-1950"]["known_gender_count"] == 5
    assert rows["1901-1950"]["percentage"] == 40.0
    assert rows["2011-present"]["women_count"] == 2 and rows["2011-present"]["known_gender_count"] == 5


def test_average_age_uses_award_observations(tools):
    data = _stats(tools, operation="average_age_at_award", category="Chemistry")
    assert data["result"] == {"average_age_at_award": 57.8}  # 347 / 6 observations
    assert data["counting_unit"] == "age-at-award observations"


def test_affiliation_institution_counts_use_institution_country(tools):
    data = _stats(tools, operation="laureates_by_affiliation_institution", category="Chemistry",
                  affiliation_country="United States")
    assert data["applied_filters"]["affiliation_country"] == "USA"
    assert data["result"] == [
        {"institution": "Scripps Research", "laureate_count": 1},
        {"institution": "Stanford University", "laureate_count": 1},
    ]
    assert "not the laureate's birth country" in data["metric_definition"]


def test_empty_statistics_are_flagged(tools):
    data = _stats(tools, operation="laureates_by_category", start_year=1950, end_year=1960)
    assert data["result"] == [] and data["empty"] is True


@pytest.mark.parametrize("args", [
    {"operation": "raw_sql", "query": "SELECT 1"},
    {"operation": "summary; DROP TABLE laureate"},
    {"operation": "average_age_at_award"},
    {"operation": "summary", "category": "Mathematics"},
])
def test_statistics_rejects_unsupported_requests(tools, args):
    result = tools["get_nobel_statistics"].invoke(args)
    assert result["ok"] is False and result["error"]["type"] == "validation_error"
