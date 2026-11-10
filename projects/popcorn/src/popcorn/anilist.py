"""Small, read-only adapter for AniList's public GraphQL API."""

from __future__ import annotations

import json
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API_URL = "https://graphql.anilist.co"

SEARCH_QUERY = """query ($search: String!, $type: MediaType!) {
  Page(page: 1, perPage: 8) {
    media(search: $search, type: $type, isAdult: false, sort: [SEARCH_MATCH]) {
      id type format status startDate { year } episodes chapters volumes
      title { romaji english native }
      siteUrl
    }
  }
}"""

DETAIL_QUERY = """query ($id: Int!, $type: MediaType!) {
  Media(id: $id, type: $type, isAdult: false) {
    id type format status description(asHtml: false) startDate { year month day }
    episodes chapters volumes countryOfOrigin genres averageScore siteUrl
    title { romaji english native }
    relations { edges { relationType node { id type format title { romaji english native } siteUrl } } }
    characters(sort: [ROLE, RELEVANCE], perPage: 8) { edges { role node { id name { full } siteUrl } } }
  }
}"""

DISCOVERY_QUERY = """query ($type: MediaType!, $genre: String, $country: CountryCode, $format: MediaFormat, $status: MediaStatus, $season: MediaSeason, $year: Int) {
  Page(page: 1, perPage: 10) {
    media(type: $type, genre: $genre, countryOfOrigin: $country, format: $format,
      status: $status, season: $season, seasonYear: $year, isAdult: false,
      sort: [POPULARITY_DESC, SCORE_DESC]) {
      id type format status startDate { year } title { romaji english native } siteUrl
    }
  }
}"""

CHARACTER_SEARCH_QUERY = """query ($search: String!) { Page(page: 1, perPage: 8) {
  characters(search: $search, sort: [SEARCH_MATCH]) { id name { full native alternative } siteUrl }
} }"""
CHARACTER_DETAILS_QUERY = """query ($id: Int!) { Character(id: $id) {
  id name { full native } description(asHtml: false) gender age siteUrl
  media(page: 1, perPage: 8, sort: [POPULARITY_DESC]) { nodes { id type title { romaji english native } siteUrl } }
} }"""
STAFF_SEARCH_QUERY = """query ($search: String!) { Page(page: 1, perPage: 8) {
  staff(search: $search, sort: [SEARCH_MATCH]) { id name { full native alternative } primaryOccupations languageV2 siteUrl }
} }"""
STAFF_DETAILS_QUERY = """query ($id: Int!) { Staff(id: $id) {
  id name { full native } description(asHtml: false) primaryOccupations languageV2 siteUrl
  staffMedia(page: 1, perPage: 10, sort: [POPULARITY_DESC]) { edges { staffRole node { id type title { romaji english native } siteUrl } } }
  characterMedia(page: 1, perPage: 10, sort: [POPULARITY_DESC]) { edges { characterName characters { id name { full } siteUrl } node { id type title { romaji english native } siteUrl } } }
} }"""


class AniListError(RuntimeError):
    """Safe user-facing AniList request error."""


