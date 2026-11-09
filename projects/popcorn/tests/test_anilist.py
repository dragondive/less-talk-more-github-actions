import asyncio
import json
from urllib.error import HTTPError

import pytest

from popcorn.anilist import AniListClient, AniListError, SEARCH_QUERY, DISCOVERY_QUERY


def test_search_posts_graphql_variables_and_returns_results():
    captured = {}
    def post(url, headers, timeout, body):
        captured.update(url=url, headers=headers, timeout=timeout, body=json.loads(body))
        return json.dumps({"data": {"Page": {"media": [{"id": 1}]}}}).encode()
    result = asyncio.run(AniListClient(request_bytes=post).search_media("Cowboy Bebop", "ANIME"))
    assert result == [{"id": 1}]
    assert captured["url"] == "https://graphql.anilist.co"
    assert captured["body"]["variables"] == {"search": "Cowboy Bebop", "type": "ANIME"}
    assert "isAdult: false" in captured["body"]["query"]
    assert captured["headers"]["Content-Type"] == "application/json"


def test_details_detects_graphql_errors_even_with_http_success():
    client = AniListClient(request_bytes=lambda *_: b'{"data":null,"errors":[{"message":"bad query"}]}')
    with pytest.raises(AniListError, match="GraphQL request"):
        asyncio.run(client.media_details(1, "MANGA"))


def test_rate_limit_and_invalid_type_have_safe_actionable_errors():
    def limited(*_):
        raise HTTPError("https://graphql.anilist.co", 429, "Too Many Requests", {}, None)
    with pytest.raises(AniListError, match="rate limit reached"):
        asyncio.run(AniListClient(request_bytes=limited).search_media("x", "ANIME"))
    with pytest.raises(AniListError, match="ANIME or MANGA"):
        asyncio.run(AniListClient().search_media("x", "MOVIE"))


def test_empty_and_malformed_graphql_payloads_are_handled():
    empty = AniListClient(request_bytes=lambda *_: b'{"data":{"Page":{"media":[]}}}')
    assert asyncio.run(empty.search_media("unknown title", "MANGA")) == []
    malformed = AniListClient(request_bytes=lambda *_: b'{')
    with pytest.raises(AniListError, match="unreadable response"):
        asyncio.run(malformed.search_media("x", "ANIME"))


def test_search_query_is_read_only_and_bounds_page_size():
    assert "perPage: 8" in SEARCH_QUERY
    assert "mutation" not in SEARCH_QUERY.casefold()


def test_filtered_discovery_sends_only_typed_filters():
    captured = {}
    def post(_url, _headers, _timeout, body):
        captured.update(json.loads(body))
        return b'{"data":{"Page":{"media":[{"id":2}]}}}'
    result = asyncio.run(AniListClient(request_bytes=post).discover_media(
        "ANIME", {"genre": "Adventure", "season": "SUMMER", "year": 2020}))
    assert result == [{"id": 2}]
    assert captured["variables"] == {"type": "ANIME", "genre": "Adventure", "season": "SUMMER", "year": 2020}
    assert "isAdult: false" in DISCOVERY_QUERY


def test_character_and_staff_queries_parse_public_search_results():
    def post(_url, _headers, _timeout, body):
        query = json.loads(body)["query"]
        key, identity = ("staff", 2) if "staff(search:" in query else ("characters", 1)
        return json.dumps({"data": {"Page": {key: [{"id": identity}]}}}).encode()
    client = AniListClient(request_bytes=post)
    assert asyncio.run(client.search_character("Spike")) == [{"id": 1}]
    assert asyncio.run(client.search_staff("Yoko Kanno")) == [{"id": 2}]
