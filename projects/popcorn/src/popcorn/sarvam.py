"""Small REST client for Sarvam's tool-capable OpenAI-compatible chat API."""

from __future__ import annotations

import json
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from popcorn.config import configured_value


class SarvamError(RuntimeError):
    """Safe, user-facing Sarvam API error."""


API_URL = "https://api.sarvam.ai/v2/chat/completions"
DEFAULT_MODEL = "sarvam-105b"


def api_key() -> str:
    return configured_value("SARVAM_API_KEY")


def model_name() -> str:
    return configured_value("SARVAM_MODEL") or DEFAULT_MODEL


def _post_json(
    payload: dict[str, Any],
    key: str,
    *,
    timeout: float,
    get_bytes: Callable[[str, bytes, dict[str, str], float], bytes] | None = None,
) -> dict[str, Any]:
    if not key:
        raise SarvamError("Sarvam is not configured. Set SARVAM_API_KEY on the server.")
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "api-subscription-key": key,
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
        if error.code in (401, 403):
            raise SarvamError(f"Sarvam rejected the API key or access (HTTP {error.code}). Check SARVAM_API_KEY and model access.") from None
        if error.code == 429:
            raise SarvamError("Sarvam rate limit or quota reached (HTTP 429). Check the account quota and try again later.") from None
        raise SarvamError(f"Sarvam request failed with HTTP {error.code}.") from None
    except (TimeoutError, URLError, OSError):
        raise SarvamError("Sarvam could not be reached. Check the network and try again.") from None
    try:
        data = json.loads(result)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise SarvamError("Sarvam returned an unreadable response.") from None
    if not isinstance(data, dict):
        raise SarvamError("Sarvam returned an unexpected response.")
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
    """Request one bounded tool-capable completion from Sarvam."""
    payload: dict[str, Any] = {
        "model": model or model_name(),
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
        "max_tokens": 800,
        "reasoning_effort": "none",
    }
    return _post_json(
        payload,
        key if key is not None else api_key(),
        timeout=timeout,
        get_bytes=get_bytes,
    )
