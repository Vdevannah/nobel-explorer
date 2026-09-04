from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_list_categories():
    response = client.get("/categories")

    assert response.status_code == 200

    categories = response.json()

    assert isinstance(categories, list)
    assert any(category["name"] == "Chemistry" for category in categories)


def test_get_existing_category():
    categories_response = client.get("/categories")
    categories = categories_response.json()
    existing_category = categories[0]

    response = client.get(
        f"/categories/{existing_category['category_id']}"
    )

    assert response.status_code == 200
    assert response.json() == existing_category
    assert set(response.json()) == {
        "category_id",
        "name",
        "description"
    }


def test_get_missing_category():
    response = client.get("/categories/999999")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Category not found: 999999"
    }


def test_get_category_with_non_integer_id():
    response = client.get("/categories/abc")

    assert response.status_code == 422
