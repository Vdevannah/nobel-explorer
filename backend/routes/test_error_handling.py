from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_global_not_found_handler_across_resources():
    cases = [
        ("/categories/999999999", "Category not found: 999999999"),
        ("/laureates/999999999", "Laureate not found: 999999999"),
        ("/prizes/999999999", "Prize not found: 999999999"),
        ("/institutions/999999999", "Institution not found: 999999999"),
        (
            "/institutions/999999999/awards",
            "Institution not found: 999999999"
        ),
    ]

    for path, expected_detail in cases:
        response = client.get(path)
        assert response.status_code == 404
        assert response.json() == {"detail": expected_detail}


def test_fastapi_validation_status_codes_are_preserved():
    paths = [
        "/categories/not-an-integer",
        "/laureates?limit=0",
        "/prizes?offset=-1",
        "/analytics/birth-countries",
        "/analytics/institutions?category=Chemistry",
    ]

    for path in paths:
        assert client.get(path).status_code == 422


def test_valid_empty_results_return_200():
    laureates_response = client.get(
        "/laureates",
        params={"search": "VALUE-THAT-DOES-NOT-EXIST"}
    )
    analytics_response = client.get(
        "/analytics/birth-countries",
        params={"category": "CATEGORY-THAT-DOES-NOT-EXIST"}
    )

    assert laureates_response.status_code == 200
    assert laureates_response.json()["items"] == []
    assert laureates_response.json()["total"] == 0
    assert analytics_response.status_code == 200
    assert analytics_response.json() == []
