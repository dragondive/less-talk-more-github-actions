"""Filtered movie and TV discovery based on criteria supplied by the user."""

from collections.abc import Awaitable, Callable
from typing import Any

SKILL_NAME = "title_discovery"
ToolInvoker = Callable[[str, dict[str, object]], Awaitable[Any]]


async def _resolve(query: str, kind: str, invoke: ToolInvoker, code_key: str) -> str | None:
    if kind == "languages":
        candidate = query.split("-", 1)[0]
        if len(candidate) == 2 and candidate.isalpha():
            return candidate.lower()
    if kind == "countries" and len(query) == 2 and query.isalpha():
        return query.upper()
    found = await invoke("get_reference_data", {"kind": kind, "query": query})
    results = found.get("results", []) if isinstance(found, dict) else []
    exact = [x for x in results if any(str(value).casefold() == query.casefold() for value in x.values())]
    if not exact:
        exact = [x for x in results if query.casefold() in " ".join(str(v) for v in x.values()).casefold()]
    return str(exact[0][code_key]) if len(exact) == 1 and exact[0].get(code_key) else None


async def run(arguments: dict[str, object], invoke: ToolInvoker) -> str:
    media = arguments.get("media", "movie")
    if media not in ("movie", "tv"):
        return "Choose movie or TV discovery."
    tool = "discover_movies" if media == "movie" else "discover_tv"
    filters = {key: arguments[key] for key in (
        "language", "region", "country", "genres", "original_language", "year"
    ) if arguments.get(key) is not None}
    for field in ("region", "country"):
        value = filters.get(field)
        if isinstance(value, str):
            code = await _resolve(value, "countries", invoke, "iso_3166_1")
            if code is None:
                return f"I couldn't match {value!r} to a TMDB country code."
            filters[field] = code
    original_language = filters.get("original_language")
    if isinstance(original_language, str):
        code = await _resolve(original_language, "languages", invoke, "iso_639_1")
        if code is None:
            return f"I couldn't match {original_language!r} to a TMDB language code."
        filters["original_language"] = code
    genres = filters.get("genres")
    if isinstance(genres, str) and not all(part.strip().isdigit() for part in genres.replace("|", ",").split(",")):
        codes = []
        kind = "movie_genres" if media == "movie" else "tv_genres"
        separator = "|" if "|" in genres else ","
        for name in genres.split(separator):
            code = await _resolve(name.strip(), kind, invoke, "id")
            if code is None:
                return f"I couldn't match {name.strip()!r} to a TMDB {media} genre."
            codes.append(code)
        filters["genres"] = separator.join(codes)
    found = await invoke(tool, filters)
    results = found.get("results", []) if isinstance(found, dict) else []
    if not results:
        return "TMDB found no titles matching those filters."
    title_key = "title" if media == "movie" else "name"
    date_key = "release_date" if media == "movie" else "first_air_date"
    lines = [f"{x.get(title_key)} ({str(x.get(date_key, ''))[:4] or 'year unknown'}; TMDB rating {x.get('vote_average', 'not listed')}) — {x.get('source_url')}"
             for x in results[:10]]
    return "TMDB discovery results:\n" + "\n".join(lines)
