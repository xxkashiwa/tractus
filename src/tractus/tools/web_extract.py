from __future__ import annotations

import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class DownloadDebugInfo:
    status: int | None = None
    error: str | None = None


@dataclass(frozen=True)
class WebExtractResult:
    url: str
    text: str
    title: str | None = None


def extract_webpage_text(
    url: str,
    *,
    timeout: float = 15.0,
    user_agent: str = "tractus/0.1",
    headers: dict[str, str] | None = None,
) -> WebExtractResult:
    """Download and extract main text content from a web page.

    Uses `trafilatura` to fetch the page and extract the readable text.

    Args:
        url: Web page URL.
        timeout: Network timeout in seconds.
        user_agent: User-Agent header used during download.

    Returns:
        WebExtractResult containing extracted plain text.

    Raises:
        ValueError: If url is empty.
        RuntimeError: If download fails or extraction yields no text.
    """

    url = (url or "").strip()
    if not url:
        raise ValueError("url must be non-empty")

    try:
        import trafilatura
        from trafilatura.settings import use_config
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Missing dependency 'trafilatura'. Install it (e.g. pip install trafilatura)."
        ) from exc

    config = use_config()
    config.set("DEFAULT", "USER_AGENT", user_agent)
    config.set("DEFAULT", "DOWNLOAD_TIMEOUT", str(timeout))

    downloaded = trafilatura.fetch_url(url, config=config)
    debug = DownloadDebugInfo()
    if not downloaded:
        downloaded, debug = _download_via_urllib(
            url,
            timeout=timeout,
            user_agent=user_agent,
            headers=headers,
        )

    if not downloaded:
        extra = ""
        if debug.status is not None:
            extra += f" (HTTP {debug.status})"
        if debug.error:
            extra += f": {debug.error}"
        raise RuntimeError(
            "Failed to download url"
            f"{extra}: {url}\n"
            "Tip: some sites (e.g. Medium) return 403 for non-browser clients. "
            "Try a different source, or pass browser-like headers/cookies via CLI -H."
        )

    text = trafilatura.extract(
        downloaded,
        url=url,
        include_comments=False,
        include_tables=False,
        output_format="txt",
        config=config,
    )
    text = (text or "").strip()
    if not text:
        raise RuntimeError(f"No extractable text from url: {url}")

    title = None
    try:
        meta = trafilatura.extract_metadata(downloaded, default_url=url)
        if meta and getattr(meta, "title", None):
            title = str(meta.title).strip() or None
    except Exception:
        title = None

    return WebExtractResult(url=url, text=text, title=title)


def _download_via_urllib(
    url: str,
    *,
    timeout: float,
    user_agent: str,
    headers: dict[str, str] | None,
) -> tuple[str | None, DownloadDebugInfo]:
    base_headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    if headers:
        base_headers.update(headers)

    request = urllib.request.Request(url, headers=base_headers, method="GET")

    status: int | None = None
    charset: str | None = None
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            status = getattr(resp, "status", None)
            raw = resp.read()
            try:
                charset = resp.headers.get_content_charset()  # type: ignore[attr-defined]
            except Exception:
                charset = None
    except Exception as exc:
        # HTTPError is also an exception; record status if present.
        status = getattr(exc, "code", None)
        return None, DownloadDebugInfo(status=status, error=str(exc))

    # Best-effort decode; trafilatura accepts str.
    encoding = (charset or "utf-8").strip() or "utf-8"
    try:
        return raw.decode(encoding), DownloadDebugInfo(status=status)
    except Exception:
        return raw.decode("utf-8", errors="replace"), DownloadDebugInfo(status=status)
