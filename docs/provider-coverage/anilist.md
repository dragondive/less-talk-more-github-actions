# AniList API, MCP, and skill coverage

This is an implementation inventory for the Popcorn demo, not a claim that the complete AniList API is covered. Tests use mocked provider responses; live API behavior is still unverified.

| AniList capability / GraphQL fields | Popcorn MCP tools | Popcorn skill | Demo prompt |
|---|---|---|---|
| `Page.media` search; `Media` metadata, synopsis, relations, characters | `search_anilist_media`, `get_anilist_media_details` | `anime_manga_discovery` | “Tell me about Cowboy Bebop anime.” |
| `Page.media` filters: `genre`, `countryOfOrigin`, `format`, `status`, `season`, `seasonYear` | `discover_anilist_media` | `anilist_filtered_discovery` | “Recommend popular adventure anime from Japan.” |
| `Page.characters`; `Character.media` | `search_anilist_characters`, `get_anilist_character_details` | `anilist_character_exploration` | “Which anime feature Spike Spiegel?” |
| `Page.staff`; `Staff.staffMedia`, `Staff.characterMedia` | `search_anilist_staff`, `get_anilist_staff_details` | `anilist_staff_exploration` | “What anime credits does Yoko Kanno have?” |
| `Media.relations.edges.relationType` | Reuses `search_anilist_media`, `get_anilist_media_details` | `anilist_relation_exploration` | “What is related to Cowboy Bebop?” |

## Coverage boundaries

- Search/discovery returns a bounded first page; the skills do not crawl the catalogue.
- Filter discovery supports one genre plus optional country, format, status, season, and year. AniList requires season when filtering by year.
- Character and staff matches are disambiguated before details are requested. Returned appearances and credits are the records AniList exposes and may be incomplete.
- Relation exploration preserves AniList's relation labels. A relation is evidence from AniList, not a cross-provider identity match.
- All implemented operations are read-only and request `isAdult: false` for media queries. AniList documents that adult filtering may not be complete.
- User lists, account data, mutations, reviews, social features, and airing schedules are not included.
- The provider adapter handles AniList errors, rate limits, malformed responses, and timeouts. Current service availability and live response shape still need a separate optional connectivity check.
