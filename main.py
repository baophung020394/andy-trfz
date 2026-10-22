#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
import sys

from src.pipeline import run_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch support docs and ingest into Gemini.")
    parser.add_argument(
        "--fetch-only",
        action="store_true",
        help="Write Markdown files without uploading to Gemini.",
    )
    parser.add_argument(
        "--delete-stale",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=(
            "Delete remote File Search docs missing from local articles "
            "(overrides DELETE_STALE_REMOTE). Default: use env / false."
        ),
    )
    args = parser.parse_args()
    try:
        from src.config import get_settings

        settings = get_settings()
        if args.delete_stale is not None:
            from dataclasses import replace

            settings = replace(settings, delete_stale_remote=args.delete_stale)
        result = run_pipeline(settings=settings, upload=not args.fetch_only)
    except Exception as exc:  # noqa: BLE001
        logging.exception("Ingest failed")
        print(f"error={exc}", file=sys.stderr)
        return 1
    print(result.log_line())
    if result.store_name:
        print(f"store_name={result.store_name}")
    if result.error:
        print(f"error={result.error}", file=sys.stderr)
    # partial = some uploads ok (e.g. one flaky Gemini file); still exit 0 for Docker.
    if result.status == "error":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
