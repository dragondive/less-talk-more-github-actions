"""Look up TMDB's language, country, and genre reference codes."""

from collections.abc import Awaitable, Callable
from typing import Any

SKILL_NAME = "tmdb_reference"
ToolInvoker = Callable[[str, dict[str, object]], Awaitable[Any]]


async def run(kind: str, query: str, invoke: ToolInvoker) -> str:
    found = await invoke("get_reference_data", {"kind": kind, "query": query})
    results = found.get("results", []) if isinstance(found, dict) else []
    if not results:
        return f"TMDB has no {kind} entries matching {query!r}."
    label_fields = {
        "languages": ("english_name", "name", "iso_639_1"),
        "countries": ("english_name", "native_name", "iso_3166_1"),
    }
    fields = label_fields.get(kind, ("name", "id"))
    rows = [" — ".join(str(x[k]) for k in fields if x.get(k)) for x in results[:15]]
    return f"TMDB {kind} reference values:\n" + "\n".join(rows)
