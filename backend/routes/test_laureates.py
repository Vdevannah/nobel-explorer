from fastapi.testclient import TestClient

from backend.database.connection import SessionLocal
from backend.main import app
from backend.repositories import laureate_repository


client = TestClient(app)


def test_list_laureates_uses_default_pagination():
    response = client.get("/laureates")

    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"items", "total", "limit", "offset"}
    assert data["limit"] == 20
    assert data["offset"] == 0
    assert len(data["items"]) <= 20
    assert data["total"] >= len(data["items"])


def test_list_laureates_respects_limit_and_offset():
    first_response = client.get("/laureates?limit=5&offset=0")
    second_response = client.get("/laureates?limit=5&offset=5")

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    first_page = first_response.json()
    second_page = second_response.json()
    assert first_page["limit"] == 5
    assert first_page["offset"] == 0
    assert second_page["limit"] == 5
    assert second_page["offset"] == 5
    assert len(first_page["items"]) <= 5
    assert len(second_page["items"]) <= 5
    assert first_page["total"] == second_page["total"]
    assert first_page["total"] >= len(first_page["items"])

    if len(first_page["items"]) == 5 and second_page["items"]:
        first_ids = {item["laureate_id"] for item in first_page["items"]}
        second_ids = {item["laureate_id"] for item in second_page["items"]}
        assert first_ids.isdisjoint(second_ids)


def test_list_laureates_rejects_invalid_limit():
    assert client.get("/laureates?limit=0").status_code == 422
    assert client.get("/laureates?limit=101").status_code == 422


def test_list_laureates_rejects_invalid_offset():
    assert client.get("/laureates?offset=-1").status_code == 422


