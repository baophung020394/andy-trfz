from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    file_search_store_name: str
    cron_secret: str
    help_center_base: str
    help_center_locale: str
    articles_dir: Path
    last_run_path: Path
    max_chunk_tokens: int
    chunk_overlap_tokens: int
    # When true: remove remote File Search docs that are not in the local
    # article set (or lack article_id metadata). Keep false on daily deploy.
    delete_stale_remote: bool


def get_settings() -> Settings:
    articles = os.getenv("ARTICLES_DIR", "articles")
    last_run = os.getenv("LAST_RUN_PATH", "/tmp/last_run.json")
    return Settings(
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        file_search_store_name=os.getenv("FILE_SEARCH_STORE_NAME", "").strip(),
        cron_secret=os.getenv("CRON_SECRET", "").strip(),
        help_center_base=os.getenv(
            "HELP_CENTER_BASE", "https://support.optisigns.com"
        ).rstrip("/"),
        help_center_locale=os.getenv("HELP_CENTER_LOCALE", "en-us"),
        articles_dir=Path(articles) if Path(articles).is_absolute() else ROOT / articles,
        last_run_path=Path(last_run),
        max_chunk_tokens=int(os.getenv("MAX_CHUNK_TOKENS", "200")),
        chunk_overlap_tokens=int(os.getenv("CHUNK_OVERLAP_TOKENS", "20")),
        delete_stale_remote=env_bool("DELETE_STALE_REMOTE", False),
    )
