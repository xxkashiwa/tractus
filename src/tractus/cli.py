from __future__ import annotations

import argparse
import sys


def _cmd_serve(args: argparse.Namespace) -> int:
    from .app import create_app

    app = create_app()
    port = args.port if args.port is not None else 8000
    app.run(host="127.0.0.1", port=port, debug=args.debug)
    return 0


def _cmd_chat(args: argparse.Namespace) -> int:
    from .config import get_settings
    from .llm import chat_text, create_openai_client

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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tractus.cli",
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

    return parser


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    # Some task runners (e.g. poethepoet) may forward a standalone "--".
    # Strip it so argparse can still parse the actual options.
    argv = [item for item in argv if item != "--"]

    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
