"""Search for a character and inspect the AniList appearances it lists."""

from collections.abc import Awaitable, Callable
from typing import Any

SKILL_NAME = "anilist_character_exploration"
ToolInvoker = Callable[[str, dict[str, object]], Awaitable[Any]]


async def run(name: str, invoke: ToolInvoker) -> str:
    result = await invoke("search_anilist_characters", {"query": name})
    candidates = result.get("results", []) if isinstance(result, dict) else []
    if not candidates:
        return f"I couldn't find an AniList character matching {name!r}."
    exact = [x for x in candidates if str(x.get("name", "")).casefold() == name.casefold()]
    selected = exact[0] if len(exact) == 1 else candidates[0] if len(candidates) == 1 else None
    if selected is None:
        return "I found several character matches. Which one did you mean? " + "; ".join(
            f"{x.get('name')} ({x.get('source_url')})" for x in candidates[:6])
    details = await invoke("get_anilist_character_details", {"identity": selected["id"]})
    appearances = details.get("appearances", [])
    works = ", ".join(f"{x.get('title')} ({x.get('source_url')})" for x in appearances) or "no appearances listed"
    return (f"{details.get('name')} — {details.get('description') or 'No description is listed.'}\n"
            f"Appearances listed by AniList: {works}\nSource: {details.get('source_url')} (AniList).")
