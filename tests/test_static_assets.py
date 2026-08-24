from fastapi.testclient import TestClient

from app.main import app


def test_favicon_is_packaged_and_served():
    response = TestClient(app).get("/static/favicon.svg")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")
