# ADR 0005: Expand TMDB discovery and reference skills

## Context

Popcorn's first TMDB slice only handled movie details/cast and movie acting credits. The next useful scope is broader movie and TV discovery with localization and filter support. TMDB exposes these capabilities through its REST API; the repository's MCP server is a custom adapter, not a TMDB-provided MCP server.

## Decision

Extend the thin adapter with TV search/details, filtered movie and TV discovery, combined movie/TV person credits, and language/country/genre reference data. Add related-title recommendations, collection/franchise lookup, and country-specific watch-provider data. Add an explicit guest-rating workflow for movies, TV series, and episodes. A rating is submitted only after a direct user request, requires an unambiguous TMDB match and a valid 0.5–10 half-point score, and uses a temporary guest session created for that submission. The guest-session identifier is not sent to the model or stored.

Keep images, account data and lists, and content change tracking out of the current scope. Preserve provider IDs, attribution URLs, and structured skill/MCP trace events.

## Consequences

- Popcorn can answer TV and filtered discovery questions, look up related titles/collections and country availability, and submit a rating when directly asked.
- Localization uses TMDB's language codes; region and country filters use the corresponding TMDB/ISO codes, which can be looked up through reference data.
- Ratings are write operations against TMDB. Automated tests mock them, and the skill asks for clarification rather than rating an ambiguous title.
- Watch-provider data must be attributed to JustWatch as well as TMDB.
- This is a selected, user-facing subset of TMDB's API rather than exhaustive endpoint coverage. Reviews, artwork, account features, and change tracking remain excluded. TMDB data can be incomplete and the API has no SLA.
