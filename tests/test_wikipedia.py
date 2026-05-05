import pytest

from system_prompt_eval.wikipedia import search_wikipedia


def test_search_wikipedia_empty_query():
    assert "empty" in search_wikipedia("   ").lower()


def test_search_wikipedia_no_results(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResp:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict:
            return {"query": {"search": []}}

    class FakeClient:
        def __init__(self, *a: object, **kw: object) -> None:
            pass

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *a: object) -> None:
            pass

        def get(self, url: str, params: dict) -> FakeResp:
            return FakeResp()

    monkeypatch.setattr("system_prompt_eval.wikipedia.httpx.Client", FakeClient)
    out = search_wikipedia("xyznonexistent12345")
    assert "No Wikipedia" in out or "no" in out.lower()


def test_search_wikipedia_parses_hits(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResp:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict:
            return {
                "query": {
                    "search": [
                        {
                            "title": "Paris",
                            "snippet": "Capital city of <span class=\"searchmatch\">France</span>.",
                        }
                    ]
                }
            }

    class FakeClient:
        def __init__(self, *a: object, **kw: object) -> None:
            pass

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *a: object) -> None:
            pass

        def get(self, url: str, params: dict) -> FakeResp:
            return FakeResp()

    monkeypatch.setattr("system_prompt_eval.wikipedia.httpx.Client", FakeClient)
    out = search_wikipedia("Paris")
    assert "Paris" in out
    assert "France" in out


@pytest.mark.network
def test_search_wikipedia_live_smoke():
    """Live HTTP; prints only if you run ``pytest -s`` (stdout is captured by default)."""
    out = search_wikipedia("Apollo 11", limit=2)
    print("\n--- search_wikipedia('Apollo 11', limit=2) ---\n", out, "\n--- end ---\n", sep="")
    assert "Apollo" in out
