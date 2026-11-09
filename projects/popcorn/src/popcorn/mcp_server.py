"""Popcorn's MCP tools for live movie and actor discovery through TMDB."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import Any, TypeVar

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from popcorn.tmdb import TMDBClient, TMDBError

mcp = MCPServer("popcorn-tmdb")
T = TypeVar("T")


async def _provider_call(awaitable: Awaitable[T]) -> T:
    try:
        return await awaitable
    except TMDBError as error:
        raise ToolError(str(error)) from None


@mcp.tool()
async def search_movies(query: str, year: int | None = None) -> dict[str, Any]:
    """Search TMDB movie titles and return candidate IDs, release years, and summaries."""
    results = await _provider_call(TMDBClient().search_movies(query, year))
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
async def get_movie_details(movie_id: int) -> dict[str, Any]:
    """Fetch TMDB movie details and credited cast for a TMDB movie ID."""
    item = await _provider_call(TMDBClient().movie_details(movie_id))
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


def _tmdb_url(kind: str, identity: object) -> str | None:
    return f"https://www.themoviedb.org/{kind}/{identity}" if identity is not None else None


def main() -> None:
    """Run the MCP server on stdio for MCP-compatible hosts."""
    mcp.run("stdio")


if __name__ == "__main__":
    main()
