"""Country-specific streaming/rental/purchase provider lookup."""

from collections.abc import Awaitable, Callable
from typing import Any

SKILL_NAME = "watch_availability"
ToolInvoker = Callable[[str, dict[str, object]], Awaitable[Any]]


async def run(arguments: dict[str, object], invoke: ToolInvoker) -> str:
    media, title, country = arguments.get("media"), arguments.get("title"), arguments.get("country")
    if media not in ("movie", "tv") or not isinstance(title, str) or not isinstance(country, str):
        return "Provide a movie or TV title and a country."
    if len(country) == 2 and country.isalpha():
        country_code = country.upper()
    else:
        country_data = await invoke("get_reference_data", {"kind": "countries", "query": country})
        values = country_data.get("results", []) if isinstance(country_data, dict) else []
        matches = [x for x in values if any(str(v).casefold() == country.casefold() for v in x.values())]
        if len(matches) != 1:
            return f"I couldn't match {country!r} to a TMDB country code."
        country_code = str(matches[0].get("iso_3166_1", "")).upper()
    found = await invoke("search_movies" if media == "movie" else "search_tv", {"query": title})
    candidates = found.get("results", []) if isinstance(found, dict) else []
    key = "title" if media == "movie" else "name"
    exact = [x for x in candidates if str(x.get(key, "")).casefold() == title.casefold()]
    selected = exact[0] if len(exact) == 1 else candidates[0] if len(candidates) == 1 else None
    if selected is None:
        return "I couldn't identify a unique TMDB title, so I didn't check availability."
    result = await invoke("get_watch_providers", {"media_type": media, "identity": selected["id"], "country": country_code})
    providers = result.get("results", []) if isinstance(result, dict) else []
    if not providers:
        return f"TMDB lists no streaming, rental, or purchase providers for {selected.get(key)} in {country_code}."
    entries = "; ".join(f"{x.get('provider')} ({x.get('availability')})" for x in providers)
    link = result.get("tmdb_link")
    return f"Where to watch {selected.get(key)} in {country_code}: {entries}. Availability data by JustWatch via TMDB. {link or ''}"
