from fastapi.testclient import TestClient

from app.main import create_app


def test_health_route_exists():
    client = TestClient(create_app())
    response = client.get("/healthz")
    assert response.status_code == 200

