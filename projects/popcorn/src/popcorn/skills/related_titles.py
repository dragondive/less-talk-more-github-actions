"""TMDB similar-title and recommendation workflow."""

from collections.abc import Awaitable, Callable
from typing import Any

SKILL_NAME = "related_titles"
ToolInvoker = Callable[[str, dict[str, object]], Awaitable[Any]]


async def run(arguments: dict[str, object], invoke: ToolInvoker) -> str:
    media, title, relation = arguments.get("media"), arguments.get("title"), arguments.get("relation", "recommendations")
    if media not in ("movie", "tv") or not isinstance(title, str) or relation not in ("recommendations", "similar"):
        return "Provide a movie or TV title and choose recommendations or similar titles."
    found = await invoke("search_movies" if media == "movie" else "search_tv", {"query": title})
    candidates = found.get("results", []) if isinstance(found, dict) else []
    key = "title" if media == "movie" else "name"
    exact = [x for x in candidates if str(x.get(key, "")).casefold() == title.casefold()]
    selected = exact[0] if len(exact) == 1 else candidates[0] if len(candidates) == 1 else None
    if selected is None:
        if not candidates:
            return f"I couldn't find {title!r} in TMDB."
        return "I found multiple matches; please identify the title before I look for related works."
    data = await invoke("get_related_titles", {"media_type": media, "identity": selected["id"], "relation": relation})
    results = data.get("results", []) if isinstance(data, dict) else []
    if not results:
        return f"TMDB has no {relation} listed for {selected.get(key)}."
    lines = [f"{x.get('title')} ({str(x.get('date', ''))[:4] or 'year unknown'}) — {x.get('source_url')}" for x in results[:10]]
    qualifier = "TMDB's related-title results" if relation == "similar" else "TMDB's recommendations"
    return f"{qualifier} for {selected.get(key)} (not a guarantee of personal fit):\n" + "\n".join(lines)
