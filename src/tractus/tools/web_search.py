from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class WebSearchResult:
    title: str
    url: str
    snippet: str | None = None
    source: str = "duckduckgo"


Backend = Literal["auto", "library", "instant-answer"]


def web_search(
    query: str,
    *,
    max_results: int = 5,
    region: str = "wt-wt",
    safesearch: str = "moderate",
    timelimit: str | None = None,
    backend: Backend = "auto",
    timeout: float = 10.0,
) -> list[WebSearchResult]:
    """Search the web via DuckDuckGo.

    Prefers the `ddgs` library (richer results). If the library is unavailable
    or `backend="instant-answer"` is chosen, falls back to
    DuckDuckGo's Instant Answer API (more limited results).

    Args:
        query: Search query.
        max_results: Maximum number of results to return (best-effort).
        region: DuckDuckGo region code (e.g. "us-en", "cn-zh", "wt-wt").
        safesearch: "on" | "moderate" | "off".
        timelimit: Optional time filter supported by the library backend.
        backend: "auto" | "library" | "instant-answer".
        timeout: Network timeout in seconds.

    Returns:
        A list of WebSearchResult.

    Raises:
        ValueError: On invalid arguments.
        RuntimeError: If the selected backend fails.
    """

    query = (query or "").strip()
    if not query:
        raise ValueError("query must be non-empty")

    if max_results <= 0:
        raise ValueError("max_results must be > 0")

    if backend not in ("auto", "library", "instant-answer"):
        raise ValueError("backend must be 'auto', 'library', or 'instant-answer'")

    if backend in ("auto", "library"):
        try:
            return _search_via_library(
                query,
                max_results=max_results,
                region=region,
                safesearch=safesearch,
                timelimit=timelimit,
            )
        except ModuleNotFoundError:
            if backend == "library":
                raise
        except Exception as exc:
            if backend == "library":
                raise RuntimeError(f"DuckDuckGo library search failed: {exc}") from exc

    try:
        return _search_via_instant_answer(
            query, max_results=max_results, timeout=timeout
        )
    except Exception as exc:
        raise RuntimeError(f"DuckDuckGo instant-answer search failed: {exc}") from exc


def _search_via_library(
    query: str,
    *,
    max_results: int,
    region: str,
    safesearch: str,
    timelimit: str | None,
) -> list[WebSearchResult]:
    DDGS = _import_ddgs_DDGS()

    results: list[WebSearchResult] = []

    with DDGS() as ddgs:
        # ddgs.text() yields dicts like: {"title": ..., "href": ..., "body": ...}
        for item in ddgs.text(
            query,
            region=region,
            safesearch=safesearch,
            timelimit=timelimit,
            max_results=max_results,
        ):
            if not isinstance(item, dict):
                continue

            title = str(item.get("title") or "").strip()
            url = str(item.get("href") or "").strip()
            snippet = str(item.get("body") or "").strip() or None

            if not title or not url:
                continue

            results.append(WebSearchResult(title=title, url=url, snippet=snippet))
            if len(results) >= max_results:
                break

    return results


def _import_ddgs_DDGS():
    """Import DDGS class from supported DuckDuckGo search libraries.

    Primary: `ddgs`.
    Secondary: `duckduckgo_search` (kept only as a compatibility fallback).
    """

    try:
        from ddgs import DDGS  # type: ignore

        return DDGS
    except ModuleNotFoundError:
        pass

    from duckduckgo_search import DDGS  # type: ignore

    return DDGS


def _search_via_instant_answer(
    query: str,
    *,
    max_results: int,
    timeout: float,
) -> list[WebSearchResult]:
    # NOTE: Instant Answer API is not a full web search API.
    # It may return 0 results for many queries.
    params = {
        "q": query,
        "format": "json",
        "no_html": "1",
        "skip_disambig": "1",
    }
    url = "https://api.duckduckgo.com/?" + urllib.parse.urlencode(params)

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "tractus/0.1 (+https://duckduckgo.com/)",
        },
        method="GET",
    )

    with urllib.request.urlopen(request, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    results: list[WebSearchResult] = []

    abstract_text = (data.get("AbstractText") or "").strip()
    abstract_url = (data.get("AbstractURL") or "").strip()
    heading = (data.get("Heading") or "").strip()
    if abstract_url and (heading or abstract_text):
        results.append(
            WebSearchResult(
                title=heading or query,
                url=abstract_url,
                snippet=abstract_text or None,
                source="duckduckgo_instant_answer",
            )
        )

    # 'Results' is often empty; 'RelatedTopics' may contain useful links.
    for item in _flatten_related_topics(data.get("Results") or []):
        if len(results) >= max_results:
            break
        results.append(item)

    if len(results) < max_results:
        for item in _flatten_related_topics(data.get("RelatedTopics") or []):
            if len(results) >= max_results:
                break
            results.append(item)

    # De-duplicate by URL (preserving order)
    seen: set[str] = set()
    deduped: list[WebSearchResult] = []
    for r in results:
        if r.url in seen:
            continue
        seen.add(r.url)
        deduped.append(r)

    return deduped[:max_results]


def _flatten_related_topics(items: list[object]) -> list[WebSearchResult]:
    out: list[WebSearchResult] = []

    for raw in items:
        if (
            isinstance(raw, dict)
            and "Topics" in raw
            and isinstance(raw["Topics"], list)
        ):
            out.extend(_flatten_related_topics(raw["Topics"]))
            continue

        if not isinstance(raw, dict):
            continue

        text = str(raw.get("Text") or "").strip()
        first_url = str(raw.get("FirstURL") or "").strip()
        if not first_url:
            continue

        title = text.split(" - ", 1)[0].strip() if text else first_url
        snippet = None
        if text and " - " in text:
            snippet = text.split(" - ", 1)[1].strip() or None

        out.append(
            WebSearchResult(
                title=title,
                url=first_url,
                snippet=snippet,
                source="duckduckgo_instant_answer",
            )
        )

    return out
