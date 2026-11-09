"""Read-only AniList anime and manga discovery workflow."""

from collections.abc import Awaitable, Callable
from typing import Any

SKILL_NAME = "anime_manga_discovery"
ToolInvoker = Callable[[str, dict[str, object]], Awaitable[Any]]


def _title(media: dict[str, Any]) -> str:
    titles = media.get("title") if isinstance(media.get("title"), dict) else {}
    return str(titles.get("english") or titles.get("romaji") or titles.get("native") or "Untitled")


async def run(query: str, media_type: str, invoke: ToolInvoker) -> str:
    found = await invoke("search_anilist_media", {"query": query, "media_type": media_type})
    candidates = found.get("results", []) if isinstance(found, dict) else []
    if not candidates:
        return f"I couldn't find {media_type.lower()} matching {query!r} in AniList."
    exact = [item for item in candidates if query.casefold() in {
        str((item.get("title") or {}).get(key, "")).casefold() for key in ("english", "romaji", "native")
    }]
    selected = exact[0] if len(exact) == 1 else candidates[0] if len(candidates) == 1 else None
    if selected is None:
        choices = "; ".join(
            f"{_title(item)} ({item.get('year') or 'year unknown'}; {item.get('format') or 'format unknown'}; {item.get('source_url')})"
            for item in candidates[:5]
        )
        return f"I found several possible AniList matches for {query!r}. Which one did you mean? {choices}"
    details = await invoke("get_anilist_media_details", {"identity": selected["id"], "media_type": media_type})
    if not isinstance(details, dict):
        return "AniList returned details in an unexpected format."
    year = details.get("year") or "year unknown"
    description = details.get("description") or "No synopsis is listed."
    genres = ", ".join(details.get("genres", [])) or "not listed"
    relations = ", ".join(
        f"{item.get('relation')}: {item.get('title')}" for item in details.get("relations", [])[:6]
    ) or "none listed"
    characters = ", ".join(item.get("name", "") for item in details.get("characters", [])[:6] if item.get("name")) or "not listed"
    return (f"{details.get('title')} ({year}) — {details.get('format') or media_type}\n"
            f"Status: {details.get('status') or 'not listed'}; genres: {genres}\n"
            f"Synopsis: {description}\nCharacters: {characters}\nRelated media: {relations}\n"
            f"Source: {details.get('source_url')} (AniList).")
