import asyncio

from popcorn.agent import answer
from popcorn import gemini
from popcorn import llm
from popcorn import mcp_server
from popcorn import deepseek


class FakeTMDB:
    async def search_movies(self, query, year=None):
        return [{"id": 603, "title": "The Matrix", "release_date": "1999-03-31"}]

    async def movie_details(self, movie_id):
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
    assert "The Matrix (1999)" in response
    assert "https://www.themoviedb.org/person/6384" in response
    assert [event.attributes.get("tool") for event in trace.events if event.name == "mcp.tool.call"] == [
        "search_people",
        "get_person_movie_credits",
    ]
    assert any(event.attributes.get("skill") == "actor_filmography" for event in trace.events)


def test_unsupported_intent_does_not_call_mcp(monkeypatch):
    monkeypatch.setattr(gemini, "api_key", lambda: "")
    monkeypatch.setattr(deepseek, "api_key", lambda: "")
    response, trace = asyncio.run(answer("Hello there"))
    assert "Tell me about The Matrix" in response
    assert not any(event.name == "mcp.tool.call" for event in trace.events)


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
        "search_people", "get_person_movie_credits"
    ]
