from __future__ import annotations

import logging
import threading
import time

import pytest
from fastapi.testclient import TestClient

from src.pipeline import RunResult
from src.progress import get_controller
from src.server import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolate_run_state(tmp_path, monkeypatch):
    monkeypatch.setenv("LAST_RUN_PATH", str(tmp_path / "last_run.json"))
    monkeypatch.setenv("CRON_SECRET", "")
    controller = get_controller()
    controller.reset()
    controller.set_persist_path(tmp_path / "last_run.json")
    yield
    controller.reset()


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_last_run_without_history():
    response = client.get("/last-run")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "none"
    assert payload["running"] is False
    assert payload["logs"] == []


def test_run_requires_secret(monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "s3cret")
    response = client.get("/run")
    assert response.status_code == 401


def test_abort_requires_secret(monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "s3cret")
    response = client.get("/abort")
    assert response.status_code == 401


def test_abort_when_idle():
    response = client.get("/abort")
    assert response.status_code == 200
    assert response.json()["status"] == "not_running"


def test_last_run_is_live_immediately(monkeypatch):
    started = threading.Event()
    release = threading.Event()

    def fake_pipeline(settings=None, upload=True):
        log = logging.getLogger("src.pipeline")
        log.info("Fetching articles")
        get_controller().update(phase="uploading", added=2, skipped=10, persist=True)
        started.set()
        if not release.wait(timeout=5):
            raise RuntimeError("test timed out")
        log.info("added=2 updated=0 skipped=10")
        return RunResult(status="ok", added=2, skipped=10)

    monkeypatch.setattr("src.server.run_pipeline", fake_pipeline)

    response = client.get("/run")
    assert response.status_code == 200
    assert response.json()["status"] == "started"

    immediate = client.get("/last-run").json()
    assert immediate["status"] == "running"
    assert immediate["running"] is True
    assert immediate["logs"]
    assert any("Ingest started" in line for line in immediate["logs"])

    assert started.wait(timeout=5)
    live = client.get("/last-run").json()
    assert live["status"] == "running"
    assert live["added"] == 2
    assert live["skipped"] == 10
    assert live["phase"] == "uploading"
    assert any("Fetching articles" in line for line in live["logs"])

    release.set()
    for _ in range(20):
        payload = client.get("/last-run").json()
        if payload.get("status") == "ok":
            break
        time.sleep(0.05)
    else:
        payload = client.get("/last-run").json()
    assert payload["status"] == "ok"
    assert payload["running"] is False


def test_abort_stops_running_job(monkeypatch):
    entered = threading.Event()
    left = threading.Event()

    def fake_pipeline(settings=None, upload=True):
        from src.progress import AbortRequested, get_controller as gc

        entered.set()
        try:
            gc().sleep(5)
        except AbortRequested:
            return RunResult(status="aborted", added=1, files_uploaded=1, error="Aborted by operator")
        finally:
            left.set()
        return RunResult(status="ok")

    monkeypatch.setattr("src.server.run_pipeline", fake_pipeline)
    assert client.get("/run").json()["status"] == "started"
    assert entered.wait(timeout=5)

    aborted = client.get("/abort")
    assert aborted.status_code == 200
    body = aborted.json()
    assert body["status"] == "aborting"
    assert any("Abort requested" in line for line in body["last_run"]["logs"])

    assert left.wait(timeout=5)
    for _ in range(20):
        payload = client.get("/last-run").json()
        if payload.get("status") == "aborted":
            break
        time.sleep(0.05)
    payload = client.get("/last-run").json()
    assert payload["status"] == "aborted"
    assert payload["running"] is False
