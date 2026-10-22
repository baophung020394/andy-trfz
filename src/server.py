from __future__ import annotations

import logging
import os
import threading
from typing import Any

from fastapi import FastAPI, Header, HTTPException

from src.config import get_settings
from src.pipeline import load_last_run, run_pipeline, save_last_run
from src.pipeline import RunResult

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="kb-ingest")
_lock = threading.Lock()
_running = False
_last_run: dict[str, Any] | None = None


def _load_cached_last_run() -> dict[str, Any] | None:
    global _last_run
    if _last_run is None:
        _last_run = load_last_run(get_settings().last_run_path)
    return _last_run


def _check_secret(authorization: str | None) -> None:
    secret = get_settings().cron_secret
    if not secret:
        return
    expected = f"Bearer {secret}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _run_ingest() -> None:
    global _running, _last_run
    try:
        result = run_pipeline(upload=True)
        _last_run = result.to_dict()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ingest failed")
        result = RunResult(
            status="error",
            error=str(exc),
        )
        _last_run = result.to_dict()
        save_last_run(get_settings().last_run_path, result)
    finally:
        with _lock:
            _running = False


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/run")
def run(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _check_secret(authorization)
    global _running
    with _lock:
        if _running:
            return {"status": "already_running", "last_run": _load_cached_last_run()}
        _running = True
        thread = threading.Thread(target=_run_ingest, daemon=True)
        thread.start()
    return {"status": "started"}


@app.get("/last-run")
def last_run() -> dict[str, Any]:
    payload = _load_cached_last_run()
    if not payload:
        return {"status": "none"}
    return payload


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.server:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
    )
