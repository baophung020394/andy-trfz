from src.chunk import estimate_chunks, estimate_tokens


def test_short_doc_is_one_chunk():
    text = "short"
    assert estimate_tokens(text) < 800
    assert estimate_chunks(text, max_chunk_tokens=800, overlap_tokens=400) == 1


def test_window_math_matches_800_400():
    # 4 chars/token => 4800 chars == 1200 tokens.
    text = "x" * 4800
    assert estimate_tokens(text) == 1200
    assert estimate_chunks(text, max_chunk_tokens=800, overlap_tokens=400) == 2


def test_empty_text_has_zero_chunks():
    assert estimate_chunks("") == 0
