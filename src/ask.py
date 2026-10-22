"""Ask the File Search store the assignment sample questions."""

from __future__ import annotations

from google import genai
from google.genai import types

from src.config import get_settings
from src.ingest import make_client, normalize_store_name
from src.prompt import SYSTEM_PROMPT

QUESTIONS = [
    "How do I add a YouTube video?",
    "Làm thế nào để thêm một video YouTube?",
]


def ask(question: str, client: genai.Client, store_name: str) -> str:
    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=question,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[
                types.Tool(
                    file_search=types.FileSearch(file_search_store_names=[store_name])
                )
            ],
        ),
    )
    return (response.text or "").strip()


def main() -> None:
    settings = get_settings()
    client = make_client(settings.gemini_api_key)
    store_name = normalize_store_name(settings.file_search_store_name)
    if not store_name:
        raise SystemExit("FILE_SEARCH_STORE_NAME is required")
    for question in QUESTIONS:
        print(f"Q: {question}")
        print(ask(question, client, store_name))
        print()


if __name__ == "__main__":
    main()
