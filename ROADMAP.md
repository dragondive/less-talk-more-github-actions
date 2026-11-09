# ROADMAP.md — Popcorn

## Status conventions

Use these statuses consistently:

- `NOT STARTED`
- `IN PROGRESS`
- `COMPLETED`
- `BLOCKED`

Do not mark a milestone complete until its acceptance criteria have been checked and the results documented.

## Overall sequence

**Build Popcorn first.** Add real providers, skills, and useful user workflows. Resume Popcorn Tasting after Popcorn reaches a functional demonstration.

Structured observability is included in Popcorn from the start so the separate runner can inspect execution evidence.

---

## Phase 0 — Repository and architecture

**Status:** COMPLETED

### Objectives
- Establish the repository and project guidance.
- Review the current requirements and assumptions.
- Agree a practical Popcorn architecture before coding.

### Tasks
- [x] Create the Git repository.
- [x] Add `AGENTS.md`, `PROJECT_CONTEXT.md` and `ROADMAP.md`.
- [x] Open the repository in VS Code and Codex.
- [x] Ask Codex to inspect the documents and propose Popcorn architecture only.
- [x] Review the architecture critically before implementation.
- [x] Verify current API terms, authentication, limits and relevant endpoints for the four providers; validate endpoint-specific needs during provider implementation.
- [x] Decide not to depend on third-party provider MCP servers for the first slice; recheck individual candidates only if one is proposed.
- [x] Record significant approved decisions as ADRs.

### Acceptance criteria
- [x] Architecture proposal reviewed and approved.
- [x] Initial implementation scope is small and explicit.
- [x] Provider and MCP assumptions are validated or clearly marked unresolved.
- [x] No application code was written before architecture approval.

---

## Phase 1 — Popcorn foundation

**Status:** IN PROGRESS — real TMDB-backed slice

### Objectives
Create the smallest runnable agent foundation.

### Candidate tasks
- [x] Set up Python project metadata and supported Python version.
- [x] Establish environment-based configuration and secrets handling.
- [ ] Define domain models and provider integration interfaces.
- [x] Define bounded skill modules and a lightweight intent router.
- [x] Implement movie and actor workflows through TMDB-backed MCP tools.
- [x] Add structured execution identifiers and events.
- [x] Add initial unit tests and developer setup instructions.
- [x] Organize Popcorn and Popcorn Tasting as independent sibling projects under `projects/`.

### Acceptance criteria
- [x] A developer can install and run the application using documented steps.
- [x] A basic request completes through the agent's execution path.
- [x] Core logic can be tested without live provider credentials.
- [x] Provider credentials are read from the environment and omitted from traces/errors.
- [x] The Popcorn agent does not depend on Popcorn Tasting.

### Remaining work
- [ ] Validate the TMDB integration with a user-provided token.
- [ ] Improve trace timing, error metadata, and redaction checks.
- [x] Add an optional LLM provider for natural-language skill selection and response phrasing.
- [x] Add Gemini as a selectable LLM provider while retaining DeepSeek.
- [ ] Configure a Gemini API key on Render and validate live model-to-skill-to-MCP flow.

---

## Phase 2 — Provider integrations

**Status:** IN PROGRESS — TMDB

### Objectives
Connect the initial entertainment data sources behind replaceable adapters.

### Providers
- [ ] TMDB — movies and TV.
- [ ] AniList — anime and manga.
- [ ] MusicBrainz — music.
- [ ] IGDB — video games.

### Tasks
- [x] Validate current TMDB authentication, attribution, endpoint coverage, and rate-limit guidance.
- [x] Select suitable existing MCP servers or implement thin custom adapters.
- [x] Document each MCP server's tools and schemas.
- [x] Implement environment-based TMDB credential handling.
- [x] Add timeouts, error handling and rate-limit messaging.
- [x] Add mocked tests for success, malformed responses, and authentication failures.
- [ ] Add additional mocked cases for empty search results and transient provider failures.
- [ ] Run an optional live connectivity check when TMDB access is configured.

### Acceptance criteria
- [ ] The first provider can be queried live through documented MCP tools.
- [ ] Normal automated tests do not require live credentials.
- [ ] Provider limitations are documented.
- [ ] Tool invocations are observable.

---

## Phase 3 — Initial skills and orchestration

**Status:** IN PROGRESS — TMDB movie and TV capabilities

### Objectives
Deliver useful domain-specific discovery with a small, testable skill set.

### Candidate capabilities
- [x] Movie discovery, details, and credited cast.
- [x] Person movie and TV acting-credit lookup.
- [x] TV discovery and series details/cast.
- [x] Movie and TV discovery with language, country, genre, and year filters.
- [x] TMDB language, country, and genre reference lookup.
- [x] Explicit guest ratings for movies, TV series, and episodes.
- [x] TMDB similar/recommended titles and collection/franchise lookup.
- [x] Country-specific movie/TV watch-provider lookup with JustWatch attribution.
- [ ] Anime and manga discovery.
- [ ] Music discovery.
- [ ] Game discovery.
- [x] TMDB movie collection/franchise exploration (cross-domain franchise links remain future work).
- [x] TMDB similar/recommended movie and TV title lookup.

### Acceptance criteria
- [x] Each current skill has a clear contract and focused tests.
- [x] The agent exposes bounded model tools for the current TMDB skills.
- [x] Tool failures, missing credentials, and ambiguous results are handled honestly.
- [x] Results retain TMDB source references.

Do not create a large number of nominal skills before their boundaries are justified.

