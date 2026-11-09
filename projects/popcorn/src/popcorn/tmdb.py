"""Small asynchronous adapter for the TMDB v3 read API."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class TMDBError(RuntimeError):
    """A safe, user-facing TMDB request error."""


ENV_FILE = Path(__file__).resolve().parents[4] / ".env"


def _configured_token() -> str:
    token = os.getenv("TMDB_ACCESS_TOKEN", "").strip()
    if token:
        return token
    try:
        lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if separator and key.strip() == "TMDB_ACCESS_TOKEN":
            return value.strip().strip("\"'")
    return ""


class TMDBClient:
    def __init__(
        self,
        access_token: str | None = None,
        *,
        timeout: float = 15,
        get_bytes: Callable[[str, dict[str, str], float], bytes] | None = None,
        request_bytes: Callable[[str, dict[str, str], float, str, bytes | None], bytes] | None = None,
    ) -> None:
        self._access_token = (access_token or _configured_token()).strip()
        self._timeout = timeout
        self._get_bytes_override = get_bytes
        self._get_bytes = get_bytes or self._urlopen
        self._request_bytes = request_bytes or self._urlopen_request

    @staticmethod
    def _urlopen(url: str, headers: dict[str, str], timeout: float) -> bytes:
        request = Request(url, headers=headers, method="GET")
        with urlopen(request, timeout=timeout) as response:
            return response.read()

    @staticmethod
    def _urlopen_request(
        url: str, headers: dict[str, str], timeout: float, method: str, body: bytes | None
    ) -> bytes:
        request = Request(url, data=body, headers=headers, method=method)
        with urlopen(request, timeout=timeout) as response:
            return response.read()

    def _request_json(
        self,
        path: str,
        params: dict[str, str | int | float | None],
        *,
        method: str = "GET",
        body: dict[str, object] | None = None,
    ) -> dict[str, Any] | list[Any]:
        if not self._access_token:
            raise TMDBError(
                "TMDB access is not configured. Set TMDB_ACCESS_TOKEN to your TMDB API Read Access Token."
            )
        query = urlencode({key: value for key, value in params.items() if value is not None})
        url = f"https://api.themoviedb.org/3/{path}"
        if query:
            url = f"{url}?{query}"
        try:
            request_body = json.dumps(body).encode("utf-8") if body is not None else None
            headers = {
                    "Authorization": f"Bearer {self._access_token}",
                    "Accept": "application/json",
                    **({"Content-Type": "application/json"} if request_body is not None else {}),
                }
            if method == "GET" and self._get_bytes_override is not None:
                response_body = self._get_bytes(url, headers, self._timeout)
            else:
                response_body = self._request_bytes(url, headers, self._timeout, method, request_body)
        except HTTPError as error:
            if error.code == 401:
                raise TMDBError("TMDB rejected the access token (HTTP 401). Check TMDB_ACCESS_TOKEN.") from None
            if error.code == 429:
                raise TMDBError("TMDB rate limit reached (HTTP 429). Try again later.") from None
            if error.code == 404:
                raise TMDBError("TMDB did not find that record (HTTP 404).") from None
            raise TMDBError(f"TMDB request failed with HTTP {error.code}.") from None
        except (TimeoutError, URLError, OSError):
            raise TMDBError("TMDB could not be reached. Check the network and try again.") from None
        try:
            data = json.loads(response_body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise TMDBError("TMDB returned an unreadable response.") from None
        if not isinstance(data, (dict, list)):
            raise TMDBError("TMDB returned an unexpected response.")
        return data

    async def get_json(self, path: str, **params: str | int | None) -> dict[str, Any]:
        # urllib is synchronous. The single-request demo flow keeps this simple;
        # the configured timeout bounds how long a provider call can block.
        data = self._request_json(path, params)
        if not isinstance(data, dict):
            raise TMDBError("TMDB returned an unexpected response shape.")
        return data

    async def search_movies(self, query: str, year: int | None = None, language: str = "en-US") -> list[dict[str, Any]]:
        data = await self.get_json("search/movie", query=query, year=year, language=language, include_adult="false")
        return _list_of_objects(data, "results")

    async def movie_details(self, movie_id: int, language: str = "en-US") -> dict[str, Any]:
        return await self.get_json(f"movie/{movie_id}", language=language, append_to_response="credits")

    async def search_people(self, query: str) -> list[dict[str, Any]]:
        data = await self.get_json("search/person", query=query, include_adult="false")
        return _list_of_objects(data, "results")

    async def person_movie_credits(self, person_id: int) -> list[dict[str, Any]]:
        data = await self.get_json(f"person/{person_id}/movie_credits")
        return _list_of_objects(data, "cast")

    async def search_tv(self, query: str, year: int | None = None, language: str = "en-US") -> list[dict[str, Any]]:
        data = await self.get_json("search/tv", query=query, first_air_date_year=year, language=language, include_adult="false")
        return _list_of_objects(data, "results")

    async def tv_details(self, series_id: int, language: str = "en-US") -> dict[str, Any]:
        return await self.get_json(f"tv/{series_id}", language=language, append_to_response="aggregate_credits")

    async def person_combined_credits(self, person_id: int, language: str = "en-US") -> dict[str, list[dict[str, Any]]]:
        data = await self.get_json(f"person/{person_id}/combined_credits", language=language)
        return {"cast": _list_of_objects(data, "cast"), "crew": _list_of_objects(data, "crew")}

    async def discover_movies(
        self, *, language: str = "en-US", region: str | None = None,
        with_genres: str | None = None, with_origin_country: str | None = None, with_original_language: str | None = None,
        year: int | None = None, sort_by: str = "popularity.desc", page: int = 1,
    ) -> list[dict[str, Any]]:
        data = await self.get_json(
            "discover/movie", language=language, region=region, with_genres=with_genres, with_origin_country=with_origin_country,
            with_original_language=with_original_language, year=year, sort_by=sort_by,
            page=page, include_adult="false",
        )
        return _list_of_objects(data, "results")

    async def discover_tv(
        self, *, language: str = "en-US", with_genres: str | None = None,
        with_origin_country: str | None = None, with_original_language: str | None = None,
        year: int | None = None, sort_by: str = "popularity.desc", page: int = 1,
    ) -> list[dict[str, Any]]:
        data = await self.get_json(
            "discover/tv", language=language, with_genres=with_genres,
            with_origin_country=with_origin_country, with_original_language=with_original_language,
            first_air_date_year=year, sort_by=sort_by, page=page, include_adult="false",
        )
        return _list_of_objects(data, "results")

    async def languages(self) -> list[dict[str, Any]]:
        data = self._request_json("configuration/languages", {})
        return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []

    async def countries(self) -> list[dict[str, Any]]:
        data = self._request_json("configuration/countries", {})
        return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []

    async def movie_genres(self, language: str = "en-US") -> list[dict[str, Any]]:
        return _list_of_objects(await self.get_json("genre/movie/list", language=language), "genres")

    async def tv_genres(self, language: str = "en-US") -> list[dict[str, Any]]:
        return _list_of_objects(await self.get_json("genre/tv/list", language=language), "genres")

    async def related_titles(self, media_type: str, identity: int, relation: str, language: str = "en-US") -> list[dict[str, Any]]:
        if media_type not in {"movie", "tv"} or relation not in {"recommendations", "similar"}:
            raise TMDBError("Unsupported title relationship request.")
        data = await self.get_json(f"{media_type}/{identity}/{relation}", language=language)
        return _list_of_objects(data, "results")

    async def watch_providers(self, media_type: str, identity: int) -> dict[str, Any]:
        if media_type not in {"movie", "tv"}:
            raise TMDBError("Watch-provider lookup supports movies and TV series.")
        return await self.get_json(f"{media_type}/{identity}/watch/providers")

    async def search_collections(self, query: str, language: str = "en-US") -> list[dict[str, Any]]:
        data = await self.get_json("search/collection", query=query, language=language, include_adult="false")
        return _list_of_objects(data, "results")

    async def collection_details(self, collection_id: int, language: str = "en-US") -> dict[str, Any]:
        return await self.get_json(f"collection/{collection_id}", language=language)

    async def create_guest_session(self) -> str:
        data = await self.get_json("authentication/guest_session/new")
        session_id = data.get("guest_session_id")
        if not isinstance(session_id, str) or not session_id:
            raise TMDBError("TMDB did not return a guest session.")
        return session_id

    async def rate_movie(self, movie_id: int, rating: float, guest_session_id: str) -> dict[str, Any]:
        return self._request_json(f"movie/{movie_id}/rating", {"guest_session_id": guest_session_id}, method="POST", body={"value": rating})

    async def rate_tv(self, series_id: int, rating: float, guest_session_id: str) -> dict[str, Any]:
        return self._request_json(f"tv/{series_id}/rating", {"guest_session_id": guest_session_id}, method="POST", body={"value": rating})

    async def rate_tv_episode(self, series_id: int, season_number: int, episode_number: int,
                              rating: float, guest_session_id: str) -> dict[str, Any]:
        path = f"tv/{series_id}/season/{season_number}/episode/{episode_number}/rating"
        return self._request_json(path, {"guest_session_id": guest_session_id}, method="POST", body={"value": rating})


def _list_of_objects(data: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = data.get(key, [])
    if not isinstance(value, list):
        raise TMDBError("TMDB returned an unexpected response shape.")
    return [item for item in value if isinstance(item, dict)]
