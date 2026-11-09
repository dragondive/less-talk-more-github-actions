"""Search AniList voice actors/production staff and inspect selected credits."""

from collections.abc import Awaitable, Callable
from typing import Any

SKILL_NAME = "anilist_staff_exploration"
ToolInvoker = Callable[[str, dict[str, object]], Awaitable[Any]]


async def run(name: str, invoke: ToolInvoker) -> str:
    result = await invoke("search_anilist_staff", {"query": name})
    candidates = result.get("results", []) if isinstance(result, dict) else []
    if not candidates:
        return f"I couldn't find AniList staff matching {name!r}."
    exact = [x for x in candidates if str(x.get("name", "")).casefold() == name.casefold()]
    selected = exact[0] if len(exact) == 1 else candidates[0] if len(candidates) == 1 else None
    if selected is None:
        return "I found several staff matches. Which one did you mean? " + "; ".join(
            f"{x.get('name')} ({x.get('source_url')})" for x in candidates[:6])
    details = await invoke("get_anilist_staff_details", {"identity": selected["id"]})
    credits = "; ".join(f"{x.get('title')} — {x.get('role')} ({x.get('source_url')})" for x in details.get("credits", [])) or "no credits listed"
    voice_credits = "; ".join(f"{x.get('character') or 'voice role'} in {x.get('title')} ({x.get('source_url')})" for x in details.get("voice_credits", [])) or "no voice credits listed"
    occupations = ", ".join(details.get("occupations", [])) or "occupation not listed"
    return (f"{details.get('name')} ({occupations})\nProduction credits: {credits}\nVoice credits: {voice_credits}\n"
            f"Source: {details.get('source_url')} (AniList).")
