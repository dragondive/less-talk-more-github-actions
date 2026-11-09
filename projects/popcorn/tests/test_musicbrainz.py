import asyncio
import json
from urllib.error import HTTPError

import pytest

from popcorn.musicbrainz import MusicBrainzClient, MusicBrainzError
from popcorn import mcp_server, gemini, deepseek
from popcorn.agent import answer


def test_adapter_escapes_query_sets_user_agent_and_spaces_requests():
    calls, now, slept = [], [0.0], []

    def request(url, headers, timeout):
        calls.append((url, headers, timeout))
        return b'{"artists": []}'

    client = MusicBrainzClient(request_bytes=request, clock=lambda: now[0], sleeper=lambda s: (slept.append(s), now.__setitem__(0, now[0] + s)))
    asyncio.run(client.search_artists('A "Band"'))
    asyncio.run(client.search_artists("Again"))
    assert 'artist%3A%22A%20%5C%22Band%5C%22%22' in calls[0][0]
    assert "Popcorn/0.1.0" in calls[0][1]["User-Agent"]
    assert slept == [1.0]


def test_adapter_rejects_malformed_and_surfaces_503_without_retry():
    client = MusicBrainzClient(request_bytes=lambda *_: b"not-json")
    with pytest.raises(MusicBrainzError, match="unreadable"):
        asyncio.run(client.search_artists("x"))

    def unavailable(*_):
        raise HTTPError("url", 503, "busy", {}, None)
    client = MusicBrainzClient(request_bytes=unavailable)
    with pytest.raises(MusicBrainzError, match="HTTP 503"):
        asyncio.run(client.search_artists("x"))

    def timeout(*_):
        raise TimeoutError()
    client = MusicBrainzClient(request_bytes=timeout)
    with pytest.raises(MusicBrainzError, match="could not be reached"):
        asyncio.run(client.search_artists("x"))


def test_adapter_preserves_empty_search_results():
    client = MusicBrainzClient(request_bytes=lambda *_: b'{"artists": []}')
    assert asyncio.run(client.search_artists("No Such Artist")) == []


def test_music_agent_path_disambiguates_and_traces(monkeypatch):
    class FakeMusicBrainz:
        async def search_artists(self, query):
            return [{"id": "12345678-1234-1234-1234-123456789abc", "name": "Yoko Kanno", "type": "Person", "area": {"name": "Japan"}}]
        async def artist_details(self, mbid):
            return {"id": mbid, "name": "Yoko Kanno", "type": "Person", "area": {"name": "Japan"}, "aliases": []}
        async def artist_release_groups(self, mbid):
            return [{"id": "def", "title": "Cowboy Bebop", "primary-type": "Album", "first-release-date": "1998"}]

    monkeypatch.setattr(mcp_server, "_musicbrainz", FakeMusicBrainz())
    monkeypatch.setattr(gemini, "api_key", lambda: "")
    monkeypatch.setattr(deepseek, "api_key", lambda: "")
    monkeypatch.setattr(__import__("popcorn.llm", fromlist=["configured_value"]), "configured_value", lambda _: "")
    async def run():
        from popcorn.skills.music_discovery import run as skill_run
        async def invoke(tool, args):
            if tool == "search_musicbrainz_artists":
                return {"results": [{"id": "1", "name": "Alpha", "source_url": "url1"}, {"id": "2", "name": "Beta", "source_url": "url2"}]}
            raise AssertionError("ambiguous candidates must not trigger detail lookup")
        return await skill_run("nobody", invoke)
    assert "Which one did you mean?" in asyncio.run(run())

    from popcorn.agent import _invoke_skill, new_trace
    trace = new_trace()
    response = asyncio.run(_invoke_skill("music_discovery", "Yoko Kanno", trace, "root"))
    assert "Cowboy Bebop" in response and "musicbrainz.org/artist/12345678-1234-1234-1234-123456789abc" in response
    assert [e.attributes.get("tool") for e in trace.events if e.name == "mcp.tool.call"] == [
        "search_musicbrainz_artists", "get_musicbrainz_artist", "get_musicbrainz_artist_release_groups"]
