from __future__ import annotations

import hashlib
import re
from typing import Any

from bs4 import BeautifulSoup, Comment
from markdownify import markdownify

REMOVE_TAGS = (
    "script",
    "style",
    "nav",
    "footer",
    "aside",
    "noscript",
    "form",
    "iframe",
    "button",
)
UNWRAP_TAGS = ("span", "font")
FILENAME_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def html_to_markdown(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup.find_all(list(REMOVE_TAGS)):
        tag.decompose()
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    for tag in soup.find_all(list(UNWRAP_TAGS)):
        tag.unwrap()
    markdown = markdownify(str(soup), heading_style="ATX", bullets="-")
    markdown = markdown.replace("\xa0", " ")
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    return markdown.strip()


def article_to_markdown(article: dict[str, Any]) -> str:
    title = (article.get("title") or "Untitled").strip()
    url = (article.get("html_url") or "").strip()
    body = html_to_markdown(article.get("body") or "")
    parts = [f"# {title}", "", f"Article URL: {url}"]
    if body:
        parts.extend(["", body])
    return "\n".join(parts).strip() + "\n"


def content_hash(markdown: str) -> str:
    return hashlib.sha256(markdown.encode("utf-8")).hexdigest()


def article_filename(article: dict[str, Any]) -> str:
    html_url = article.get("html_url") or ""
    tail = html_url.rstrip("/").split("/")[-1] if html_url else ""
    article_id = str(article.get("id") or "unknown")
    if not tail or tail == html_url:
        tail = article_id
    if not tail.startswith(article_id):
        tail = f"{article_id}-{tail}"
    safe = FILENAME_SAFE.sub("-", tail).strip("-.")
    return f"{safe}.md"
