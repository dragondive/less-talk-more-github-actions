import asyncio

from mcp import Client

from popcorn.mcp_server import mcp


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
    }
