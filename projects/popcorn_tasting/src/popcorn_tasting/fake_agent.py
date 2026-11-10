"""Offline chat/provider boundary fakes that exercise Popcorn's real agent and MCP path."""

from __future__ import annotations

import asyncio
import json
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from popcorn import agent, llm, mcp_server
from popcorn.anilist import AniListClient
from popcorn.lastfm import LastFMClient
from popcorn.musicbrainz import MusicBrainzClient
from popcorn.tmdb import TMDBClient

MATRIX = {"id": 603, "title": "The Matrix", "release_date": "1999-03-31", "overview": "A computer hacker discovers reality is a simulation.", "runtime": 136, "genres": [{"name": "Action"}, {"name": "Science Fiction"}], "vote_average": 8.7, "credits": {"cast": [{"name": "Keanu Reeves", "character": "Neo"}, {"name": "Carrie-Anne Moss", "character": "Trinity"}]}}
MBID = "12345678-1234-1234-1234-123456789abc"


ANILIST_MEDIA = {"id": 1, "type": "ANIME", "title": {"english": "Cowboy Bebop"}, "format": "TV", "status": "FINISHED", "description": "A space western following bounty hunters.", "startDate": {"year": 1998}, "genres": ["Action", "Sci-Fi"], "relations": {"edges": [{"relationType": "SIDE_STORY", "node": {"id": 5, "type": "ANIME", "title": {"english": "Cowboy Bebop: The Movie - Knockin' on Heaven's Door"}, "siteUrl": "https://anilist.co/anime/5"}}]}, "characters": {"edges": [{"role": "MAIN", "node": {"id": 1, "name": {"full": "Spike Spiegel"}, "siteUrl": "https://anilist.co/character/1"}}]}, "siteUrl": "https://anilist.co/anime/1"}


def _json_bytes(value: object) -> bytes:
    return json.dumps(value).encode()


