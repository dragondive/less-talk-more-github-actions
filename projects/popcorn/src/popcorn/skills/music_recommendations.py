"""Seed-based music recommendation workflow backed by Last.fm."""

from collections.abc import Awaitable, Callable
from typing import Any

SKILL_NAME = "music_recommendations"
ToolInvoker = Callable[[str, dict[str, object]], Awaitable[Any]]


async def run(*, invoke: ToolInvoker, artist: str | None = None,
              track: str | None = None) -> str:
    if track:
        result = await invoke("get_lastfm_recommendations", {"artist": artist, "track": track})
        candidates = result.get("results", []) if isinstance(result, dict) else []
        heading = f"Tracks similar to {artist} — {track}"
        items = [f"{x.get('artist')}: {x.get('name')} (match {x.get('match')}; {x.get('source_url')})" for x in candidates]
    else:
        result = await invoke("get_lastfm_recommendations", {"artist": artist, "track": None})
        candidates = result.get("results", []) if isinstance(result, dict) else []
        heading = f"Artists similar to {artist}"
        items = [f"{x.get('name')} (match {x.get('match')}; {x.get('source_url')})" for x in candidates]
    if not items:
        return f"Last.fm did not return recommendations for {artist}{' — ' + track if track else ''}."
    return f"{heading} (based on Last.fm listening data):\n" + "\n".join(f"- {item}" for item in items) + "\nSource: Last.fm."
