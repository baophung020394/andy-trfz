from src.fetch import iter_articles


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self):
        self.headers = {}

    def get(self, url, timeout=60):
        if "page" in url:
            return FakeResponse(
                {
                    "articles": [
                        {"id": 1, "draft": False, "title": "One"},
                        {"id": 2, "draft": True, "title": "Draft"},
                    ],
                    "links": {"next": "https://example.test/next"},
                }
            )
        return FakeResponse(
            {
                "articles": [{"id": 3, "draft": False, "title": "Three"}],
                "links": {},
            }
        )


def test_iter_articles_paginates_and_skips_drafts():
    articles = list(
        iter_articles("https://example.test", locale="en-us", session=FakeSession())
    )
    assert [article["id"] for article in articles] == [1, 3]
