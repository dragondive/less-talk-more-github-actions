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
    assert captured["url"] == "https://api.themoviedb.org/3/search/movie?query=The+Matrix&year=1999&language=en-US&include_adult=false"
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


def test_tv_search_and_discovery_use_expected_tmdb_paths_and_filters():
    urls = []
    def get_bytes(url, _headers, _timeout):
        urls.append(url)
        return b'{"results":[{"id":1,"name":"Example"}]}'
    client = TMDBClient("token", get_bytes=get_bytes)
    assert asyncio.run(client.search_tv("Example", 2020))[0]["name"] == "Example"
    assert asyncio.run(client.discover_tv(with_origin_country="IN", with_original_language="hi", year=2020))[0]["name"] == "Example"
    assert "/search/tv?query=Example&first_air_date_year=2020" in urls[0]
    assert "discover/tv?language=en-US&with_origin_country=IN&with_original_language=hi&first_air_date_year=2020" in urls[1]


def test_guest_rating_posts_rating_and_keeps_session_out_of_body():
    captured = {}
    def request_bytes(url, headers, _timeout, method, body):
        captured.update(url=url, headers=headers, method=method, body=body)
        return b'{"status_message":"Success"}'
    client = TMDBClient("api-token", request_bytes=request_bytes)
    result = asyncio.run(client.rate_movie(603, 8.5, "private-session"))
    assert result["status_message"] == "Success"
    assert captured["method"] == "POST"
    assert captured["url"].endswith("movie/603/rating?guest_session_id=private-session")
    assert captured["body"] == b'{"value": 8.5}'
    assert "private-session" not in captured["headers"]["Authorization"]


def test_reference_language_endpoint_accepts_tmdb_top_level_array():
    client = TMDBClient("token", get_bytes=lambda *_: b'[{"english_name":"Hindi","iso_639_1":"hi"}]')
    assert asyncio.run(client.languages()) == [{"english_name": "Hindi", "iso_639_1": "hi"}]


def test_tv_episode_rating_posts_to_episode_endpoint():
    captured = {}
    def request_bytes(url, _headers, _timeout, method, body):
        captured.update(url=url, method=method, body=body)
        return b'{"status_message":"Success"}'
    client = TMDBClient("token", request_bytes=request_bytes)
    asyncio.run(client.rate_tv_episode(1399, 2, 3, 9.5, "guest-session"))
    assert captured["method"] == "POST"
    assert captured["url"].endswith("tv/1399/season/2/episode/3/rating?guest_session_id=guest-session")
    assert captured["body"] == b'{"value": 9.5}'


def test_related_title_and_collection_requests_keep_documented_paths():
    urls = []
    def get_bytes(url, _headers, _timeout):
        urls.append(url)
        return b'{"results":[],"parts":[]}'
    client = TMDBClient("token", get_bytes=get_bytes)
    asyncio.run(client.related_titles("movie", 603, "recommendations"))
    asyncio.run(client.search_collections("Star Wars"))
    asyncio.run(client.collection_details(10))
    assert "/movie/603/recommendations?language=en-US" in urls[0]
    assert "/search/collection?query=Star+Wars&language=en-US&include_adult=false" in urls[1]
    assert "/collection/10?language=en-US" in urls[2]


def test_watch_provider_response_is_returned_by_country():
    client = TMDBClient("token", get_bytes=lambda *_: b'{"id":603,"results":{"IN":{"link":"tmdb-link","flatrate":[{"provider_name":"Example"}]}}}')
    result = asyncio.run(client.watch_providers("movie", 603))
    assert result["results"]["IN"]["flatrate"][0]["provider_name"] == "Example"
