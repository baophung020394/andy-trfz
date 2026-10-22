from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = ROOT / "articles"
YOUTUBE = ARTICLES / "360051014713-How-to-Use-YouTube-with-OptiSigns.md"


def test_repo_has_at_least_30_clean_markdown_articles():
    files = sorted(ARTICLES.glob("*.md"))
    assert len(files) >= 30
    assert YOUTUBE.exists()
    text = YOUTUBE.read_text(encoding="utf-8")
    assert text.startswith("# How to Use YouTube with OptiSigns")
    assert "Article URL: https://support.optisigns.com/hc/en-us/articles/360051014713-How-to-Use-YouTube-with-OptiSigns" in text
    assert "## Add a YouTube video" in text
