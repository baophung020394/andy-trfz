from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from src.config import Settings
from src.diff import DiffResult, classify_changes

logger = logging.getLogger(__name__)

# Substrings matched against the error message / status text.
RETRYABLE_TOKENS = (
    "429",
    "500",
    "502",
    "503",
    "504",
    "RESOURCE_EXHAUSTED",
    "UNAVAILABLE",
    "INTERNAL",
    "Upload has already been terminated",
    "Timed out waiting for File Search upload",
)
RETRYABLE_HTTP_CODES = {429, 500, 502, 503, 504}
# Gemini File Search: max_tokens_per_chunk must be in (0, 512), i.e. 1–511.
GEMINI_MAX_TOKENS_PER_CHUNK = 511
UPLOAD_OPERATION_TIMEOUT_SEC = 600
# Space uploads to reduce resumable-upload 503s from the Gemini API.
UPLOAD_GAP_SEC = 1.5


def _file_search_chunking(settings: Settings) -> types.ChunkingConfig:
    max_tokens = min(max(settings.max_chunk_tokens, 1), GEMINI_MAX_TOKENS_PER_CHUNK)
    overlap = min(max(settings.chunk_overlap_tokens, 0), max_tokens - 1)
    if (
        max_tokens != settings.max_chunk_tokens
        or overlap != settings.chunk_overlap_tokens
    ):
        logger.info(
            "Clamped File Search chunking to max_tokens_per_chunk=%s max_overlap_tokens=%s",
            max_tokens,
            overlap,
        )
    return types.ChunkingConfig(
        white_space_config=types.WhiteSpaceConfig(
            max_tokens_per_chunk=max_tokens,
            max_overlap_tokens=overlap,
        )
    )


def normalize_store_name(raw: str) -> str:
    name = raw.strip()
    if not name:
        return ""
    if name.startswith("fileSearchStores/"):
        return name
    return f"fileSearchStores/{name}"


def _metadata_map(doc: Any) -> dict[str, str]:
    result: dict[str, str] = {}
    metas = getattr(doc, "custom_metadata", None) or []
    for item in metas:
        if isinstance(item, dict):
            key = item.get("key")
            value = item.get("string_value") or item.get("stringValue")
        else:
            key = getattr(item, "key", None)
            value = getattr(item, "string_value", None)
        if key and value is not None:
            result[str(key)] = str(value)
    return result


def _is_retryable(exc: Exception) -> bool:
    """Return True when a fresh retry (new upload session) may succeed.

    After a mid-upload 503 the SDK retries the same resumable upload URL and
    gets 400 \"Upload has already been terminated.\" That must start a *new*
    upload, not reuse the dead session.
    """
    code = getattr(exc, "code", None)
    if isinstance(code, int) and code in RETRYABLE_HTTP_CODES:
        return True
    message = str(exc)
    if any(token in message for token in RETRYABLE_TOKENS):
        return True
    if isinstance(code, int) and code == 400 and "terminated" in message.lower():
        return True
    return False


def _with_retry(fn, attempts: int = 6):
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - SDK raises mixed types
            last_error = exc
            if not _is_retryable(exc):
                raise
            sleep_for = min(60, 2**attempt)
            logger.warning(
                "Retryable Gemini error (attempt %s/%s): %s. Sleeping %ss",
                attempt + 1,
                attempts,
                exc,
                sleep_for,
            )
            time.sleep(sleep_for)
    raise RuntimeError(f"Gemini request failed after retries: {last_error}")


def make_client(api_key: str) -> genai.Client:
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required")
    return genai.Client(api_key=api_key)


def ensure_store(client: genai.Client, store_name: str) -> str:
    name = normalize_store_name(store_name)
    if name:
        _with_retry(lambda: client.file_search_stores.get(name=name))
        return name
    for store in client.file_search_stores.list():
        if (store.display_name or "") == "support-kb":
            logger.info("Reusing File Search store %s", store.name)
            return store.name
    created = _with_retry(
        lambda: client.file_search_stores.create(
            config={"display_name": "support-kb"}
        )
    )
    logger.info("Created File Search store %s — set FILE_SEARCH_STORE_NAME=%s", created.name, created.name)
    return created.name


def wait_for_operation(
    client: genai.Client,
    operation: Any,
    timeout: int = UPLOAD_OPERATION_TIMEOUT_SEC,
) -> Any:
    started = time.time()
    current = operation
    while not getattr(current, "done", False):
        if time.time() - started > timeout:
            raise TimeoutError("Timed out waiting for File Search upload")
        time.sleep(2)
        current = client.operations.get(operation=current)
    error = getattr(current, "error", None)
    if error:
        raise RuntimeError(f"File Search upload failed: {error}")
    return current


