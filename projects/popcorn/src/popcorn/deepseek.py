"""Minimal async client for DeepSeek's OpenAI-compatible chat completions API."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class DeepSeekError(RuntimeError):
    """Safe, user-facing DeepSeek API error."""


ENV_FILE = Path(__file__).resolve().parents[4] / ".env"
API_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_MODEL = "deepseek-flash"


def _configured_value(name: str) -> str:
    value = os.getenv(name, "").strip()
    if value:
        return value
    try:
        lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if separator and key.strip() == name:
            return value.strip().strip("\"'")
    return ""


def api_key() -> str:
    return _configured_value("DEEPSEEK_API_KEY")


def model_name() -> str:
    return _configured_value("DEEPSEEK_MODEL") or DEFAULT_MODEL


def _post_json(
    payload: dict[str, Any],
    key: str,
    *,
    timeout: float,
    get_bytes: Callable[[str, bytes, dict[str, str], float], bytes] | None = None,
) -> dict[str, Any]:
    if not key:
        raise DeepSeekError("DeepSeek is not configured. Set DEEPSEEK_API_KEY on the server.")
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    try:
        if get_bytes is None:
            request = Request(API_URL, data=body, headers=headers, method="POST")
            with urlopen(request, timeout=timeout) as response:
                result = response.read()
        else:
            result = get_bytes(API_URL, body, headers, timeout)
    except HTTPError as error:
        if error.code == 401:
            raise DeepSeekError("DeepSeek rejected the API key (HTTP 401). Check DEEPSEEK_API_KEY.") from None
        if error.code == 429:
            raise DeepSeekError("DeepSeek rate limit or quota reached (HTTP 429). Try again later.") from None
        raise DeepSeekError(f"DeepSeek request failed with HTTP {error.code}.") from None
    except (TimeoutError, URLError, OSError):
        raise DeepSeekError("DeepSeek could not be reached. Check the network and try again.") from None
    try:
        data = json.loads(result)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise DeepSeekError("DeepSeek returned an unreadable response.") from None
    if not isinstance(data, dict):
        raise DeepSeekError("DeepSeek returned an unexpected response.")
    return data


async def chat_completion(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    *,
    key: str | None = None,
    model: str | None = None,
    timeout: float = 45,
    get_bytes: Callable[[str, bytes, dict[str, str], float], bytes] | None = None,
) -> dict[str, Any]:
    """Request one bounded tool-capable completion from DeepSeek."""
    payload: dict[str, Any] = {
        "model": model or model_name(),
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
        "max_tokens": 800,
        # DeepSeek's Chat Completions API requires non-thinking mode for tool_choice=auto.
        "thinking": {"type": "disabled"},
    }
    return _post_json(
        payload,
        key if key is not None else api_key(),
        timeout=timeout,
        get_bytes=get_bytes,
    )
