"""Small REST client for Gemini function calling, normalized for the agent loop."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from popcorn.config import configured_value


class GeminiError(RuntimeError):
    """Safe, user-facing Gemini API error."""


class GeminiUnavailableError(GeminiError):
    """Retryable Gemini service overload response."""


DEFAULT_MODEL = "gemini-3.8-flash"
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
RETRY_DELAYS_SECONDS = (1, 2)


def api_key() -> str:
    return configured_value("GEMINI_API_KEY")


def model_name() -> str:
    return configured_value("GEMINI_MODEL") or DEFAULT_MODEL


def _schema_to_gemini(schema: Any) -> Any:
    if isinstance(schema, list):
        return [_schema_to_gemini(value) for value in schema]
    if not isinstance(schema, dict):
        return schema
    result = {}
    for key, value in schema.items():
        if key == "additionalProperties":
            continue
        if key == "type" and isinstance(value, str):
            result[key] = value.upper()
        else:
            result[key] = _schema_to_gemini(value)
    return result


def _convert_messages(messages: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    contents: list[dict[str, Any]] = []
    system_instruction = None
    call_names: dict[str, str] = {}
    for message in messages:
        role = message.get("role")
        if role == "system":
            system_instruction = {"parts": [{"text": str(message.get("content") or "")}]}
        elif role in {"user", "assistant"}:
            if role == "assistant" and isinstance(message.get("tool_calls"), list):
                parts = []
                for call in message["tool_calls"]:
                    function = call.get("function", {})
                    name = function.get("name")
                    call_id = call.get("id")
                    try:
                        args = json.loads(function.get("arguments", "{}"))
                    except (TypeError, json.JSONDecodeError):
                        args = {}
                    if isinstance(name, str):
                        part_call: dict[str, Any] = {"name": name, "args": args}
                        if isinstance(call_id, str):
                            part_call["id"] = call_id
                            call_names[call_id] = name
                        signature = call.get("gemini_thought_signature")
                        if isinstance(signature, str):
                            part_call["thoughtSignature"] = signature
                        parts.append({"functionCall": part_call})
                if parts:
                    contents.append({"role": "model", "parts": parts})
            else:
                text = message.get("content")
                if isinstance(text, str) and text:
                    contents.append({"role": "model" if role == "assistant" else "user", "parts": [{"text": text}]})
        elif role == "tool":
            call_id = message.get("tool_call_id")
            name = call_names.get(call_id, "unknown_tool")
            text = message.get("content")
            contents.append({"role": "user", "parts": [{"functionResponse": {
                "name": name,
                "response": {"result": text if isinstance(text, str) else str(text)},
                **({"id": call_id} if isinstance(call_id, str) else {}),
            }}]})
    return contents, system_instruction


def _convert_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    declarations = []
    for tool in tools:
        function = tool.get("function", {})
        if not isinstance(function, dict):
            continue
        declaration = {
            key: _schema_to_gemini(function[key])
            for key in ("name", "description", "parameters")
            if key in function
        }
        declarations.append(declaration)
    return [{"functionDeclarations": declarations}] if declarations else []


def _post_json(
    model: str,
    payload: dict[str, Any],
    key: str,
    *,
    timeout: float,
    get_bytes: Callable[[str, bytes, dict[str, str], float], bytes] | None = None,
) -> dict[str, Any]:
    if not key:
        raise GeminiError("Gemini is not configured. Set GEMINI_API_KEY on the server.")
    url = API_URL.format(model=quote(model, safe=""))
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "x-goog-api-key": key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    try:
        if get_bytes is None:
            request = Request(url, data=body, headers=headers, method="POST")
            with urlopen(request, timeout=timeout) as response:
                result = response.read()
        else:
            result = get_bytes(url, body, headers, timeout)
    except HTTPError as error:
        if error.code == 503:
            raise GeminiUnavailableError("Gemini is temporarily unavailable (HTTP 503).") from None
        if error.code in (401, 403):
            raise GeminiError(f"Gemini rejected the API key or access (HTTP {error.code}). Check GEMINI_API_KEY and model access.") from None
        if error.code == 429:
            raise GeminiError("Gemini rate limit or quota reached (HTTP 429). Check the project quota and try again later.") from None
        if error.code == 402:
            raise GeminiError("Gemini request failed with HTTP 402. Check the Google AI project billing and quota.") from None
        raise GeminiError(f"Gemini request failed with HTTP {error.code}.") from None
    except (TimeoutError, URLError, OSError):
        raise GeminiError("Gemini could not be reached. Check the network and try again.") from None
    try:
        data = json.loads(result)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise GeminiError("Gemini returned an unreadable response.") from None
    if not isinstance(data, dict):
        raise GeminiError("Gemini returned an unexpected response.")
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
    """Request one function-capable Gemini response and normalize it to Chat Completions shape."""
    selected_model = model or model_name()
    contents, system_instruction = _convert_messages(messages)
    payload: dict[str, Any] = {
        "contents": contents,
        "tools": _convert_tools(tools),
        "generationConfig": {"maxOutputTokens": 800},
    }
    if system_instruction:
        payload["systemInstruction"] = system_instruction
    data = None
    for delay in (*RETRY_DELAYS_SECONDS, None):
        try:
            data = _post_json(
                selected_model,
                payload,
                key if key is not None else api_key(),
                timeout=timeout,
                get_bytes=get_bytes,
            )
            break
        except GeminiUnavailableError:
            if delay is None:
                raise GeminiError(
                    "Gemini is temporarily unavailable (HTTP 503) after retrying. Try again shortly."
                ) from None
            await asyncio.sleep(delay)
    if data is None:
        raise GeminiError("Gemini returned no response.")
    candidates = data.get("candidates")
    if not isinstance(candidates, list) or not candidates or not isinstance(candidates[0], dict):
        raise GeminiError("Gemini returned no candidate response.")
    content = candidates[0].get("content")
    parts = content.get("parts") if isinstance(content, dict) else None
    if not isinstance(parts, list):
        raise GeminiError("Gemini returned an unexpected candidate response.")
    text_parts = []
    tool_calls = []
    for index, part in enumerate(parts):
        if not isinstance(part, dict):
            continue
        if isinstance(part.get("text"), str):
            text_parts.append(part["text"])
        function_call = part.get("functionCall")
        if isinstance(function_call, dict) and isinstance(function_call.get("name"), str):
            normalized_call = {
                "id": function_call.get("id") or f"gemini_call_{index}",
                "type": "function",
                "function": {
                    "name": function_call["name"],
                    "arguments": json.dumps(function_call.get("args", {})),
                },
            }
            signature = part.get("thoughtSignature")
            if isinstance(signature, str):
                normalized_call["gemini_thought_signature"] = signature
            tool_calls.append(normalized_call)
    message: dict[str, Any] = {"content": "\n".join(text_parts) or None}
    if tool_calls:
        message["tool_calls"] = tool_calls
    usage = data.get("usageMetadata", {})
    normalized: dict[str, Any] = {"choices": [{"message": message}]}
    if isinstance(usage, dict):
        normalized["usage"] = {
            "prompt_tokens": usage.get("promptTokenCount"),
            "completion_tokens": usage.get("candidatesTokenCount"),
        }
    return normalized
