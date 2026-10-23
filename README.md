# cedar-kb-nightly

Daily Zendesk Help Center → clean Markdown → [Gemini File Search](https://ai.google.dev/gemini-api/docs/file-search) (API only). No custom chat UI — verify in [AI Studio](https://aistudio.google.com/). Full walkthrough: [docs/README.md](docs/README.md).

## Setup & run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.sample .env   # GEMINI_API_KEY (+ FILE_SEARCH_STORE_NAME after first upload)
python main.py --fetch-only   # articles/*.md only
python main.py                # fetch + incremental upload to File Search
```

Docker one-shot (exits `0`; secrets via env, never baked into the image):

```bash
docker build -t cedar-kb-nightly .
docker run --rm --env-file .env cedar-kb-nightly
```

Incremental sync: SHA-256 of each Markdown + `article_id` / `content_hash` metadata → log `added` / `updated` / `skipped`. Gemini chunking: `MAX_CHUNK_TOKENS=200`, `CHUNK_OVERLAP_TOKENS=20` (`white_space_config`).

## AI Studio

Paste system prompt **verbatim**, attach the File Search store (no drag-and-drop). Ask: `How do I add a YouTube video?` and `Làm thế nào để thêm một video YouTube?`

```text
You are OptiBot, the customer-support bot for OptiSigns.com.

• Tone: helpful, factual, concise.
• Only answer using the uploaded docs.
• Max 5 bullet points; else link to the doc.
• Cite up to 3 "Article URL:" lines per reply.
```

## Daily job (Render free + cron-job.org)

Web Service start command (override Dockerfile `CMD`):

`uvicorn src.server:app --host 0.0.0.0 --port $PORT`

| Job | URL | Schedule |
|-----|-----|----------|
| Wake | [GET /health](https://andy-trfz.onrender.com/health) | every 10–14 min |
| Ingest | [GET /run](https://andy-trfz.onrender.com/run) + `Authorization: Bearer $CRON_SECRET` | daily |
| Abort | [GET /abort](https://andy-trfz.onrender.com/abort) + Bearer | stop further uploads |

**Job logs (submission):** `/last-run` is live while ingest runs (`status=running`, `logs`, `added`/`updated`/`skipped`).

- Last run JSON: https://andy-trfz.onrender.com/last-run
- cron-job.org history (ingest, Save responses): _paste console history URL here_

Example log line: `added=3 updated=1 skipped=411 deleted=0 files_uploaded=4 chunks_embedded=18`.

Tests: `pytest`.

# Result from playground Gemini
![English](screenshots/result.png)
