"""Popcorn's MCP tools for live movie and actor discovery through TMDB."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import Any, TypeVar

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from popcorn.tmdb import TMDBClient, TMDBError
from popcorn.anilist import AniListClient, AniListError

mcp = MCPServer("popcorn-discovery")
T = TypeVar("T")


async def _provider_call(awaitable: Awaitable[T]) -> T:
    try:
        return await awaitable
    except TMDBError as error:
        raise ToolError(str(error)) from None


async def _anilist_call(awaitable: Awaitable[T]) -> T:
    try:
        return await awaitable
    except AniListError as error:
        raise ToolError(str(error)) from None


@mcp.tool()
async def search_anilist_media(query: str, media_type: str) -> dict[str, Any]:
    """Search public AniList anime or manga records by title."""
    if not query.strip() or len(query) > 200:
        raise ToolError("query must be a non-empty title under 200 characters")
    if media_type not in {"ANIME", "MANGA"}:
        raise ToolError("media_type must be ANIME or MANGA")
    results = await _anilist_call(AniListClient().search_media(query, media_type))
    return {"provider": "AniList", "results": [
        {"id": item.get("id"), "title": item.get("title", {}), "format": item.get("format"),
         "year": (item.get("startDate") or {}).get("year"), "status": item.get("status"),
         "source_url": item.get("siteUrl")} for item in results[:8]
    ]}


@mcp.tool()
async def get_anilist_media_details(identity: int, media_type: str) -> dict[str, Any]:
    """Retrieve public AniList anime/manga details, relations and characters by ID."""
    if identity < 1 or media_type not in {"ANIME", "MANGA"}:
        raise ToolError("Provide a positive AniList ID and media_type ANIME or MANGA")
    item = await _anilist_call(AniListClient().media_details(identity, media_type))
    date = item.get("startDate") if isinstance(item.get("startDate"), dict) else {}
    relation_edges = (item.get("relations") or {}).get("edges", [])
    relations = [{"relation": edge.get("relationType"), "title": _anilist_title(edge.get("node", {}).get("title")),
                  "source_url": edge.get("node", {}).get("siteUrl")}
                 for edge in relation_edges if isinstance(edge, dict) and isinstance(edge.get("node"), dict)]
    character_edges = (item.get("characters") or {}).get("edges", [])
    characters = [{"name": ((edge.get("node") or {}).get("name") or {}).get("full"),
                   "role": edge.get("role"), "source_url": (edge.get("node") or {}).get("siteUrl")}
                  for edge in character_edges if isinstance(edge, dict)]
    return {"provider": "AniList", "id": item.get("id"), "title": _anilist_title(item.get("title")),
            "year": date.get("year"), "format": item.get("format"), "status": item.get("status"),
            "description": item.get("description"), "genres": item.get("genres", []),
            "average_score": item.get("averageScore"), "episodes": item.get("episodes"),
            "chapters": item.get("chapters"), "volumes": item.get("volumes"),
            "relations": relations[:10], "characters": characters[:8], "source_url": item.get("siteUrl")}


@mcp.tool()
async def discover_anilist_media(media_type: str, genre: str | None = None, country: str | None = None,
                                 format: str | None = None, status: str | None = None,
                                 season: str | None = None, year: int | None = None) -> dict[str, Any]:
    """Discover popular public AniList anime or manga using genre, country, format, status, or season filters."""
    _validate_anilist_filter(media_type, genre, country, format, status, season, year)
    filters = {"genre": genre, "country": country.upper() if country else None,
               "format": format, "status": status, "season": season, "year": year}
    results = await _anilist_call(AniListClient().discover_media(media_type, filters))
    return {"provider": "AniList", "filters": {key: value for key, value in filters.items() if value is not None},
            "results": [_anilist_media_summary(item) for item in results[:10]]}


@mcp.tool()
async def search_anilist_characters(query: str) -> dict[str, Any]:
    """Search public AniList characters by name."""
    _validate_anilist_query(query)
    results = await _anilist_call(AniListClient().search_character(query))
    return {"provider": "AniList", "results": [
        {"id": item.get("id"), "name": (item.get("name") or {}).get("full"),
         "native_name": (item.get("name") or {}).get("native"), "source_url": item.get("siteUrl")}
        for item in results[:8]]}


@mcp.tool()
async def get_anilist_character_details(identity: int) -> dict[str, Any]:
    """Get public AniList character description and anime/manga appearances."""
    if identity < 1:
        raise ToolError("Provide a positive AniList character ID")
    item = await _anilist_call(AniListClient().character_details(identity))
    media = item.get("media") or {}
    appearances = [_anilist_media_summary(x) for x in media.get("nodes", []) if isinstance(x, dict)]
    name = item.get("name") or {}
    return {"provider": "AniList", "id": item.get("id"), "name": name.get("full"),
            "description": item.get("description"), "gender": item.get("gender"),
            "age": item.get("age"), "appearances": appearances, "source_url": item.get("siteUrl")}


@mcp.tool()
async def search_anilist_staff(query: str) -> dict[str, Any]:
    """Search public AniList voice actors and production staff by name."""
    _validate_anilist_query(query)
    results = await _anilist_call(AniListClient().search_staff(query))
    return {"provider": "AniList", "results": [
        {"id": item.get("id"), "name": (item.get("name") or {}).get("full"),
         "occupations": item.get("primaryOccupations", []), "language": item.get("languageV2"),
         "source_url": item.get("siteUrl")} for item in results[:8]]}


@mcp.tool()
async def get_anilist_staff_details(identity: int) -> dict[str, Any]:
    """Get public AniList staff roles and credited anime/manga."""
    if identity < 1:
        raise ToolError("Provide a positive AniList staff ID")
    item = await _anilist_call(AniListClient().staff_details(identity))
    credits = (item.get("staffMedia") or {}).get("edges", [])
    voice_credits = (item.get("characterMedia") or {}).get("edges", [])
    name = item.get("name") or {}
    return {"provider": "AniList", "id": item.get("id"), "name": name.get("full"),
            "description": item.get("description"), "occupations": item.get("primaryOccupations", []),
            "language": item.get("languageV2"), "credits": [
                {"role": edge.get("staffRole"), **_anilist_media_summary(edge.get("node", {}))}
                for edge in credits if isinstance(edge, dict) and isinstance(edge.get("node"), dict)
            ][:10], "voice_credits": [
                {"character": edge.get("characterName") or next((c.get("name", {}).get("full") for c in edge.get("characters", []) if isinstance(c, dict)), None),
                 **_anilist_media_summary(edge.get("node", {}))}
                for edge in voice_credits if isinstance(edge, dict) and isinstance(edge.get("node"), dict)
            ][:10], "source_url": item.get("siteUrl")}


def _validate_anilist_query(query: str) -> None:
    if not query.strip() or len(query) > 200:
        raise ToolError("query must be non-empty and under 200 characters")


def _validate_anilist_filter(media_type: str, genre: str | None, country: str | None,
                             format: str | None, status: str | None,
                             season: str | None, year: int | None) -> None:
    if media_type not in {"ANIME", "MANGA"}:
        raise ToolError("media_type must be ANIME or MANGA")
    if genre is not None and (not genre.strip() or len(genre) > 80):
        raise ToolError("genre must be a non-empty AniList genre name under 80 characters")
    if country is not None and (len(country) != 2 or not country.isalpha()):
        raise ToolError("country must be a two-letter country code")
    if format is not None and format not in {"TV", "TV_SHORT", "MOVIE", "SPECIAL", "OVA", "ONA", "MUSIC", "MANGA", "NOVEL", "ONE_SHOT"}:
        raise ToolError("format must be a supported AniList media format")
    if status is not None and status not in {"FINISHED", "RELEASING", "NOT_YET_RELEASED", "CANCELLED", "HIATUS"}:
        raise ToolError("status must be a supported AniList media status")
    if season is not None and season not in {"WINTER", "SPRING", "SUMMER", "FALL"}:
        raise ToolError("season must be WINTER, SPRING, SUMMER, or FALL")
    if year is not None and (year < 1900 or year > 2200):
        raise ToolError("year must be between 1900 and 2200")
    if year is not None and season is None:
        raise ToolError("season is required when filtering by year")


def _anilist_media_summary(item: dict[str, Any]) -> dict[str, Any]:
    return {"id": item.get("id"), "type": item.get("type"), "title": _anilist_title(item.get("title")),
            "format": item.get("format"), "status": item.get("status"),
            "year": (item.get("startDate") or {}).get("year"), "source_url": item.get("siteUrl")}


def _anilist_title(titles: object) -> str:
    if not isinstance(titles, dict):
        return "Untitled"
    return str(titles.get("english") or titles.get("romaji") or titles.get("native") or "Untitled")


@mcp.tool()
async def search_movies(query: str, year: int | None = None, language: str = "en-US") -> dict[str, Any]:
    """Search TMDB movie titles and return candidate IDs, release years, and summaries."""
    results = await _provider_call(TMDBClient().search_movies(query, year, language))
    return {
        "provider": "TMDB",
        "results": [
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "release_date": item.get("release_date", ""),
                "overview": item.get("overview", ""),
                "vote_average": item.get("vote_average"),
                "source_url": _tmdb_url("movie", item.get("id")),
            }
            for item in results[:10]
        ],
    }


@mcp.tool()
async def get_movie_details(movie_id: int, language: str = "en-US") -> dict[str, Any]:
    """Fetch TMDB movie details and credited cast for a TMDB movie ID."""
    item = await _provider_call(TMDBClient().movie_details(movie_id, language))
    credits = item.get("credits") if isinstance(item.get("credits"), dict) else {}
    cast = credits.get("cast") if isinstance(credits.get("cast"), list) else []
    return {
        "provider": "TMDB",
        "id": item.get("id"),
        "title": item.get("title"),
        "release_date": item.get("release_date", ""),
        "overview": item.get("overview", ""),
        "runtime": item.get("runtime"),
        "genres": [genre.get("name") for genre in item.get("genres", []) if isinstance(genre, dict)],
        "vote_average": item.get("vote_average"),
        "cast": [
            {"name": member.get("name"), "character": member.get("character")}
            for member in cast[:15]
            if isinstance(member, dict)
        ],
        "source_url": _tmdb_url("movie", item.get("id")),
    }


@mcp.tool()
async def search_people(query: str) -> dict[str, Any]:
    """Search TMDB people by name and return candidate IDs for disambiguation."""
    results = await _provider_call(TMDBClient().search_people(query))
    return {
        "provider": "TMDB",
        "results": [
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "known_for_department": item.get("known_for_department"),
                "known_for": [
                    work.get("title") or work.get("name")
                    for work in item.get("known_for", [])
                    if isinstance(work, dict)
                ][:3],
                "source_url": _tmdb_url("person", item.get("id")),
            }
            for item in results[:10]
        ],
    }


@mcp.tool()
async def get_person_movie_credits(person_id: int) -> dict[str, Any]:
    """Get the movie acting credits for a TMDB person ID."""
    works = await _provider_call(TMDBClient().person_movie_credits(person_id))
    works.sort(key=lambda work: str(work.get("release_date", "")), reverse=True)
    return {
        "provider": "TMDB",
        "person_id": person_id,
        "results": [
            {
                "id": work.get("id"),
                "title": work.get("title"),
                "release_date": work.get("release_date", ""),
                "character": work.get("character", ""),
                "source_url": _tmdb_url("movie", work.get("id")),
            }
            for work in works[:20]
        ],
    }


@mcp.tool()
async def search_tv(query: str, year: int | None = None, language: str = "en-US") -> dict[str, Any]:
    """Search TMDB television series by title and optional first-air year."""
    results = await _provider_call(TMDBClient().search_tv(query, year, language))
    return {"provider": "TMDB", "results": [
        {"id": item.get("id"), "name": item.get("name"), "first_air_date": item.get("first_air_date", ""),
         "overview": item.get("overview", ""), "vote_average": item.get("vote_average"),
         "source_url": _tmdb_url("tv", item.get("id"))} for item in results[:10]]}


@mcp.tool()
async def get_tv_details(series_id: int, language: str = "en-US") -> dict[str, Any]:
    """Get TMDB TV series details and aggregate cast credits."""
    item = await _provider_call(TMDBClient().tv_details(series_id, language))
    credits = item.get("aggregate_credits") if isinstance(item.get("aggregate_credits"), dict) else {}
    cast = credits.get("cast") if isinstance(credits.get("cast"), list) else []
    return {"provider": "TMDB", "id": item.get("id"), "name": item.get("name"),
            "first_air_date": item.get("first_air_date", ""), "overview": item.get("overview", ""),
            "number_of_seasons": item.get("number_of_seasons"), "number_of_episodes": item.get("number_of_episodes"),
            "genres": [g.get("name") for g in item.get("genres", []) if isinstance(g, dict)],
            "origin_country": item.get("origin_country", []), "original_language": item.get("original_language"),
            "cast": [{"name": person.get("name"), "roles": [r.get("character") for r in person.get("roles", []) if isinstance(r, dict)]}
                     for person in cast[:15] if isinstance(person, dict)],
            "source_url": _tmdb_url("tv", item.get("id"))}


@mcp.tool()
async def discover_movies(language: str = "en-US", region: str | None = None, country: str | None = None, genres: str | None = None,
                          original_language: str | None = None, year: int | None = None) -> dict[str, Any]:
    """Discover movies with optional genre, language, region, and year filters."""
    results = await _provider_call(TMDBClient().discover_movies(
        language=language, region=region, with_genres=genres,
        with_origin_country=country, with_original_language=original_language, year=year))
    return {"provider": "TMDB", "results": [
        {"id": x.get("id"), "title": x.get("title"), "release_date": x.get("release_date", ""),
         "overview": x.get("overview", ""), "vote_average": x.get("vote_average"),
         "original_language": x.get("original_language"), "source_url": _tmdb_url("movie", x.get("id"))}
        for x in results[:10]]}


@mcp.tool()
async def discover_tv(language: str = "en-US", country: str | None = None, genres: str | None = None,
                      original_language: str | None = None, year: int | None = None) -> dict[str, Any]:
    """Discover TV series with optional genre, language, country, and year filters."""
    results = await _provider_call(TMDBClient().discover_tv(
        language=language, with_origin_country=country, with_genres=genres,
        with_original_language=original_language, year=year))
    return {"provider": "TMDB", "results": [
        {"id": x.get("id"), "name": x.get("name"), "first_air_date": x.get("first_air_date", ""),
         "overview": x.get("overview", ""), "vote_average": x.get("vote_average"),
         "original_language": x.get("original_language"), "origin_country": x.get("origin_country", []),
         "source_url": _tmdb_url("tv", x.get("id"))} for x in results[:10]]}


@mcp.tool()
async def get_person_combined_credits(person_id: int) -> dict[str, Any]:
    """List a person's TMDB movie and television acting credits."""
    credits = await _provider_call(TMDBClient().person_combined_credits(person_id))
    results = []
    for item in credits["cast"]:
        is_tv = item.get("media_type") == "tv"
        results.append({"media_type": item.get("media_type"), "id": item.get("id"),
                        "title": item.get("title") or item.get("name"),
                        "date": item.get("release_date") or item.get("first_air_date", ""),
                        "character": item.get("character", ""),
                        "source_url": _tmdb_url("tv" if is_tv else "movie", item.get("id"))})
    results.sort(key=lambda item: str(item["date"]), reverse=True)
    return {"provider": "TMDB", "person_id": person_id, "results": results[:30]}