def _tool_choice(question: str, history: list[dict[str, str]]) -> tuple[str, dict[str, str]] | None:
    q = question.casefold()
    if "similar artists" in q or "recommend artists like" in q or "last.fm" in q:
        return "music_recommendations", {"artist": "Portishead"}
    if "yoko kanno" in q or "staff credits" in q or "composer credits" in q:
        return "anilist_staff_exploration", {"name": "Yoko Kanno"}
    if "spike spiegel" in q and ("character" in q or "appearances" in q):
        return "anilist_character_exploration", {"name": "Spike Spiegel"}
    if "relation" in q and ("cowboy bebop" in q or history and any("cowboy bebop" in x["content"].casefold() for x in history)):
        return "anilist_relation_exploration", {"title": "Cowboy Bebop", "media_type": "ANIME"}
    if "game of thrones" in q or "tv series" in q:
        return "tv_discovery", {"title": "Game of Thrones"}
    if "keanu reeves" in q and ("filmography" in q or "movies" in q or "credits" in q):
        return "actor_filmography", {"person_name": "Keanu Reeves"}
    if "no such artist" in q or "musicbrainz" in q and "artist" in q and "radiohead" not in q:
        return "music_discovery", {"query": "No Such Artist" if "no such artist" in q else "Mercury"}
    if "mercury" in q:
        return "music_discovery", {"query": "Mercury"}
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
        if parsed.path.endswith("/search/movie"):
            response = {"results": [MATRIX] if "matrix" in query.get("query", [""])[0].casefold() else []}
        elif parsed.path.endswith("/search/tv"):
            response = {"results": [{"id": 1399, "name": "Game of Thrones", "first_air_date": "2011-04-17"}]}
        elif parsed.path.endswith("/tv/1399"):
            response = {"id": 1399, "name": "Game of Thrones", "first_air_date": "2011-04-17", "overview": "Noble families vie for control of the Iron Throne.", "genres": [{"name": "Drama"}, {"name": "Fantasy"}], "aggregate_credits": {"cast": [{"name": "Emilia Clarke", "roles": [{"character": "Daenerys Targaryen"}]}]}}
        elif parsed.path.endswith("/search/person"):
            response = {"results": [{"id": 6384, "name": "Keanu Reeves", "known_for_department": "Acting"}]}
        elif parsed.path.endswith("/person/6384/combined_credits"):
            response = {"cast": [{"id": 603, "media_type": "movie", "title": "The Matrix", "release_date": "1999-03-31", "character": "Neo"}], "crew": []}
        else:
            response = MATRIX
        return record("TMDB", "GET", url, None, response)

    def musicbrainz_http(url, headers, timeout):
        path = urlparse(url).path
        if path.endswith("/artist/"):
            query = parse_qs(urlparse(url).query).get("query", [""])[0].casefold()
            if "no such artist" in query:
                response = {"artists": []}
            elif "mercury" in query:
                response = {"artists": [{"id": MBID, "name": "Mercury", "type": "Person", "area": {"name": "United Kingdom"}}, {"id": "22345678-1234-1234-1234-123456789abc", "name": "Mercury", "type": "Group", "area": {"name": "United States"}}]}
            else:
                response = {"artists": [{"id": MBID, "name": "Radiohead", "type": "Group", "area": {"name": "United Kingdom"}}]}
        elif path.endswith(f"/artist/{MBID}"):
            response = {"id": MBID, "name": "Radiohead", "type": "Group", "area": {"name": "United Kingdom"}, "aliases": []}
        else:
            response = {"release-groups": [{"id": "release-1", "title": "OK Computer", "primary-type": "Album", "first-release-date": "1997-06-16"}]}
        return record("MusicBrainz", "GET", url, None, response)

    def anilist_http(url, headers, timeout, body):
        request = json.loads(body)
        query = request["query"]
        qnorm = query.casefold()
        if "staff(id:" in qnorm:
            response = {"data": {"Staff": {"id": 4, "name": {"full": "Yoko Kanno"}, "description": "Japanese composer.", "primaryOccupations": ["Composer"], "staffMedia": {"edges": [{"staffRole": "Music", "node": {"id": 1, "type": "ANIME", "title": {"english": "Cowboy Bebop"}, "siteUrl": "https://anilist.co/anime/1"}}]}, "characterMedia": {"edges": []}, "siteUrl": "https://anilist.co/staff/4"}}}
        elif "staff(search:" in qnorm:
            response = {"data": {"Page": {"staff": [{"id": 4, "name": {"full": "Yoko Kanno"}, "primaryOccupations": ["Composer"], "siteUrl": "https://anilist.co/staff/4"}]}}}
        elif "character(id:" in qnorm:
            response = {"data": {"Character": {"id": 1, "name": {"full": "Spike Spiegel"}, "description": "A bounty hunter aboard the Bebop.", "media": {"nodes": [{"id": 1, "type": "ANIME", "title": {"english": "Cowboy Bebop"}, "siteUrl": "https://anilist.co/anime/1"}]}, "siteUrl": "https://anilist.co/character/1"}}}
        elif "characters(search:" in qnorm:
            response = {"data": {"Page": {"characters": [{"id": 1, "name": {"full": "Spike Spiegel"}, "siteUrl": "https://anilist.co/character/1"}]}}}
        elif "media(id:" in qnorm:
            response = {"data": {"Media": ANILIST_MEDIA}}
        else:
            response = {"data": {"Page": {"media": [ANILIST_MEDIA]}}}
        return record("AniList", "POST", url, {"query": request["query"], "variables": request["variables"]}, response)

    def lastfm_http(url, headers, timeout):
        params = parse_qs(urlparse(url).query)
        response = {"similarartists": {"artist": [{"name": "Broadcast", "match": "0.7", "url": "https://www.last.fm/music/Broadcast"}]}}
        return record("Last.fm", "GET", url, None, response)

    async def completion(messages, tools, *, model):
        nonlocal request_no
        request_no += 1
        if request_no == 1 and choice:
            name, arguments = choice
            return {"choices": [{"message": {"content": None, "tool_calls": [{"id": "offline-call-1", "function": {"name": name, "arguments": json.dumps(arguments)}}]}}]}
        payload = next((m["content"] for m in reversed(messages) if m.get("role") == "tool"), "")
        if "The Matrix" in payload:
            answer = "TMDB lists The Matrix (1999) as action and science fiction, with Keanu Reeves as Neo and Carrie-Anne Moss as Trinity."
        elif "relation" in question.casefold() and "Cowboy Bebop" in payload:
            answer = "AniList lists a SIDE_STORY edge to Cowboy Bebop: The Movie - Knockin' on Heaven's Door."
        elif "Radiohead" in payload:
            answer = "MusicBrainz lists Radiohead, a UK group, and its release groups include OK Computer. This is a separate music lookup; no soundtrack relationship to The Matrix is established."
        elif "several possible MusicBrainz artists" in payload:
            answer = "MusicBrainz returned multiple candidate artists named Mercury. Please clarify which artist you mean; I won't guess."
        elif "couldn't find an artist" in payload:
            answer = "MusicBrainz returned no artist candidate for that search."
        elif "Broadcast" in payload:
            answer = "Last.fm recommends Broadcast as an artist similar to Portishead, based on Last.fm listening data."
        elif "Yoko Kanno" in payload:
            answer = "AniList lists Yoko Kanno as a composer with a music credit for Cowboy Bebop."
        elif "Spike Spiegel" in payload and ("character" in question.casefold() or "appearance" in question.casefold()):
            answer = "AniList lists Spike Spiegel and associates the character with Cowboy Bebop."
        elif "Game of Thrones" in payload:
            answer = "TMDB lists Game of Thrones as a fantasy drama series first aired in 2011, with Emilia Clarke in the cast."
        elif "Keanu Reeves" in payload:
            answer = "TMDB lists Keanu Reeves' movie acting credits, including The Matrix (1999)."
        elif "Cowboy Bebop" in payload:
            answer = ("AniList lists a SIDE_STORY edge to Cowboy Bebop: The Movie - Knockin' on Heaven's Door." if "relation" in question.casefold()
                      else "AniList lists Cowboy Bebop as a finished 1998 TV anime and explicitly associates Spike Spiegel as a main character.")
        else:
            answer = "I could not find a supported result for that request."
        return {"choices": [{"message": {"content": answer}}]}

    with patch.object(llm, "active_provider_name", return_value="offline-script"), \
         patch.object(llm, "provider_module", return_value=type("FakeLLM", (), {"model_name": staticmethod(lambda: "scripted-fake"), "chat_completion": staticmethod(completion)})), \
         patch.object(mcp_server, "TMDBClient", lambda: TMDBClient(access_token="offline-fixture-token", get_bytes=tmdb_http)), \
         patch.object(mcp_server, "AniListClient", lambda: AniListClient(request_bytes=anilist_http)), \
         patch.object(mcp_server, "LastFMClient", lambda: LastFMClient(api_key="offline-fixture-key", get_bytes=lastfm_http)), \
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


