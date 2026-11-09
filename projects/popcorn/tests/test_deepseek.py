import asyncio
import json
from urllib.error import HTTPError

import pytest

from popcorn.deepseek import API_URL, DeepSeekError, chat_completion


def test_chat_completion_sends_tool_call_request_with_api_key():
    captured = {}

    def fake_post(url, body, headers, timeout):
        captured.update(
            url=url,
            body=json.loads(body),
            headers=headers,
            timeout=timeout,
        )
        return b'{"choices": []}'

    result = asyncio.run(
        chat_completion(
            [{"role": "user", "content": "Who is in The Matrix?"}],
            [{"type": "function", "function": {"name": "movie_discovery"}}],
            key="test-secret",
            model="deepseek-flash",
            get_bytes=fake_post,
        )
    )

    assert result == {"choices": []}
    assert captured["url"] == API_URL
    assert captured["headers"]["Authorization"] == "Bearer test-secret"
    assert captured["body"]["model"] == "deepseek-flash"
    assert captured["body"]["tool_choice"] == "auto"
    assert captured["body"]["thinking"] == {"type": "disabled"}


def test_chat_completion_sanitizes_authentication_errors():
    def unauthorized(_url, _body, _headers, _timeout):
        raise HTTPError(API_URL, 401, "unauthorized", {}, None)

    with pytest.raises(DeepSeekError, match="rejected the API key") as error:
        asyncio.run(
            chat_completion([], [], key="test-secret", get_bytes=unauthorized)
        )
    assert "test-secret" not in str(error.value)
