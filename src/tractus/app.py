from __future__ import annotations

from pathlib import Path

from flasgger import Swagger, swag_from
from flask import Flask, jsonify, request

from .config import get_settings
from .llm import chat_text, create_openai_client


def create_app() -> Flask:
    app = Flask(__name__)

    Swagger(
        app,
        template={
            "swagger": "2.0",
            "info": {
                "title": "Tractus API",
                "version": "0.1.0",
                "description": "Minimal Flask backend for OpenAI-compatible chat",
            },
        },
    )

    swagger_dir = Path(__file__).resolve().parent / "swagger"

    @app.get("/health")
    @swag_from(str(swagger_dir / "health.yml"))
    def health():
        return jsonify({"ok": True})

    @app.post("/chat")
    @swag_from(str(swagger_dir / "chat.yml"))
    def chat():
        payload = request.get_json(silent=True) or {}
        message = payload.get("message")
        model = payload.get("model")

        if not isinstance(message, str) or not message.strip():
            return (
                jsonify({"error": "Field 'message' must be a non-empty string."}),
                400,
            )

        settings = get_settings()
        client = create_openai_client(settings)
        text = chat_text(
            client=client,
            model=model or settings.model,
            user_message=message,
        )
        return jsonify({"text": text})

    return app
