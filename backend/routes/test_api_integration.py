from fastapi.testclient import TestClient

from backend.database.connection import SessionLocal
from backend.main import app
from backend.repositories import (
    category_repository,
    laureate_repository,
    prize_repository,
)


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


def get_laureate_by_nobel_id(nobel_laureate_id: str) -> dict:
    db = SessionLocal()
    try:
        laureate = laureate_repository.get_by_nobel_id(
            db,
            nobel_laureate_id
        )
        assert laureate is not None
        return {
            "laureate_id": laureate.laureate_id,
            "nobel_laureate_id": laureate.nobel_laureate_id,
            "birth_country": laureate.birth_country,
        }
    finally:
        db.close()


def test_category_to_laureates_journey():
    categories_response = client.get("/categories")

    assert categories_response.status_code == 200
    category = next(
        item
        for item in categories_response.json()
        if item["name"] == "Chemistry"
    )
    laureates_response = client.get(
        "/laureates",
        params={"category": category["name"], "limit": 5}
    )

    assert laureates_response.status_code == 200
    data = laureates_response.json()
    assert set(data) == {"items", "total", "limit", "offset"}
    assert data["total"] >= 0

    for laureate in data["items"]:
        detail = client.get(
            f"/laureates/{laureate['laureate_id']}"
        ).json()
        assert any(
            award["prize"]["category"]["name"] == category["name"]
            for award in detail["awards"]
        )


def test_laureate_list_detail_and_prize_round_trip():
    list_response = client.get("/laureates?limit=5&offset=0")

    assert list_response.status_code == 200
    summary = list_response.json()["items"][0]
    detail_response = client.get(
        f"/laureates/{summary['laureate_id']}"
    )

    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["laureate_id"] == summary["laureate_id"]
    assert detail["nobel_laureate_id"] == summary["nobel_laureate_id"]
    assert detail["full_name"] == summary["full_name"]
    assert detail["awards"]

    award = detail["awards"][0]
    prize_response = client.get(f"/prizes/{award['prize']['prize_id']}")
    assert prize_response.status_code == 200
    prize = prize_response.json()
    assert prize["prize_id"] == award["prize"]["prize_id"]
    assert prize["year"] == award["prize"]["year"]
    assert prize["category"] == award["prize"]["category"]
    assert any(
        laureate["laureate_id"] == detail["laureate_id"]
        for laureate in prize["laureates"]
    )


def test_prize_to_institution_journey():
    prize_id = get_2001_chemistry_prize_id()
    prize = client.get(f"/prizes/{prize_id}").json()
    laureate = next(
        item for item in prize["laureates"]
        if item["affiliations"]
    )
    affiliation = laureate["affiliations"][0]

    institution_response = client.get(
        f"/institutions/{affiliation['institution_id']}"
    )
    assert institution_response.status_code == 200
    assert institution_response.json() == affiliation

    awards_response = client.get(
        f"/institutions/{affiliation['institution_id']}/awards",
        params={"limit": 100}
    )
    assert awards_response.status_code == 200
    assert any(
        item["laureate_id"] == laureate["laureate_id"]
        and item["prize_id"] == prize_id
        for item in awards_response.json()["items"]
    )


