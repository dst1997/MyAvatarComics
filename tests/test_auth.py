from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.auth import SESSION_COOKIE, UserStore
from app.storage import ProjectStorage


SPEC = {
    "consent_given": True,
    "recipient_name": "Priya",
    "occasion": "Graduation",
    "event_details": "She graduated with honors after months of hard work.",
}


@pytest.fixture()
def client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setattr(main, "storage", ProjectStorage(tmp_path / "projects"))
    monkeypatch.setattr(main, "user_store", UserStore(tmp_path / "users.json"))
    return TestClient(main.app)


def register(client: TestClient, email: str = "alice@example.com", password: str = "secret-pass-1"):
    return client.post("/api/auth/register", json={"email": email, "password": password})


def test_register_sets_session(client: TestClient) -> None:
    response = register(client)
    assert response.status_code == 200
    assert response.json() == {"email": "alice@example.com"}
    assert SESSION_COOKIE in response.cookies
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json() == {"email": "alice@example.com"}


def test_register_rejects_duplicate_email(client: TestClient) -> None:
    assert register(client).status_code == 200
    duplicate = register(client, password="another-pass-2")
    assert duplicate.status_code == 400
    assert "already exists" in duplicate.json()["detail"]


def test_register_rejects_short_password(client: TestClient) -> None:
    response = register(client, password="short")
    assert response.status_code == 400


def test_register_rejects_invalid_email(client: TestClient) -> None:
    response = register(client, email="not-an-email")
    assert response.status_code == 400


def test_login_logout_cycle(client: TestClient) -> None:
    register(client)
    client.cookies.clear()

    wrong = client.post("/api/auth/login", json={"email": "alice@example.com", "password": "wrong-pass-1"})
    assert wrong.status_code == 401

    login = client.post("/api/auth/login", json={"email": "Alice@Example.com", "password": "secret-pass-1"})
    assert login.status_code == 200
    assert client.get("/api/auth/me").status_code == 200

    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401


def test_tampered_session_cookie_rejected(client: TestClient) -> None:
    client.cookies.set(SESSION_COOKIE, "YWxpY2U.9999999999.deadbeef")
    assert client.get("/api/auth/me").status_code == 401


def test_project_api_requires_auth(client: TestClient) -> None:
    assert client.post("/api/projects", json=SPEC).status_code == 401
    assert client.get("/api/projects/abcdef123456/status").status_code == 401
    assert client.delete("/api/projects/abcdef123456").status_code == 401


def test_home_redirects_anonymous_to_login(client: TestClient) -> None:
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_login_page_redirects_signed_in_user(client: TestClient) -> None:
    register(client)
    response = client.get("/login", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_projects_are_scoped_to_owner(client: TestClient) -> None:
    register(client)
    project_id = client.post("/api/projects", json=SPEC).json()["project_id"]
    assert client.get(f"/api/projects/{project_id}/status").status_code == 200

    other = TestClient(main.app)
    register(other, email="bob@example.com", password="another-pass-2")
    assert other.get(f"/api/projects/{project_id}/status").status_code == 404
    assert other.delete(f"/api/projects/{project_id}").status_code == 404

    assert client.get(f"/api/projects/{project_id}/status").status_code == 200
