from __future__ import annotations

import os
from dataclasses import dataclass


def _load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        # python-dotenv is optional.
        return


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model: str = "qwen-long"


def get_settings() -> Settings:
    _load_dotenv_if_available()

    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "Missing DASHSCOPE_API_KEY. Set it as an environment variable or put it in a .env file."
        )

    base_url = os.getenv("DASHSCOPE_BASE_URL", "").strip() or Settings.base_url
    model = os.getenv("DASHSCOPE_MODEL", "").strip() or Settings.model

    return Settings(api_key=api_key, base_url=base_url, model=model)
