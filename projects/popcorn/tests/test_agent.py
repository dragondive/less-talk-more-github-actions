import asyncio
import pytest

from popcorn.agent import answer
from popcorn import gemini
from popcorn import llm
from popcorn import mcp_server
from popcorn import deepseek


class FakeTMDB:
    async def search_movies(self, query, year=None, language="en-US"):
        return [{"id": 603, "title": "The Matrix", "release_date": "1999-03-31"}]

    async def movie_details(self, movie_id, language="en-US"):
        return {
            "id": movie_id,
            "title": "The Matrix",
            "release_date": "1999-03-31",
            "overview": "A computer hacker learns the truth.",
            "runtime": 136,
            "genres": [{"name": "Action"}, {"name": "Science Fiction"}],
            "vote_average": 8.2,
            "credits": {"cast": [{"name": "Keanu Reeves", "character": "Neo"}]},
        }

    async def search_people(self, query):
        return [{"id": 6384, "name": "Keanu Reeves", "known_for_department": "Acting"}]

    async def person_movie_credits(self, person_id):
        return [{"id": 603, "title": "The Matrix", "release_date": "1999-03-31", "character": "Neo"}]

    async def person_combined_credits(self, person_id):
        return {"cast": [{"id": 603, "media_type": "movie", "title": "The Matrix", "release_date": "1999-03-31", "character": "Neo"}], "crew": []}

    async def search_tv(self, query, year=None, language="en-US"):
        return [{"id": 1399, "name": "Game of Thrones", "first_air_date": "2011-04-17"}]

    async def tv_details(self, series_id, language="en-US"):
        return {"id": series_id, "name": "Game of Thrones", "first_air_date": "2011-04-17", "overview": "Fantasy drama.",
                "genres": [{"name": "Drama"}], "aggregate_credits": {"cast": [{"name": "Actor", "roles": [{"character": "Hero"}]}]}}

    async def discover_movies(self, **filters):
        return [{"id": 10, "title": "Example", "release_date": "2020-01-01", "vote_average": 7.1}]

    async def create_guest_session(self):
        return "temporary-session"

    async def rate_movie(self, movie_id, rating, guest_session_id):
        return {"status_message": "Success"}


class FakeAniList:
    async def search_media(self, query, media_type):
        return [{"id": 1, "type": media_type, "title": {"english": "Cowboy Bebop"}, "format": "TV", "startDate": {"year": 1998}, "siteUrl": "https://anilist.co/anime/1"}]

    async def media_details(self, identity, media_type):
        return {"id": identity, "title": {"english": "Cowboy Bebop"}, "format": "TV", "status": "FINISHED", "description": "A space western.", "startDate": {"year": 1998}, "genres": ["Adventure"], "relations": {"edges": [{"relationType": "PREQUEL", "node": {"id": 2, "title": {"english": "Example Prequel"}, "siteUrl": "https://anilist.co/anime/2"}}]}, "characters": {"edges": [{"role": "MAIN", "node": {"id": 3, "name": {"full": "Spike Spiegel"}, "siteUrl": "https://anilist.co/character/3"}}]}, "siteUrl": "https://anilist.co/anime/1"}

    async def discover_media(self, media_type, filters):
        return [{"id": 1, "type": media_type, "format": "TV", "title": {"english": "Cowboy Bebop"}, "siteUrl": "https://anilist.co/anime/1"}]

    async def search_character(self, query):
        return [{"id": 3, "name": {"full": "Spike Spiegel"}, "siteUrl": "https://anilist.co/character/3"}]

    async def character_details(self, identity):
        return {"id": identity, "name": {"full": "Spike Spiegel"}, "description": "A bounty hunter.", "media": {"nodes": [{"id": 1, "type": "ANIME", "title": {"english": "Cowboy Bebop"}, "siteUrl": "https://anilist.co/anime/1"}]}, "siteUrl": "https://anilist.co/character/3"}

    async def search_staff(self, query):
        return [{"id": 4, "name": {"full": "Yoko Kanno"}, "siteUrl": "https://anilist.co/staff/4"}]

    async def staff_details(self, identity):
        return {"id": identity, "name": {"full": "Yoko Kanno"}, "primaryOccupations": ["Composer"], "staffMedia": {"edges": [{"staffRole": "Music", "node": {"id": 1, "type": "ANIME", "title": {"english": "Cowboy Bebop"}, "siteUrl": "https://anilist.co/anime/1"}}]}, "characterMedia": {"edges": [{"characterName": "Faye Valentine", "node": {"id": 1, "type": "ANIME", "title": {"english": "Cowboy Bebop"}, "siteUrl": "https://anilist.co/anime/1"}}]}, "siteUrl": "https://anilist.co/staff/4"}