@mcp.tool()
async def get_reference_data(kind: str, query: str = "", language: str = "en-US") -> dict[str, Any]:
    """Get TMDB language, country, or movie/TV genre codes and labels."""
    client = TMDBClient()
    methods = {"languages": client.languages, "countries": client.countries,
               "movie_genres": lambda: client.movie_genres(language),
               "tv_genres": lambda: client.tv_genres(language)}
    if kind not in methods:
        raise ToolError("kind must be languages, countries, movie_genres, or tv_genres")
    results = await _provider_call(methods[kind]())
    if query:
        needle = query.casefold()
        results = [item for item in results if needle in " ".join(str(v) for v in item.values()).casefold()]
    return {"provider": "TMDB", "kind": kind, "results": results[:30]}


@mcp.tool()
async def get_related_titles(media_type: str, identity: int, relation: str, language: str = "en-US") -> dict[str, Any]:
    """Get TMDB similar or recommended movies/TV based on a selected TMDB title ID."""
    results = await _provider_call(TMDBClient().related_titles(media_type, identity, relation, language))
    title_key, date_key = ("title", "release_date") if media_type == "movie" else ("name", "first_air_date")
    return {"provider": "TMDB", "relation": relation, "media_type": media_type, "results": [
        {"id": x.get("id"), "title": x.get(title_key), "date": x.get(date_key, ""), "overview": x.get("overview", ""),
         "vote_average": x.get("vote_average"), "source_url": _tmdb_url(media_type, x.get("id"))} for x in results[:10]]}


