import pytest

from system_prompt_eval.wikipedia import search_wikipedia


def test_search_wikipedia_empty_query():
    assert "empty" in search_wikipedia("   ").lower()


def test_search_wikipedia_no_results(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResp:
        def __init__(self, payload: dict) -> None:
            self._payload = payload

        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict:
            return self._payload

    class FakeClient:
        def __init__(self, *a: object, **kw: object) -> None:
            pass

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *a: object) -> None:
            pass

        def get(self, url: str, params: dict | None = None) -> FakeResp:
            return FakeResp({"query": {"search": []}})

    monkeypatch.setattr("system_prompt_eval.wikipedia.httpx.Client", FakeClient)
    out = search_wikipedia("xyznonexistent12345")
    assert "No Wikipedia" in out or "no" in out.lower()


def test_search_wikipedia_parses_hits(monkeypatch: pytest.MonkeyPatch) -> None:
    search_payload = {
        "query": {
            "search": [
                {
                    "title": "Paris",
                    "snippet": "Capital city of <span class=\"searchmatch\">France</span>.",
                }
            ]
        }
    }
    extract_payload = {
        "query": {
            "pages": {
                "1": {
                    "title": "Paris",
                    "extract": "Paris is the capital and largest city of France.",
                }
            }
        }
    }

    class FakeResp:
        def __init__(self, payload: dict) -> None:
            self._payload = payload

        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict:
            return self._payload

    class FakeClient:
        def __init__(self, *a: object, **kw: object) -> None:
            pass

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *a: object) -> None:
            pass

        def get(self, url: str, params: dict | None = None) -> FakeResp:
            p = params or {}
            if p.get("list") == "search":
                return FakeResp(search_payload)
            if p.get("prop") == "extracts":
                return FakeResp(extract_payload)
            return FakeResp({})

    monkeypatch.setattr("system_prompt_eval.wikipedia.httpx.Client", FakeClient)
    out = search_wikipedia("Paris")
    assert "Paris" in out
    assert "France" in out
    assert "_Lead_" in out or "capital" in out.lower()


@pytest.mark.network
def test_search_wikipedia_live_smoke():
    """Live HTTP; prints only if you run ``pytest -s`` (stdout is captured by default)."""
    out = search_wikipedia("Apollo 11", limit=2)
    print("\n--- search_wikipedia('Apollo 11', limit=2) ---\n", out, "\n--- end ---\n", sep="")
    assert "Apollo" in out
