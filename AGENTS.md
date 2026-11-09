# AGENTS.md — Popcorn

## 1. Purpose and project sequence

This repository can hold several hobby projects. The two related but independently designed projects currently live as siblings under `projects/`:

1. **Popcorn** — an entertainment discovery agent.
2. **Popcorn Tasting** — a reusable, framework- and language-independent continuous evaluation platform for AI agents.

The agreed development order is:

1. Build Popcorn's first functional vertical slice.
2. Build a thin, separate Popcorn Tasting runner alongside that slice so the demo measures it end to end.
3. Expand Popcorn and its evaluation cases together as providers and skills are added.
4. Generalize Popcorn Tasting only after Popcorn demonstrates the required evidence and evaluation semantics.

Do not build a general-purpose evaluation platform prematurely. A narrow runner for Popcorn's first slice is in scope. Build suitable observability into Popcorn from the beginning so execution evidence is not lost or retrofitted.

## 2. How to work

Act as a collaborative software engineer and, when asked, an architect. Be precise and critical rather than automatically agreeing with assumptions.

For each meaningful task:

1. Read the relevant project documentation and inspect the existing code before proposing changes.
2. State important assumptions and identify material risks or trade-offs.
3. Prefer the smallest coherent implementation that advances the current milestone.
4. Make changes in focused, reviewable increments.
5. Add or update tests alongside implementation.
6. Run relevant tests, linters and type checks where configured.
7. Report what changed, what was tested, the actual results, and remaining limitations.
8. Update documentation when behaviour, interfaces, setup or decisions change.

Do not claim tests passed unless they were actually run and passed. Do not silently skip failing tests.

Ask before:
- Changing an agreed architectural direction in a material way.
- Adding heavyweight infrastructure or dependencies.
- Expanding the agreed scope substantially.
- Introducing paid services, accounts, credentials or external costs.
- Performing destructive operations or changing user data.

You may recommend changing an earlier preference when evidence supports it. Explain the reason and alternatives; do not treat preferences as immutable technical requirements.

## 3. Scope discipline

- Focus on Popcorn until it reaches a useful working demonstration.
- Do not implement the future evaluation engine prematurely.
- Avoid building a comprehensive entertainment catalogue.
- Avoid scraping websites to compensate for missing API coverage unless separately approved.
- Avoid a full graph database or distributed infrastructure until demonstrated needs justify them.
- Prefer simple, replaceable components and explicit interfaces.
- Do not add features merely because a provider or framework supports them.

## 4. Popcorn product scope

Popcorn is an AI-powered entertainment discovery assistant spanning:

- Movies
- Television
- Anime and manga
- Music
- Video games

It should support both domain-specific discovery and cross-domain exploration. Representative questions include:

- Which games are based on a particular movie franchise?
- Which games feature characters originating in a particular anime?
- Which movies have soundtracks or scores associated with a named composer?
- Are there anime adaptations of a particular manga or game franchise?
- Which games are associated with Marvel characters?
- Recommend movies, anime, games or music around a shared theme.

These examples are intended to guide capability design, not to imply that every provider exposes all required relationships.

## 5. Initial data-provider choices

The current provider preferences are:

| Domain | Initial provider | Interface |
|---|---|---|
| Movies and TV | TMDB | HTTP REST API |
| Anime and manga | AniList | GraphQL API |
| Music | MusicBrainz | HTTP REST API |
| Video games | IGDB | HTTP API / query interface |

Treat these as the agreed starting shortlist, not as a guarantee of API suitability or free access for every use.

Before implementation, verify current:
- API terms, permitted use, attribution and redistribution restrictions.
- Authentication and account requirements.
- Rate limits and request policies.
- Relevant endpoints and relationship coverage.
- Availability and maintenance status of any third-party MCP server.
- Data quality and limitations.

Prefer official APIs and documented interfaces. Existing MCP servers may be reused if they are suitable, maintained enough for the demo, and have acceptable licences and behaviour. Otherwise, implement a small adapter using the official API.

Do not assume that an MCP server exists, is actively maintained, or exposes a particular tool until verified. Do not assume that a data provider has comprehensive records.

## 6. Agent and skill design

Keep the orchestration lightweight initially. Do not select a framework simply because it is popular. Compare options against actual requirements and explain the trade-offs before committing.

