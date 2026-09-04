from fastapi.testclient import TestClient

from backend.database.connection import SessionLocal
from backend.main import app
from backend.repositories import (
    award_affiliation_repository,
    institution_repository,
)


client = TestClient(app)


def get_stanford_institution_id() -> int:
    db = SessionLocal()
    try:
        institution = institution_repository.get_by_name(
            db,
            "Stanford University"
        )
        assert institution is not None
        return institution.institution_id
    finally:
        db.close()


def test_list_institutions_uses_default_pagination():
    response = client.get("/institutions")

    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"items", "total", "limit", "offset"}
    assert data["limit"] == 20
    assert data["offset"] == 0
    assert len(data["items"]) <= 20
    assert data["total"] >= len(data["items"])


def test_list_institutions_respects_pagination():
    first_response = client.get("/institutions?limit=5&offset=0")
    second_response = client.get("/institutions?limit=5&offset=5")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    first_page = first_response.json()
    second_page = second_response.json()
    assert first_page["limit"] == 5
    assert first_page["offset"] == 0
    assert second_page["limit"] == 5
    assert second_page["offset"] == 5
    assert first_page["total"] == second_page["total"]
    assert first_page["total"] > len(first_page["items"])

    first_ids = {
        institution["institution_id"]
        for institution in first_page["items"]
    }
    second_ids = {
        institution["institution_id"]
        for institution in second_page["items"]
    }
    assert first_ids.isdisjoint(second_ids)


def test_list_institutions_rejects_invalid_pagination():
    assert client.get("/institutions?limit=0").status_code == 422
    assert client.get("/institutions?limit=101").status_code == 422
    assert client.get("/institutions?offset=-1").status_code == 422


def test_get_institution_detail():
    institution_id = get_stanford_institution_id()

    response = client.get(f"/institutions/{institution_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Stanford University"
    assert set(data) == {
        "institution_id",
        "name",
        "city",
        "state",
        "country"
    }


def test_get_missing_and_invalid_institution():
    missing_response = client.get("/institutions/999999999")
    invalid_response = client.get("/institutions/not-an-integer")

    assert missing_response.status_code == 404
    assert missing_response.json() == {
        "detail": "Institution not found: 999999999"
    }
    assert invalid_response.status_code == 422


def test_list_institution_awards():
    institution_id = get_stanford_institution_id()

    response = client.get(f"/institutions/{institution_id}/awards")

    assert response.status_code == 200
    data = response.json()
    assert data["items"]
    assert data["total"] >= len(data["items"])

    item = data["items"][0]
    assert item["laureate_id"]
    assert item["nobel_laureate_id"]
    assert item["full_name"]
    assert item["prize_id"]
    assert item["year"]
    assert item["category"]["name"]
    assert "prize_share" in item
    assert "motivation" in item

    db = SessionLocal()
    try:
        expected_ids = {
            affiliation.award_affiliation_id
            for affiliation in (
                award_affiliation_repository.get_by_institution(
                    db,
                    institution_id
                )
            )
        }
    finally:
        db.close()

    assert {
        award["award_affiliation_id"] for award in data["items"]
    }.issubset(expected_ids)


def test_institution_awards_pagination_and_total():
    institution_id = get_stanford_institution_id()

    full_response = client.get(
        f"/institutions/{institution_id}/awards?limit=100"
    )
    first_response = client.get(
        f"/institutions/{institution_id}/awards?limit=1&offset=0"
    )

    assert full_response.status_code == 200
    assert first_response.status_code == 200
    full_data = full_response.json()
    first_page = first_response.json()
    assert first_page["limit"] == 1
    assert first_page["offset"] == 0
    assert len(first_page["items"]) <= 1
    assert first_page["total"] == full_data["total"]
    assert first_page["total"] == len(full_data["items"])


def test_missing_institution_awards_returns_404():
    response = client.get("/institutions/999999999/awards")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Institution not found: 999999999"
    }
