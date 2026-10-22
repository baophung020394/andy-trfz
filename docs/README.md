# Usage guide

This guide walks through the flow from a local machine to a daily job on Render + [cron-job.org](https://cron-job.org/en/).

1. [Prepare accounts and machine](01-setup.md)
2. [Run locally: fetch articles and load Gemini](02-run-local.md)
3. [Test the bot in AI Studio](03-ai-studio.md)
4. [Run with Docker](04-docker.md)
5. [Deploy the daily job](05-daily-deploy.md)
6. [Submission checklist](06-submission-checklist.md)

Short flow:

```text
support.optisigns.com (Zendesk API)
        ↓
  articles/*.md
        ↓  python main.py  (API, no drag-and-drop)
  Gemini File Search
        ↓
  Google AI Studio  (try questions, take screenshots)
        ↓
  Render Web (free)  ←  cron-job.org wakes + runs daily
```
