# 6. Submission checklist

Cross-check before you submit:

- [ ] ≥30 clean Markdown files in `articles/` (this repo currently has ~415).
- [ ] Python script uploads via API (`python main.py`), no drag-and-drop in the UI.
- [ ] Assistant / prompt on AI Studio uses the system prompt verbatim; answers include `Article URL:`.
- [ ] Log of file and chunk counts (`files_uploaded`, `chunks_embedded`).
- [ ] `docker run --env-file .env` runs once and exits with code `0`.
- [ ] Daily cloud job: cron-job.org → Render `/run`.
- [ ] Only upload new/changed articles; log shows `added` / `updated` / `skipped`.
- [ ] GitHub repo name is hard to guess and does **not** contain optisigns.
- [ ] No hard-coded API key; `.env.sample` is present.
- [ ] Root README ≤ 1 page, with job log links and images `screenshots/youtube-en.png`, `screenshots/youtube-vi.png`.

## Suggested submission order

1. Local ingest done; AI Studio screenshots ready.
2. Push to GitHub.
3. Render + 2 cron-job.org jobs.
4. Trigger the daily job; copy `/last-run` and history.
5. Add the 2 log links to the root README.
6. Commit screenshots + README, create the submission.

## Handy commands

```bash
source .venv/bin/activate
pytest
python main.py --fetch-only
python main.py
python -m src.ask
```
