# Popcorn and Popcorn Tasting

Popcorn is an entertainment discovery agent. Popcorn Tasting is its separate evaluation and measurement harness. The first vertical slice demonstrates an MCP server, two skills, structured execution events, deterministic checks, rubric scoring, and a GitHub Actions workflow.

## Run the first slice

Requires Python 3.11 or newer.

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements-dev.txt
python3 -m popcorn "Hello Maya" --trace artifacts/hello-trace.json
python3 -m popcorn "Movie fit: The Matrix"
python3 -m pytest
python3 -m popcorn_tasting
```

The golden evaluation report is written to `artifacts/evaluation.json`; a compact skill and MCP tool coverage summary is written to `artifacts/coverage.txt`. The first slice uses a local MCP server and fixed demo data; it needs no provider credentials or model API key.

## Repository layout

```text
projects/
  popcorn/          # agent, MCP server, and agent-specific tests
  popcorn_tasting/  # evaluator, golden data, and evaluation-specific tests
tests/integration/  # checks that span both projects
.github/            # shared repository automation
docs/               # shared decisions and project guidance
requirements-dev.txt # install both local projects for development
```

Popcorn and Popcorn Tasting are sibling projects. This keeps the evaluator separate from the agent and leaves `projects/` available for other hobby projects.

## Project documents

- `AGENTS.md`: persistent project guidance.
- `PROJECT_CONTEXT.md`: product requirements and agreed decisions.
- `ROADMAP.md`: current milestones and acceptance criteria.
- `CODEX_START_PROMPT.md`: original architecture-review prompt.

## Current limits

- The movie profile is a fixed fixture, not TMDB or another live provider.
- The movie-fit rubric is a small, inspectable keyword rubric. It scores the agent response and two varied sample responses; it is not an LLM judge or a live model evaluation.
- The CLI uses a simple request router. There is no hosted model or public web service yet.
- The GitHub Actions workflow is configured but has not yet run on GitHub.
- The MCP client connects to the in-process SDK server. Stdio and Streamable HTTP hosting have not been exercised.
