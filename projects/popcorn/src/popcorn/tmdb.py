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
    ) -> None:
        self._access_token = (access_token or _configured_token()).strip()
        self._timeout = timeout
        self._get_bytes = get_bytes or self._urlopen

    @staticmethod
    def _urlopen(url: str, headers: dict[str, str], timeout: float) -> bytes:
        request = Request(url, headers=headers, method="GET")
        with urlopen(request, timeout=timeout) as response:
            return response.read()

    def _get_json(self, path: str, params: dict[str, str | int | None]) -> dict[str, Any]:
        if not self._access_token:
            raise TMDBError(
                "TMDB access is not configured. Set TMDB_ACCESS_TOKEN to your TMDB API Read Access Token."
            )
        query = urlencode({key: value for key, value in params.items() if value is not None})
        url = f"https://api.themoviedb.org/3/{path}"
        if query:
            url = f"{url}?{query}"
        try:
            body = self._get_bytes(
                url,
                {"Authorization": f"Bearer {self._access_token}", "Accept": "application/json"},
                self._timeout,
            )
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
            data = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise TMDBError("TMDB returned an unreadable response.") from None
        if not isinstance(data, dict):
            raise TMDBError("TMDB returned an unexpected response.")
        return data

    async def get_json(self, path: str, **params: str | int | None) -> dict[str, Any]:
        # urllib is synchronous. The single-request demo flow keeps this simple;
        # the configured timeout bounds how long a provider call can block.
        return self._get_json(path, params)

    async def search_movies(self, query: str, year: int | None = None) -> list[dict[str, Any]]:
        data = await self.get_json("search/movie", query=query, year=year, include_adult="false")
        return _list_of_objects(data, "results")

    async def movie_details(self, movie_id: int) -> dict[str, Any]:
        return await self.get_json(f"movie/{movie_id}", append_to_response="credits")

    async def search_people(self, query: str) -> list[dict[str, Any]]:
        data = await self.get_json("search/person", query=query, include_adult="false")
        return _list_of_objects(data, "results")

    async def person_movie_credits(self, person_id: int) -> list[dict[str, Any]]:
        data = await self.get_json(f"person/{person_id}/movie_credits")
        return _list_of_objects(data, "cast")


def _list_of_objects(data: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = data.get(key, [])
    if not isinstance(value, list):
        raise TMDBError("TMDB returned an unexpected response shape.")
    return [item for item in value if isinstance(item, dict)]
