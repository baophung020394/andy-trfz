from __future__ import annotations

import threading
import time

import pytest

from src.diff import DiffResult
from src.ingest import apply_diff, wait_for_operation
from src.progress import AbortRequested, get_controller


@pytest.fixture(autouse=True)
def isolate_controller():
    controller = get_controller()
    controller.reset()
    yield
    controller.reset()


def test_apply_diff_stops_on_abort(monkeypatch, tmp_path):
    uploaded_ids: list[str] = []

    def fake_upload(client, store, path, article_id, content_hash, settings):
        uploaded_ids.append(article_id)
        if len(uploaded_ids) == 1:
            get_controller().request_abort()

    monkeypatch.setattr("src.ingest.upload_markdown", fake_upload)
    monkeypatch.setattr("src.ingest.delete_document", lambda *a, **k: None)
    monkeypatch.setattr("src.ingest.UPLOAD_GAP_SEC", 0)

    get_controller().begin()
    diff = DiffResult(added=["1", "2", "3"])
    files = {article_id: tmp_path / f"{article_id}.md" for article_id in diff.added}
    for path in files.values():
        path.write_text("x", encoding="utf-8")

    uploaded, failed, remaining = apply_diff(
        client=None,
        store_name="store",
        diff=diff,
        local_files=files,
        local_hashes={"1": "a", "2": "b", "3": "c"},
        remote_docs={},
        settings=None,
    )
    assert uploaded == 1
    assert failed == []
    assert remaining == ["2", "3"]
    assert uploaded_ids == ["1"]


def test_wait_for_operation_aborts():
    class Op:
        done = False
        error = None

    class Operations:
        def get(self, operation):
            return operation

    class Client:
        operations = Operations()

    get_controller().begin()

    def abort_soon():
        time.sleep(0.05)
        get_controller().request_abort()

    threading.Thread(target=abort_soon, daemon=True).start()
    with pytest.raises(AbortRequested):
        wait_for_operation(Client(), Op(), timeout=5)
