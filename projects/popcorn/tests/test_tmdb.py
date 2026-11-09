import asyncio
import json
from urllib.error import HTTPError

import pytest

from popcorn import tmdb
from popcorn.tmdb import TMDBClient, TMDBError


def test_search_movies_sends_bearer_token_and_parses_json():
    captured = {}

    def get_bytes(url, headers, timeout):
        captured.update(url=url, headers=headers, timeout=timeout)
        return json.dumps({"results": [{"id": 603, "title": "The Matrix"}]}).encode()

    client = TMDBClient("secret-test-token", get_bytes=get_bytes)
    results = asyncio.run(client.search_movies("The Matrix", year=1999))

    assert results == [{"id": 603, "title": "The Matrix"}]
    assert captured["url"] == "https://api.themoviedb.org/3/search/movie?query=The+Matrix&year=1999&include_adult=false"
    assert captured["headers"]["Authorization"] == "Bearer secret-test-token"
    assert "secret-test-token" not in captured["url"]


def test_missing_access_token_fails_with_setup_guidance(monkeypatch, tmp_path):
    monkeypatch.setattr(tmdb, "ENV_FILE", tmp_path / "missing.env")
    monkeypatch.delenv("TMDB_ACCESS_TOKEN", raising=False)
    client = TMDBClient("")
    with pytest.raises(TMDBError, match="TMDB_ACCESS_TOKEN"):
        asyncio.run(client.search_people("Keanu Reeves"))


def test_access_token_can_be_loaded_from_local_env_file(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text('TMDB_ACCESS_TOKEN="local-secret"\n', encoding="utf-8")
    monkeypatch.setattr(tmdb, "ENV_FILE", env_file)
    monkeypatch.delenv("TMDB_ACCESS_TOKEN", raising=False)
    captured = {}
    client = TMDBClient(get_bytes=lambda _url, headers, _timeout: captured.update(headers=headers) or b'{"results":[]}')

    asyncio.run(client.search_people("Keanu Reeves"))
    assert captured["headers"]["Authorization"] == "Bearer local-secret"


def test_bad_response_shape_is_reported():
    client = TMDBClient("token", get_bytes=lambda *_: b"[]")
    with pytest.raises(TMDBError, match="unexpected response"):
        asyncio.run(client.search_movies("Anything"))


def test_empty_search_results_are_returned_without_invention():
    client = TMDBClient("token", get_bytes=lambda *_: b'{"results":[]}')
    assert asyncio.run(client.search_movies("Unknown movie")) == []


def test_authentication_error_is_reported_without_exposing_token():
    def unauthorized(*_):
        raise HTTPError("https://api.themoviedb.org/3/search/movie", 401, "Unauthorized", {}, None)

    client = TMDBClient("private-token", get_bytes=unauthorized)
    with pytest.raises(TMDBError, match="rejected the access token") as error:
        asyncio.run(client.search_movies("The Matrix"))
    assert "private-token" not in str(error.value)


def test_rate_limit_response_has_actionable_message():
    def rate_limited(*_):
        raise HTTPError("https://api.themoviedb.org/3/search/movie", 429, "Too Many Requests", {}, None)

    client = TMDBClient("token", get_bytes=rate_limited)
    with pytest.raises(TMDBError, match="rate limit reached"):
        asyncio.run(client.search_movies("The Matrix"))
