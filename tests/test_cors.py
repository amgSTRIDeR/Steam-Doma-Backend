from fastapi.testclient import TestClient

from steam_doma.main import (
    CORS_ORIGINS,
    app,
    parse_cors_origins,
)


def test_parse_cors_origins() -> None:
    result = parse_cors_origins(" http://localhost:5173/, http://127.0.0.1:5173/ ")

    assert result == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def test_cors_preflight_allowed() -> None:
    origin = CORS_ORIGINS[0]
    client = TestClient(app)

    response = client.options(
        "/graphql",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": ("content-type,authorization"),
        },
    )

    assert response.status_code == 200

    assert response.headers["access-control-allow-origin"] == origin

    assert "POST" in response.headers["access-control-allow-methods"]

    allowed_headers = response.headers["access-control-allow-headers"].lower()

    assert "content-type" in allowed_headers
    assert "authorization" in allowed_headers


def test_cors_preflight_rejects_unknown_origin() -> None:
    client = TestClient(app)

    response = client.options(
        "/graphql",
        headers={
            "Origin": "https://untrusted.example.invalid",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 400

    assert "access-control-allow-origin" not in response.headers


def test_cors_headers_on_allowed_get() -> None:
    origin = CORS_ORIGINS[0]
    client = TestClient(app)

    response = client.get(
        "/openapi.json",
        headers={"Origin": origin},
    )

    assert response.status_code == 200

    assert response.headers["access-control-allow-origin"] == origin


def test_cors_headers_not_added_for_unknown_origin() -> None:
    client = TestClient(app)

    response = client.get(
        "/openapi.json",
        headers={"Origin": "https://untrusted.example.invalid"},
    )

    assert response.status_code == 200

    assert "access-control-allow-origin" not in response.headers
