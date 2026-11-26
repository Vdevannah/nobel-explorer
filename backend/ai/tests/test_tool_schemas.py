"""Argument validation for the four tool schemas (no database needed)."""

import pytest
from pydantic import ValidationError

from backend.ai.tools.schemas import (
    CURRENT_YEAR,
    NOBEL_CATEGORIES,
    KnowledgeSearchInput,
    LaureateDetailsInput,
    NobelStatisticsInput,
    SearchLaureatesInput,
)


@pytest.mark.parametrize("alias, canonical", [
    ("chemistry", "Chemistry"), ("  PHYSICS ", "Physics"), ("Medicine", "Physiology or Medicine"),
    ("physiology", "Physiology or Medicine"), ("Economics", "Economic Sciences"),
    ("economic sciences", "Economic Sciences"), ("peace", "Peace"), ("Literature", "Literature"),
])
def test_category_aliases_normalise(alias, canonical):
    assert SearchLaureatesInput(category=alias).category == canonical


@pytest.mark.parametrize("bad", ["Mathematics", "Maths", "Biology", "Computer Science", ""])
def test_invalid_categories_rejected_with_valid_list(bad):
    with pytest.raises(ValidationError) as info:
        SearchLaureatesInput(category=bad, year=2000)
    message = str(info.value)
    if bad:
        assert "Physiology or Medicine" in message
    if bad.lower().startswith("math"):
        assert "no Nobel Prize in Mathematics" in message


def test_category_list_matches_six_nobel_categories():
    assert NOBEL_CATEGORIES == ("Chemistry", "Economic Sciences", "Literature", "Peace", "Physics",
                                "Physiology or Medicine")


@pytest.mark.parametrize("year", [1900, 1850, CURRENT_YEAR + 1, -5, True, "twenty", 2022.5])
def test_invalid_years_rejected(year):
    with pytest.raises(ValidationError):
        SearchLaureatesInput(year=year)


@pytest.mark.parametrize("year", [1901, 2022, CURRENT_YEAR, "2022"])
def test_valid_years_accepted(year):
    assert SearchLaureatesInput(year=year).year == int(year)


@pytest.mark.parametrize("limit", [0, 21, -1, True])
def test_invalid_limits_rejected(limit):
    with pytest.raises(ValidationError):
        SearchLaureatesInput(name="Curie", limit=limit)


def test_search_requires_at_least_one_filter():
    with pytest.raises(ValidationError, match="at least one"):
        SearchLaureatesInput()
    with pytest.raises(ValidationError, match="at least one"):
        SearchLaureatesInput(limit=5)


@pytest.mark.parametrize("name", ["50%", "Cur_e", "a\\b", "x\x00y", "a"])
def test_unsafe_or_too_short_names_rejected(name):
    with pytest.raises(ValidationError):
        SearchLaureatesInput(name=name)


@pytest.mark.parametrize("name", ["Anne L’Huillier", "The 14th Dalai Lama", "Il´ja Frank", "Joliot-Curie"])
def test_real_name_characters_accepted(name):
    assert SearchLaureatesInput(name=name).name == name


def test_unknown_arguments_rejected():
    with pytest.raises(ValidationError, match="Extra inputs"):
        SearchLaureatesInput(year=2022, sql="DROP TABLE laureate")


@pytest.mark.parametrize("alias, canonical", [
    ("United States", "USA"), ("u.s.", "USA"), ("UK", "United Kingdom"), ("Netherlands", "the Netherlands"),
    ("Germany", "Germany"), ("Russian Empire", "Russian Empire"),
])
def test_country_aliases(alias, canonical):
    assert SearchLaureatesInput(birth_country=alias).birth_country == canonical


@pytest.mark.parametrize("gender, canonical", [("female", "female"), ("Women", "female"), ("MALE", "male")])
def test_gender_normalisation(gender, canonical):
    assert SearchLaureatesInput(gender=gender).gender == canonical


def test_invalid_gender_rejected():
    with pytest.raises(ValidationError, match="organizations have no gender"):
        SearchLaureatesInput(gender="organization")


@pytest.mark.parametrize("laureate_id", [0, -1, True, "abc", 3_000_000_000])
def test_details_rejects_invalid_ids(laureate_id):
    with pytest.raises(ValidationError):
        LaureateDetailsInput(laureate_id=laureate_id)


def test_details_level_normalised():
    assert LaureateDetailsInput(laureate_id=1, include_explanation_level="expert").include_explanation_level == "Expert"
    with pytest.raises(ValidationError):
        LaureateDetailsInput(laureate_id=1, include_explanation_level="Beginner")


def test_statistics_operation_allow_list():
    with pytest.raises(ValidationError):
        NobelStatisticsInput(operation="SELECT * FROM laureate")
    with pytest.raises(ValidationError):
        NobelStatisticsInput(operation="count_everything")


@pytest.mark.parametrize("kwargs, message", [
    ({"operation": "average_age_at_award"}, "requires: category"),
    ({"operation": "laureates_by_category", "category": "Physics"}, "does not support: category"),
    ({"operation": "laureates_by_affiliation_institution", "category": "Physics"}, "requires: affiliation_country"),
    ({"operation": "summary", "limit": 5}, "does not support: limit"),
    ({"operation": "summary", "affiliation_country": "USA"}, "does not support: affiliation_country"),
    ({"operation": "summary", "start_year": 2000, "end_year": 1990}, "start_year must be less"),
])
def test_statistics_per_operation_filter_rules(kwargs, message):
    with pytest.raises(ValidationError, match=message):
        NobelStatisticsInput(**kwargs)


def test_knowledge_input_bounds():
    assert KnowledgeSearchInput(query="photons").k == 5
    assert KnowledgeSearchInput(query="photons").dedupe_by_document is True
    for bad in ({"query": ""}, {"query": "x" * 501}, {"query": "ok", "k": 11}, {"query": "ok", "k": 0},
                {"query": "ok", "level": "Beginner"}, {"query": "ok", "laureate_id": -1}):
        with pytest.raises(ValidationError):
            KnowledgeSearchInput(**bad)
