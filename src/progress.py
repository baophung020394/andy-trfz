from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

MAX_LOG_LINES = 400


class AbortRequested(Exception):
    """Ingest was cancelled via /abort."""


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunController:
    """Process-wide ingest state: live /last-run snapshot + abort flag."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._abort = threading.Event()
        self._running = False
        self._persist_path: Path | None = None
        self._logs: list[str] = []
        self._data: dict[str, Any] = self._empty()

    @staticmethod
    def _empty() -> dict[str, Any]:
        return {
            "status": "none",
            "phase": "",
            "running": False,
            "added": 0,
            "updated": 0,
            "skipped": 0,
            "deleted": 0,
            "files_uploaded": 0,
            "files_to_upload": 0,
            "chunks_embedded": 0,
            "article_count": 0,
            "store_name": "",
            "current_file": "",
            "started_at": "",
            "finished_at": "",
            "error": None,
            "failed_uploads": None,
            "remaining_uploads": None,
            "logs": [],
        }

    def reset(self) -> None:
        """Tests: idle memory state. Does not delete the persist file."""
        with self._lock:
            self._abort.clear()
            self._running = False
            self._logs = []
            self._data = self._empty()

    def set_persist_path(self, path: Path) -> None:
        self._persist_path = path

    def ensure_persist_path(self, path: Path) -> None:
        if self._persist_path is None:
            self._persist_path = path
            self.load_from_disk()

    def load_from_disk(self) -> None:
        path = self._persist_path
        if path is None or not path.exists():
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return
        if not isinstance(payload, dict):
            return
        with self._lock:
            if self._running:
                return
            data = self._empty()
            data.update(payload)
            data["running"] = False
            if data.get("status") == "running":
                data["status"] = "error"
                data["error"] = data.get("error") or "Process restarted during ingest"
                data["phase"] = "done"
            self._logs = [str(line) for line in (data.get("logs") or [])][-MAX_LOG_LINES:]
            data["logs"] = list(self._logs)
            self._data = data

    @property
    def running(self) -> bool:
        return self._running

    def try_begin(self) -> dict[str, Any] | None:
        with self._lock:
            if self._running:
                return None
            self._abort.clear()
            self._running = True
            self._logs = []
            self._data = self._empty()
            self._data.update(
                {
                    "status": "running",
                    "phase": "starting",
                    "running": True,
                    "started_at": _utcnow(),
                }
            )
            self._append_unlocked(f"{_utcnow()} INFO Ingest started")
            snapshot = dict(self._data)
        self._persist(snapshot)
        return snapshot

    def begin(self) -> dict[str, Any]:
        snapshot = self.try_begin()
        if snapshot is None:
            return self.snapshot()
        return snapshot

    def request_abort(self) -> bool:
        with self._lock:
            if not self._running:
                return False
            self._abort.set()
            self._append_unlocked(
                f"{_utcnow()} INFO Abort requested — stopping further uploads"
            )
            snapshot = dict(self._data)
        self._persist(snapshot)
        return True

    def aborted(self) -> bool:
        return self._abort.is_set()

    def check_abort(self) -> None:
        if self._abort.is_set():
            raise AbortRequested("Abort requested")

    def sleep(self, seconds: float) -> None:
        deadline = time.time() + max(float(seconds), 0.0)
        while True:
            self.check_abort()
            remaining = deadline - time.time()
            if remaining <= 0:
                return
            time.sleep(min(0.25, remaining))

    def append_log(self, line: str) -> None:
        with self._lock:
            self._append_unlocked(line)

    def _append_unlocked(self, line: str) -> None:
        text = str(line).rstrip()
        if not text:
            return
        self._logs.append(text)
        if len(self._logs) > MAX_LOG_LINES:
            self._logs = self._logs[-MAX_LOG_LINES:]
        self._data["logs"] = list(self._logs)

    def update(self, persist: bool = False, **fields: Any) -> dict[str, Any]:
        with self._lock:
            for key, value in fields.items():
                self._data[key] = value
            self._data["running"] = self._running
            self._data["logs"] = list(self._logs)
            snapshot = dict(self._data)
        if persist:
            self._persist(snapshot)
        return snapshot

    def complete(self, **fields: Any) -> dict[str, Any]:
        with self._lock:
            self._running = False
            self._abort.clear()
            for key, value in fields.items():
                self._data[key] = value
            if not self._data.get("finished_at"):
                self._data["finished_at"] = _utcnow()
            self._data["running"] = False
            self._data["current_file"] = ""
            self._data["phase"] = fields.get("phase") or "done"
            self._data["logs"] = list(self._logs)
            snapshot = dict(self._data)
        self._persist(snapshot)
        return snapshot

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._data)

    def _persist(self, snapshot: dict[str, Any]) -> None:
        path = self._persist_path
        if path is None:
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
        except OSError:
            logger.debug("Could not persist last-run snapshot", exc_info=True)


_controller: RunController | None = None
_controller_lock = threading.Lock()


def get_controller() -> RunController:
    global _controller
    with _controller_lock:
        if _controller is None:
            _controller = RunController()
        return _controller


class ProgressLogHandler(logging.Handler):
    """Copy src.* log lines into the live /last-run snapshot."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            get_controller().append_log(self.format(record))
        except Exception:  # noqa: BLE001 - logging must not break ingest
            self.handleError(record)
