from src.diff import classify_changes


def test_classify_added_updated_skipped():
    local = {
        "1": "aaa",
        "2": "bbb-new",
        "3": "ccc",
    }
    remote = {
        "2": "bbb-old",
        "3": "ccc",
        "4": "gone-from-local-is-ignored",
    }
    diff = classify_changes(local, remote)
    assert diff.added == ["1"]
    assert diff.updated == ["2"]
    assert diff.skipped == ["3"]
    assert diff.upload_ids == ["1", "2"]


def test_first_run_marks_everything_added():
    diff = classify_changes({"10": "hash"}, {})
    assert diff.added == ["10"]
    assert diff.updated == []
    assert diff.skipped == []
