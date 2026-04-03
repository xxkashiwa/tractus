from __future__ import annotations

import argparse
import sys


def _cmd_serve(args: argparse.Namespace) -> int:
    from ..flask import create_app

    app = create_app()
    port = args.port if args.port is not None else 8000
    app.run(host="127.0.0.1", port=port, debug=args.debug)
    return 0


def _cmd_chat(args: argparse.Namespace) -> int:
    from ..config import get_settings
    from ..model import chat_text, create_openai_client

    message = " ".join(args.message).strip()
    if not message:
        raise SystemExit("Missing message. Usage: poe chat 你好")

    settings = get_settings()
    client = create_openai_client(settings)

    text = chat_text(
        client=client,
        model=settings.model,
        user_message=message,
    )
    print(text)
    return 0


def _cmd_search(args: argparse.Namespace) -> int:
    from .web_search import web_search

    query = " ".join(args.query).strip()
    if not query:
        raise SystemExit(
            "Missing query. Usage: python -m tractus.tools.cli search 关键词"
        )

    try:
        results = web_search(query, max_results=int(args.max_results))
        for i, r in enumerate(results, start=1):
            print(f"[{i}] {r.title}")
            print(r.url)
            if r.snippet:
                print(r.snippet)
            print()
    except BrokenPipeError:
        try:
            sys.stdout.close()
        except Exception:
            pass
        return 0

    return 0


def _cmd_extract(args: argparse.Namespace) -> int:
    from .web_extract import extract_webpage_text

    url = (args.url or "").strip()
    if not url:
        raise SystemExit(
            "Missing url. Usage: python -m tractus.tools.cli extract https://example.com"
        )

    headers: dict[str, str] = {}
    for raw in args.header or []:
        if ":" not in raw:
            raise SystemExit("Invalid header format. Use -H 'Name: Value'")
        name, value = raw.split(":", 1)
        name = name.strip()
        value = value.lstrip()
        if not name:
            raise SystemExit("Invalid header name in -H")
        headers[name] = value

    try:
        result = extract_webpage_text(
            url,
            timeout=float(args.timeout),
            user_agent=str(args.user_agent),
            headers=headers or None,
        )
        if result.title:
            print(result.title)
            print()
        print(result.text)
    except BrokenPipeError:
        try:
            sys.stdout.close()
        except Exception:
            pass
        return 0
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tractus.tools.cli",
        description="CLI utilities for Tractus.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="Start Flask dev server")
    serve.add_argument("port", nargs="?", type=int, help="Port (default: 8000)")
    serve.add_argument("--debug", action="store_true")
    serve.set_defaults(func=_cmd_serve)

    chat = sub.add_parser("chat", help="Send a single chat message and print the reply")
    chat.add_argument(
        "message",
        nargs=argparse.REMAINDER,
        help="Message text. Example: poe chat 你好",
    )
    chat.set_defaults(func=_cmd_chat)

    search = sub.add_parser("search", help="Search the web via DuckDuckGo")
    search.add_argument(
        "query",
        nargs="+",
        help="Query text. Example: python -m tractus.tools.cli search flask quickstart",
    )
    search.add_argument(
        "--max-results",
        type=int,
        default=5,
        help="Maximum number of results to print (default: 5)",
    )
    search.set_defaults(func=_cmd_search)

    extract = sub.add_parser("extract", help="Extract main text from a web page")
    extract.add_argument("url", help="Web page URL")
    extract.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="Download timeout in seconds (default: 15)",
    )
    extract.add_argument(
        "--user-agent",
        default="Mozilla/5.0",
        help="User-Agent header (default: Mozilla/5.0)",
    )
    extract.add_argument(
        "-H",
        "--header",
        action="append",
        help="Extra HTTP header, can be repeated. Example: -H 'Cookie: ...'",
    )
    extract.set_defaults(func=_cmd_extract)

    return parser


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    # Windows consoles may default to legacy encodings (e.g. gbk/cp936) which can
    # crash printing Unicode. Never fail due to encoding.
    stdout_reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(stdout_reconfigure):
        try:
            stdout_reconfigure(errors="replace")
        except Exception:
            pass

    stderr_reconfigure = getattr(sys.stderr, "reconfigure", None)
    if callable(stderr_reconfigure):
        try:
            stderr_reconfigure(errors="replace")
        except Exception:
            pass

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except BrokenPipeError:
        try:
            sys.stdout.close()
        except Exception:
            pass
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
