import asyncio

from popcorn.skills import actor_filmography, movie_discovery


def test_movie_skill_asks_for_clarification_when_search_is_ambiguous():
    calls = []

    async def invoke(tool, arguments):
        calls.append(tool)
        return {
            "results": [
                {"id": 1, "title": "Crash", "release_date": "1996-05-17", "source_url": "tmdb/1"},
                {"id": 2, "title": "Crash", "release_date": "2004-05-06", "source_url": "tmdb/2"},
            ]
        }

    response = asyncio.run(movie_discovery.run("Crash", invoke))
    assert "Which one did you mean?" in response
    assert "1996" in response and "2004" in response
    assert calls == ["search_movies"]


def test_actor_skill_limits_results_to_acting_matches_and_does_not_guess():
    calls = []

    async def invoke(tool, arguments):
        calls.append(tool)
        return {
            "results": [
                {"id": 1, "name": "Jordan Smith", "known_for_department": "Directing", "source_url": "tmdb/1"},
                {"id": 2, "name": "Jordan Smith", "known_for_department": "Acting", "source_url": "tmdb/2"},
                {"id": 3, "name": "Jordan Smith", "known_for_department": "Acting", "source_url": "tmdb/3"},
            ]
        }

    response = asyncio.run(actor_filmography.run("Jordan Smith", invoke))
    assert "Which one did you mean?" in response
    assert "tmdb/1" not in response
    assert calls == ["search_people"]


def test_movie_skill_reports_empty_provider_search_without_inventing_a_match():
    async def invoke(_tool, _arguments):
        return {"results": []}

    response = asyncio.run(movie_discovery.run("Unknown Movie", invoke))
    assert "couldn't find" in response
