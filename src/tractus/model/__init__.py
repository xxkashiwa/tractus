"""Model/LLM integration layer.

This package contains code that talks to external model providers.
"""

from .openai import chat_text, create_openai_client

__all__ = [
    "chat_text",
    "create_openai_client",
]
