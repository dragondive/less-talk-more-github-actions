# Handoff: Continue Popcorn with Music Discovery

**Prepared:** 2026-11-09
**Repository:** `dragondive/less-talk-more-github-actions`
**Working directory:** `/home/mayajaal/dragondive/less-talk-more-github-actions`
**Branch:** `main`

## Ready-to-paste opening prompt

> Continue Popcorn development from `docs/handoffs/music-discovery-next-chat.md`. First inspect the current branch/status and project docs. Then implement a focused, read-only MusicBrainz discovery slice that fits Popcorn's existing provider adapter → MCP tools → skills → LLM tool-selection path. Verify current MusicBrainz API behavior, terms/licensing/attribution, rate policy, and endpoints from official docs before coding. Keep the scope to useful music discovery, likely artist search/details and selected releases/recordings, with a soundtrack/work relationship workflow only if MusicBrainz documents a usable relationship for it. Add mocked adapter, MCP, skill, and agent-path tests; update the coverage map, README, PROJECT_CONTEXT, ROADMAP, and an ADR if the design warrants one. Do not implement Popcorn Tasting, music account/list mutations, bulk harvesting, or cross-provider assertions. Run the relevant tests and report whether any live API check was performed. Do not commit or push until I ask.

## Current project state

- Popcorn is the active project. Popcorn Tasting remains separate and deferred.
- Python 3.11+, lightweight custom orchestration, official MCP Python SDK, pytest, and mocked provider tests are the current approach.
- `main` has the TMDB expansion commit `d4114ea Expand TMDB-backed Popcorn discovery skills` pushed to `origin`.
- The AniList implementation (including the additional skills in this handoff's current chat) was committed and pushed as the next commit; see `git log -1` for its hash.
- At the time this handoff was drafted, the full Popcorn suite passed: **60 passed**. `git diff --check` and `python3 -m compileall -q projects/popcorn/src/popcorn` also passed.
- The AniList/MusicBrainz API paths have not been live-validated. Automated tests mock network responses.
- A pre-existing worktree deletion of root `.env.example` was not part of the AniList work and was intentionally excluded from the AniList commit. Check `git status --short` before editing; do not restore or stage it without inspecting why it was deleted.

## Architecture and implementation patterns

The request flow for model-backed requests is:

1. `popcorn.agent` provides bounded function tools to Gemini or DeepSeek.
2. The selected tool routes into one skill module under `projects/popcorn/src/popcorn/skills/`.
3. A skill calls MCP tools through the in-process official Python SDK `Client(mcp)`.
4. MCP tools call a provider adapter, returning bounded normalized JSON with provider source links.
5. `ExecutionTrace` records LLM tool selection, skill invocation, MCP tool name, provider, and outcome.

Important files:

- `projects/popcorn/src/popcorn/agent.py` — model tool schemas, dispatch, execution trace.
- `projects/popcorn/src/popcorn/mcp_server.py` — current shared MCP server `popcorn-discovery`; TMDB and AniList tools coexist here. Trace events identify the provider separately.
- `projects/popcorn/src/popcorn/anilist.py` — public read-only GraphQL adapter with injectable HTTP function, 15-second timeout, safe provider errors, GraphQL error handling, no credentials.
- `projects/popcorn/src/popcorn/tmdb.py` — existing REST adapter pattern.
- `projects/popcorn/src/popcorn/skills/` — skill implementation modules.
- `projects/popcorn/skills/*/SKILL.md` — product-facing skill contracts/instructions.
- `projects/popcorn/tests/` — deterministic tests with mocked provider responses.
- `docs/provider-coverage/anilist.md` — simple provider/API → MCP → skill inventory and example prompts. Extend this for MusicBrainz.
- `docs/decisions/0006-anilist-read-only-discovery.md` — AniList decision record.
- `PROJECT_CONTEXT.md` — product context and decisions.
- `ROADMAP.md` — milestone status.

Normal dev tests do not require external API credentials or a live network. Popcorn's in-process MCP tools are the path exercised by tests. The standalone `popcorn-mcp` stdio transport exists but has not been validated end to end with an external MCP host.

## Implemented TMDB scope

The TMDB adapter and MCP set cover selected text-based movie/TV paths: title search and details/cast, people and combined credits, filtered discovery, language/country/genre references, guest ratings (explicit user request only), related/recommended titles, collections/franchises, and watch providers with JustWatch attribution. Artwork/images and TMDB account settings/content changes remain excluded. Full endpoint inventory is in README and roadmap.

## Implemented AniList scope

AniList is accessed through its official public GraphQL endpoint. No credentials are needed for public reads. The adapter asks for `isAdult: false` on media search/discovery/details, but AniList documentation says adult filtering may not be complete. Search returns bounded pages; no bulk catalogue harvesting or account list access is implemented.

Current skills:

1. `anime_manga_discovery` — title search, disambiguation, metadata/synopsis, listed characters and related media.
2. `anilist_filtered_discovery` — genre, country, format, status, season, and year (year requires season); results are popularity/score ordered.
3. `anilist_character_exploration` — character search and AniList-listed media appearances.
4. `anilist_staff_exploration` — staff search, production credits, and voice credits.
5. `anilist_relation_exploration` — explicit AniList relation labels such as adaptation, prequel, sequel, and spin-off.

Distinct AniList MCP tools are `search_anilist_media`, `get_anilist_media_details`, `discover_anilist_media`, `search_anilist_characters`, `get_anilist_character_details`, `search_anilist_staff`, and `get_anilist_staff_details`. Relation exploration intentionally reuses media search/details, since the detail query already returns relation edges.

The 2026-11-09 documentation check found AniList docs reporting a temporarily degraded 30 requests/minute service limit (nominal documented limit 90); treat that as time-sensitive and recheck. Respect 429/403 responses and do not add uncontrolled retries. See [AniList rate limits](https://docs.anilist.co/guide/rate-limiting), [terms](https://docs.anilist.co/guide/terms-of-use), [media query guide](https://docs.anilist.co/guide/graphql/queries/media), and [authentication](https://docs.anilist.co/guide/auth/).

## MusicBrainz research to carry forward

The official documentation was checked on 2026-11-09; re-check during the next chat before implementation because provider rules and schema can change.

- Official API root: `https://musicbrainz.org/ws/2/`.
- It exposes REST-style GET lookup, search, and browse operations for artist, release group, release, recording, work, and related entities. `fmt=json` is supported.
- Search supports artist, recording, release, release-group, work, and other entity types. Search results are candidates, not proof of identity; preserve MBIDs and disambiguate before fetching details.
- Lookup by MBID supports `inc=` subqueries, including artist recordings/releases/release-groups/works and relationship includes. Linked entities are limited to 25 per lookup; browse supports paging.
- A useful bounded demo could cover artist search/details, artist release groups, recording/release lookup, and a documented composer/soundtrack relationship. Confirm exact relationship direction/include parameters before building soundtrack behavior; do not assume MusicBrainz has a direct film/anime catalogue or that similar titles prove a soundtrack link.
- Every request should include a meaningful, versioned `User-Agent` with a maintainable contact value. MusicBrainz docs state a conservative source-IP rate policy averaging at most one request per second; docs may be changed to protect the service. Space calls accordingly and handle `503 Service Unavailable` without tight retries.
- MusicBrainz API use is free for non-commercial usage according to its products page, but data licensing and attribution are separate concerns. The database data is released under CC BY-NC-SA 3.0 per MusicBrainz documentation; determine what attribution and share-alike obligations apply to displayed API-derived output. The user has said Popcorn is a non-commercial public demo. Do not conflate this demo with the later internal commercial project; do not provide legal conclusions.
- Official sources: [API overview](https://musicbrainz.org/doc/MusicBrainz_API), [rate limits](https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting), [search syntax and entity search](https://musicbrainz.org/doc/MusicBrainz_API/Search), [database licensing overview](https://musicbrainz.org/doc/About), and [products](https://musicbrainz.org/doc/Products).

## Suggested next-slice boundaries

Start with two or three user-visible music workflows, for example:

- Artist search/detail and disambiguation by artist type/area where supported.
- Artist releases/release groups with dates and source links.
- Recording or work lookup with explicit artist-credit/relationship evidence.
- Optional soundtrack/composer relationship exploration only after confirming the exact relationship types, includes, direction, and useful metadata.

Prefer a small adapter in `projects/popcorn/src/popcorn/musicbrainz.py` that follows current adapter error and test patterns. Consider a lightweight per-process throttle enforcing a gap between calls; ensure it does not delay indefinitely and is testable with an injectable clock/sleeper. Use a clear product/version/contact `User-Agent`; decide where the contact value belongs without placing secrets in traces. Avoid broad Lucene syntax supplied directly by model output; expose bounded search inputs or construct controlled query fields.

Build an explicit `music_discovery` skill or a small cohesive set, and add corresponding LLM tool schemas and dispatch. Ensure returned MBIDs and MusicBrainz source URLs survive into answers and traces. Tests should assert one skill path performs model tool selection → skill → MCP → adapter with deterministic mocks, test disambiguation, empty results, malformed JSON, timeouts, 503/rate-limit behavior, and rate spacing, and confirm no unsupported soundtrack relationship is invented.

## Product and scope constraints

- Popcorn is an entertainment discovery assistant across movies, TV, anime/manga, music, and games. Cross-domain exploration is a later differentiator.
- Preserve provider IDs, URLs, relationship types, and evidence. Distinguish sourced relationships from inference or unresolved matching.
- Keep user accounts/lists and mutations out of this discovery slice.
- Do not add Popcorn Tasting evaluator logic, scoring, coverage dashboard, or regression gates in Popcorn. This file/map are lightweight documentation inventories only.
- Do not implement game discovery or cross-provider relationship matching as part of the MusicBrainz slice.
- Update README, `PROJECT_CONTEXT.md`, `ROADMAP.md`, coverage inventory, and a concise ADR when an architectural decision warrants it.
- Do not commit/push next chat's MusicBrainz changes unless the user asks.
