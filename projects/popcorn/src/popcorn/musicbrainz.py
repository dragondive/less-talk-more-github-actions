"""Read-only, bounded MusicBrainz API client."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

API_URL = "https://musicbrainz.org/ws/2"
USER_AGENT = "Popcorn/0.1.0 (https://github.com/dragondive/less-talk-more-github-actions)"


class MusicBrainzError(RuntimeError):
    """Safe user-facing MusicBrainz request error."""


class MusicBrainzClient:
    def __init__(self, *, timeout: float = 15,
                 request_bytes: Callable[[str, dict[str, str], float], bytes] | None = None,
                 clock: Callable[[], float] = time.monotonic,
                 sleeper: Callable[[float], None] = time.sleep) -> None:
        self._timeout, self._request_bytes = timeout, request_bytes or self._urlopen
        self._clock, self._sleeper, self._last_request = clock, sleeper, None

    @staticmethod
    def _urlopen(url: str, headers: dict[str, str], timeout: float) -> bytes:
        with urlopen(Request(url, headers=headers), timeout=timeout) as response:
            return response.read()

    def _get(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        if self._last_request is not None:
            wait = 1.0 - (self._clock() - self._last_request)
            if wait > 0:
                self._sleeper(wait)
        self._last_request = self._clock()
        query = "&".join(f"{quote(k)}={quote(v, safe='') }" for k, v in params.items())
        url = f"{API_URL}/{path}?{query}"
        try:
            raw = self._request_bytes(url, {"Accept": "application/json", "User-Agent": USER_AGENT}, self._timeout)
        except HTTPError as error:
            if error.code == 503:
                raise MusicBrainzError("MusicBrainz is busy or rate limiting requests (HTTP 503). Wait before trying again.") from None
            if error.code == 404:
                raise MusicBrainzError("MusicBrainz did not find that record (HTTP 404).") from None
            raise MusicBrainzError(f"MusicBrainz request failed with HTTP {error.code}.") from None
        except (TimeoutError, URLError, OSError):
            raise MusicBrainzError("MusicBrainz could not be reached. Check the network and try again.") from None
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise MusicBrainzError("MusicBrainz returned an unreadable response.") from None
        if not isinstance(data, dict):
            raise MusicBrainzError("MusicBrainz returned an unexpected response.")
        return data

    async def search_artists(self, query: str) -> list[dict[str, Any]]:
        # Keep Lucene operators and metacharacters from user input inert, but
        # leave the terms unquoted so aliases and multi-word names can match.
        escaped = "".join("\\" + c if c in '+-&|!(){}[]^"~*?:\\/' else c for c in query)
        data = self._get("artist/", {"query": escaped, "fmt": "json", "limit": "8"})
        results = data.get("artists")
        if not isinstance(results, list) or any(not isinstance(x, dict) for x in results):
            raise MusicBrainzError("MusicBrainz returned an unexpected artist search response.")
        return results

    async def artist_details(self, mbid: str) -> dict[str, Any]:
        data = self._get(f"artist/{quote(mbid, safe='')}", {"fmt": "json", "inc": "aliases+url-rels"})
        if not isinstance(data.get("id"), str):
            raise MusicBrainzError("MusicBrainz did not return that artist record.")
        return data

    async def artist_release_groups(self, mbid: str) -> list[dict[str, Any]]:
        data = self._get("release-group/", {"artist": mbid, "fmt": "json", "limit": "10", "type": "album|ep|single"})
        results = data.get("release-groups")
        if not isinstance(results, list) or any(not isinstance(x, dict) for x in results):
            raise MusicBrainzError("MusicBrainz returned an unexpected release-group response.")
        return results