def list_remote_documents(client: genai.Client, store_name: str) -> dict[str, dict[str, str]]:
    remote: dict[str, dict[str, str]] = {}
    pager = client.file_search_stores.documents.list(
        parent=store_name,
        config={"page_size": 20},
    )
    for doc in pager:
        meta = _metadata_map(doc)
        article_id = meta.get("article_id")
        if not article_id:
            continue
        remote[article_id] = {
            "name": getattr(doc, "name", ""),
            "content_hash": meta.get("content_hash", ""),
        }
    return remote


def delete_document(client: genai.Client, document_name: str) -> None:
    if not document_name:
        return
    _with_retry(
        lambda: client.file_search_stores.documents.delete(name=document_name)
    )


def delete_stale_remote_documents(
    client: genai.Client,
    store_name: str,
    local_article_ids: set[str],
) -> int:
    """Delete remote docs missing from local set, or lacking article_id metadata.

    Used for a one-shot cleanup (DELETE_STALE_REMOTE=true). Daily deploy should
    keep the flag false so incremental sync only touches added/updated files.
    """
    deleted = 0
    pager = client.file_search_stores.documents.list(
        parent=store_name,
        config={"page_size": 20},
    )
    for doc in pager:
        name = getattr(doc, "name", "") or ""
        if not name:
            continue
        meta = _metadata_map(doc)
        article_id = meta.get("article_id")
        if article_id and article_id in local_article_ids:
            continue
        reason = "no article_id" if not article_id else f"not in local ({article_id})"
        logger.info("Deleting stale remote doc %s (%s)", name, reason)
        delete_document(client, name)
        deleted += 1
    if deleted:
        logger.info("Deleted %s stale remote document(s)", deleted)
    else:
        logger.info("No stale remote documents to delete")
    return deleted


def upload_markdown(
    client: genai.Client,
    store_name: str,
    path: Path,
    article_id: str,
    content_hash: str,
    settings: Settings,
) -> None:
    """Upload via Files API then importFile.

    Direct ``upload_to_file_search_store`` often hangs ~160s then returns 503
    (resumable session terminated). ``files.upload`` + ``import_file`` is the
    reliable path for this Free Tier / Developer API store.
    """
    metadata = [
        types.CustomMetadata(key="article_id", string_value=article_id),
        types.CustomMetadata(key="content_hash", string_value=content_hash),
    ]
    chunking = _file_search_chunking(settings)

    def _do_upload():
        uploaded = client.files.upload(
            file=str(path),
            config={
                "mime_type": "text/markdown",
                "display_name": path.name,
            },
        )
        file_name = getattr(uploaded, "name", None)
        if not file_name:
            raise RuntimeError(f"File upload returned no name for {path.name}")
        try:
            # Wait until ACTIVE if the SDK returns PROCESSING.
            current = uploaded
            deadline = time.time() + 120
            while str(getattr(current, "state", "") or "").endswith("PROCESSING"):
                if time.time() > deadline:
                    raise TimeoutError(f"Timed out waiting for file {file_name}")
                time.sleep(1)
                current = client.files.get(name=file_name)
            operation = client.file_search_stores.import_file(
                file_search_store_name=store_name,
                file_name=file_name,
                config=types.ImportFileConfig(
                    custom_metadata=metadata,
                    chunking_config=chunking,
                ),
            )
            return wait_for_operation(client, operation)
        finally:
            try:
                client.files.delete(name=file_name)
            except Exception as exc:  # noqa: BLE001 - best-effort cleanup
                logger.debug("Could not delete temp file %s: %s", file_name, exc)

    _with_retry(_do_upload)


def apply_diff(
    client: genai.Client,
    store_name: str,
    diff: DiffResult,
    local_files: dict[str, Path],
    local_hashes: dict[str, str],
    remote_docs: dict[str, dict[str, str]],
    settings: Settings,
) -> int:
    uploaded = 0
    failures: list[tuple[str, Exception]] = []
    for article_id in diff.updated:
        delete_document(client, remote_docs.get(article_id, {}).get("name", ""))
    total = len(diff.upload_ids)
    for index, article_id in enumerate(diff.upload_ids, start=1):
        path = local_files[article_id]
        try:
            upload_markdown(
                client,
                store_name,
                path,
                article_id,
                local_hashes[article_id],
                settings,
            )
            uploaded += 1
            logger.info("Uploaded %s/%s %s (%s)", index, total, article_id, path.name)
        except Exception as exc:  # noqa: BLE001 - keep batch going
            logger.error(
                "Failed upload %s/%s %s (%s): %s",
                index,
                total,
                article_id,
                path.name,
                exc,
            )
            failures.append((article_id, exc))
        if index < total and UPLOAD_GAP_SEC > 0:
            time.sleep(UPLOAD_GAP_SEC)
    if failures:
        ids = ", ".join(article_id for article_id, _ in failures[:20])
        more = "" if len(failures) <= 20 else f" (+{len(failures) - 20} more)"
        raise RuntimeError(
            f"Failed to upload {len(failures)}/{total} article(s): {ids}{more}. "
            "Re-run python main.py to retry remaining files."
        )
    return uploaded
