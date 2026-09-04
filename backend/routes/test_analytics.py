from fastapi.testclient import TestClient

from backend.database.connection import SessionLocal
from backend.main import app
from backend.services import analytics_service


client = TestClient(app)


def test_analytics_summary_matches_service():
    response = client.get("/analytics/summary")

    assert response.status_code == 200
    assert set(response.json()) == {"total_laureates", "total_prizes"}

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


def test_analytics_empty_list_result():
    response = client.get(
        "/analytics/gender",
        params={"category": "CATEGORY-THAT-DOES-NOT-EXIST"}
    )

    assert response.status_code == 200
    assert response.json() == []