class AniListClient:
    def __init__(self, *, timeout: float = 15, request_bytes: Callable[[str, dict[str, str], float, bytes], bytes] | None = None) -> None:
        self._timeout = timeout
        self._request_bytes = request_bytes or self._urlopen

    @staticmethod
    def _urlopen(url: str, headers: dict[str, str], timeout: float, body: bytes) -> bytes:
        request = Request(url, data=body, headers=headers, method="POST")
        with urlopen(request, timeout=timeout) as response:
            return response.read()

    def _query(self, query: str, variables: dict[str, object]) -> dict[str, Any]:
        body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
        headers = {"Accept": "application/json", "Content-Type": "application/json", "User-Agent": "Popcorn entertainment discovery demo"}
        try:
            raw = self._request_bytes(API_URL, headers, self._timeout, body)
        except HTTPError as error:
            if error.code == 429:
                raise AniListError("AniList rate limit reached. Wait before trying again.") from None
            if error.code == 403:
                raise AniListError("AniList temporarily refused this request (HTTP 403). Try again later.") from None
            if error.code == 404:
                raise AniListError("AniList did not find that record (HTTP 404).") from None
            raise AniListError(f"AniList request failed with HTTP {error.code}.") from None
        except (TimeoutError, URLError, OSError):
            raise AniListError("AniList could not be reached. Check the network and try again.") from None
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise AniListError("AniList returned an unreadable response.") from None
        if not isinstance(data, dict):
            raise AniListError("AniList returned an unexpected response.")
        errors = data.get("errors")
        if isinstance(errors, list) and errors:
            message = errors[0].get("message") if isinstance(errors[0], dict) else None
            if "too many requests" in str(message).casefold():
                raise AniListError("AniList rate limit reached. Wait before trying again.")
            raise AniListError("AniList could not complete the GraphQL request.")
        return data

    async def search_media(self, query: str, media_type: str) -> list[dict[str, Any]]:
        _validate_type(media_type)
        data = self._query(SEARCH_QUERY, {"search": query, "type": media_type})
        page = data.get("data", {}).get("Page", {}) if isinstance(data.get("data"), dict) else {}
        results = page.get("media", []) if isinstance(page, dict) else []
        if not isinstance(results, list) or any(not isinstance(item, dict) for item in results):
            raise AniListError("AniList returned an unexpected search response.")
        return results

    async def media_details(self, identity: int, media_type: str) -> dict[str, Any]:
        _validate_type(media_type)
        data = self._query(DETAIL_QUERY, {"id": identity, "type": media_type})
        media = data.get("data", {}).get("Media") if isinstance(data.get("data"), dict) else None
        if not isinstance(media, dict):
            raise AniListError("AniList did not return that anime or manga record.")
        return media

    async def discover_media(self, media_type: str, filters: dict[str, object]) -> list[dict[str, Any]]:
        _validate_type(media_type)
        variables = {"type": media_type, **filters}
        data = self._query(DISCOVERY_QUERY, variables)
        page = data.get("data", {}).get("Page", {}) if isinstance(data.get("data"), dict) else {}
        results = page.get("media", []) if isinstance(page, dict) else []
        if not isinstance(results, list) or any(not isinstance(item, dict) for item in results):
            raise AniListError("AniList returned an unexpected discovery response.")
        return results

    async def search_character(self, query: str) -> list[dict[str, Any]]:
        return self._search_entities(CHARACTER_SEARCH_QUERY, "characters", query)

    async def character_details(self, identity: int) -> dict[str, Any]:
        return self._entity_details(CHARACTER_DETAILS_QUERY, "Character", identity, "character")

    async def search_staff(self, query: str) -> list[dict[str, Any]]:
        return self._search_entities(STAFF_SEARCH_QUERY, "staff", query)

    async def staff_details(self, identity: int) -> dict[str, Any]:
        return self._entity_details(STAFF_DETAILS_QUERY, "Staff", identity, "staff")

    def _search_entities(self, query_text: str, key: str, search: str) -> list[dict[str, Any]]:
        data = self._query(query_text, {"search": search})
        page = data.get("data", {}).get("Page", {}) if isinstance(data.get("data"), dict) else {}
        results = page.get(key, []) if isinstance(page, dict) else []
        if not isinstance(results, list) or any(not isinstance(item, dict) for item in results):
            raise AniListError("AniList returned an unexpected search response.")
        return results

    def _entity_details(self, query_text: str, key: str, identity: int, label: str) -> dict[str, Any]:
        data = self._query(query_text, {"id": identity})
        entity = data.get("data", {}).get(key) if isinstance(data.get("data"), dict) else None
        if not isinstance(entity, dict):
            raise AniListError(f"AniList did not return that {label} record.")
        return entity


def _validate_type(media_type: str) -> None:
    if media_type not in {"ANIME", "MANGA"}:
        raise AniListError("media_type must be ANIME or MANGA.")
