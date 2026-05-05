"""Wikipedia retrieval via the MediaWiki Action API."""

from __future__ import annotations

import re
from html import unescape

import httpx

_API = "https://en.wikipedia.org/w/api.php"
# https://meta.wikimedia.org/wiki/User-Agent_policy
_USER_AGENT = (
    "SystemPromptEval/0.1 (local eval project; Python httpx) "
    "+https://www.mediawiki.org/wiki/API:Etiquette"
)


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", "", html)
    return unescape(text).replace("\n", " ").strip()


def _fetch_extracts(client: httpx.Client, titles: list[str], *, exchars: int = 1200) -> dict[str, str]:
    """Map canonical page title -> plain-text lead extract (best effort)."""
    if not titles:
        return {}
    params = {
        "action": "query",
        "prop": "extracts",
        "exintro": "true",
        "explaintext": "true",
        "exchars": str(exchars),
        "redirects": "1",
        "titles": "|".join(titles),
        "format": "json",
    }
    r = client.get(_API, params=params)
    r.raise_for_status()
    data = r.json()
    pages = (data.get("query") or {}).get("pages") or {}
    out: dict[str, str] = {}
    for _pid, page in pages.items():
        if not isinstance(page, dict) or page.get("missing"):
            continue
        title = page.get("title") or ""
        ext = page.get("extract") or ""
        if title and ext:
            out[title] = ext.strip()
    return out


def search_wikipedia(query: str, *, limit: int = 5, extract_top_n: int = 3) -> str:
    """
    Search English Wikipedia: ranked hits with snippets, plus lead extracts for the top results.

    Two API calls: ``list=search``, then ``prop=extracts`` for the first ``extract_top_n`` titles.
    """
    q = (query or "").strip()
    if not q:
        return "Error: empty query."

    limit = max(1, min(int(limit), 10))
    extract_top_n = max(0, min(int(extract_top_n), limit))

    params = {
        "action": "query",
        "list": "search",
        "srsearch": q,
        "format": "json",
        "srlimit": str(limit),
    }
    headers = {"User-Agent": _USER_AGENT}

    with httpx.Client(timeout=30.0, headers=headers) as client:
        r = client.get(_API, params=params)
        r.raise_for_status()
        data = r.json()

        if "error" in data:
            return f"Wikipedia API error: {data['error']}"

        searches = (data.get("query") or {}).get("search") or []
        if not searches:
            return f"No Wikipedia search hits for query: {q!r}"

        titles_for_extracts = [h.get("title", "") for h in searches[:extract_top_n] if h.get("title")]
        extracts: dict[str, str] = {}
        if titles_for_extracts:
            try:
                extracts = _fetch_extracts(client, titles_for_extracts)
            except (httpx.HTTPError, KeyError, ValueError):
                extracts = {}

        blocks: list[str] = []
        blocks.append(f"# Wikipedia results for query: {q}\n")
        for hit in searches:
            title = hit.get("title", "")
            snippet = _strip_html(hit.get("snippet", ""))
            body = [f"## {title}", f"_Snippet:_ {snippet}"]
            ext = extracts.get(title)
            if ext:
                clip = ext if len(ext) <= 1600 else ext[:1600].rsplit(" ", 1)[0] + " …"
                body.append(f"_Lead:_\n{clip}")
            blocks.append("\n".join(body) + "\n")

    return "\n".join(blocks).strip()
