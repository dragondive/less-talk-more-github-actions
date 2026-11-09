import asyncio

from popcorn.agent import answer
from popcorn import mcp_server


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
    response, trace = asyncio.run(answer("What movies has Keanu Reeves acted in?"))
    assert "The Matrix (1999)" in response
    assert "https://www.themoviedb.org/person/6384" in response
    assert [event.attributes.get("tool") for event in trace.events if event.name == "mcp.tool.call"] == [
        "search_people",
        "get_person_movie_credits",
    ]
    assert any(event.attributes.get("skill") == "actor_filmography" for event in trace.events)


def test_unsupported_intent_does_not_call_mcp():
    response, trace = asyncio.run(answer("Hello there"))
    assert "Tell me about The Matrix" in response
    assert not any(event.name == "mcp.tool.call" for event in trace.events)
