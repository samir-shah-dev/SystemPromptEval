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


def search_wikipedia(query: str, *, limit: int = 5) -> str:
    """
    Search English Wikipedia and return titles plus plain-text search snippets.

    Uses ``action=query&list=search`` (no second-hop full-article fetch yet).
    """
    q = (query or "").strip()
    if not q:
        return "Error: empty query."

    limit = max(1, min(int(limit), 10))
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

    blocks: list[str] = []
    for hit in searches:
        title = hit.get("title", "")
        snippet = _strip_html(hit.get("snippet", ""))
        blocks.append(f"## {title}\n{snippet}\n")

    return "\n".join(blocks).strip()
