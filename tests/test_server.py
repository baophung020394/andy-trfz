from fastapi.testclient import TestClient

from src.server import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_last_run_without_history():
    response = client.get("/last-run")
    assert response.status_code == 200
    assert "status" in response.json()


def test_run_requires_secret(monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "s3cret")
    response = client.get("/run")
    assert response.status_code == 401
