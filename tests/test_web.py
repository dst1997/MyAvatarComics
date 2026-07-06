from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.auth import UserStore
from app.storage import ProjectStorage


@pytest.fixture()
def client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setattr(main, "storage", ProjectStorage(tmp_path / "projects"))
    monkeypatch.setattr(main, "user_store", UserStore(tmp_path / "users.json"))
    return TestClient(main.app)


def test_login_page_renders(client: TestClient) -> None:
    response = client.get("/login")
    assert response.status_code == 200
    assert "My Avatar Comics" in response.text


def test_home_page_renders_for_signed_in_user(client: TestClient) -> None:
    client.post("/api/auth/register", json={"email": "alice@example.com", "password": "secret-pass-1"})
    response = client.get("/")
    assert response.status_code == 200
    assert "My Avatar Comics" in response.text
    assert "alice@example.com" in response.text