Candidate skill responsibilities include:

- Movie discovery
- TV discovery
- Anime and manga discovery
- Music discovery
- Game discovery
- Character exploration
- Franchise exploration
- Cross-media discovery
- Recommendations

These are candidate boundaries, not a requirement to create one module or agent per item immediately. Start with a small number of independently testable capabilities and split them when that improves cohesion, reuse or testability.

Skills should have clear input/output contracts, bounded responsibilities, useful error behaviour and tests. Keep provider-specific details behind replaceable integration interfaces.

## 7. Cross-domain entities and relationships

Cross-provider entity matching is a significant risk. Similar names do not prove that two records refer to the same entity.

For relationships and entity links:
- Preserve provider identifiers and source URLs/references where available.
- Record the provider or evidence supporting a relationship.
- Distinguish directly sourced/verified facts from inferred or unresolved links.
- Do not present an inference as a verified fact.
- Handle ambiguity and conflicting provider data explicitly.
- Avoid inventing relationships to make an answer appear complete.

A lightweight relational model or SQLite is the initial preference if persistence is needed. Do not introduce a graph database without a concrete, demonstrated requirement.

## 8. Observability from day one

Popcorn must expose structured execution information so a future independent evaluator can inspect what happened, not just the final natural-language response.

Where practical, capture:
- Request/session identifier and execution identifier.
- Start/end timestamps and duration.
- Skills selected and invoked.
- MCP server and tool names invoked.
- Tool call status, errors and retry information.
- Parent/child relationships between agent, skill and tool operations.
- Relevant structured outputs or safe references to them.
- Final response and execution status.
- Token usage and model information when available from the runtime.

Use OpenTelemetry-compatible instrumentation where proportionate, but do not make the application dependent on a particular telemetry backend.

Security and privacy:
- Do not log API keys, access tokens, passwords or other secrets.
- Redact sensitive values from tool arguments and outputs.
- Avoid storing more user data than needed.
- Make logging failures non-fatal to ordinary agent operation where possible.
- Document what is captured and where it is stored.

Do not build evaluation scoring, judge models, statistical analysis, regression gates or an evaluation dashboard inside Popcorn. Those belong to Popcorn Tasting.

The future handoff should be documented and machine-readable (initially JSON or JSONL is acceptable). Finalise its schema when implementation details are known; do not pretend an illustrative schema is already a stable contract.

## 9. Initial technology preferences

These are starting preferences subject to technical validation:

| Area | Initial preference |
|---|---|
| Language | Python |
| MCP | Official Python MCP SDK, if suitable |
| Orchestration | Lightweight/custom initially |
| Local persistence | SQLite if needed |
| Observability | OpenTelemetry-compatible |
| Tests | pytest |
| CI | GitHub Actions |
| Initial UI | Decide based on demo needs; do not assume a UI framework prematurely |

Use supported Python versions and dependency versions after checking the current environment and project requirements. Pin dependencies appropriately.

## 10. Quality and testing

- Unit-test domain logic and skill behaviour.
- Test provider adapters independently from orchestration.
- Use mocks/fakes for ordinary tests; tests must not require live API credentials.
- Keep a small set of optional live connectivity checks, clearly marked as network-dependent.
- Test missing data, ambiguous matches, provider errors, rate limits, timeouts and malformed responses.
- Test that unsupported relationships are not asserted.
- Test redaction of secrets from logs and traces.
- Make tests deterministic wherever possible.

## 11. Documentation and decisions

Keep `PROJECT_CONTEXT.md` as the record of product context and agreed decisions. Keep `ROADMAP.md` as the current plan and milestone status.

When a significant technical decision is made, record the context, alternatives, decision and consequences in a short Architecture Decision Record under `docs/decisions/`. Do not create an ADR for every minor implementation detail.

If documents conflict, identify the conflict and ask or propose a resolution rather than arbitrarily choosing one. Keep the documents aligned after approved decisions.

## 12. Definition of done

A task is not complete merely because code was written. Completion should include, as applicable:
- Implementation.
- Tests and actual test results.
- Error handling.
- Documentation/configuration updates.
- No committed secrets.
- A concise summary of limitations and follow-up work.