def test_filter_search_and_pagination_journey():
    search_response = client.get(
        "/laureates",
        params={"search": "Marie", "limit": 100}
    )
    candidate = next(
        laureate
        for laureate in search_response.json()["items"]
        if laureate["gender"] == "female"
    )
    detail = client.get(
        f"/laureates/{candidate['laureate_id']}"
    ).json()
    chemistry_award = next(
        award for award in detail["awards"]
        if award["prize"]["category"]["name"] == "Chemistry"
    )

    params = {
        "search": "Curie",
        "category": chemistry_award["prize"]["category"]["name"],
        "gender": candidate["gender"],
        "limit": 5,
        "offset": 0,
    }
    if candidate["birth_country"] is not None:
        params["country"] = candidate["birth_country"]

    response = client.get("/laureates", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= len(data["items"])
    assert len(data["items"]) <= 5
    assert any(
        item["laureate_id"] == candidate["laureate_id"]
        for item in data["items"]
    )
    assert all(
        "curie" in item["full_name"].lower()
        and item["gender"] == candidate["gender"]
        for item in data["items"]
    )


def test_analytics_summary_matches_collection_totals():
    summary_response = client.get("/analytics/summary")
    laureates_response = client.get("/laureates?limit=1")
    prizes_response = client.get("/prizes?limit=1")

    assert summary_response.status_code == 200
    assert laureates_response.status_code == 200
    assert prizes_response.status_code == 200
    summary = summary_response.json()
    assert summary["total_laureates"] == laureates_response.json()["total"]
    assert summary["total_prizes"] == prizes_response.json()["total"]


def test_birthplace_and_award_affiliation_remain_separate():
    marie = get_laureate_by_nobel_id("6")
    detail = client.get(f"/laureates/{marie['laureate_id']}").json()
    award_with_affiliation = next(
        award for award in detail["awards"]
        if award["affiliations"]
    )
    affiliation = award_with_affiliation["affiliations"][0]
    institution = client.get(
        f"/institutions/{affiliation['institution_id']}"
    ).json()

    assert detail["birth_country"] == marie["birth_country"]
    assert institution["country"] == affiliation["country"]
    assert "birth_country" in detail
    assert "country" in institution
    assert "birth_country" not in institution


def test_repeat_winner_round_trip():
    pauling = get_laureate_by_nobel_id("217")
    detail = client.get(f"/laureates/{pauling['laureate_id']}").json()

    assert len(detail["awards"]) >= 2
    for award in detail["awards"]:
        prize = client.get(f"/prizes/{award['prize']['prize_id']}").json()
        assert any(
            laureate["laureate_id"] == pauling["laureate_id"]
            for laureate in prize["laureates"]
        )


def test_shared_prize_inverse_relationships():
    prize_id = get_2001_chemistry_prize_id()
    prize = client.get(f"/prizes/{prize_id}").json()

    assert len(prize["laureates"]) > 1
    assert all("prize_share" in laureate for laureate in prize["laureates"])
    assert all("motivation" in laureate for laureate in prize["laureates"])

    for laureate in prize["laureates"]:
        detail = client.get(
            f"/laureates/{laureate['laureate_id']}"
        ).json()
        matching_award = next(
            award for award in detail["awards"]
            if award["prize"]["prize_id"] == prize_id
        )
        assert matching_award["prize_share"] == laureate["prize_share"]
        assert matching_award["motivation"] == laureate["motivation"]


def test_api_error_contract_smoke_journey():
    assert client.get("/categories").status_code == 200
    assert client.get("/prizes/999999999").status_code == 404
    assert client.get("/laureates?limit=0").status_code == 422

    empty_response = client.get(
        "/laureates",
        params={"search": "NO-SUCH-LAUREATE-IN-NOBEL-EXPLORER"}
    )
    assert empty_response.status_code == 200
    assert empty_response.json()["items"] == []
    assert empty_response.json()["total"] == 0


def test_openapi_contains_all_phase_seven_paths():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    expected_paths = {
        "/categories",
        "/categories/{category_id}",
        "/laureates",
        "/laureates/{laureate_id}",
        "/prizes",
        "/prizes/{prize_id}",
        "/institutions",
        "/institutions/{institution_id}",
        "/institutions/{institution_id}/awards",
        "/analytics/summary",
        "/analytics/laureates-by-category",
        "/analytics/birth-countries",
        "/analytics/us-birth-states",
        "/analytics/institutions",
        "/analytics/gender",
        "/analytics/decades",
        "/analytics/average-age",
    }
    assert expected_paths.issubset(paths)


def test_openapi_documents_api_metadata_and_parameters():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Nobel Explorer API"
    assert schema["info"]["version"]

    documented_tags = {
        tag
        for path in schema["paths"].values()
        for operation in path.values()
        for tag in operation.get("tags", [])
    }
    assert {
        "Health",
        "Categories",
        "Laureates",
        "Prizes",
        "Institutions",
        "Analytics",
    }.issubset(documented_tags)

    major_operations = [
        schema["paths"]["/categories"]["get"],
        schema["paths"]["/laureates"]["get"],
        schema["paths"]["/prizes"]["get"],
        schema["paths"]["/institutions"]["get"],
        schema["paths"]["/analytics/summary"]["get"],
    ]
    assert all(operation.get("summary") for operation in major_operations)

    laureate_parameters = {
        parameter["name"]: parameter
        for parameter in schema["paths"]["/laureates"]["get"]["parameters"]
    }
    assert {
        "limit",
        "offset",
        "category",
        "year",
        "country",
        "gender",
        "search",
    }.issubset(laureate_parameters)
    assert all(
        laureate_parameters[name].get("description")
        for name in laureate_parameters
    )

    birth_country_parameters = schema["paths"][
        "/analytics/birth-countries"
    ]["get"]["parameters"]
    institution_parameters = schema["paths"][
        "/analytics/institutions"
    ]["get"]["parameters"]
    assert all(parameter["required"] for parameter in birth_country_parameters)
    assert all(parameter["required"] for parameter in institution_parameters)
