from __future__ import annotations

import logging
import os
import threading
from typing import Any

from fastapi import FastAPI, Header, HTTPException

from src.config import get_settings
from src.pipeline import run_pipeline
from src.progress import AbortRequested, ProgressLogHandler, RunController, get_controller

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="kb-ingest")
_handler_lock = threading.Lock()
_log_handler: ProgressLogHandler | None = None


def _controller() -> RunController:
    controller = get_controller()
    controller.ensure_persist_path(get_settings().last_run_path)
    return controller


def _attach_log_handler() -> None:
    global _log_handler
    with _handler_lock:
        if _log_handler is not None:
            return
        handler = ProgressLogHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        handler.setLevel(logging.INFO)
        src_logger = logging.getLogger("src")
        # Own level so INFO still reaches /last-run when root is WARNING (pytest).
        src_logger.setLevel(logging.INFO)
        src_logger.addHandler(handler)
        _log_handler = handler


def _check_secret(authorization: str | None) -> None:
    secret = get_settings().cron_secret
    if not secret:
        return
    expected = f"Bearer {secret}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _run_ingest() -> None:
    controller = _controller()
    try:
        result = run_pipeline(upload=True)
        if controller.running:
            controller.complete(**result.to_dict(), phase="done")
    except AbortRequested:
        logger.info("Ingest aborted")
        if controller.running:
            controller.complete(
                status="aborted",
                error="Aborted by operator",
                phase="done",
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ingest failed")
        if controller.running:
            controller.complete(status="error", error=str(exc), phase="done")


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/run")
def run(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _check_secret(authorization)
    controller = _controller()
    _attach_log_handler()
    started = controller.try_begin()
    if started is None:
        return {"status": "already_running", "last_run": controller.snapshot()}
    logger.info("Ingest started")
    thread = threading.Thread(target=_run_ingest, daemon=True)
    thread.start()
    return {"status": "started"}


@app.get("/abort")
def abort(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _check_secret(authorization)
    controller = _controller()
    if controller.request_abort():
        return {"status": "aborting", "last_run": controller.snapshot()}
    return {"status": "not_running", "last_run": controller.snapshot()}


@app.get("/last-run")
def last_run() -> dict[str, Any]:
    return _controller().snapshot()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.server:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
    )
