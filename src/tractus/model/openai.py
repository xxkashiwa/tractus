from __future__ import annotations

from typing import Any

from openai import OpenAI

from ..config import Settings


def create_openai_client(settings: Settings) -> OpenAI:
    return OpenAI(api_key=settings.api_key, base_url=settings.base_url)


def chat_text(
    *,
    client: OpenAI,
    model: str,
    user_message: str,
    system_prompt: str = "You are a helpful assistant.",
) -> str:
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )

    message: Any = completion.choices[0].message
    return message.content
