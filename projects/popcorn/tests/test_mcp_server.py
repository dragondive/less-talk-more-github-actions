import asyncio
import pytest

from mcp import Client

from popcorn.mcp_server import mcp
from popcorn import mcp_server
from mcp.server.mcpserver.exceptions import ToolError


def test_mcp_server_exposes_tmdb_discovery_tools():
    async def list_tools():
        async with Client(mcp) as client:
            result = await client.list_tools()
            return {tool.name for tool in result.tools}

    assert asyncio.run(list_tools()) == {
        "search_movies",
        "get_movie_details",
        "search_people",
        "get_person_movie_credits",
        "search_tv",
        "get_tv_details",
        "discover_movies",
        "discover_tv",
        "get_person_combined_credits",
        "get_reference_data",
        "rate_movie",
        "rate_tv",
        "rate_tv_episode",
        "get_related_titles",
        "get_watch_providers",
        "search_collections",
        "get_collection_details",
        "search_anilist_media",
        "get_anilist_media_details",
        "discover_anilist_media",
        "search_anilist_characters",
        "get_anilist_character_details",
        "search_anilist_staff",
        "get_anilist_staff_details",
        "search_musicbrainz_artists",
        "get_musicbrainz_artist",
        "get_musicbrainz_artist_release_groups",
        "get_lastfm_recommendations",
    }


def test_rating_tool_requires_explicit_user_request():
    with pytest.raises(ToolError, match="explicit request"):
        asyncio.run(mcp_server.rate_movie(movie_id=603, rating=8, user_requested=False))


def test_rating_tool_rejects_invalid_rating_before_network_call():
    with pytest.raises(ToolError, match="half-point increments"):
        asyncio.run(mcp_server.rate_movie(movie_id=603, rating=8.2, user_requested=True))
