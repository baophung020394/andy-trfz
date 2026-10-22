from __future__ import annotations

from typing import Any, Iterator
from urllib.parse import urlencode

import requests

USER_AGENT = "cedar-kb-nightly/1.0"


def iter_articles(
    base_url: str,
    locale: str = "en-us",
    page_size: int = 100,
    session: requests.Session | None = None,
) -> Iterator[dict[str, Any]]:
    sess = session or requests.Session()
    sess.headers.update(
        {
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }
    )
    query = urlencode({"page[size]": page_size})
    url = f"{base_url.rstrip('/')}/api/v2/help_center/{locale}/articles.json?{query}"

    while url:
        response = sess.get(url, timeout=60)
        response.raise_for_status()
        payload = response.json()
        for article in payload.get("articles") or []:
            if article.get("draft"):
                continue
            yield article
        links = payload.get("links") or {}
        url = links.get("next") or payload.get("next_page")


def fetch_articles(base_url: str, locale: str = "en-us") -> list[dict[str, Any]]:
    return list(iter_articles(base_url, locale=locale))
