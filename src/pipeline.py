from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.chunk import estimate_chunks
from src.config import Settings, get_settings
from src.convert import article_filename, article_to_markdown, content_hash
from src.diff import classify_changes
from src.fetch import fetch_articles

logger = logging.getLogger(__name__)


@dataclass
class RunResult:
    status: str
    added: int = 0
    updated: int = 0
    skipped: int = 0
    deleted: int = 0
    files_uploaded: int = 0
    chunks_embedded: int = 0
    article_count: int = 0
    store_name: str = ""
    finished_at: str = ""
    error: str | None = None
    failed_uploads: list[str] | None = None

    def log_line(self) -> str:
        line = (
            f"added={self.added} updated={self.updated} skipped={self.skipped} "
            f"deleted={self.deleted} files_uploaded={self.files_uploaded} "
            f"chunks_embedded={self.chunks_embedded}"
        )
        if self.failed_uploads:
            line += f" failed_uploads={len(self.failed_uploads)}"
        return line

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def write_articles(articles: list[dict[str, Any]], articles_dir: Path) -> dict[str, dict[str, Any]]:
    articles_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, dict[str, Any]] = {}
    for article in articles:
        article_id = str(article["id"])
        markdown = article_to_markdown(article)
        path = articles_dir / article_filename(article)
        path.write_text(markdown, encoding="utf-8")
        written[article_id] = {
            "path": path,
            "hash": content_hash(markdown),
            "markdown": markdown,
            "title": article.get("title") or "",
        }
    return written


def save_last_run(path: Path, result: RunResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")


def load_last_run(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def run_pipeline(settings: Settings | None = None, upload: bool = True) -> RunResult:
    settings = settings or get_settings()
    finished_at = datetime.now(timezone.utc).isoformat()
    logger.info("Fetching articles from %s", settings.help_center_base)
    articles = fetch_articles(settings.help_center_base, settings.help_center_locale)
    local = write_articles(articles, settings.articles_dir)
    local_hashes = {article_id: item["hash"] for article_id, item in local.items()}
    logger.info("Wrote %s markdown files to %s", len(local), settings.articles_dir)

    if not upload:
        result = RunResult(
            status="ok",
            added=len(local),
            article_count=len(local),
            finished_at=finished_at,
        )
        logger.info(result.log_line())
        return result

    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is required for upload")

    from src.ingest import (
        apply_diff,
        delete_stale_remote_documents,
        ensure_store,
        list_remote_documents,
        make_client,
    )

    client = make_client(settings.gemini_api_key)
    store_name = ensure_store(client, settings.file_search_store_name)
    # Print early so a long upload / Ctrl+C still leaves a copyable store name.
    print(f"store_name={store_name}", flush=True)
    logger.info("Using File Search store %s", store_name)
    deleted = 0
    if settings.delete_stale_remote:
        logger.info("DELETE_STALE_REMOTE=true — removing remote docs not in local set")
        deleted = delete_stale_remote_documents(client, store_name, set(local_hashes))
    else:
        logger.info("DELETE_STALE_REMOTE=false — keeping existing remote docs")

    remote_docs = list_remote_documents(client, store_name)
    remote_hashes = {
        article_id: doc.get("content_hash", "") for article_id, doc in remote_docs.items()
    }
    diff = classify_changes(local_hashes, remote_hashes)
    chunks_this_run = sum(
        estimate_chunks(
            local[article_id]["markdown"],
            settings.max_chunk_tokens,
            settings.chunk_overlap_tokens,
        )
        for article_id in diff.upload_ids
    )
    files_uploaded, failed_uploads = apply_diff(
        client,
        store_name,
        diff,
        {article_id: item["path"] for article_id, item in local.items()},
        local_hashes,
        remote_docs,
        settings,
    )
    if failed_uploads and files_uploaded == 0 and diff.upload_ids:
        status = "error"
        error = (
            f"Failed to upload all {len(failed_uploads)} article(s): "
            + ", ".join(failed_uploads[:20])
        )
    elif failed_uploads:
        status = "partial"
        error = (
            f"Failed to upload {len(failed_uploads)} article(s): "
            + ", ".join(failed_uploads[:20])
        )
    else:
        status = "ok"
        error = None
    result = RunResult(
        status=status,
        added=len(diff.added),
        updated=len(diff.updated),
        skipped=len(diff.skipped),
        deleted=deleted,
        files_uploaded=files_uploaded,
        chunks_embedded=chunks_this_run,
        article_count=len(local),
        store_name=store_name,
        finished_at=datetime.now(timezone.utc).isoformat(),
        error=error,
        failed_uploads=failed_uploads or None,
    )
    logger.info(result.log_line())
    save_last_run(settings.last_run_path, result)
    if status == "error":
        raise RuntimeError(error)
    return result
