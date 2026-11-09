import asyncio
import json
from urllib.error import HTTPError

import pytest

from popcorn.gemini import API_URL, GeminiError, chat_completion


def test_gemini_function_call_is_normalized_for_agent_loop():
    captured = {}

    def fake_post(url, body, headers, timeout):
        captured.update(url=url, body=json.loads(body), headers=headers, timeout=timeout)
        return json.dumps({
            "candidates": [{"content": {"parts": [{
                "functionCall": {"name": "actor_filmography", "args": {"person_name": "Keanu Reeves"}, "id": "call-4"},
                "thoughtSignature": "opaque-signature",
            }]}}],
            "usageMetadata": {"promptTokenCount": 12, "candidatesTokenCount": 4},
        }).encode()

    result = asyncio.run(chat_completion(
        [
            {"role": "system", "content": "Use tools."},
            {"role": "user", "content": "Find Keanu Reeves's movies."},
        ],
        [{"type": "function", "function": {
            "name": "actor_filmography",
            "description": "List movie credits.",
            "parameters": {"type": "object", "properties": {"person_name": {"type": "string"}}, "required": ["person_name"], "additionalProperties": False},
        }}],
        key="test-secret",
        model="gemini-test-model",
        get_bytes=fake_post,
    ))

    assert captured["url"] == API_URL.format(model="gemini-test-model")
    assert captured["headers"]["x-goog-api-key"] == "test-secret"
    assert "test-secret" not in captured["url"]
    assert captured["body"]["systemInstruction"]["parts"][0]["text"] == "Use tools."
    declaration = captured["body"]["tools"][0]["functionDeclarations"][0]
    assert declaration["parameters"]["type"] == "OBJECT"
    assert "additionalProperties" not in declaration["parameters"]
    message = result["choices"][0]["message"]
    assert message["tool_calls"][0]["function"]["name"] == "actor_filmography"
    assert json.loads(message["tool_calls"][0]["function"]["arguments"]) == {"person_name": "Keanu Reeves"}
    assert message["tool_calls"][0]["gemini_thought_signature"] == "opaque-signature"
    assert result["usage"] == {"prompt_tokens": 12, "completion_tokens": 4}


def test_gemini_serializes_function_result_for_followup_request():
    captured = {}

    def fake_post(_url, body, _headers, _timeout):
        captured["body"] = json.loads(body)
        return b'{"candidates":[{"content":{"parts":[{"text":"Found the credits."}]}}]}'

    asyncio.run(chat_completion(
        [
            {"role": "user", "content": "Find credits."},
            {"role": "assistant", "content": None, "tool_calls": [{
                "id": "call-1", "type": "function", "gemini_thought_signature": "opaque-signature", "function": {"name": "actor_filmography", "arguments": "{\"person_name\":\"Keanu Reeves\"}"}
            }]},
            {"role": "tool", "tool_call_id": "call-1", "content": "The Matrix (1999)"},
        ],
        [], key="test-secret", get_bytes=fake_post,
    ))
    contents = captured["body"]["contents"]
    assert contents[-2]["role"] == "model"
    assert contents[-2]["parts"][0]["functionCall"]["thoughtSignature"] == "opaque-signature"
    assert contents[-1]["parts"][0]["functionResponse"]["name"] == "actor_filmography"
    assert contents[-1]["parts"][0]["functionResponse"]["id"] == "call-1"


def test_gemini_sanitizes_authentication_error():
    def unauthorized(_url, _body, _headers, _timeout):
        raise HTTPError("https://example.invalid", 403, "forbidden", {}, None)

    with pytest.raises(GeminiError, match="rejected the API key") as error:
        asyncio.run(chat_completion([], [], key="test-secret", get_bytes=unauthorized))
    assert "test-secret" not in str(error.value)
