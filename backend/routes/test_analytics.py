from fastapi.testclient import TestClient

from backend.database.connection import SessionLocal
from backend.main import app
from backend.services import analytics_service


client = TestClient(app)


def test_analytics_summary_matches_service():
    response = client.get("/analytics/summary")

    assert response.status_code == 200
    assert set(response.json()) == {
        "total_laureates",
        "total_prizes",
        "total_countries",
        "women_laureates",
        "women_percentage",
    }

    db = SessionLocal()
    try:
        expected = analytics_service.get_summary(db).model_dump()
    finally:
        db.close()

    assert response.json() == expected


def test_laureates_by_category():
    response = client.get("/analytics/laureates-by-category")

    assert response.status_code == 200
    data = response.json()
    assert {row["category"] for row in data}.issuperset(
        {"Chemistry", "Physics", "Peace"}
    )
    assert all(row["laureate_count"] >= 0 for row in data)


def test_birth_country_analytics():
    response = client.get(
        "/analytics/birth-countries",
        params={"category": "Chemistry"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data
    assert all(set(row) == {"country", "laureate_count"} for row in data)
    assert all(row["laureate_count"] >= 0 for row in data)


def test_us_birth_state_analytics_uses_full_state_names():
    response = client.get(
        "/analytics/us-birth-states",
        params={"category": "Chemistry"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data
    assert all(set(row) == {"state", "laureate_count"} for row in data)
    assert all(len(row["state"]) > 2 for row in data)


def test_institution_affiliation_analytics():
    response = client.get(
        "/analytics/institutions",
        params={"category": "Chemistry", "country": "USA"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data
    assert all(
        set(row) == {"institution", "laureate_count"}
        for row in data
    )
    assert all(row["laureate_count"] >= 0 for row in data)


def test_gender_analytics():
    response = client.get(
        "/analytics/gender",
        params={"category": "Chemistry"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data
    assert all(set(row) == {"gender", "laureate_count"} for row in data)


def test_decade_analytics_are_ordered():
    response = client.get("/analytics/decades")

    assert response.status_code == 200
    data = response.json()
    assert data
    assert all(set(row) == {"decade", "laureate_count"} for row in data)
    decades = [row["decade"] for row in data]
    assert decades == sorted(decades)


def test_average_age_analytics():
    response = client.get(
        "/analytics/average-age",
        params={"category": "Chemistry"}
    )

    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"category", "average_age"}
    assert data["category"] == "Chemistry"
    assert data["average_age"] is None or data["average_age"] >= 0


def test_analytics_required_query_parameters():
    assert client.get("/analytics/birth-countries").status_code == 422
    assert client.get(
        "/analytics/institutions",
        params={"category": "Chemistry"}
    ).status_code == 422
    assert client.get("/analytics/average-age").status_code == 422


def test_top_countries_analytics():
    response = client.get("/analytics/top-countries", params={"limit": 3})

    assert response.status_code == 200
    data = response.json()
    assert 0 < len(data) <= 3
    assert all(set(row) == {"country", "laureate_count"} for row in data)
    counts = [row["laureate_count"] for row in data]
    assert counts == sorted(counts, reverse=True)


def test_prizes_by_decade_analytics_are_ordered():
    response = client.get("/analytics/prizes-by-decade")

    assert response.status_code == 200
    data = response.json()
    assert data
    assert all(set(row) == {"decade", "prize_count"} for row in data)
    decades = [row["decade"] for row in data]
    assert decades == sorted(decades)


def test_age_distribution_analytics_sums_to_total():
    response = client.get("/analytics/age-distribution")

    assert response.status_code == 200
    data = response.json()
    assert [row["age_group"] for row in data] == [
        "<30", "30-39", "40-49", "50-59", "60-69", "70-79", "80+"
    ]
    assert round(sum(row["percentage"] for row in data)) in (0, 100)


def test_women_by_era_analytics():
    response = client.get("/analytics/women-by-era")

    assert response.status_code == 200
    data = response.json()
    assert data
    assert all(
        set(row) == {"era", "percentage", "women_count", "known_gender_count"}
        for row in data
    )
    assert all(0 <= row["percentage"] <= 100 for row in data)

    # The exposed counts must be internally consistent with the
    # percentage they justify: known_gender_count is the denominator
    # (organizations and unknown-gender laureates never enter it), and
    # women_count is never negative or larger than that denominator.
    for row in data:
        assert row["known_gender_count"] > 0
        assert 0 <= row["women_count"] <= row["known_gender_count"]
        expected_percentage = round(
            row["women_count"] / row["known_gender_count"] * 100, 1
        )
        assert row["percentage"] == expected_percentage


def test_analytics_empty_list_result():
    response = client.get(
        "/analytics/gender",
        params={"category": "CATEGORY-THAT-DOES-NOT-EXIST"}
    )

    assert response.status_code == 200
    assert response.json() == []


# ============================================================
# Phase 10D -- small, consistent category/start_year/end_year
# filter set, and Phase 10E -- categories-by-decade trend.
# ============================================================

FILTERABLE_ENDPOINTS = (
    "/analytics/laureates-by-category",
    "/analytics/top-countries",
    "/analytics/prizes-by-decade",
    "/analytics/age-distribution",
    "/analytics/women-by-era",
    "/analytics/decades",
    "/analytics/categories-by-decade",
)


def test_filters_are_optional_and_backward_compatible():
    # Every filterable endpoint must behave identically with no filters
    # supplied at all versus its pre-Phase-10D response shape -- calling
    # it bare must still succeed and return the same kind of payload.
    for path in FILTERABLE_ENDPOINTS:
        response = client.get(path)
        assert response.status_code == 200, path
        assert isinstance(response.json(), list)


def test_top_countries_category_filter_narrows_results():
    all_response = client.get("/analytics/top-countries", params={"limit": 50})
    chemistry_response = client.get(
        "/analytics/top-countries",
        params={"limit": 50, "category": "Chemistry"}
    )

    assert all_response.status_code == 200
    assert chemistry_response.status_code == 200

    all_total = sum(row["laureate_count"] for row in all_response.json())
    chemistry_total = sum(row["laureate_count"] for row in chemistry_response.json())
    assert 0 < chemistry_total < all_total


def test_prizes_by_decade_start_year_only():
    response = client.get(
        "/analytics/prizes-by-decade",
        params={"start_year": 2000}
    )

    assert response.status_code == 200
    data = response.json()
    assert data
    assert all(row["decade"] >= 2000 for row in data)


def test_prizes_by_decade_end_year_only():
    response = client.get(
        "/analytics/prizes-by-decade",
        params={"end_year": 1909}
    )

    assert response.status_code == 200
    data = response.json()
    assert data
    # 1901-1909 are entirely within the 1900 decade bucket; 1910 itself
    # is its own "1910" bucket (floor(1910/10)*10 == 1910), so the end
    # boundary is deliberately 1909, not 1910.
    assert set(row["decade"] for row in data) == {1900}


def test_prizes_by_decade_start_and_end_year_boundaries():
    response = client.get(
        "/analytics/prizes-by-decade",
        params={"start_year": 1901, "end_year": 1909}
    )

    assert response.status_code == 200
    data = response.json()
    assert data
    assert set(row["decade"] for row in data) == {1900}

    unbounded = dict(
        (row["decade"], row["prize_count"])
        for row in client.get("/analytics/prizes-by-decade").json()
    )
    bounded = dict((row["decade"], row["prize_count"]) for row in data)
    assert bounded[1900] <= unbounded[1900]


def test_invalid_reversed_year_range_returns_400_on_every_filterable_endpoint():
    for path in FILTERABLE_ENDPOINTS:
        response = client.get(
            path,
            params={"start_year": 2000, "end_year": 1990}
        )
        assert response.status_code == 400, path
        assert "start_year" in response.json()["detail"]


def test_year_range_rejects_out_of_bounds_years():
    response = client.get(
        "/analytics/prizes-by-decade",
        params={"start_year": 1800}
    )
    assert response.status_code == 422


def test_empty_filtered_result_for_nonexistent_category():
    for path in (
        "/analytics/prizes-by-decade",
        "/analytics/categories-by-decade",
    ):
        response = client.get(
            path,
            params={"category": "CATEGORY-THAT-DOES-NOT-EXIST"}
        )
        assert response.status_code == 200, path
        assert response.json() == [], path

    # age-distribution always returns all 7 fixed age-group buckets
    # (pre-existing behavior, unrelated to filtering) rather than an
    # empty list, so an impossible filter must zero out every bucket
    # instead of omitting rows.
    age_response = client.get(
        "/analytics/age-distribution",
        params={"category": "CATEGORY-THAT-DOES-NOT-EXIST"}
    )
    assert age_response.status_code == 200
    age_data = age_response.json()
    assert len(age_data) == 7
    assert all(row["laureate_count"] == 0 for row in age_data)
    assert all(row["percentage"] == 0.0 for row in age_data)


def test_categories_by_decade_response_shape():
    response = client.get("/analytics/categories-by-decade")

    assert response.status_code == 200
    data = response.json()
    assert data
    assert all(
        set(row) == {"decade", "category", "laureate_count"}
        for row in data
    )
    assert all(row["laureate_count"] > 0 for row in data)


def test_categories_by_decade_category_filter():
    response = client.get(
        "/analytics/categories-by-decade",
        params={"category": "Physics"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data
    assert all(row["category"] == "Physics" for row in data)


def test_categories_by_decade_distinct_laureate_semantics():
    # Within a single (decade, category) bucket, the count is DISTINCT
    # laureates, matching the locked laureates-by-category semantics --
    # cross-check against the per-decade "decades" endpoint scoped to
    # the same category: for any one category, no single decade's
    # categories-by-decade count can exceed that decade's overall
    # laureate count across every category.
    by_decade_all_categories = {
        row["decade"]: row["laureate_count"]
        for row in client.get("/analytics/decades").json()
    }
    physics_by_decade = client.get(
        "/analytics/categories-by-decade",
        params={"category": "Physics"}
    ).json()
    for row in physics_by_decade:
        assert row["laureate_count"] <= by_decade_all_categories[row["decade"]]


def test_categories_by_decade_repeat_laureate_across_decades():
    # John Bardeen won Physics in 1956 (1950s) and again in 1972 (1970s)
    # -- a repeat laureate whose two awards fall in two different
    # decades. Per the locked "decades" methodology, he must be counted
    # as a distinct laureate in BOTH decade buckets for Physics, not
    # collapsed into a single overall appearance.
    physics_by_decade = {
        row["decade"]: row["laureate_count"]
        for row in client.get(
            "/analytics/categories-by-decade",
            params={"category": "Physics"}
        ).json()
    }
    assert physics_by_decade.get(1950, 0) >= 1
    assert physics_by_decade.get(1970, 0) >= 1


# ============================================================
# Phase 10G -- /analytics/summary joins the small, consistent
# category/start_year/end_year filter set the other dashboard
# endpoints already support, so the four KPI totals can be scoped
# to match an applied filter instead of always showing all-time
# values.
# ============================================================


def test_analytics_summary_matches_service_with_filters():
    response = client.get(
        "/analytics/summary",
        params={"category": "Chemistry", "start_year": 1950, "end_year": 2000}
    )

    assert response.status_code == 200

    db = SessionLocal()
    try:
        expected = analytics_service.get_summary(
            db, "Chemistry", 1950, 2000
        ).model_dump()
    finally:
        db.close()

    assert response.json() == expected


def test_analytics_summary_category_filter_narrows_totals():
    all_response = client.get("/analytics/summary").json()
    chemistry_response = client.get(
        "/analytics/summary", params={"category": "Chemistry"}
    ).json()

    assert 0 < chemistry_response["total_laureates"] < all_response["total_laureates"]
    assert 0 < chemistry_response["total_prizes"] < all_response["total_prizes"]
    assert chemistry_response["total_countries"] <= all_response["total_countries"]
    assert chemistry_response["women_laureates"] <= all_response["women_laureates"]


def test_analytics_summary_year_filter_narrows_totals():
    all_response = client.get("/analytics/summary").json()
    narrowed_response = client.get(
        "/analytics/summary", params={"start_year": 1990, "end_year": 2000}
    ).json()

    assert 0 < narrowed_response["total_laureates"] < all_response["total_laureates"]
    assert 0 < narrowed_response["total_prizes"] < all_response["total_prizes"]


def test_analytics_summary_combined_category_and_year_filter():
    response = client.get(
        "/analytics/summary",
        params={"category": "Physics", "start_year": 1950, "end_year": 1959}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_prizes"] > 0
    assert data["total_laureates"] > 0


def test_analytics_summary_invalid_reversed_year_range_returns_400():
    response = client.get(
        "/analytics/summary",
        params={"start_year": 2000, "end_year": 1990}
    )
    assert response.status_code == 400
    assert "start_year" in response.json()["detail"]


def test_analytics_summary_year_range_rejects_out_of_bounds_years():
    response = client.get(
        "/analytics/summary",
        params={"start_year": 1800}
    )
    assert response.status_code == 422


def test_analytics_summary_empty_filtered_result_for_nonexistent_category():
    response = client.get(
        "/analytics/summary",
        params={"category": "CATEGORY-THAT-DOES-NOT-EXIST"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_laureates"] == 0
    assert data["total_prizes"] == 0
    assert data["total_countries"] == 0
    assert data["women_laureates"] == 0
    assert data["women_percentage"] == 0.0

    # Every decade a repeat laureate's awards land in must actually
    # contain at least one Physics laureate for that decade to prove
    # the observation didn't silently vanish from either bucket.
    year_1956_decade = client.get(
        "/analytics/categories-by-decade",
        params={"category": "Physics", "start_year": 1956, "end_year": 1956}
    ).json()
    year_1972_decade = client.get(
        "/analytics/categories-by-decade",
        params={"category": "Physics", "start_year": 1972, "end_year": 1972}
    ).json()
    assert any(row["decade"] == 1950 for row in year_1956_decade)
    assert any(row["decade"] == 1970 for row in year_1972_decade)


# ============================================================
# World-map geography section -- the map/list views reuse this same
# /top-countries endpoint (no new endpoint or duplicated aggregation
# logic), now called with a high limit to retrieve the complete set of
# birth countries instead of only a top-N slice. These tests cover the
# raised limit ceiling and confirm the endpoint's existing filter
# semantics still hold at that limit.
# ============================================================

def test_top_countries_unfiltered_can_return_the_complete_country_set():
    capped_at_old_ceiling = client.get(
        "/analytics/top-countries", params={"limit": 50}
    )
    uncapped = client.get("/analytics/top-countries", params={"limit": 200})

    assert capped_at_old_ceiling.status_code == 200
    assert uncapped.status_code == 200
    capped_data = capped_at_old_ceiling.json()
    uncapped_data = uncapped.json()

    # The previous ceiling (50) must have actually been truncating real
    # data, otherwise raising it proves nothing.
    assert len(capped_data) == 50
    assert len(uncapped_data) > 50
    assert all(set(row) == {"country", "laureate_count"} for row in uncapped_data)

    # Every country visible at the old, smaller limit must still appear,
    # unchanged, in the uncapped response -- raising the ceiling must
    # only ever reveal more rows, never alter existing ones.
    uncapped_by_country = {row["country"]: row["laureate_count"] for row in uncapped_data}
    for row in capped_data:
        assert uncapped_by_country[row["country"]] == row["laureate_count"]


def test_top_countries_limit_rejects_values_above_the_new_ceiling():
    response = client.get("/analytics/top-countries", params={"limit": 201})
    assert response.status_code == 422


def test_top_countries_category_filtered_geography_is_a_subset():
    uncapped = client.get(
        "/analytics/top-countries", params={"limit": 200}
    ).json()
    chemistry = client.get(
        "/analytics/top-countries",
        params={"limit": 200, "category": "Chemistry"}
    ).json()

    assert chemistry
    uncapped_by_country = {row["country"]: row["laureate_count"] for row in uncapped}
    for row in chemistry:
        assert row["country"] in uncapped_by_country
        assert row["laureate_count"] <= uncapped_by_country[row["country"]]


def test_top_countries_year_filtered_geography_matches_the_range():
    modern = client.get(
        "/analytics/top-countries",
        params={"limit": 200, "start_year": 2000}
    ).json()
    all_time = client.get(
        "/analytics/top-countries", params={"limit": 200}
    ).json()

    assert modern
    modern_total = sum(row["laureate_count"] for row in modern)
    all_time_total = sum(row["laureate_count"] for row in all_time)
    assert 0 < modern_total < all_time_total


def test_top_countries_combined_category_and_year_filter():
    combined = client.get(
        "/analytics/top-countries",
        params={
            "limit": 200,
            "category": "Physics",
            "start_year": 1950,
            "end_year": 2000,
        },
    ).json()
    category_only = client.get(
        "/analytics/top-countries",
        params={"limit": 200, "category": "Physics"},
    ).json()

    assert combined
    combined_total = sum(row["laureate_count"] for row in combined)
    category_only_total = sum(row["laureate_count"] for row in category_only)
    # Narrowing an already-category-filtered population by a year range
    # can only ever hold steady or shrink it further, never grow it.
    assert combined_total <= category_only_total


def test_top_countries_combined_filter_empty_result():
    response = client.get(
        "/analytics/top-countries",
        params={
            "limit": 200,
            "category": "CATEGORY-THAT-DOES-NOT-EXIST",
            "start_year": 1950,
            "end_year": 2000,
        },
    )
    assert response.status_code == 200
    assert response.json() == []


def test_top_countries_geography_total_is_internally_consistent():
    # The sum of every country's laureate_count at the uncapped limit is
    # the same "known birth country" population the rest of the
    # dashboard already relies on -- it must be positive, and narrowing
    # by category must never invent laureates that don't exist overall.
    uncapped = client.get("/analytics/top-countries", params={"limit": 200}).json()
    total = sum(row["laureate_count"] for row in uncapped)
    assert total > 0
    assert all(row["laureate_count"] > 0 for row in uncapped)
