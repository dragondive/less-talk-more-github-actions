---
name: movie-discovery
description: Look up movie facts and credited cast from TMDB using Popcorn MCP tools.
---

# Movie discovery

Search for a movie by title with `search_movies`, passing a TMDB language code when requested. Use the result's TMDB ID with `get_movie_details` to retrieve localized details and cast. If the search is ambiguous, show candidate titles, years, and TMDB links and ask the user to choose. Do not silently treat the first result as a confirmed match when multiple candidates exist. Attribute all sourced details to TMDB.
