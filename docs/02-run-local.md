# 2. Run locally: fetch articles and load Gemini

The first ingest (~415 articles) should run on your machine. Do not rely on cron-job.org for it (30-second timeout).

## 2.1. Fetch articles only (no upload)

In the project, with the venv activated:

```bash
python main.py --fetch-only
```

Expected result:

```text
Wrote 415 markdown files to .../articles
added=415 updated=0 skipped=0 files_uploaded=0 chunks_embedded=0
```

Each file: `articles/{id}-{slug}.md`, with title, an `Article URL:` line, headings, code, and relative links.

The repo already includes these files. Run `--fetch-only` again when you want to refresh from Zendesk.

Check the YouTube article:

```bash
ls articles | grep -i youtube
```

Main file: `articles/360051014713-How-to-Use-YouTube-with-OptiSigns.md`.

## 2.2. Upload to Gemini File Search (must use the API)

If a previous run hit `503` / `Upload has already been terminated`, run `python main.py` again: the script only uploads missing articles (diff by `article_id` + `content_hash`). You do not need to delete the store.

To clean up stale remote documents (no longer in `articles/`, or missing `article_id`):

```bash
# .env
DELETE_STALE_REMOTE=true
python main.py
# or one-shot:
python main.py --delete-stale
```

After cleanup (or on Render), set `DELETE_STALE_REMOTE=false` — the daily job only adds/updates, and does not bulk-delete.

`.env` must include `GEMINI_API_KEY`.

```bash
python main.py
```

First run:

- Creates a File Search store (`display_name=support-kb`) if `FILE_SEARCH_STORE_NAME` is empty.
- Uploads every new article.
- Prints logs like:

```text
added=415 updated=0 skipped=0 files_uploaded=415 chunks_embedded=...
store_name=fileSearchStores/support-kb-xxxxxxxxxxxx
```

Copy `store_name` into `.env`:

```bash
FILE_SEARCH_STORE_NAME=fileSearchStores/support-kb-xxxxxxxxxxxx
```

Later runs only upload articles that are **new** or whose **hash changed**:

```text
added=0 updated=1 skipped=414 files_uploaded=1 chunks_embedded=...
```

Log fields:

| Field | Meaning |
|---|---|
| `added` | Article not yet on the store |
| `updated` | Markdown hash changed → delete old doc, upload again |
| `skipped` | Unchanged, skipped |
| `files_uploaded` | Number of files just sent to the API |
| `chunks_embedded` | Estimated chunk count (800-token window, 400 overlap) |

On Free Tier rate limits, the script backs off and retries. Re-run until `skipped` is close to the total article count.

## 2.3. Try asking via script (does not replace AI Studio)

```bash
python -m src.ask
```

Two sample questions:

- `How do I add a YouTube video?`
- `Làm thế nào để thêm một video YouTube?`

Answers should be short, based on the docs, and include an `Article URL:` line.

## 2.4. Tests

```bash
pytest
```

All tests must pass before you deploy.
