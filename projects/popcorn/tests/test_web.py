import asyncio
import json

from popcorn import web


class FakeTrace:
    def to_dict(self):
        return {"schema_version": "0.1", "events": []}


def _request(body: bytes, *, content_length: str | None = None):
    headers = [(b"content-type", b"application/json")]
    if content_length is not None:
        headers.append((b"content-length", content_length.encode()))

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/chat",
        "raw_path": b"/api/chat",
        "query_string": b"",
        "headers": headers,
        "server": ("testserver", 80),
        "client": ("testclient", 123),
    }
    return web.Request(scope, receive)


def test_homepage_and_health_are_served():
    async def run():
        home = await web.homepage(None)
        health = await web.health(None)
        return home.body, health.body

    home, health = asyncio.run(run())
    assert b"Entertainment discovery" in home
    assert json.loads(health) == {"status": "ok"}


def test_chat_endpoint_routes_question_and_returns_trace(monkeypatch):
    async def fake_answer(question):
        assert question == "Tell me about The Matrix"
        return "Found the movie.", FakeTrace()

    monkeypatch.setattr(web, "answer", fake_answer)
    request = _request(b'{"message":"Tell me about The Matrix"}')
    response = asyncio.run(web.chat(request))

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "reply": "Found the movie.",
        "trace": {"schema_version": "0.1", "events": []},
    }


def test_chat_endpoint_rejects_invalid_or_oversized_input():
    async def run():
        invalid = await web.chat(_request(b"no json"))
        oversized = await web.chat(
            _request(b"{}", content_length=str(web.MAX_REQUEST_BYTES + 1))
        )
        return invalid, oversized

    invalid, oversized = asyncio.run(run())
    assert invalid.status_code == 400
    assert oversized.status_code == 413
