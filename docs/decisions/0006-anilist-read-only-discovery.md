# ADR 0006: Add a read-only AniList discovery slice

**Status:** Accepted

## Context

Popcorn's product scope includes anime and manga, and AniList is the agreed initial provider. Its official API is GraphQL; public media reads do not require OAuth. AniList titles are not unique, so the workflow must preserve candidate disambiguation. Its documented current service state is degraded to 30 requests per minute, so this integration should make few calls and surface rate-limit/service failures.

## Decision

Use the official AniList GraphQL endpoint behind a small custom adapter and Popcorn MCP tools. Implement bounded title search/details, filtered catalog discovery, character appearances, staff production and voice credits, and explicit media relation exploration. Request adult filtering and retain source links. Do not add user authentication, list mutations, bulk harvesting, or an external AniList MCP dependency.

## Consequences

- Anime and manga discovery is available through one independently testable skill.
- Titles remain ambiguous until the skill selects a unique exact match or the user chooses from candidates.
- The provider's public API can change availability or rate limits; these remain operational limitations.
- AniList documents restrictions on hoarding/mass collection and on competing anime/manga list or tracker services. Popcorn remains a discovery assistant and must not turn this adapter into a catalogue mirror or tracker.
- Adult filtering is requested, but AniList documents that filtering may not be complete.

## Sources

- [AniList Terms of Use](https://docs.anilist.co/guide/terms-of-use)
- [AniList Rate Limiting](https://docs.anilist.co/guide/rate-limiting)
- [AniList Authentication](https://docs.anilist.co/guide/auth/)
- [AniList Media Queries](https://docs.anilist.co/guide/graphql/queries/media)