def run_scripted_live_agent(question: str, history: list[dict[str, str]]) -> tuple[str, dict]:
    """Run the same scripted model decisions against configured real provider APIs."""
    choice = _tool_choice(question, history)
    request_no = 0

    async def completion(messages, tools, *, model):
        nonlocal request_no
        request_no += 1
        if request_no == 1 and choice:
            name, arguments = choice
            return {"choices": [{"message": {"content": None, "tool_calls": [{"id": "scripted-live-call", "function": {"name": name, "arguments": json.dumps(arguments)}}]}}]}
        payload = next((m["content"] for m in reversed(messages) if m.get("role") == "tool"), "")
        if "couldn't find" in payload.casefold() or "failed" in payload.casefold():
            answer = "TMDB did not return a usable result, so I can't verify those movie details."
        elif "Radiohead" in payload:
            answer = "MusicBrainz lists Radiohead and its release groups, including OK Computer. The lookup does not establish a soundtrack relationship to The Matrix."
        elif "Cowboy Bebop" in payload:
            answer = ("AniList lists a SIDE_STORY relation from Cowboy Bebop to Cowboy Bebop: The Movie - Knockin' on Heaven's Door." if "relation" in question.casefold()
                      else "AniList lists Cowboy Bebop as a 1998 TV anime and names Spike Spiegel among its main characters.")
        elif "The Matrix" in payload:
            answer = "TMDB lists The Matrix (1999) as action and science fiction, with Keanu Reeves as Neo and Carrie-Anne Moss as Trinity."
        else:
            answer = "The provider did not return a matching record."
        return {"choices": [{"message": {"content": answer}}]}

    with patch.object(llm, "active_provider_name", return_value="scripted-live"), \
         patch.object(llm, "provider_module", return_value=type("ScriptedLLM", (), {"model_name": staticmethod(lambda: "scripted-no-network"), "chat_completion": staticmethod(completion)})):
        response, trace = asyncio.run(agent.answer(question, history=history))
    return response, trace.to_dict()
