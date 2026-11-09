"""MusicBrainz artist and release discovery workflow."""

from collections.abc import Awaitable, Callable
from typing import Any

SKILL_NAME = "music_discovery"
ToolInvoker = Callable[[str, dict[str, object]], Awaitable[Any]]


async def run(query: str, invoke: ToolInvoker) -> str:
    found = await invoke("search_musicbrainz_artists", {"query": query})
    candidates = found.get("results", []) if isinstance(found, dict) else []
    if not candidates:
        return f"I couldn't find an artist matching {query!r} in MusicBrainz."
    exact = [x for x in candidates if str(x.get("name", "")).casefold() == query.casefold()]
    if len(exact) == 1:
        selected = exact[0]
    elif len(candidates) == 1:
        selected = candidates[0]
    else:
        choices = "; ".join(f"{x.get('name')} ({x.get('type') or 'type unknown'}; {x.get('area') or 'area unknown'}; {x.get('source_url')})" for x in candidates[:6])
        return f"I found several possible MusicBrainz artists for {query!r}. Which one did you mean? {choices}"
    details = await invoke("get_musicbrainz_artist", {"mbid": selected["id"]})
    groups = await invoke("get_musicbrainz_artist_release_groups", {"mbid": selected["id"]})
    releases = groups.get("results", []) if isinstance(groups, dict) else []
    discography = "; ".join(f"{x.get('title')} ({x.get('first-release-date') or 'date unknown'}; {x.get('type') or 'type unknown'})" for x in releases[:8]) or "none listed"
    aliases = ", ".join(x.get("name", "") for x in details.get("aliases", [])[:5] if isinstance(x, dict)) or "none listed"
    area = details.get("area")
    area_name = area.get("name") if isinstance(area, dict) else area
    return (f"{details.get('name')} — {details.get('type') or 'type not listed'}; area: {area_name or 'not listed'}\n"
            f"Disambiguation: {details.get('disambiguation') or 'not listed'}; aliases: {aliases}\n"
            f"Release groups: {discography}\nSource: {details.get('source_url')} (MusicBrainz).")