@pytest.fixture(autouse=True)
def settings_use_test_defaults(monkeypatch):
    monkeypatch.setattr(llm, "configured_value", lambda _name: "")


def test_movie_skill_uses_mcp_tools_and_traces_provider_calls(monkeypatch):
    monkeypatch.setattr(mcp_server, "TMDBClient", FakeTMDB)
    monkeypatch.setattr(gemini, "api_key", lambda: "")
    monkeypatch.setattr(deepseek, "api_key", lambda: "")
    response, trace = asyncio.run(answer("Who is in The Matrix?"))
    assert "Keanu Reeves as Neo" in response
    assert "https://www.themoviedb.org/movie/603" in response
    assert [event.attributes.get("tool") for event in trace.events if event.name == "mcp.tool.call"] == [
        "search_movies",
        "get_movie_details",
    ]
    assert any(event.attributes.get("skill") == "movie_discovery" for event in trace.events)


def test_actor_skill_uses_tmdb_person_and_credit_tools(monkeypatch):
    monkeypatch.setattr(mcp_server, "TMDBClient", FakeTMDB)
    monkeypatch.setattr(gemini, "api_key", lambda: "")
    monkeypatch.setattr(deepseek, "api_key", lambda: "")
    response, trace = asyncio.run(answer("What movies has Keanu Reeves acted in?"))
    assert "The Matrix (1999," in response
    assert "https://www.themoviedb.org/person/6384" in response
    assert [event.attributes.get("tool") for event in trace.events if event.name == "mcp.tool.call"] == [
        "search_people", "get_person_combined_credits",
    ]
    assert any(event.attributes.get("skill") == "actor_filmography" for event in trace.events)


def test_unsupported_intent_does_not_call_mcp(monkeypatch):
    monkeypatch.setattr(gemini, "api_key", lambda: "")
    monkeypatch.setattr(deepseek, "api_key", lambda: "")
    response, trace = asyncio.run(answer("Hello there"))
    assert "movie, TV, anime, manga, and music artist details" in response
    assert not any(event.name == "mcp.tool.call" for event in trace.events)


def test_trace_payloads_redact_secrets_and_bound_large_values():
    from popcorn.agent import _trace_value

    safe = _trace_value({"api_key": "do-not-store", "nested": {"Authorization": "Bearer secret"}, "ok": "value"})
    assert safe == {"api_key": "[REDACTED]", "nested": {"Authorization": "[REDACTED]"}, "ok": "value"}
    bounded = _trace_value({"payload": "x" * 20_000}, limit=100)
    assert bounded["truncated"] is True
    assert bounded["original_chars"] > 100


def test_deepseek_selects_skill_and_returns_final_response(monkeypatch):
    monkeypatch.setattr(deepseek, "api_key", lambda: "test-secret")
    monkeypatch.setattr(gemini, "api_key", lambda: "")
    monkeypatch.setattr(deepseek, "model_name", lambda: "deepseek-flash")
    monkeypatch.setattr(mcp_server, "TMDBClient", FakeTMDB)
    calls = iter(
        [
            {
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "function": {
                                        "name": "movie_discovery",
                                        "arguments": '{"title":"The Matrix"}',
                                    },
                                }
                            ],
                        }
                    }
                ],
                "usage": {"prompt_tokens": 20, "completion_tokens": 8},
            },
            {
                "choices": [
                    {"message": {"content": "The Matrix stars Keanu Reeves as Neo."}}
                ]
            },
        ]
    )

    async def fake_completion(messages, tools, *, model):
        assert model == "deepseek-flash"
        assert tools
        return next(calls)

    monkeypatch.setattr(deepseek, "chat_completion", fake_completion)
    response, trace = asyncio.run(answer("Who is in The Matrix?"))

    assert response == "The Matrix stars Keanu Reeves as Neo."
    assert [event.name for event in trace.events].count("llm.request") == 2
    assert any(event.attributes.get("skill") == "movie_discovery" for event in trace.events)
    assert [event.attributes.get("tool") for event in trace.events if event.name == "mcp.tool.call"] == [
        "search_movies",
        "get_movie_details",
    ]
    assert any(
        event.attributes.get("input_tokens") == 20
        for event in trace.events
        if event.name == "llm.request"
    )


