# cedar-kb-nightly

Daily Zendesk → Markdown → [Gemini File Search](https://ai.google.dev/gemini-api/docs/file-search) ingest. No chat UI; test in [AI Studio](https://aistudio.google.com/).

Step-by-step: [docs/README.md](docs/README.md).

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.sample .env   # set GEMINI_API_KEY
```

Fetch and write Markdown only:

```bash
python main.py --fetch-only
```

Upload (creates a File Search store if `FILE_SEARCH_STORE_NAME` is empty; copy the printed name into `.env`):

```bash
python main.py
```

Docker one-shot (exits `0` on success; keys via env, never baked in):

```bash
docker build -t cedar-kb-nightly .
docker run --rm --env-file .env cedar-kb-nightly
```

## Chunking

One Markdown file per article. Gemini indexes with **800-token chunks, 400-token overlap** (`white_space_config`). Local logs estimate the same window (`chars/4`). Incremental compare is SHA-256 of the Markdown plus `article_id`/`content_hash` metadata — unchanged files are `skipped`.

## AI Studio

Create a prompt, paste this **verbatim**, attach the File Search store (do not drag-and-drop files):

```text
You are OptiBot, the customer-support bot for OptiSigns.com.

• Tone: helpful, factual, concise.
• Only answer using the uploaded docs.
• Max 5 bullet points; else link to the doc.
• Cite up to 3 "Article URL:" lines per reply.
```

Ask: `How do I add a YouTube video?` and `Làm thế nào để thêm một video YouTube?`

![English answer](screenshots/youtube-en.png)
![Vietnamese answer](screenshots/youtube-vi.png)

## Daily job (free)

Render **Web Service** (free) + [cron-job.org](https://cron-job.org/en/):

1. Deploy with `render.yaml`. Override start: `uvicorn src.server:app --host 0.0.0.0 --port $PORT`.
2. Wake: `GET https://<app>.onrender.com/health` every 10–14 minutes.
3. Ingest: `GET https://<app>.onrender.com/run` daily `03:00 UTC`, header `Authorization: Bearer $CRON_SECRET`, save responses.

Logs: `/last-run` and cron-job.org history. Example: `added=3 updated=1 skipped=411 files_uploaded=4 chunks_embedded=18`.

Tests: `pytest`.