@mcp.tool()
async def get_watch_providers(media_type: str, identity: int, country: str) -> dict[str, Any]:
    """Get movie/TV streaming availability for a country; availability data is provided by JustWatch."""
    if len(country) != 2 or not country.isalpha():
        raise ToolError("country must be a two-letter ISO country code")
    data = await _provider_call(TMDBClient().watch_providers(media_type, identity))
    regions = data.get("results") if isinstance(data.get("results"), dict) else {}
    region = regions.get(country.upper())
    if not isinstance(region, dict):
        return {"provider": "TMDB", "data_source": "JustWatch", "country": country.upper(), "results": [],
                "message": "No watch-provider information is listed for this country."}
    groups = []
    for category in ("flatrate", "free", "ads", "rent", "buy"):
        values = region.get(category)
        if isinstance(values, list):
            groups.extend({"availability": category, "provider": x.get("provider_name"), "logo_path": x.get("logo_path")}
                          for x in values if isinstance(x, dict))
    return {"provider": "TMDB", "data_source": "JustWatch", "country": country.upper(),
            "tmdb_link": region.get("link"), "results": groups}


@mcp.tool()
async def search_collections(query: str, language: str = "en-US") -> dict[str, Any]:
    """Search TMDB movie collections/franchises by name."""
    results = await _provider_call(TMDBClient().search_collections(query, language))
    return {"provider": "TMDB", "results": [
        {"id": x.get("id"), "name": x.get("name"), "overview": x.get("overview", ""),
         "source_url": _tmdb_url("collection", x.get("id"))} for x in results[:10]]}


