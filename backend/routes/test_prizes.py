from fastapi.testclient import TestClient

from backend.database.connection import SessionLocal
from backend.main import app
from backend.repositories import category_repository, prize_repository


client = TestClient(app)


def get_2001_chemistry_prize_id() -> int:
    db = SessionLocal()
    try:
        category = category_repository.get_by_name(db, "Chemistry")
        assert category is not None
        prize = prize_repository.get_by_year_and_category(
            db,
            2001,
            category.category_id
        )
        assert prize is not None
        return prize.prize_id
    finally:
        db.close()


def test_list_prizes_uses_default_pagination():
    response = client.get("/prizes")

    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"items", "total", "limit", "offset"}
    assert data["limit"] == 20
    assert data["offset"] == 0
    assert len(data["items"]) <= 20
    assert data["total"] >= len(data["items"])


def test_list_prizes_respects_pagination():
    first_response = client.get("/prizes?limit=5&offset=0")
    second_response = client.get("/prizes?limit=5&offset=5")

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

    first_ids = {prize["prize_id"] for prize in first_page["items"]}
    second_ids = {prize["prize_id"] for prize in second_page["items"]}
    assert first_ids.isdisjoint(second_ids)


def test_list_prizes_rejects_invalid_pagination():
    assert client.get("/prizes?limit=0").status_code == 422
    assert client.get("/prizes?limit=101").status_code == 422
    assert client.get("/prizes?offset=-1").status_code == 422


def test_get_shared_prize_detail():
    prize_id = get_2001_chemistry_prize_id()

    response = client.get(f"/prizes/{prize_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["year"] == 2001
    assert data["category"]["name"] == "Chemistry"
    assert len(data["laureates"]) == 3
    assert {
        laureate["full_name"] for laureate in data["laureates"]
    } == {
        "K. Barry Sharpless",
        "Ryoji Noyori",
        "William S. Knowles"
    }


def test_prize_detail_preserves_award_motivations():
    prize_id = get_2001_chemistry_prize_id()

    data = client.get(f"/prizes/{prize_id}").json()
    motivations = {
        laureate["full_name"]: laureate["motivation"]
        for laureate in data["laureates"]
    }
    assert "oxidation" in motivations["K. Barry Sharpless"].lower()
    assert "hydrogenation" in motivations["Ryoji Noyori"].lower()
    assert "hydrogenation" in motivations["William S. Knowles"].lower()
    assert len(set(motivations.values())) > 1


def test_prize_detail_includes_affiliations():
    prize_id = get_2001_chemistry_prize_id()

    data = client.get(f"/prizes/{prize_id}").json()
    affiliations = [
        affiliation
        for laureate in data["laureates"]
        for affiliation in laureate["affiliations"]
    ]
    assert affiliations
    assert all(
        set(affiliation) == {
            "institution_id",
            "name",
            "city",
            "state",
            "country"
        }
        for affiliation in affiliations
    )


def test_get_missing_prize_returns_404():
    response = client.get("/prizes/999999999")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Prize not found: 999999999"
    }


def test_get_prize_rejects_non_integer_id():
    response = client.get("/prizes/not-an-integer")

    assert response.status_code == 422
