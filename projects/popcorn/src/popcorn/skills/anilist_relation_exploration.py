"""Explore AniList's explicit media relationship edges."""

from collections.abc import Awaitable, Callable
from typing import Any

SKILL_NAME = "anilist_relation_exploration"
ToolInvoker = Callable[[str, dict[str, object]], Awaitable[Any]]


async def run(title: str, media_type: str, invoke: ToolInvoker) -> str:
    found = await invoke("search_anilist_media", {"query": title, "media_type": media_type})
    candidates = found.get("results", []) if isinstance(found, dict) else []
    if not candidates:
        return f"I couldn't find {media_type.lower()} matching {title!r} in AniList."
    exact = [x for x in candidates if title.casefold() in {str((x.get("title") or {}).get(k, "")).casefold() for k in ("english", "romaji", "native")}]
    selected = exact[0] if len(exact) == 1 else candidates[0] if len(candidates) == 1 else None
    if selected is None:
        return "I found several possible AniList matches. Which one did you mean? " + "; ".join(
            f"{(x.get('title') or {}).get('english') or (x.get('title') or {}).get('romaji')} ({x.get('source_url')})" for x in candidates[:6])
    details = await invoke("get_anilist_media_details", {"identity": selected["id"], "media_type": media_type})
    relations = details.get("relations", [])
    if not relations:
        return f"AniList lists no related media for {details.get('title')}. Source: {details.get('source_url')}"
    edges = "; ".join(f"{x.get('relation')}: {x.get('title')} ({x.get('source_url')})" for x in relations)
    return f"AniList relations for {details.get('title')}: {edges}\nSource: {details.get('source_url')} (AniList)."
