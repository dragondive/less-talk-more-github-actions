"""Explicit user-requested TMDB ratings for movies, TV, or TV episodes."""

from collections.abc import Awaitable, Callable
from typing import Any

SKILL_NAME = "title_rating"
ToolInvoker = Callable[[str, dict[str, object]], Awaitable[Any]]


async def run(arguments: dict[str, object], invoke: ToolInvoker) -> str:
    media = arguments.get("media", "movie")
    title = arguments.get("title")
    rating = arguments.get("rating")
    if media not in ("movie", "tv", "tv_episode") or not isinstance(title, str):
        return "Provide movie or TV title and a rating."
    if not isinstance(rating, (int, float)) or isinstance(rating, bool) or not 0.5 <= rating <= 10 or round(rating * 2) != rating * 2:
        return "TMDB ratings must be from 0.5 to 10 in half-point increments."
    search_tool = "search_movies" if media == "movie" else "search_tv"
    found = await invoke(search_tool, {"query": title})
    candidates = found.get("results", []) if isinstance(found, dict) else []
    title_key = "title" if media == "movie" else "name"
    exact = [x for x in candidates if str(x.get(title_key, "")).casefold() == title.casefold()]
    selected = exact[0] if len(exact) == 1 else candidates[0] if len(candidates) == 1 else None
    if selected is None:
        if not candidates:
            return f"I couldn't identify {title!r} in TMDB, so I didn't submit a rating."
        choices = "; ".join(f"{x.get(title_key)} ({str(x.get('release_date') or x.get('first_air_date', ''))[:4]}; {x.get('source_url')})" for x in candidates[:5])
        return f"I found multiple possible matches and didn't submit a rating. Which did you mean? {choices}"
    if media == "movie":
        tool, parameters = "rate_movie", {"movie_id": selected["id"]}
    elif media == "tv":
        tool, parameters = "rate_tv", {"series_id": selected["id"]}
    else:
        season, episode = arguments.get("season_number"), arguments.get("episode_number")
        if not isinstance(season, int) or not isinstance(episode, int):
            return "To rate an episode, include its season and episode numbers. No rating was submitted."
        tool, parameters = "rate_tv_episode", {"series_id": selected["id"], "season_number": season, "episode_number": episode}
    result = await invoke(tool, {**parameters, "rating": float(rating), "user_requested": True})
    return f"TMDB rating submitted for {selected.get(title_key)}: {rating:g}/10. {result.get('source_url', '')}"
