
from fastapi.testclient import TestClient

from steam_doma.main import app


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_graphql_ping():
    with TestClient(app) as client:
        response = client.post(
            "/graphql",
            json={"query": "{ ping }"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "data": {"ping": "pong"}
    }