def test_gemini_selects_skill_and_records_provider(monkeypatch):
    monkeypatch.setattr(llm, "active_provider_name", lambda: "gemini")
    monkeypatch.setattr(gemini, "model_name", lambda: "gemini-test-model")
    monkeypatch.setattr(mcp_server, "TMDBClient", FakeTMDB)
    calls = iter([
        {"choices": [{"message": {"content": None, "tool_calls": [{
            "id": "gemini_call_0", "function": {"name": "actor_filmography", "arguments": '{"person_name":"Keanu Reeves"}'}
        }]}}], "usage": {"prompt_tokens": 11, "completion_tokens": 5}},
        {"choices": [{"message": {"content": "Keanu Reeves appeared in The Matrix."}}]},
    ])

    async def fake_completion(messages, tools, *, model):
        assert model == "gemini-test-model"
        assert tools
        return next(calls)

    monkeypatch.setattr(gemini, "chat_completion", fake_completion)
    response, trace = asyncio.run(answer("Find Keanu Reeves's cinematic acting history."))

    assert response == "Keanu Reeves appeared in The Matrix."
    assert [event.attributes.get("provider") for event in trace.events if event.name == "llm.request"] == ["gemini", "gemini"]
    assert any(event.attributes.get("skill") == "actor_filmography" for event in trace.events)
    assert [event.attributes.get("tool") for event in trace.events if event.name == "mcp.tool.call"] == [
        "search_people", "get_person_combined_credits"
    ]


def test_gemini_selects_tv_skill_and_runs_tmdb_mcp_flow(monkeypatch):
    monkeypatch.setattr(llm, "active_provider_name", lambda: "gemini")
    monkeypatch.setattr(gemini, "model_name", lambda: "gemini-test-model")
    monkeypatch.setattr(mcp_server, "TMDBClient", FakeTMDB)
    calls = iter([
        {"choices": [{"message": {"content": None, "tool_calls": [{"id": "tv1", "function": {"name": "tv_discovery", "arguments": '{"title":"Game of Thrones"}'}}]}}]},
        {"choices": [{"message": {"content": "Game of Thrones is a fantasy drama series."}}]},
    ])
    async def fake_completion(messages, tools, *, model):
        return next(calls)
    monkeypatch.setattr(gemini, "chat_completion", fake_completion)
    response, trace = asyncio.run(answer("Tell me about Game of Thrones the TV series"))
    assert "fantasy drama" in response
    assert [event.attributes.get("tool") for event in trace.events if event.name == "mcp.tool.call"] == ["search_tv", "get_tv_details"]
    assert any(event.attributes.get("skill") == "tv_discovery" for event in trace.events)


def test_gemini_selects_music_skill_through_musicbrainz_mcp(monkeypatch):
    class FakeMusicBrainz:
        async def search_artists(self, query):
            return [{"id": "12345678-1234-1234-1234-123456789abc", "name": "Yoko Kanno", "type": "Person", "area": {"name": "Japan"}}]
        async def artist_details(self, mbid):
            return {"id": mbid, "name": "Yoko Kanno", "type": "Person", "area": {"name": "Japan"}, "aliases": []}
        async def artist_release_groups(self, mbid):
            return [{"id": "def", "title": "Cowboy Bebop", "primary-type": "Album", "first-release-date": "1998"}]

    monkeypatch.setattr(llm, "active_provider_name", lambda: "gemini")
    monkeypatch.setattr(gemini, "model_name", lambda: "gemini-test-model")
    monkeypatch.setattr(mcp_server, "_musicbrainz", FakeMusicBrainz())
    calls = iter([
        {"choices": [{"message": {"content": None, "tool_calls": [{"id": "music1", "function": {"name": "music_discovery", "arguments": '{"query":"Yoko Kanno"}'}}]}}]},
        {"choices": [{"message": {"content": "Yoko Kanno released the Cowboy Bebop soundtrack album."}}]},
    ])
    async def fake_completion(messages, tools, *, model):
        assert any(tool["function"]["name"] == "music_discovery" for tool in tools)
        return next(calls)
    monkeypatch.setattr(gemini, "chat_completion", fake_completion)
    response, trace = asyncio.run(answer("What has Yoko Kanno released?"))
    assert "Cowboy Bebop" in response
    assert [e.attributes.get("provider") for e in trace.events if e.name == "mcp.tool.call"] == ["MusicBrainz"] * 3
    assert [e.attributes.get("tool") for e in trace.events if e.name == "mcp.tool.call"] == [
        "search_musicbrainz_artists", "get_musicbrainz_artist", "get_musicbrainz_artist_release_groups"]


