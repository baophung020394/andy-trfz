from src.config import env_bool


def test_env_bool_true_values(monkeypatch):
    for value in ("true", "TRUE", "1", "yes", "on"):
        monkeypatch.setenv("DELETE_STALE_REMOTE", value)
        assert env_bool("DELETE_STALE_REMOTE", False) is True


def test_env_bool_false_values(monkeypatch):
    for value in ("false", "0", "no", "off"):
        monkeypatch.setenv("DELETE_STALE_REMOTE", value)
        assert env_bool("DELETE_STALE_REMOTE", True) is False


def test_env_bool_default_when_missing_or_blank(monkeypatch):
    monkeypatch.delenv("DELETE_STALE_REMOTE", raising=False)
    assert env_bool("DELETE_STALE_REMOTE", False) is False
    assert env_bool("DELETE_STALE_REMOTE", True) is True
    monkeypatch.setenv("DELETE_STALE_REMOTE", "  ")
    assert env_bool("DELETE_STALE_REMOTE", True) is True
