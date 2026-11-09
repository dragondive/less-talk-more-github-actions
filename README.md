# Popcorn

Popcorn is an entertainment discovery agent. This first real-data slice connects movie and actor lookup skills to TMDB through Popcorn's MCP tools. Popcorn Tasting remains a separate project and is deferred while the agent is built out.

## Configure TMDB

Create a TMDB account and request API access from the account's API settings. Create a local `.env` file (ignored by Git) containing:

```bash
TMDB_ACCESS_TOKEN=your_api_read_access_token_here
```

You can also set `TMDB_ACCESS_TOKEN` in the process environment. Do not commit credentials or put them in a trace.

The API supports this token as a Bearer authorization header. See [TMDB application authentication](https://developer.themoviedb.org/docs/authentication-application).

## Run Popcorn

Requires Python 3.11 or newer.

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements-dev.txt
python3 -m popcorn "Tell me about The Matrix"
python3 -m popcorn "Who is in The Matrix?"
python3 -m popcorn "What movies has Keanu Reeves acted in?"
python3 -m popcorn --credits
python3 -m pytest projects/popcorn/tests
```

## Run the chat app

```bash
uvicorn popcorn.web:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`. The chat app calls the same deterministic Popcorn router as the CLI and exposes structured execution traces from `/api/chat`. It currently supports the movie and actor requests listed above; it does not use an LLM or retain conversation history.

Popcorn uses a small deterministic intent router at this stage. Supported requests are movie details/cast lookup and a person's movie acting credits. It searches first and shows candidate choices when a name or title is ambiguous. The agent uses the official TMDB API through a replaceable adapter exposed as MCP tools; normal tests use mocked provider responses and need no credential or network.

## Skills and MCP tools

| Skill | MCP tools | Workflow |
|---|---|---|
| Movie discovery | `search_movies`, `get_movie_details` | Search the title, resolve an unambiguous result, return details and credited cast |
| Actor filmography | `search_people`, `get_person_movie_credits` | Search a person, resolve an unambiguous result, list TMDB movie acting credits |

The standalone MCP server can be launched with `popcorn-mcp` after installation. It uses the MCP stdio transport. Popcorn's CLI currently hosts the same MCP tools in process through the official Python SDK client; stdio hosting is available for other MCP-compatible hosts but has not yet been validated end to end.

## Attribution

This product uses the TMDB API but is not endorsed or certified by TMDB. Movie and person results include TMDB source links. The CLI prints the attribution notice with `--credits`. See [TMDB's API FAQ and attribution requirements](https://developer.themoviedb.org/docs/faq).

## Deploy to Render

The repository includes a Render Blueprint at `render.yaml`. In Render, create a Blueprint from this GitHub repository and provide `TMDB_ACCESS_TOKEN` when prompted. The Blueprint creates a free Python web service and disables automatic deploys so deployment happens only after GitHub Actions passes Popcorn tests.

Copy the service's Deploy Hook URL from Render's Settings and add it to the GitHub repository as an Actions secret named `RENDER_DEPLOY_HOOK_URL`. The workflow skips deployment until this secret exists. Render's deploy hook is a secret; do not put its URL in source or chat. See [Render's deploy hook guide](https://render.com/docs/deploy-hooks).

## Repository layout

```text
projects/
  popcorn/          # agent, skills, TMDB adapter, MCP server, and tests
  popcorn_tasting/  # separate evaluation project, to be resumed later
tests/integration/  # shared repository checks
.github/            # shared repository automation
docs/               # decisions and project guidance
```

## Current limits

- The router is deterministic and pattern based; no language model is connected yet. This was deferred by choice so provider and skill contracts can be established first.
- TMDB only provides movies and people for this slice. TV, anime/manga, music, games, cross-media links, images, and recommendations are not implemented.
- Movie/person matching uses simple exact-name preference and otherwise asks the user to disambiguate. It does not infer identity from similar names.
- TMDB data can be incomplete. Actor credits are described as the credits TMDB lists, not a complete filmography.
- The API has no SLA and asks clients to respect HTTP 429 responses. The adapter applies a request timeout and reports rate limiting without retrying.
- The separate Popcorn Tasting project still targets the earlier demo agent and has not been updated for this real-data slice.