TMDB remains a domain API behind Popcorn's own MCP adapter; TMDB does not provide an official MCP server. This phase covers selected text-based discovery/reference workflows and explicit rating actions, not the full TMDB REST surface. Artwork, reviews, account settings/lists, and content change tracking remain out of scope.

---

## Phase 4 — Cross-domain discovery

**Status:** NOT STARTED

### Objectives
Demonstrate multi-skill, multi-provider questions.

### Candidate scenarios
- [ ] Find games related to a named movie franchise.
- [ ] Find games featuring characters associated with a named anime.
- [ ] Find music associated with a movie or game.
- [ ] Explore adaptations across media.
- [ ] Compare two franchises across available domains.

### Tasks
- [ ] Define entity identity and matching strategy.
- [ ] Define relationship representation and provenance.
- [ ] Distinguish verified, inferred and unresolved links.
- [ ] Add a lightweight persistence layer only if required.
- [ ] Test ambiguous matches, conflicting data and absent relationships.

### Acceptance criteria
- [ ] At least two cross-domain scenarios work end to end.
- [ ] Results include evidence or explain the source limitation.
- [ ] The agent does not assert unsupported relationships.
- [ ] Uncertainty and missing provider coverage are communicated clearly.

---

## Phase 5 — Popcorn observability and demo readiness

**Status:** NOT STARTED

Observability should be implemented incrementally in earlier phases; this phase consolidates and validates it.

### Tasks
- [ ] Capture request and execution identifiers.
- [ ] Capture skill invocation events.
- [ ] Capture MCP server/tool invocation events and outcomes.
- [ ] Capture timing, errors and parent-child relationships.
- [ ] Redact credentials and sensitive values.
- [ ] Define and document a versioned JSON/JSONL export or retrieval contract.
- [ ] Add tests for trace completeness and redaction.
- [ ] Prepare a small set of repeatable demonstration scenarios.

### Acceptance criteria
- [ ] Popcorn completes the agreed demo scenarios.
- [ ] Execution traces expose the relevant skill and MCP tool activity.
- [ ] Trace capture does not expose secrets.
- [ ] Trace data can be consumed without importing Popcorn's internal Python implementation.
- [ ] Setup and demo instructions are documented.

**Gate:** Keep Popcorn Tasting separate from the agent. Generalize its runner only after the Popcorn demo proves the required execution-evidence contract and evaluation semantics.

---

## Phase 6 — Popcorn Tasting: evaluation foundation

**Status:** NOT STARTED — FUTURE

### Objectives
Create an independent evaluation platform, using Popcorn as its first target.

### Candidate tasks
- [ ] Define language-neutral agent execution contract.
- [ ] Define test-case format and versioning.
- [ ] Implement evaluation runner.
- [ ] Implement agent adapters, beginning with Popcorn.
- [ ] Store runs and results.
- [ ] Implement deterministic assertions and basic metrics.
- [ ] Produce JSON and HTML reports.

### Acceptance criteria
- [ ] Popcorn can be evaluated through the external contract/adapter.
- [ ] Evaluator code does not depend on Popcorn's internal modules.
- [ ] A second mock agent can be evaluated through the same interface.
- [ ] Results are reproducible enough to compare and inspect.

---

## Phase 7 — Popcorn Tasting: advanced evaluation

**Status:** NOT STARTED — FUTURE

### Candidate capabilities
- [ ] Repeated executions.
- [ ] Variability and consistency analysis.
- [ ] Pluggable evaluation metrics.
- [ ] Optional LLM-as-a-judge evaluation.
- [ ] Task completion, correctness, relevance and completeness metrics.
- [ ] Tool selection and tool execution assessment.
- [ ] Skill invocation coverage.
- [ ] MCP server and tool coverage.
- [ ] Latency and token usage where available.
- [ ] Regression comparison against a baseline.

### Important measurement distinction
Track at least:
- Invocation attempted.
- Invocation completed successfully.
- Invocation failed.
- Expected invocation omitted.
- Unexpected invocation made.

Do not equate tool coverage with successful tool execution.

### Acceptance criteria
- [ ] Repeated runs produce interpretable distributions and summaries.
- [ ] Metrics document their limitations and scoring semantics.
- [ ] Regression thresholds are configurable and supported by evidence.
- [ ] Failed tool calls are not counted as successful coverage.

---

## Phase 8 — Dashboard and CI/CD

**Status:** NOT STARTED — FUTURE

### Candidate tasks
- [ ] Historical run comparison.
- [ ] Quality and consistency views.
- [ ] Skill and MCP tool coverage views.
- [ ] Latency and failure analysis.
- [ ] Baseline and regression visualisation.
- [ ] GitHub Actions integration.
- [ ] Configurable CI quality gates.
- [ ] Publish evaluation reports as build artifacts.

### Acceptance criteria
- [ ] A code change can trigger an evaluation run.
- [ ] Results can be compared against a selected baseline.
- [ ] CI reports meaningful regressions without treating normal response variation as a deterministic failure.
- [ ] Reports retain enough metadata to explain what was evaluated.

---

## Deferred scope

Do not add these to the initial Popcorn milestone without an explicit decision:
- User accounts and personal watchlists.
- Streaming availability.
- Spotify integration.
- Comprehensive entertainment catalogue coverage.
- Large-scale scraping.
- Full graph database infrastructure.
- Production distributed deployment.
- Popcorn Tasting scoring and dashboard features inside Popcorn.

## Current next action

Add `GEMINI_API_KEY` to the Render service environment, set `LLM_PROVIDER=gemini`, and redeploy. Verify the live Gemini tool-calling flow, then expand provider/skill coverage based on the result. DeepSeek remains selectable with `LLM_PROVIDER=deepseek`. Popcorn Tasting remains deferred.
