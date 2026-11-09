"""Actor search and movie-credit skill backed by TMDB MCP tools."""

from collections.abc import Awaitable, Callable
from typing import Any

SKILL_NAME = "actor_filmography"
ToolInvoker = Callable[[str, dict[str, object]], Awaitable[Any]]


async def run(name: str, invoke: ToolInvoker, media: str = "all") -> str:
    found = await invoke("search_people", {"query": name})
    candidates = found.get("results", []) if isinstance(found, dict) else []
    if not candidates:
        return f"I couldn't find a person matching {name!r} in TMDB."

    actors = [item for item in candidates if item.get("known_for_department") == "Acting"] or candidates
    exact = [item for item in actors if str(item.get("name", "")).casefold() == name.casefold()]
    selected = exact[0] if len(exact) == 1 else actors[0] if len(actors) == 1 else None
    if selected is None:
        choices = "; ".join(
            f"{item.get('name')} ({item.get('known_for_department') or 'department unknown'}; {item.get('source_url')})"
            for item in actors[:5]
        )
        return f"I found several people matching {name!r}. Which one did you mean? {choices}"

    if media == "movie":
        credits = await invoke("get_person_movie_credits", {"person_id": selected["id"]})
        raw_works = credits.get("results", []) if isinstance(credits, dict) else []
        works = [{**work, "date": work.get("release_date", ""), "media_type": "movie"} for work in raw_works]
    else:
        credits = await invoke("get_person_combined_credits", {"person_id": selected["id"]})
        works = credits.get("results", []) if isinstance(credits, dict) else []
        if media == "tv":
            works = [work for work in works if work.get("media_type") == "tv"]
    if not works:
        return f"TMDB has no movie acting credits listed for {selected.get('name')}."
    titles = "; ".join(
        f"{work.get('title')} ({str(work.get('date', ''))[:4] or 'year unknown'}, {work.get('media_type', 'title')})"
        for work in works[:15]
        if work.get("title")
    )
    return (
        f"TMDB lists these movie credits for {selected.get('name')}: {titles}. "
        f"Person source: {selected.get('source_url')}."
    )
