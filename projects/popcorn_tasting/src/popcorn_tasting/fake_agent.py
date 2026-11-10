"""Offline chat/provider boundary fakes that exercise Popcorn's real agent and MCP path."""

from __future__ import annotations

import asyncio
import json
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from popcorn import agent, llm, mcp_server
from popcorn.anilist import AniListClient
from popcorn.musicbrainz import MusicBrainzClient
from popcorn.tmdb import TMDBClient

MATRIX = {"id": 603, "title": "The Matrix", "release_date": "1999-03-31", "overview": "A computer hacker discovers reality is a simulation.", "runtime": 136, "genres": [{"name": "Action"}, {"name": "Science Fiction"}], "vote_average": 8.7, "credits": {"cast": [{"name": "Keanu Reeves", "character": "Neo"}, {"name": "Carrie-Anne Moss", "character": "Trinity"}]}}
MBID = "12345678-1234-1234-1234-123456789abc"


ANILIST_MEDIA = {"id": 1, "type": "ANIME", "title": {"english": "Cowboy Bebop"}, "format": "TV", "status": "FINISHED", "description": "A space western following bounty hunters.", "startDate": {"year": 1998}, "genres": ["Action", "Sci-Fi"], "relations": {"edges": [{"relationType": "PREQUEL", "node": {"id": 2, "type": "ANIME", "title": {"english": "Cowboy Bebop: The Movie"}, "siteUrl": "https://anilist.co/anime/2"}}]}, "characters": {"edges": [{"role": "MAIN", "node": {"id": 3, "name": {"full": "Spike Spiegel"}, "siteUrl": "https://anilist.co/character/3"}}]}, "siteUrl": "https://anilist.co/anime/1"}


def _json_bytes(value: object) -> bytes:
    return json.dumps(value).encode()


def _tool_choice(question: str, history: list[dict[str, str]]) -> tuple[str, dict[str, str]] | None:
    q = question.casefold()
    if "music" in q or "radiohead" in q:
        return "music_discovery", {"query": "Radiohead"}
    if "anime" in q or "bebop" in q or "spike" in q or (history and any("bebop" in x["content"].casefold() for x in history)):
        title = "Cowboy Bebop" if any(x in q for x in ("bebop", "spike")) else "Cowboy Bebop"
        return "anime_manga_discovery", {"title": title, "media": "ANIME"}
    if "matrix" in q or (history and any("matrix" in x["content"].casefold() for x in history)):
        return "movie_discovery", {"title": "The Matrix"}
    return None


def run_fake_agent(question: str, history: list[dict[str, str]]) -> tuple[str, dict]:
    """Fake model and HTTP boundaries; execute real provider adapters, agent and MCP path."""
    choice = _tool_choice(question, history)
    request_no = 0
    provider_requests: list[dict] = []

    def record(provider: str, method: str, url: str, request: object, response: object) -> bytes:
        parsed = urlparse(url)
        provider_requests.append({"provider": provider, "method": method, "url": url,
            "query": parse_qs(parsed.query), "request": request, "response": response})
        return _json_bytes(response)

    def tmdb_http(url, headers, timeout):
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        response = {"results": [MATRIX] if "matrix" in query.get("query", [""])[0].casefold() else []} if parsed.path.endswith("/search/movie") else MATRIX
        return record("TMDB", "GET", url, None, response)

    def musicbrainz_http(url, headers, timeout):
        path = urlparse(url).path
        if path.endswith("/artist/"):
            response = {"artists": [{"id": MBID, "name": "Radiohead", "type": "Group", "area": {"name": "United Kingdom"}}]}
        elif path.endswith(f"/artist/{MBID}"):
            response = {"id": MBID, "name": "Radiohead", "type": "Group", "area": {"name": "United Kingdom"}, "aliases": []}
        else:
            response = {"release-groups": [{"id": "release-1", "title": "OK Computer", "primary-type": "Album", "first-release-date": "1997-06-16"}]}
        return record("MusicBrainz", "GET", url, None, response)

    def anilist_http(url, headers, timeout, body):
        request = json.loads(body)
        response = {"data": {"Media": ANILIST_MEDIA}} if "Media(id:" in request["query"] else {"data": {"Page": {"media": [ANILIST_MEDIA]}}}
        return record("AniList", "POST", url, {"query": request["query"], "variables": request["variables"]}, response)

    async def completion(messages, tools, *, model):
        nonlocal request_no
        request_no += 1
        if request_no == 1 and choice:
            name, arguments = choice
            return {"choices": [{"message": {"content": None, "tool_calls": [{"id": "offline-call-1", "function": {"name": name, "arguments": json.dumps(arguments)}}]}}]}
        payload = next((m["content"] for m in reversed(messages) if m.get("role") == "tool"), "")
        if "Radiohead" in payload:
            answer = "MusicBrainz lists Radiohead, a UK group, and its release groups include OK Computer. This is a separate music lookup; no soundtrack relationship to The Matrix is established."
        elif "Cowboy Bebop" in payload:
            answer = ("AniList's details include an explicit PREQUEL edge to Cowboy Bebop: The Movie." if "relation" in question.casefold()
                      else "AniList lists Cowboy Bebop as a finished 1998 TV anime and explicitly associates Spike Spiegel as a main character.")
        elif "The Matrix" in payload:
            answer = "TMDB lists The Matrix (1999) as action and science fiction, with Keanu Reeves as Neo and Carrie-Anne Moss as Trinity."
        else:
            answer = "I could not find a supported result for that request."
        return {"choices": [{"message": {"content": answer}}]}

    with patch.object(llm, "active_provider_name", return_value="offline-script"), \
         patch.object(llm, "provider_module", return_value=type("FakeLLM", (), {"model_name": staticmethod(lambda: "scripted-fake"), "chat_completion": staticmethod(completion)})), \
         patch.object(mcp_server, "TMDBClient", lambda: TMDBClient(access_token="offline-fixture-token", get_bytes=tmdb_http)), \
         patch.object(mcp_server, "AniListClient", lambda: AniListClient(request_bytes=anilist_http)), \
         patch.object(mcp_server, "_musicbrainz", MusicBrainzClient(request_bytes=musicbrainz_http, clock=lambda: 0, sleeper=lambda _: None)):
        original_call_tool = agent._call_tool

        async def traced_call_tool(name, arguments, trace, parent_id):
            start = len(provider_requests)
            result = await original_call_tool(name, arguments, trace, parent_id)
            if len(provider_requests) > start:
                trace.events[-1].attributes["provider_http"] = agent._trace_value(provider_requests[start:])
            return result

        with patch.object(agent, "_call_tool", traced_call_tool):
            response, trace = asyncio.run(agent.answer(question, history=history))
    return response, trace.to_dict()
