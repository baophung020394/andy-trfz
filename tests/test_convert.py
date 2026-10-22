from src.convert import article_filename, article_to_markdown, content_hash, html_to_markdown

SAMPLE_HTML = """
<nav>Skip this menu</nav>
<h2>Add a YouTube video</h2>
<p>Open <a href="/hc/en-us/articles/360051014713-How-to-Use-YouTube-with-OptiSigns">YouTube</a>.</p>
<pre><code>Files/Assets &gt; Apps</code></pre>
<script>alert("ads")</script>
<p><span style="color:#434343">Keep the heading text.</span></p>
"""


def test_html_to_markdown_keeps_relative_links_headings_and_code():
    markdown = html_to_markdown(SAMPLE_HTML)
    assert "Skip this menu" not in markdown
    assert "alert(" not in markdown
    assert "## Add a YouTube video" in markdown
    assert "[YouTube](/hc/en-us/articles/360051014713-How-to-Use-YouTube-with-OptiSigns)" in markdown
    assert "Files/Assets > Apps" in markdown
    assert "Keep the heading text." in markdown


def test_article_to_markdown_includes_article_url():
    article = {
        "id": 360051014713,
        "title": "How to Use YouTube with OptiSigns",
        "html_url": "https://support.optisigns.com/hc/en-us/articles/360051014713-How-to-Use-YouTube-with-OptiSigns",
        "body": "<h2>Add a video</h2><p>Use Apps.</p>",
    }
    markdown = article_to_markdown(article)
    assert markdown.startswith("# How to Use YouTube with OptiSigns\n")
    assert (
        "Article URL: https://support.optisigns.com/hc/en-us/articles/360051014713-How-to-Use-YouTube-with-OptiSigns"
        in markdown
    )
    assert "## Add a video" in markdown


def test_keeps_relative_image_urls():
    markdown = html_to_markdown(
        '<p><img src="/attachments/token/abc123/?name=image.png" alt="diagram"></p>'
    )
    assert "/attachments/token/abc123/?name=image.png" in markdown


def test_filename_and_hash_are_stable():
    article = {
        "id": 360051014713,
        "html_url": "https://support.optisigns.com/hc/en-us/articles/360051014713-How-to-Use-YouTube-with-OptiSigns",
        "title": "How to Use YouTube with OptiSigns",
        "body": "<p>Hello</p>",
    }
    assert (
        article_filename(article)
        == "360051014713-How-to-Use-YouTube-with-OptiSigns.md"
    )
    markdown = article_to_markdown(article)
    assert content_hash(markdown) == content_hash(markdown)
    assert content_hash(markdown) != content_hash(markdown + " ")
