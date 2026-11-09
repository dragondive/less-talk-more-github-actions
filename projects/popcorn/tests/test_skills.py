import asyncio

from popcorn.skills import actor_filmography, franchise_exploration, movie_discovery, related_titles, title_discovery, title_rating, tmdb_reference, tv_discovery, watch_availability


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


def test_tv_skill_searches_and_returns_details_with_source():
    calls = []
    async def invoke(tool, args):
        calls.append((tool, args))
        if tool == "search_tv":
            return {"results": [{"id": 4, "name": "Dark", "first_air_date": "2017-12-01"}]}
        return {"name": "Dark", "first_air_date": "2017-12-01", "genres": ["Drama"],
                "overview": "A missing child changes a town.", "cast": [{"name": "Actor"}], "source_url": "tmdb/tv/4"}
    response = asyncio.run(tv_discovery.run("Dark", invoke, "de-DE"))
    assert "Dark (2017)" in response and "tmdb/tv/4" in response
    assert calls[0][1]["language"] == "de-DE"


def test_title_discovery_passes_only_selected_filters():
    async def invoke(tool, args):
        assert tool == "discover_movies"
        assert args == {"region": "IN", "year": 2020}
        return {"results": [{"title": "Example", "release_date": "2020-01-01", "source_url": "tmdb/1"}]}
    response = asyncio.run(title_discovery.run({"media": "movie", "region": "IN", "year": 2020}, invoke))
    assert "Example (2020" in response


def test_title_discovery_resolves_country_language_and_genre_names_to_tmdb_codes():
    calls = []
    async def invoke(tool, args):
        calls.append((tool, args))
        if tool == "get_reference_data":
            return {"results": {
                "countries": [{"english_name": "India", "iso_3166_1": "IN"}],
                "languages": [{"english_name": "Hindi", "iso_639_1": "hi"}],
                "movie_genres": [{"name": "Comedy", "id": 35}],
            }[args["kind"]]}
        assert args == {"country": "IN", "original_language": "hi", "genres": "35"}
        return {"results": [{"title": "Example", "release_date": "2020-01-01", "source_url": "tmdb/1"}]}
    asyncio.run(title_discovery.run({"media": "movie", "country": "India", "original_language": "Hindi", "genres": "Comedy"}, invoke))
    assert len(calls) == 4


def test_reference_skill_formats_language_and_country_codes():
    async def invoke(tool, args):
        assert tool == "get_reference_data"
        assert args == {"kind": "languages", "query": "Hindi"}
        return {"results": [{"english_name": "Hindi", "name": "हिन्दी", "iso_639_1": "hi"}]}
    response = asyncio.run(tmdb_reference.run("languages", "Hindi", invoke))
    assert "Hindi — हिन्दी — hi" in response


def test_rating_skill_does_not_rate_ambiguous_title():
    calls = []
    async def invoke(tool, _args):
        calls.append(tool)
        return {"results": [{"id": 1, "title": "Crash", "release_date": "1996-01-01"},
                            {"id": 2, "title": "Crash", "release_date": "2004-01-01"}]}
    response = asyncio.run(title_rating.run({"media": "movie", "title": "Crash", "rating": 8}, invoke))
    assert "didn't submit a rating" in response
    assert calls == ["search_movies"]


def test_related_titles_skill_resolves_seed_then_returns_tmdb_suggestions():
    calls = []
    async def invoke(tool, args):
        calls.append((tool, args))
        if tool == "search_movies":
            return {"results": [{"id": 603, "title": "The Matrix"}]}
        return {"results": [{"title": "Example", "date": "2020-01-01", "source_url": "tmdb/1"}]}
    response = asyncio.run(related_titles.run({"media": "movie", "title": "The Matrix", "relation": "similar"}, invoke))
    assert "TMDB's related-title results" in response
    assert calls[1][1]["identity"] == 603


def test_watch_availability_attributes_justwatch():
    async def invoke(tool, args):
        if tool == "search_tv":
            return {"results": [{"id": 4, "name": "Dark"}]}
        assert args["country"] == "IN"
        return {"results": [{"provider": "Example", "availability": "flatrate"}], "tmdb_link": "tmdb/link"}
    response = asyncio.run(watch_availability.run({"media": "tv", "title": "Dark", "country": "in"}, invoke))
    assert "Availability data by JustWatch via TMDB" in response


def test_franchise_skill_lists_source_linked_movies():
    async def invoke(tool, _args):
        if tool == "search_collections":
            return {"results": [{"id": 10, "name": "Star Wars Collection"}]}
        return {"name": "Star Wars Collection", "source_url": "tmdb/c/10", "parts": [{"title": "Star Wars", "release_date": "1977-05-25"}]}
    response = asyncio.run(franchise_exploration.run("Star Wars Collection", invoke))
    assert "Star Wars (1977)" in response and "tmdb/c/10" in response
