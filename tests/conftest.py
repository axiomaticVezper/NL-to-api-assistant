import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Every test gets its own empty database file, so tests never interfere."""
    monkeypatch.setenv("APP_DB_PATH", str(tmp_path / "test.db"))


@pytest.fixture
def client():
    return TestClient(app)


def login(client, username):
    r = client.post("/auth/login", data={"username": username, "password": "password123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def as_user(client):
    """Usage: headers = as_user("bob_agent")"""
    return lambda username: login(client, username)