def test_laureate_image_provenance_fields_serialize_null():
    list_response = client.get(
        "/laureates",
        params={"search": "A. Michael Spence"}
    )

    assert list_response.status_code == 200
    summary = next(
        laureate
        for laureate in list_response.json()["items"]
        if laureate["nobel_laureate_id"] == "745"
    )
    image_fields = {
        "image_url",
        "image_source_url",
        "image_attribution",
        "image_license"
    }
    assert image_fields.issubset(summary)
    assert all(summary[field] is None for field in image_fields)

    detail_response = client.get(
        f"/laureates/{summary['laureate_id']}"
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert image_fields.issubset(detail)
    assert all(detail[field] is None for field in image_fields)


def get_laureate_id_by_nobel_id(nobel_laureate_id: str) -> int:
    db = SessionLocal()
    try:
        laureate = laureate_repository.get_by_nobel_id(
            db,
            nobel_laureate_id
        )
        assert laureate is not None
        return laureate.laureate_id
    finally:
        db.close()


def test_get_laureate_detail_includes_awards_and_affiliations():
    laureate_id = get_laureate_id_by_nobel_id("745")

    response = client.get(f"/laureates/{laureate_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["nobel_laureate_id"] == "745"
    assert data["full_name"] == "A. Michael Spence"
    assert data["awards"]

    award = data["awards"][0]
    assert award["prize"]["year"] == 2001
    assert award["prize"]["category"]["name"] == "Economic Sciences"
    assert award["motivation"]
    assert award["affiliations"]
    assert set(award["affiliations"][0]) == {
        "institution_id",
        "name",
        "city",
        "state",
        "country"
    }


def test_get_repeat_winner_includes_multiple_awards():
    laureate_id = get_laureate_id_by_nobel_id("217")

    response = client.get(f"/laureates/{laureate_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["nobel_laureate_id"] == "217"
    assert "Pauling" in data["full_name"]
    assert [award["prize"]["year"] for award in data["awards"]] == [
        1954,
        1962
    ]
    assert all(award["motivation"] for award in data["awards"])


def test_get_missing_laureate_returns_404():
    response = client.get("/laureates/999999999")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Laureate not found: 999999999"
    }


def test_get_laureate_rejects_non_integer_id():
    response = client.get("/laureates/not-an-integer")

    assert response.status_code == 422


def test_filter_laureates_by_category():
    response = client.get("/laureates?category=Chemistry&limit=100")

    assert response.status_code == 200
    data = response.json()
    assert data["items"]
    assert data["total"] >= len(data["items"])

    for laureate in data["items"]:
        detail = client.get(
            f"/laureates/{laureate['laureate_id']}"
        ).json()
        assert any(
            award["prize"]["category"]["name"] == "Chemistry"
            for award in detail["awards"]
        )


def test_filter_laureates_by_year():
    response = client.get("/laureates?year=2001&limit=100")

    assert response.status_code == 200
    data = response.json()
    assert data["items"]

    for laureate in data["items"]:
        detail = client.get(
            f"/laureates/{laureate['laureate_id']}"
        ).json()
        assert any(
            award["prize"]["year"] == 2001
            for award in detail["awards"]
        )


def test_filter_laureates_by_country():
    response = client.get("/laureates?country=USA&limit=100")

    assert response.status_code == 200
    data = response.json()
    assert data["items"]
    assert all(
        laureate["birth_country"] == "USA"
        for laureate in data["items"]
    )


def test_filter_laureates_by_gender():
    response = client.get("/laureates?gender=female&limit=100")

    assert response.status_code == 200
    data = response.json()
    assert data["items"]
    assert all(
        laureate["gender"] == "female"
        for laureate in data["items"]
    )


def test_filter_laureates_by_category_and_gender():
    response = client.get(
        "/laureates?category=Chemistry&gender=female&limit=100"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["items"]
    assert all(
        laureate["gender"] == "female"
        for laureate in data["items"]
    )

    for laureate in data["items"]:
        detail = client.get(
            f"/laureates/{laureate['laureate_id']}"
        ).json()
        assert any(
            award["prize"]["category"]["name"] == "Chemistry"
            for award in detail["awards"]
        )


def test_filtered_total_and_pagination():
    first_response = client.get(
        "/laureates?category=Chemistry&limit=5&offset=0"
    )
    second_response = client.get(
        "/laureates?category=Chemistry&limit=5&offset=5"
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    first_page = first_response.json()
    second_page = second_response.json()
    assert first_page["total"] == second_page["total"]
    assert first_page["total"] > len(first_page["items"])
    assert len(first_page["items"]) <= 5
    assert len(second_page["items"]) <= 5

    first_ids = {
        laureate["laureate_id"] for laureate in first_page["items"]
    }
    second_ids = {
        laureate["laureate_id"] for laureate in second_page["items"]
    }
    assert first_ids.isdisjoint(second_ids)


def test_filter_with_no_matches_returns_empty_page():
    response = client.get(
        "/laureates?country=DOES-NOT-EXIST&limit=5&offset=0"
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total": 0,
        "limit": 5,
        "offset": 0
    }


def test_search_laureates_by_name_and_partial_name():
    full_response = client.get("/laureates", params={"search": "Einstein"})
    partial_response = client.get("/laureates", params={"search": "Ein"})

    assert full_response.status_code == 200
    assert partial_response.status_code == 200
    full_data = full_response.json()
    partial_data = partial_response.json()
    assert full_data["items"]
    assert all(
        "einstein" in laureate["full_name"].lower()
        for laureate in full_data["items"]
    )
    assert any(
        "einstein" in laureate["full_name"].lower()
        for laureate in partial_data["items"]
    )


def test_search_is_case_insensitive_and_trims_whitespace():
    lowercase_response = client.get(
        "/laureates",
        params={"search": "einstein"}
    )
    whitespace_response = client.get(
        "/laureates",
        params={"search": " Einstein "}
    )

    assert lowercase_response.status_code == 200
    assert whitespace_response.status_code == 200
    assert lowercase_response.json() == whitespace_response.json()


def test_empty_search_is_treated_as_no_filter():
    default_response = client.get("/laureates?limit=5")
    empty_response = client.get(
        "/laureates",
        params={"search": "   ", "limit": 5}
    )

    assert empty_response.status_code == 200
    assert empty_response.json() == default_response.json()


def test_unknown_search_returns_empty_page():
    response = client.get(
        "/laureates",
        params={"search": "NAME-THAT-DOES-NOT-EXIST", "limit": 5}
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total": 0,
        "limit": 5,
        "offset": 0
    }


def test_search_combines_with_category_and_gender():
    response = client.get(
        "/laureates",
        params={
            "search": "Marie",
            "category": "Chemistry",
            "gender": "female"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["items"]
    assert all(
        "marie" in laureate["full_name"].lower()
        and laureate["gender"] == "female"
        for laureate in data["items"]
    )

    for laureate in data["items"]:
        detail = client.get(
            f"/laureates/{laureate['laureate_id']}"
        ).json()
        assert any(
            award["prize"]["category"]["name"] == "Chemistry"
            for award in detail["awards"]
        )


def test_search_pagination_and_total_are_consistent():
    first_response = client.get(
        "/laureates",
        params={"search": "a", "limit": 5, "offset": 0}
    )
    second_response = client.get(
        "/laureates",
        params={"search": "a", "limit": 5, "offset": 5}
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    first_page = first_response.json()
    second_page = second_response.json()
    assert first_page["total"] == second_page["total"]
    assert first_page["total"] > len(first_page["items"])

    first_ids = {
        laureate["laureate_id"] for laureate in first_page["items"]
    }
    second_ids = {
        laureate["laureate_id"] for laureate in second_page["items"]
    }
    assert first_ids.isdisjoint(second_ids)
