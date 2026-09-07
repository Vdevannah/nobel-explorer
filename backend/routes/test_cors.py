from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_localhost_vite_origin_is_allowed():
    response = client.get(
        "/",
        headers={"Origin": "http://localhost:5173"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "http://localhost:5173"
    )
    assert response.json() == {"message": "Nobel Explorer API is running"}


def test_loopback_vite_origin_is_allowed():
    response = client.get(
        "/",
        headers={"Origin": "http://127.0.0.1:5173"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "http://127.0.0.1:5173"
    )


def test_unapproved_origin_is_not_granted_cors_access():
    response = client.get(
        "/",
        headers={"Origin": "https://unapproved.example"},
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_allowed_get_preflight():
    response = client.options(
        "/categories",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "http://localhost:5173"
    )
    assert "GET" in response.headers["access-control-allow-methods"]
    assert "Content-Type" in response.headers["access-control-allow-headers"]
