# 4. Run with Docker

The default Dockerfile runs ingest **once and exits** with code `0` on success. The API key is passed only via environment variables.

## 4.1. Build

Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and open the app so the daemon is running.

```bash
docker build -t cedar-kb-nightly .
```

## 4.2. Run one-shot (matches the assignment)

`.env` already has `GEMINI_API_KEY` and `FILE_SEARCH_STORE_NAME`:

```bash
docker run --rm --env-file .env cedar-kb-nightly
```

Expect logs like `added=... updated=... skipped=...`, then the process exits. `echo $?` must be `0`.

On later runs with no changed articles: high `skipped`, `files_uploaded=0`.

## 4.3. Run the web server in a container (like Render)

```bash
docker run --rm --env-file .env -p 8000:8000 \
  -e PORT=8000 \
  cedar-kb-nightly \
  uvicorn src.server:app --host 0.0.0.0 --port 8000
```

Try:

```bash
curl http://localhost:8000/health
# {"ok":true}

curl http://localhost:8000/last-run
```

Trigger ingest (`CRON_SECRET` must match `.env`):

```bash
curl -H "Authorization: Bearer $CRON_SECRET" http://localhost:8000/run
# {"status":"started"}
```

`/run` responds immediately (`{"status":"started"}`). Ingest runs in the background because cron-job.org times out after 30 seconds. Poll live logs right away:

```bash
curl http://localhost:8000/last-run
# status=running, logs[], added/updated/skipped as soon as the diff is known
```

Stop further File Search uploads (current file may finish first):

```bash
curl -H "Authorization: Bearer $CRON_SECRET" http://localhost:8000/abort
# {"status":"aborting", ...}
```
