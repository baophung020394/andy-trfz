# 5. Deploy the daily job (Render free + cron-job.org)

Render **Web Service free** sleeps after ~15 minutes without traffic. [cron-job.org](https://cron-job.org/en/) is free: it both wakes the server and triggers ingest every day. Do not use Render Cron (paid).

## 5.1. Push code to GitHub

Repo name must **not** contain `optisigns`.

```bash
git init
git add .
git status   # confirm .env is not in the list
git commit -m "Initial ingest pipeline"
git remote add origin git@github.com:<user>/<your-repo-name>.git
git push -u origin main
```

## 5.2. Create a Web Service on Render

Option A — Blueprint:

1. Render Dashboard → **New** → **Blueprint**.
2. Select the repo. The `render.yaml` file creates service `cedar-kb-nightly`, free plan, health check `/health`.

Option B — manual:

1. **New** → **Web Service** → this repo.
2. Runtime: **Docker**.
3. Instance: **Free**.
4. **Docker / Start Command** (bắt buộc — override CMD `python main.py` trong Dockerfile):

```text
uvicorn src.server:app --host 0.0.0.0 --port $PORT
```

Nếu để mặc định `python main.py`, Render sẽ **ingest ngay lúc deploy** và crash khi Gemini lỗi 1 file → service không lên. Đề bài: service chỉ listen HTTP; ingest chạy khi cron gọi **`GET /run`** (không dùng `/execute`).

5. Health check path: `/health`.

Environment variables on Render:

| Key | Value |
|---|---|
| `GEMINI_API_KEY` | Gemini key |
| `FILE_SEARCH_STORE_NAME` | `fileSearchStores/...` from local ingest |
| `CRON_SECRET` | Secret string (Blueprint may auto-generate — copy it out) |
| `ARTICLES_DIR` | `/tmp/articles` |
| `LAST_RUN_PATH` | `/tmp/last_run.json` |
| `DELETE_STALE_REMOTE` | `false` (set `true` only when you need a one-time store cleanup) |

After deploy, open `https://<app>.onrender.com/health` → `{"ok":true}`. The first request may take 30–60 seconds (cold start).

Note the app URL, for example `https://cedar-kb-nightly.onrender.com`.

## 5.3. Job 1 on cron-job.org: wake

1. [cron-job.org Console](https://console.cron-job.org/) → **Create cronjob**.
2. Title: `kb-wake`.
3. URL: `https://<app>.onrender.com/health`
4. Schedule: every **10–14 minutes** (Render sleeps after 15 minutes).
5. Method: GET.
6. Save.

This job keeps the instance warm and fits within ~750 free hours/month — enough for the submission week.

## 5.4. Job 2: daily ingest

1. **Create cronjob**.
2. Title: `kb-ingest-daily`.
3. URL: `https://<app>.onrender.com/run`
4. Schedule: every day at **03:00 UTC** (or a time you choose).
5. Method: GET.
6. Headers: `Authorization` = `Bearer <CRON_SECRET>` (include the word Bearer; must match the Render secret).
7. Enable **Save responses**.
8. Save. Click **Test run** once.

Expected response: `{"status":"started"}` or `{"status":"already_running",...}`. Do not wait for ingest to finish within 30 seconds.

Poll immediately (do not wait for ingest to finish):

```text
https://<app>.onrender.com/last-run
```

While running: `status=running`, `phase`, `logs`, and counts as soon as the diff is known (`added` / `updated` / `skipped`). After finish: `files_uploaded`, `chunks_embedded`, `finished_at`. Stop leftover uploads with `GET /abort` + the same Bearer token.

## 5.5. Logs for submission

- Daily job history on cron-job.org (with save responses enabled) — copy the execution / history link.
- Public `/last-run` URL (contains no secret).
- If needed: Render → service → Logs, capture the `added=... updated=... skipped=...` line.

Paste these links into the root README when you submit.