def test_gemini_selects_lastfm_music_recommendations(monkeypatch):
    class FakeLastFM:
        async def similar_artists(self, artist, limit):
            return [{"name": "Broadcast", "match": "0.7", "url": "https://www.last.fm/music/Broadcast"}]

        async def similar_tracks(self, artist, track, limit):
            return [{"name": "Ray of Light", "artist": {"name": "Madonna"}, "match": "0.5", "url": "https://www.last.fm/music/Madonna/_/Ray+of+Light"}]

    monkeypatch.setattr(llm, "active_provider_name", lambda: "gemini")
    monkeypatch.setattr(gemini, "model_name", lambda: "gemini-test-model")
    monkeypatch.setattr(mcp_server, "LastFMClient", lambda: FakeLastFM())
    calls = iter([
        {"choices": [{"message": {"content": None, "tool_calls": [{"id": "rec1", "function": {"name": "music_recommendations", "arguments": '{"artist":"Portishead"}'}}]}}]},
        {"choices": [{"message": {"content": "Try Broadcast, which Last.fm suggests as similar to Portishead."}}]},
    ])

    async def fake_completion(messages, tools, *, model):
        assert any(tool["function"]["name"] == "music_recommendations" for tool in tools)
        return next(calls)

    monkeypatch.setattr(gemini, "chat_completion", fake_completion)
    response, trace = asyncio.run(answer("Recommend artists like Portishead"))
    assert "Broadcast" in response
    assert [e.attributes.get("provider") for e in trace.events if e.name == "mcp.tool.call"] == ["Last.fm"]
    assert [e.attributes.get("tool") for e in trace.events if e.name == "mcp.tool.call"] == ["get_lastfm_recommendations"]


def test_answer_includes_bounded_conversation_history_in_llm_messages(monkeypatch):
    monkeypatch.setattr(llm, "active_provider_name", lambda: "gemini")
    monkeypatch.setattr(gemini, "model_name", lambda: "gemini-test-model")
    captured = {}

    async def fake_completion(messages, tools, *, model):
        captured["messages"] = messages
        return {"choices": [{"message": {"content": "The sequel is The Matrix Reloaded."}}]}

    monkeypatch.setattr(gemini, "chat_completion", fake_completion)
    history = [
        {"role": "user", "content": f"Earlier question {i}"} if i % 2 == 0
        else {"role": "assistant", "content": f"Earlier answer {i}"}
        for i in range(12)
    ]
    response, trace = asyncio.run(answer("What about the sequel?", history=history))
    messages = captured["messages"]
    assert response == "The sequel is The Matrix Reloaded."
    assert messages[0]["role"] == "system"
    assert messages[-1] == {"role": "user", "content": "What about the sequel?"}
    assert len(messages[1:-1]) == 8
    assert messages[1]["content"] == "Earlier question 4"
    assert messages[-2]["content"] == "Earlier answer 11"
    run_event = next(event for event in trace.events if event.name == "agent.run")
    assert run_event.attributes["history_messages"] == 8


