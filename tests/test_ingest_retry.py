from __future__ import annotations

import pytest

from src.ingest import _is_retryable, _with_retry


class FakeClientError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        super().__init__(f"{code} Bad Request. {{'message': '{message}', 'status': 'Bad Request'}}")


def test_terminated_upload_is_retryable():
    exc = FakeClientError(400, "Upload has already been terminated.")
    assert _is_retryable(exc) is True


def test_503_is_retryable():
    assert _is_retryable(Exception("503 Service Unavailable")) is True


def test_plain_400_is_not_retryable():
    exc = FakeClientError(400, "Invalid chunking config")
    assert _is_retryable(exc) is False


def test_with_retry_starts_fresh_after_terminated(monkeypatch):
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise FakeClientError(400, "Upload has already been terminated.")
        return "ok"

    monkeypatch.setattr("src.ingest.time.sleep", lambda _s: None)
    assert _with_retry(flaky, attempts=4) == "ok"
    assert calls["n"] == 3


def test_with_retry_gives_up_on_non_retryable():
    def boom():
        raise FakeClientError(400, "Invalid argument")

    with pytest.raises(FakeClientError):
        _with_retry(boom, attempts=3)