@mcp.tool()
async def get_collection_details(collection_id: int, language: str = "en-US") -> dict[str, Any]:
    """Get TMDB collection/franchise details and constituent movies."""
    item = await _provider_call(TMDBClient().collection_details(collection_id, language))
    return {"provider": "TMDB", "id": item.get("id"), "name": item.get("name"),
            "overview": item.get("overview", ""), "source_url": _tmdb_url("collection", item.get("id")),
            "parts": [{"id": x.get("id"), "title": x.get("title"), "release_date": x.get("release_date", ""),
                       "source_url": _tmdb_url("movie", x.get("id"))}
                      for x in item.get("parts", []) if isinstance(x, dict)]}


@mcp.tool()
async def rate_movie(movie_id: int, rating: float, user_requested: bool) -> dict[str, Any]:
    """Submit a 0.5–10 rating only on explicit user request using a one-use TMDB guest session."""
    _validate_rating(rating, user_requested)
    client = TMDBClient()
    session = await _provider_call(client.create_guest_session())
    result = await _provider_call(client.rate_movie(movie_id, rating, session))
    return {"provider": "TMDB", "result": result.get("status_message", "Rating submitted"),
            "source_url": _tmdb_url("movie", movie_id)}


@mcp.tool()
async def rate_tv(series_id: int, rating: float, user_requested: bool) -> dict[str, Any]:
    """Submit an explicit user-requested rating for a TV series using a temporary guest session."""
    _validate_rating(rating, user_requested)
    client = TMDBClient()
    session = await _provider_call(client.create_guest_session())
    result = await _provider_call(client.rate_tv(series_id, rating, session))
    return {"provider": "TMDB", "result": result.get("status_message", "Rating submitted"),
            "source_url": _tmdb_url("tv", series_id)}


