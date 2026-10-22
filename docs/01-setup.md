# 1. Prepare accounts and machine

Do these in order. Steps 1–2 are assignment requirements; steps 3–6 are needed to run the pipeline.

## 1.1. Understand the OptiSigns product

1. Create a trial account at [optisigns.com](https://www.optisigns.com).
2. Open OptiBot on the site and ask a few questions (for example, how to add a YouTube video) to learn the original bot’s tone.

## 1.2. Google AI Studio / Gemini API

1. Open [Google AI Studio](https://aistudio.google.com/).
2. Sign in with Google.
3. Go to **API keys** → **Create API key**.
4. Copy the key. Do not commit the key to Git.

The Free Tier is enough for this assignment (File Search is listed as free; 1 GB storage).

## 1.3. GitHub

1. Create a repo whose name does **not** contain `optisigns` (for example `cedar-kb-nightly`).
2. A private repo is fine.

## 1.4. Render (free web)

1. Create an account at [Render](https://render.com/).
2. Connect GitHub. Do not deploy yet — wait until the local run succeeds.

## 1.5. cron-job.org (free)

1. Sign up at [cron-job.org](https://cron-job.org/en/).
2. Do not create a job yet — you need the Render URL first.

## 1.6. Local machine

You need:

- Python 3.11+ (`python3 --version`)
- Git
- Docker Desktop (required to submit the Dockerfile; you can install it later)

In the project directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.sample .env
```

Open `.env` and fill in:

```bash
GEMINI_API_KEY=paste_your_key_here
FILE_SEARCH_STORE_NAME=
CRON_SECRET=a-secret-string-you-choose
```

Leave `FILE_SEARCH_STORE_NAME` empty the first time. After `python main.py`, the program prints `store_name=...` — copy that into `.env`.

`CRON_SECRET` is used for the `/run` endpoint on the server. Use a hard-to-guess string, for example `openssl rand -hex 16`.

Do not push `.env` to Git (it is already in `.gitignore`).
