"""Read-only Last.fm seed-based music recommendations."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from popcorn.provider_trace import provider_http_status, provider_request

from popcorn.config import configured_value

API_URL = "https://ws.audioscrobbler.com/2.0/"
USER_AGENT = "Popcorn/0.1.0 (https://github.com/dragondive/less-talk-more-github-actions)"


class LastFMError(RuntimeError):
    """Safe user-facing Last.fm API error."""


class LastFMClient:
    def __init__(self, api_key: str | None = None, *, timeout: float = 15,
                 get_bytes: Callable[[str, dict[str, str], float], bytes] | None = None) -> None:
        self._api_key = (api_key if api_key is not None else configured_value("LASTFM_API_KEY")).strip()
        self._timeout = timeout
        self._get_bytes = get_bytes or self._urlopen

    @staticmethod
    def _urlopen(url: str, headers: dict[str, str], timeout: float) -> bytes:
        with urlopen(Request(url, headers=headers, method="GET"), timeout=timeout) as response:
            provider_http_status(response.status)
            return response.read()

    def _request(self, method: str, params: dict[str, str]) -> dict[str, Any]:
        if not self._api_key:
            raise LastFMError("Last.fm recommendations are not configured. Set LASTFM_API_KEY.")
        query = urlencode({"method": method, **params, "api_key": self._api_key, "format": "json"})
        try:
            url = f"{API_URL}?{query}"
            with provider_request("Last.fm", "GET", url) as evidence:
                raw = self._get_bytes(url, {"Accept": "application/json", "User-Agent": USER_AGENT}, self._timeout)
                evidence.response(raw)
        except HTTPError as error:
            raise LastFMError(f"Last.fm request failed with HTTP {error.code}.") from None
        except (TimeoutError, URLError, OSError):
            raise LastFMError("Last.fm could not be reached. Check the network and try again.") from None
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise LastFMError("Last.fm returned an unreadable response.") from None
        if not isinstance(data, dict):
            raise LastFMError("Last.fm returned an unexpected response.")
        if "error" in data:
            code = str(data.get("error"))
            if code == "10":
                raise LastFMError("Last.fm rejected the configured API key.")
            if code == "29":
                raise LastFMError("Last.fm rate limit reached. Wait before trying again.")
            raise LastFMError("Last.fm could not complete the recommendation request.")
        return data

    async def similar_artists(self, artist: str, limit: int = 8) -> list[dict[str, Any]]:
        data = self._request("artist.getSimilar", {"artist": artist, "autocorrect": "1", "limit": str(limit)})
        root = data.get("similarartists")
        results = root.get("artist", []) if isinstance(root, dict) else None
        if not isinstance(results, list) or any(not isinstance(item, dict) for item in results):
            raise LastFMError("Last.fm returned an unexpected similar-artist response.")
        return results

    async def similar_tracks(self, artist: str, track: str, limit: int = 8) -> list[dict[str, Any]]:
        data = self._request("track.getSimilar", {"artist": artist, "track": track, "autocorrect": "1", "limit": str(limit)})
        root = data.get("similartracks")
        results = root.get("track", []) if isinstance(root, dict) else None
        if not isinstance(results, list) or any(not isinstance(item, dict) for item in results):
            raise LastFMError("Last.fm returned an unexpected similar-track response.")
        return results
