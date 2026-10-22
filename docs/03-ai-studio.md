# 3. Test the bot in Google AI Studio

The assignment does **not** require a custom chat UI. Test on [AI Studio](https://aistudio.google.com/) with the exact system prompt and the File Search store already loaded via the API.

## 3.1. Create a prompt

1. Open [aistudio.google.com](https://aistudio.google.com/).
2. **Create new prompt** (or equivalent chat).
3. Choose a Flash model (for example Gemini 3.8 Flash / 2.5 Flash if still available) — Free Tier.
4. Use the same Google account / project as the API key used for ingest.

## 3.2. Paste the system prompt verbatim

In System instructions / system prompt, paste **verbatim** — do not change punctuation or bullets:

```text
You are OptiBot, the customer-support bot for OptiSigns.com.

• Tone: helpful, factual, concise.
• Only answer using the uploaded docs.
• Max 5 bullet points; else link to the doc.
• Cite up to 3 "Article URL:" lines per reply.
```

## 3.3. Attach the File Search store

**Important:** *Grounding with Google Search* in the Tools menu is **not** File Search. On the newer Playground, File Search often is **not** in the Tools list (Structured outputs / Code execution / Google Search / Maps / URL context).

### Find File Search in AI Studio

1. **Turn off** *Grounding with Google Search* (if it is On in a screenshot → Off).
2. In the left AI Studio sidebar, open **File Search** (or go to [aistudio.google.com](https://aistudio.google.com/) and search for “File Search” / File Search stores). Confirm the `support-kb` / `fileSearchStores/supportkb-...` store has docs from the API.
3. Return to **Prompt / Chat**: paste the System instructions (section 3.2). Attach the store using whichever UI option is available:
   - A **File Search** chip / button near the prompt box or Run settings (not Google Search), **or**
   - When creating a **New prompt**, choose to attach a File Search store / Knowledge from an existing store.
4. Do **not** drag-and-drop Markdown files into the UI. The store was loaded with `python main.py`.

Signs you are using Google Search by mistake: a green “Grounding with Google Search” chip, a “Google Search Suggestions” footer, or Sources like `capterra.ec`.

If the UI will not let you attach a store to chat: API screenshots are also acceptable — run:

```bash
python -m src.ask
```

(uses File Search, not Search). Capture the terminal or paste answers that include `Article URL:` into the README/screenshots as your mentor requires if Studio is missing the button.

Correct URL from the loaded docs (YouTube example):

```text
Article URL: https://support.optisigns.com/hc/en-us/articles/360051014713-How-to-Use-YouTube-with-OptiSigns
```

(Zendesk also accepts the short form `.../articles/360051014713` — same article.)

If the store does not appear: same Google account as the API key, wait a few minutes, refresh, or paste the resource name from `.env` (`FILE_SEARCH_STORE_NAME`).

## 3.4. Ask the two sample questions

One after another:

```text
How do I add a YouTube video?
```

```text
Làm thế nào để thêm một video YouTube?
```

The bot meets the requirements when:

- Answers are helpful, accurate, and short (max 5 bullets; longer answers should link to docs).
- At most 3 `Article URL: ...` lines.
- URLs point to support, typically  
  `https://support.optisigns.com/hc/en-us/articles/360051014713-How-to-Use-YouTube-with-OptiSigns`

## 3.5. Screenshots for submission

Capture **both the answer and the Article URL line**, and save:

```text
screenshots/youtube-en.png
screenshots/youtube-vi.png
```

The root README already points to these two files.
