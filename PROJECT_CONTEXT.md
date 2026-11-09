# PROJECT_CONTEXT.md — Popcorn and Popcorn Tasting

## 1. Origin and motivation

The project began as a way to demonstrate meaningful testing and continuous evaluation of AI agents.

The intended demonstration should make it possible to observe and assess an agent that:
- Has multiple distinct skills.
- Uses multiple MCP servers and external data providers.
- Selects tools based on user intent.
- Combines information from multiple sources.
- Performs cross-domain reasoning.
- Produces non-deterministic natural-language responses.
- Can regress when prompts, skills, tools, models or dependencies change.

A simple chatbot backed by one search endpoint would not demonstrate enough orchestration or evaluation complexity. An entertainment discovery agent provides relatable scenarios and several data domains without requiring a proprietary business dataset.

## 2. Project identities

### Popcorn — the first project

Popcorn is the entertainment discovery agent. The name was inspired partly by the expression "pass the popcorn" (watching someone else's drama or controversy unfold) and partly by the association of popcorn with watching movies and television.

Popcorn is the application being built first.

### Popcorn Tasting — the later project

Popcorn Tasting is the name selected for the evaluation project. The food-tasting/critic metaphor is a playful thematic counterpart: Popcorn is the thing being experienced, and Popcorn Tasting evaluates its performance.

Popcorn Tasting is not intended to be limited to entertainment agents. It should ultimately evaluate arbitrary AI agents.

## 3. Agreed development order

The development sequence is deliberately incremental:

1. Build a small Popcorn request-to-skill-to-MCP-tool vertical slice.
2. Build a thin Popcorn Tasting runner alongside that first slice so measurement is demonstrated end to end.
3. Expand Popcorn's provider integrations and skills, expanding evaluation cases and coverage measurements as each capability arrives.
4. Keep Popcorn Tasting separate and make its execution-evidence interface language-neutral before generalizing it to arbitrary agents.

Do not build a general-purpose evaluation platform before the agent is functional. The initial runner is limited to the Popcorn vertical slice. Popcorn must have structured observability from the beginning; the runner consumes that execution evidence and keeps evaluation logic outside the agent.

## 4. Popcorn: product scope

Popcorn helps users discover, explore, compare and connect entertainment content across five domains:

1. Movies
2. TV shows
3. Anime and manga
4. Music
5. Video games

Two broad interaction types are expected.

### Domain-specific discovery

Examples:
- Search for a movie, TV series, anime, artist, album, track or game.
- Retrieve details about a selected entity.
- Explore cast, crew, characters, creators, studios, publishers or franchises where data is available.
- Find similar or recommended content where the provider supports it.
- Compare two works or franchises using sourced attributes.

### Cross-domain discovery

This is the differentiating capability. Examples:
- Find games based on a movie franchise.
- Find games featuring characters associated with an anime.
- Find music recordings or albums associated with a movie or game.
- Find anime adaptations of manga or game franchises.
- Explore characters or franchises across different media.
- Recommend a movie, anime, game and soundtrack connected by a theme.

Cross-domain questions may require multiple skills and providers. A relationship must not be asserted merely because names are similar or because a search result mentions both entities.

## 5. Initial data-provider shortlist

The providers selected as the starting point are:

| Domain | Provider | API style | Notes to validate |
|---|---|---|---|
| Movies and TV | TMDB | REST | Registration/credential requirements, permitted use, attribution, endpoint coverage |
| Anime and manga | AniList | GraphQL | Public read access, rate limits, terms, relevant character/staff relations |
| Music | MusicBrainz | REST | User-Agent policy, request rate, entity relationships, applicable terms |
| Video games | IGDB | HTTP API/query interface | Twitch developer credentials, rate limits, terms and character/franchise coverage |

These providers were selected for breadth and the possibility of building a convincing demo. They are not guaranteed to be comprehensive or equally easy to integrate.

An earlier discussion considered existing MCP implementations for AniList, MusicBrainz and gaming, plus custom adapters for TMDB and IGDB. Repository names and maintenance claims mentioned in earlier research must be rechecked before use. Do not rely on an old repository assessment without verifying its current status, licence, supported tools, transport and dependencies.

Prefer official APIs. Reuse an MCP server when it is demonstrably suitable; otherwise build a thin MCP adapter. A custom adapter is acceptable for a demo and gives us control over tool schemas and instrumentation.

A gaming alternative, RAWG, was discussed but is not part of the initial four-provider shortlist. Reconsider it only if IGDB access or coverage proves unsuitable.

## 6. Candidate skills and responsibilities

The following capabilities were discussed:

- Movie Explorer
- TV Explorer
- Anime Explorer
- Music Explorer
- Game Explorer
- Character Explorer
- Franchise Explorer
- Cross-Media Discovery
- Recommendation Engine

These names describe candidate responsibilities, not a requirement to create nine separate agents or modules at the outset. Codex should propose cohesive boundaries and a small initial implementation.

Example orchestration:

User asks: "Find games featuring characters from Naruto."

Possible flow:
1. Identify the anime/franchise using AniList.
2. Retrieve relevant characters where available.
3. Search IGDB for games and character records.
4. Establish whether the records are actually connected.
5. Return results with source evidence and clearly state gaps.

The precise flow depends on actual API coverage. Do not assume the providers expose every relationship.

## 7. Cross-domain data and provenance

A lightweight relationship model was proposed, with SQLite as the initial storage preference if persistence is required.

Potential relationship types include:
- `GAME_BASED_ON_MOVIE`
- `CHARACTER_APPEARS_IN_GAME`
- `ANIME_ADAPTED_FROM_MANGA`
- `MOVIE_HAS_SOUNDTRACK`
- `MUSIC_COMPOSED_BY`
- `GAME_BELONGS_TO_FRANCHISE`
- `ACTOR_APPEARS_IN`

The relationship model should preserve:
- Source entity type and provider ID.
- Relationship type.
- Target entity type and provider ID.
- Evidence provider and source reference/URL.
- Verification status (for example, verified, inferred, unresolved).
- Confidence only where a defensible method exists.
- Retrieval or observation time where useful.

The exact schema remains an architectural decision. The key agreed principle is to distinguish sourced facts from inferences and not fabricate missing links. Begin with relational storage; do not introduce Neo4j or another graph database without evidence that SQLite is insufficient.

## 8. Popcorn observability requirements

Popcorn should capture structured execution traces from the beginning, including:
- Request/session and execution IDs.
- Agent start/end and duration.
- Skills invoked.
- MCP servers and tools invoked.
- Tool call arguments after secret redaction.
- Tool outcomes, errors, retries and timing.
- Parent/child span relationships.
- Final response and execution status.
- Model/token metadata where available.

OpenTelemetry-compatible tracing was preferred, but the initial design should remain lightweight and should not depend on a particular backend.

The eventual Popcorn-to-Popcorn-Tasting contract should be language-neutral, with JSON/JSONL as a likely initial interchange format. Its final fields and versioning must be designed from actual implementation needs. Keep raw secrets and unnecessary personal data out of traces.

Important distinction: instrumentation records what happened. Popcorn Tasting will later interpret those records, score outcomes, calculate coverage and detect regressions.

## 9. Popcorn Tasting: future vision

Popcorn Tasting will be developed after Popcorn is functional.

Its longer-term purpose is to evaluate arbitrary AI agents independently of their language or agent framework. Popcorn will be its first demonstration target, not a hard-coded dependency.

Capabilities discussed:
- Test-case management and versioning.
- Automated test execution.
- Repeated runs for non-deterministic behaviour.
- Pluggable evaluation metrics.
- Deterministic checks and model-based/LLM-as-a-judge evaluation.
- Statistical summaries and variability analysis.
- Task completion, correctness, relevance and completeness measures.
- Tool-selection and tool-execution assessment.
- Skill invocation coverage.
- MCP server and individual MCP tool coverage.
- Latency and token usage where available.
- Regression detection against a baseline.
- Historical comparisons.
- JSON/HTML reports and a dashboard.
- CI/CD integration.

A critical design requirement is to separate invocation coverage from successful invocation coverage. A tool may have been exercised but failed; these are different outcomes.

The evaluator should communicate with agents through a standard contract or small adapter, not depend on Popcorn's internal Python classes. Future agents could be written in Python, C++, Java or another language.

## 10. Initial technology preferences

These are preferences to validate, not final immutable decisions:

| Area | Preference |
|---|---|
| Initial agent language | Python |
| MCP integration | Python MCP SDK where suitable |
| Orchestration | Lightweight/custom initially |
| Local persistence | SQLite if needed |
| Observability | OpenTelemetry-compatible |
| Testing | pytest |
| CI/CD | GitHub Actions |
| Future dashboard | Streamlit was suggested as a simple starting point |
| Evaluation interchange | JSON/JSONL initially |

Avoid adopting LangChain, LangGraph, a graph database, a large observability stack or other heavyweight infrastructure without a specific requirement. Frameworks may be reconsidered if a comparison demonstrates clear value.

## 11. Scope exclusions for the initial Popcorn demo

The following were deliberately deferred:
- User accounts and personal watchlists.
- Streaming-platform availability.
- Spotify integration.
- Comprehensive coverage of every entertainment franchise.
- Large-scale web scraping.
- A full graph database.
- Production-grade distributed infrastructure.
- A general-purpose Popcorn Tasting evaluation platform. The initial local runner is limited to evaluating Popcorn's first demonstrator slice.

Revisit only when a concrete demo requirement justifies it.

## 12. Decisions versus open questions

### Decisions already agreed

- Build Popcorn first; Popcorn Tasting later.
- Popcorn covers movies, TV, anime/manga, music and gaming.
- Initial provider shortlist: TMDB, AniList, MusicBrainz and IGDB.
- Cross-domain discovery is a key differentiator.
- Prefer lightweight, replaceable MCP integrations.
- Preserve evidence and distinguish verified relationships from inference.
- Instrument Popcorn from day one.
- Keep the future evaluator independent of Popcorn.
- Avoid premature infrastructure and scope expansion.
- Use one repository with independently organized project directories under `projects/`; keep shared docs and automation at the repository root. This also leaves room for unrelated hobby projects.

### Open questions for architecture review

These should be resolved with evidence and trade-off analysis:
- Which agent orchestration approach, if any, is justified?
- Which MCP servers are currently maintained and suitable?
- Which provider tools/endpoints are actually needed for the first scenarios?
- What should the first end-to-end user experience/interface be?
- What is the minimum useful set of skills for the first release?
- How should the agent resolve entity identity across providers?
- How should conflicting or incomplete provider data be presented?
- What trace format and versioning strategy best supports future external evaluation?
- What local persistence is genuinely needed for the first milestone?
- What constitutes a useful and achievable first demonstration?

## 13. Working principle

The objective is a credible, working demonstration, not a comprehensive entertainment search engine or a production-scale platform. Prefer a small end-to-end capability with honest limitations over broad but unreliable functionality.

## 14. Demo evaluation goals

The public project is a non-commercial demonstration. Its main purpose is to show how an agent can be measured through skill and MCP tool usage, deterministic answer checks, and rubric-based assessment of variable natural-language responses. A commercial internal project may later use the approach in an unrelated domain; it is not a Popcorn deployment target.

The first local slice uses an official MCP SDK server with `greeting` and `movie_fit` skills. It checks exact greeting output and expected skill/tool invocations, then scores a movie-fit response with a transparent rubric. This demonstrates measurement mechanics only: it uses a deterministic router and fixture data, not a hosted LLM, live provider, or LLM-as-a-judge.
