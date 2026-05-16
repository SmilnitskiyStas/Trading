from fastapi.testclient import TestClient

from app.main import app


def test_root_endpoint_exposes_app_metadata():
    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Crypto Trading Research Bot"
    assert body["docs_url"] == "/docs"

