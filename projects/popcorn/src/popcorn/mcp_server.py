"""Local MCP tools for the first Popcorn vertical slice."""

from mcp.server import MCPServer

mcp = MCPServer("popcorn-demo")


@mcp.tool()
async def say_hello(name: str) -> str:
    """Return a friendly Popcorn greeting."""
    clean_name = name.strip() or "movie fan"
    return f"Hello, {clean_name}! Welcome to Popcorn."


@mcp.tool()
async def get_movie_profile(title: str) -> dict[str, str]:
    """Return a small fixed demo profile for evaluating movie-fit responses."""
    normalized = title.strip().casefold()
    if normalized == "the matrix":
        return {
            "title": "The Matrix",
            "genres": "action, science fiction",
            "tone": "fast-paced, dark, and philosophical",
            "source": "Popcorn demo fixture",
        }
    return {
        "title": title.strip() or "Unknown title",
        "genres": "unknown",
        "tone": "unknown",
        "source": "Popcorn demo fixture",
    }