@mcp.tool()
async def rate_tv_episode(series_id: int, season_number: int, episode_number: int,
                          rating: float, user_requested: bool) -> dict[str, Any]:
    """Submit an explicit user-requested TV episode rating using a temporary guest session."""
    _validate_rating(rating, user_requested)
    if season_number < 0 or episode_number < 1:
        raise ToolError("Season must be zero or greater and episode must be one or greater.")
    client = TMDBClient()
    session = await _provider_call(client.create_guest_session())
    result = await _provider_call(client.rate_tv_episode(series_id, season_number, episode_number, rating, session))
    source = f"https://www.themoviedb.org/tv/{series_id}/season/{season_number}/episode/{episode_number}"
    return {"provider": "TMDB", "result": result.get("status_message", "Rating submitted"), "source_url": source}


def _validate_rating(rating: float, user_requested: bool) -> None:
    if not user_requested:
        raise ToolError("A rating can only be submitted at the user's explicit request.")
    if isinstance(rating, bool) or not 0.5 <= rating <= 10 or round(rating * 2) != rating * 2:
        raise ToolError("TMDB ratings must be from 0.5 to 10 in half-point increments.")


def _tmdb_url(kind: str, identity: object) -> str | None:
    return f"https://www.themoviedb.org/{kind}/{identity}" if identity is not None else None


def main() -> None:
    """Run the MCP server on stdio for MCP-compatible hosts."""
    mcp.run("stdio")


if __name__ == "__main__":
    main()
