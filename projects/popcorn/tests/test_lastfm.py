import asyncio
import json

import pytest

from popcorn.lastfm import LastFMClient, LastFMError


def test_lastfm_similar_artists_uses_key_and_bounded_request():
    calls = []

    def get_bytes(url, headers, timeout):
        calls.append((url, headers, timeout))
        return json.dumps({"similarartists": {"artist": [{"name": "Broadcast", "mbid": "mbid", "match": "0.7", "url": "https://www.last.fm/music/Broadcast"}]}}).encode()

    client = LastFMClient("secret-key", get_bytes=get_bytes)
    result = asyncio.run(client.similar_artists("Portishead", 8))
    assert result[0]["name"] == "Broadcast"
    assert "method=artist.getSimilar" in calls[0][0]
    assert "api_key=secret-key" in calls[0][0]
    assert "limit=8" in calls[0][0]
    assert "Popcorn/0.1.0" in calls[0][1]["User-Agent"]


def test_lastfm_similar_tracks_and_error_responses():
    response = {"similartracks": {"track": [{"name": "Ray of Light", "artist": {"name": "Madonna"}, "match": "0.5", "url": "https://www.last.fm/music/Madonna/_/Ray+of+Light"}]}}
    client = LastFMClient("key", get_bytes=lambda *_: json.dumps(response).encode())
    assert asyncio.run(client.similar_tracks("Cher", "Believe"))[0]["name"] == "Ray of Light"

    client = LastFMClient("key", get_bytes=lambda *_: b'{"error":10}')
    with pytest.raises(LastFMError, match="API key"):
        asyncio.run(client.similar_artists("Cher"))
    client = LastFMClient("key", get_bytes=lambda *_: b"bad json")
    with pytest.raises(LastFMError, match="unreadable"):
        asyncio.run(client.similar_artists("Cher"))


def test_lastfm_key_is_required():
    with pytest.raises(LastFMError, match="LASTFM_API_KEY"):
        asyncio.run(LastFMClient("").similar_artists("Cher"))
