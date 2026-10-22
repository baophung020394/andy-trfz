from __future__ import annotations

import math

DEFAULT_MAX_CHUNK_TOKENS = 800
DEFAULT_OVERLAP_TOKENS = 400


def estimate_tokens(text: str) -> int:
    """Approximate Gemini tokens as 4 characters per token."""
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def estimate_chunks(
    text: str,
    max_chunk_tokens: int = DEFAULT_MAX_CHUNK_TOKENS,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
) -> int:
    tokens = estimate_tokens(text)
    if tokens == 0:
        return 0
    if tokens <= max_chunk_tokens:
        return 1
    step = max(1, max_chunk_tokens - overlap_tokens)
    return 1 + math.ceil((tokens - max_chunk_tokens) / step)