def test_gemini_selects_anime_skill_through_anilist_mcp(monkeypatch):
    monkeypatch.setattr(llm, "active_provider_name", lambda: "gemini")
    monkeypatch.setattr(gemini, "model_name", lambda: "gemini-test-model")
    monkeypatch.setattr(mcp_server, "AniListClient", FakeAniList)
    calls = iter([
        {"choices": [{"message": {"content": None, "tool_calls": [{"id": "anime1", "function": {"name": "anime_manga_discovery", "arguments": '{"title":"Cowboy Bebop","media":"ANIME"}'}}]}}]},
        {"choices": [{"message": {"content": "Cowboy Bebop is a 1998 adventure anime."}}]},
    ])
    async def fake_completion(messages, tools, *, model):
        assert any(tool["function"]["name"] == "anime_manga_discovery" for tool in tools)
        return next(calls)
    monkeypatch.setattr(gemini, "chat_completion", fake_completion)
    response, trace = asyncio.run(answer("Tell me about Cowboy Bebop anime"))
    assert "1998 adventure anime" in response
    tool_events = [event for event in trace.events if event.name == "mcp.tool.call"]
    assert [event.attributes.get("tool") for event in tool_events] == ["search_anilist_media", "get_anilist_media_details"]
    assert all(event.attributes.get("server") == "popcorn-discovery" and event.attributes.get("provider") == "AniList" for event in tool_events)
    assert any(event.attributes.get("skill") == "anime_manga_discovery" for event in trace.events)


@pytest.mark.parametrize(("tool_name", "arguments", "wanted_skill", "expected_tools"), [
    ("anilist_filtered_discovery", '{"media_type":"ANIME","genre":"Adventure"}', "anilist_filtered_discovery", ["discover_anilist_media"]),
    ("anilist_character_exploration", '{"name":"Spike Spiegel"}', "anilist_character_exploration", ["search_anilist_characters", "get_anilist_character_details"]),
    ("anilist_staff_exploration", '{"name":"Yoko Kanno"}', "anilist_staff_exploration", ["search_anilist_staff", "get_anilist_staff_details"]),
    ("anilist_relation_exploration", '{"title":"Cowboy Bebop","media_type":"ANIME"}', "anilist_relation_exploration", ["search_anilist_media", "get_anilist_media_details"]),
])
def test_anilist_capability_tools_call_their_skills_and_mcp_tools(monkeypatch, tool_name, arguments, wanted_skill, expected_tools):
    monkeypatch.setattr(llm, "active_provider_name", lambda: "gemini")
    monkeypatch.setattr(gemini, "model_name", lambda: "gemini-test-model")
    monkeypatch.setattr(mcp_server, "AniListClient", FakeAniList)
    calls = iter([
        {"choices": [{"message": {"content": None, "tool_calls": [{"id": "anilist1", "function": {"name": tool_name, "arguments": arguments}}]}}]},
        {"choices": [{"message": {"content": "Here are the AniList results."}}]},
    ])
    async def fake_completion(messages, tools, *, model):
        assert any(tool["function"]["name"] == tool_name for tool in tools)
        return next(calls)
    monkeypatch.setattr(gemini, "chat_completion", fake_completion)
    response, trace = asyncio.run(answer("Please explore AniList."))
    assert response == "Here are the AniList results."
    assert [event.attributes.get("tool") for event in trace.events if event.name == "mcp.tool.call"] == expected_tools
    assert any(event.attributes.get("skill") == wanted_skill for event in trace.events)


def test_explicit_rating_runs_title_match_then_guest_rating_mcp_tool(monkeypatch):
    monkeypatch.setattr(llm, "active_provider_name", lambda: "gemini")
    monkeypatch.setattr(gemini, "model_name", lambda: "gemini-test-model")
    monkeypatch.setattr(mcp_server, "TMDBClient", FakeTMDB)
    calls = iter([
        {"choices": [{"message": {"content": None, "tool_calls": [{"id": "rate1", "function": {"name": "title_rating", "arguments": '{"media":"movie","title":"The Matrix","rating":8.5}'}}]}}]},
        {"choices": [{"message": {"content": "I submitted an 8.5/10 rating for The Matrix."}}]},
    ])
    async def fake_completion(messages, tools, *, model):
        return next(calls)
    monkeypatch.setattr(gemini, "chat_completion", fake_completion)
    response, trace = asyncio.run(answer("Rate The Matrix 8.5 out of 10"))
    assert "submitted" in response
    assert [event.attributes.get("tool") for event in trace.events if event.name == "mcp.tool.call"] == ["search_movies", "rate_movie"]
