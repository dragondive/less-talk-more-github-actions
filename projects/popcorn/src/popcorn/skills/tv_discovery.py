"""TV series discovery using Popcorn TMDB tools."""

from collections.abc import Awaitable, Callable
from typing import Any

SKILL_NAME = "tv_discovery"
ToolInvoker = Callable[[str, dict[str, object]], Awaitable[Any]]


async def run(query: str, invoke: ToolInvoker, language: str = "en-US") -> str:
    found = await invoke("search_tv", {"query": query, "language": language})
    candidates = found.get("results", []) if isinstance(found, dict) else []
    if not candidates:
        return f"I couldn't find a TV series matching {query!r} in TMDB."
    exact = [x for x in candidates if str(x.get("name", "")).casefold() == query.casefold()]
    selected = exact[0] if len(exact) == 1 else candidates[0] if len(candidates) == 1 else None
    if selected is None:
        choices = "; ".join(f"{x.get('name')} ({str(x.get('first_air_date', ''))[:4] or 'year unknown'}; {x.get('source_url')})" for x in candidates[:5])
        return f"I found several possible TV matches for {query!r}. Which one did you mean? {choices}"
    details = await invoke("get_tv_details", {"series_id": selected["id"], "language": language})
    if not isinstance(details, dict):
        return "TMDB returned TV details in an unexpected format."
    cast = ", ".join(x.get("name", "") for x in details.get("cast", [])[:8] if x.get("name")) or "cast not listed"
    year = str(details.get("first_air_date", ""))[:4] or "year unknown"
    return (f"{details.get('name')} ({year})\nGenres: {', '.join(details.get('genres', [])) or 'not listed'}\n"
            f"Overview: {details.get('overview') or 'No overview is listed.'}\nCast: {cast}\n"
            f"Source: {details.get('source_url')} (TMDB).")
