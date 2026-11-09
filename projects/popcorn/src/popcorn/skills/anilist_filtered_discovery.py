"""AniList anime/manga discovery using documented catalog filters."""

from collections.abc import Awaitable, Callable
from typing import Any

SKILL_NAME = "anilist_filtered_discovery"
ToolInvoker = Callable[[str, dict[str, object]], Awaitable[Any]]


async def run(media_type: str, filters: dict[str, object], invoke: ToolInvoker) -> str:
    result = await invoke("discover_anilist_media", {"media_type": media_type, **filters})
    items = result.get("results", []) if isinstance(result, dict) else []
    if not items:
        return "AniList found no titles for those filters."
    criteria = ", ".join(f"{k}: {v}" for k, v in (result.get("filters") or {}).items()) or "no extra filters"
    choices = "\n".join(f"- {item.get('title')} ({item.get('year') or 'year unknown'}, {item.get('format') or 'format unknown'}) — {item.get('source_url')}" for item in items[:10])
    return f"AniList {media_type.lower()} discovery ({criteria}; popularity/score order):\n{choices}"
