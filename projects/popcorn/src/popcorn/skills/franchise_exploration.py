"""Explore TMDB movie collections/franchises."""

from collections.abc import Awaitable, Callable
from typing import Any

SKILL_NAME = "franchise_exploration"
ToolInvoker = Callable[[str, dict[str, object]], Awaitable[Any]]


async def run(query: str, invoke: ToolInvoker) -> str:
    found = await invoke("search_collections", {"query": query})
    candidates = found.get("results", []) if isinstance(found, dict) else []
    if not candidates:
        return f"I couldn't find a movie collection matching {query!r} in TMDB."
    exact = [x for x in candidates if str(x.get("name", "")).casefold() == query.casefold()]
    selected = exact[0] if len(exact) == 1 else candidates[0] if len(candidates) == 1 else None
    if selected is None:
        return "I found multiple possible collections; please choose one before I list its movies."
    details = await invoke("get_collection_details", {"collection_id": selected["id"]})
    parts = details.get("parts", []) if isinstance(details, dict) else []
    works = "; ".join(f"{x.get('title')} ({str(x.get('release_date', ''))[:4] or 'year unknown'})" for x in parts)
    return f"TMDB collection {details.get('name')}: {works or 'no movies listed'}. Source: {details.get('source_url')}"
