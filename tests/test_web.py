from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_home_page_renders() -> None:
    response = TestClient(app).get("/")
    assert response.status_code == 200
    assert "My Avatar Comics" in response.text

