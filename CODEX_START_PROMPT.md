Read `AGENTS.md`, `PROJECT_CONTEXT.md` and `ROADMAP.md` completely.

We are continuing an architectural discussion that began in ChatGPT. Treat these files as the current project context. Do not restart the project from scratch or silently discard agreed decisions.

The two project names and sequence are:
- Popcorn: Entertainment Discovery Agent — build this first.
- Popcorn Tasting: independent continuous evaluation platform — build this later, after Popcorn is functional.

For now, focus exclusively on Popcorn. Observability and structured execution tracing must be considered from the beginning, but do not implement evaluation scoring or the Popcorn Tasting platform.

First inspect the repository and identify:
1. Missing, ambiguous or contradictory requirements.
2. Technical assumptions that need current verification.
3. Risks in the proposed provider/MCP choices.
4. The smallest useful first end-to-end demonstration.
5. Architectural choices that genuinely need to be made now versus deferred choices.

Then propose:
- High-level architecture and component boundaries.
- A practical repository structure.
- Agent orchestration and skill interfaces.
- Provider/MCP integration strategy for TMDB, AniList, MusicBrainz and IGDB.
- Cross-domain entity and relationship handling, including provenance.
- Observability and a future language-neutral JSON/JSONL handoff.
- Configuration, secrets management and testing strategy.
- Incremental milestones with acceptance criteria.

Be critical: validate assumptions, explain trade-offs and identify over-engineering. Do not claim that an API, MCP server, licence, endpoint or rate limit has been verified unless you actually verify it.

Do not write application code, create implementation scaffolding or install dependencies yet. Present the architecture proposal and wait for explicit approval.
