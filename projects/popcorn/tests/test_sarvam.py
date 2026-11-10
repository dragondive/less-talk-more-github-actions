import asyncio
import json
from urllib.error import HTTPError

import pytest

from popcorn.sarvam import API_URL, SarvamError, chat_completion


def test_chat_completion_sends_tool_call_request_with_api_key():
    captured = {}

    def fake_post(url, body, headers, timeout):
        captured.update(url=url, body=json.loads(body), headers=headers, timeout=timeout)
        return b'{"choices": []}'

    result = asyncio.run(chat_completion(
        [{"role": "user", "content": "Find a movie"}],
        [{"type": "function", "function": {"name": "movie_discovery"}}],
        key="test-secret", model="sarvam-105b", get_bytes=fake_post,
    ))

    assert result == {"choices": []}
    assert captured["url"] == API_URL
    assert captured["headers"]["api-subscription-key"] == "test-secret"
    assert captured["headers"]["Authorization"] == "Bearer test-secret"
    assert captured["body"]["model"] == "sarvam-105b"
    assert captured["body"]["tool_choice"] == "auto"
    assert captured["body"]["reasoning_effort"] == "none"


def test_chat_completion_sanitizes_authentication_errors():
    def unauthorized(_url, _body, _headers, _timeout):
        raise HTTPError(API_URL, 401, "unauthorized", {}, None)

    with pytest.raises(SarvamError, match="rejected the API key") as error:
        asyncio.run(chat_completion([], [], key="test-secret", get_bytes=unauthorized))
    assert "test-secret" not in str(error.value)


def test_chat_completion_handles_quota_and_invalid_response():
    def limited(_url, _body, _headers, _timeout):
        raise HTTPError(API_URL, 429, "limited", {}, None)

    with pytest.raises(SarvamError, match="quota"):
        asyncio.run(chat_completion([], [], key="test-secret", get_bytes=limited))
    with pytest.raises(SarvamError, match="unreadable"):
        asyncio.run(chat_completion([], [], key="test-secret", get_bytes=lambda *_: b"no json"))


def test_chat_completion_requires_key():
    with pytest.raises(SarvamError, match="SARVAM_API_KEY"):
        asyncio.run(chat_completion([], [], key=""))
