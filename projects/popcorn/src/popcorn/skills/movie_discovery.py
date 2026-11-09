"""Movie lookup skill backed by Popcorn's TMDB MCP tools."""

from collections.abc import Awaitable, Callable
from typing import Any

SKILL_NAME = "movie_discovery"
ToolInvoker = Callable[[str, dict[str, object]], Awaitable[Any]]


async def run(title: str, invoke: ToolInvoker) -> str:
    found = await invoke("search_movies", {"query": title})
    candidates = found.get("results", []) if isinstance(found, dict) else []
    if not candidates:
        return f"I couldn't find a movie matching {title!r} in TMDB."

    exact = [item for item in candidates if str(item.get("title", "")).casefold() == title.casefold()]
    selected = exact[0] if len(exact) == 1 else candidates[0] if len(candidates) == 1 else None
    if selected is None:
        choices = "; ".join(
            f"{item.get('title')} ({str(item.get('release_date', ''))[:4] or 'year unknown'}; {item.get('source_url')})"
            for item in candidates[:5]
        )
        return f"I found several possible matches for {title!r}. Which one did you mean? {choices}"

    details = await invoke("get_movie_details", {"movie_id": selected["id"]})
    if not isinstance(details, dict):
        return "TMDB returned movie details in an unexpected format."
    year = str(details.get("release_date", ""))[:4] or "release year unknown"
    genres = ", ".join(details.get("genres", [])) or "genres not listed"
    cast = details.get("cast", [])
    cast_text = ", ".join(
        f"{member.get('name')} as {member.get('character')}" if member.get("character") else str(member.get("name"))
        for member in cast[:8]
        if member.get("name")
    ) or "cast not listed"
    overview = details.get("overview") or "No overview is listed."
    return (
        f"{details.get('title')} ({year})\nGenres: {genres}\n"
        f"Overview: {overview}\nCast: {cast_text}\nSource: {details.get('source_url')} (TMDB)."
    )
