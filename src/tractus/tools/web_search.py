from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class WebSearchResult:
    """网页搜索结果。"""
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
    """通过 DuckDuckGo 搜索网络。

    优先使用 `ddgs` 库（结果更丰富）。如果库不可用
    或选择 `backend="instant-answer"`，则回退到
    DuckDuckGo 的 Instant Answer API（结果较少）。

    参数：
        query: 搜索查询。
        max_results: 返回的最大结果数（尽力而为）。
        region: DuckDuckGo 地区代码（例如 "us-en", "cn-zh", "wt-wt"）。
        safesearch: "on" | "moderate" | "off"。
        timelimit: 库后端支持的可选时间过滤。
        backend: "auto" | "library" | "instant-answer"。
        timeout: 网络超时时间（秒）。

    返回值：
        WebSearchResult 列表。

    异常：
        ValueError: 无效的参数。
        RuntimeError: 如果选定的后端失败。
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
                raise RuntimeError(f"DuckDuckGo 库搜索失败：{exc}") from exc

    try:
        return _search_via_instant_answer(
            query, max_results=max_results, timeout=timeout
        )
    except Exception as exc:
        raise RuntimeError(f"DuckDuckGo 即时回答搜索失败：{exc}") from exc


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
    """从支持的 DuckDuckGo 搜索库导入 DDGS 类。

    主要：`ddgs`。
    次要：`duckduckgo_search`（仅作为兼容性回退保留）。
    """

    try:
        # 尝试使用主库 ddgs
        from ddgs import DDGS  # type: ignore

        return DDGS
    except ModuleNotFoundError:
        pass

    # 回退到兼容性库
    from duckduckgo_search import DDGS  # type: ignore

    return DDGS


def _search_via_instant_answer(
    query: str,
    *,
    max_results: int,
    timeout: float,
) -> list[WebSearchResult]:
    # 注意：Instant Answer API 不是完整的网络搜索 API。
    # 对许多查询可能返回 0 个结果。
    params = {
        "q": query,
        "format": "json",
        "no_html": "1",
        "skip_disambig": "1",
    }
    url = "https://api.duckduckgo.com/?" + urllib.parse.urlencode(params)

    # 发送搜索请求
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

    # 'Results' 通常为空；'RelatedTopics' 可能包含有用的链接
    for item in _flatten_related_topics(data.get("Results") or []):
        if len(results) >= max_results:
            break
        results.append(item)

    if len(results) < max_results:
        for item in _flatten_related_topics(data.get("RelatedTopics") or []):
            if len(results) >= max_results:
                break
            results.append(item)

    # 按 URL 去重（保留顺序）
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
