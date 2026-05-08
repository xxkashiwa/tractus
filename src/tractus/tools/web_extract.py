from __future__ import annotations

import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class DownloadDebugInfo:
    """下载调试信息。"""
    status: int | None = None
    error: str | None = None


@dataclass(frozen=True)
class WebExtractResult:
    """网页文本提取结果。"""
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
    """下载和提取网页的主要文本内容。

    使用 `trafilatura` 获取页面并提取可读文本。

    参数：
        url: 网页 URL。
        timeout: 网络超时时间（秒）。
        user_agent: 下载时使用的 User-Agent 头。

    返回值：
        包含提取的纯文本的 WebExtractResult。

    异常：
        ValueError: 如果 url 为空。
        RuntimeError: 如果下载失败或无法提取文本。
    """

    url = (url or "").strip()
    if not url:
        raise ValueError("url must be non-empty")

    try:
        import trafilatura
        from trafilatura.settings import use_config
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "缺少依赖 'trafilatura'。请安装它（例如 pip install trafilatura）。"
        ) from exc

    config = use_config()
    config.set("DEFAULT", "USER_AGENT", user_agent)
    config.set("DEFAULT", "DOWNLOAD_TIMEOUT", str(timeout))

    downloaded = trafilatura.fetch_url(url, config=config)
    debug = DownloadDebugInfo()
    if not downloaded:
        # 使用 urllib 作为备选方案下载
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
            "无法下载 URL"
            f"{extra}: {url}\n"
            "提示：某些网站（例如 Medium）对非浏览器客户端返回 403。"
            "尝试不同的源，或通过 CLI -H 传递浏览器类型的头/Cookie。"
        )

    # 提取文本内容
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
        raise RuntimeError(f"无法从 URL 提取文本：{url}")

    # 提取标题
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
    """使用 urllib 下载网页。
    
    参数：
        url: 要下载的 URL。
        timeout: 超时时间（秒）。
        user_agent: User-Agent 头。
        headers: 额外的请求头。
    
    返回值：
        (下载内容, 调试信息) 元组。
    """
    # 构建请求头
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
        # HTTPError 也是异常；如果存在则记录状态
        status = getattr(exc, "code", None)
        return None, DownloadDebugInfo(status=status, error=str(exc))

    # 尽力解码；trafilatura 接受 str
    encoding = (charset or "utf-8").strip() or "utf-8"
    try:
        return raw.decode(encoding), DownloadDebugInfo(status=status)
    except Exception:
        return raw.decode("utf-8", errors="replace"), DownloadDebugInfo(status=status)
