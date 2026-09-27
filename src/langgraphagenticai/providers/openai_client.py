from __future__ import annotations

from typing import Any

from langgraphagenticai.utils.safety import sanitize_error


DEFAULT_MODEL_TIMEOUT = 90.0
DEFAULT_MODEL_RETRIES = 1


def build_openai_client(api_key: str, *, timeout: float = DEFAULT_MODEL_TIMEOUT, max_retries: int = DEFAULT_MODEL_RETRIES):
    """Create the direct OpenAI client with consistent bounded behavior."""
    from openai import OpenAI

    return OpenAI(api_key=api_key, timeout=timeout, max_retries=max_retries)


def safe_model_error(error: BaseException | str) -> str:
    return sanitize_error(error, fallback="The model request failed.")
