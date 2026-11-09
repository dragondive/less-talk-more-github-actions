# Popcorn

Popcorn is an entertainment discovery agent. Its current real-data slice connects movie and TV lookup, filtered discovery, person credits, TMDB references, related titles, franchise collections, watch availability, explicit guest ratings, AniList anime/manga discovery, and read-only MusicBrainz artist/release discovery through Popcorn's MCP tools. Popcorn Tasting remains separate and deferred while the agent is built out.

## Configure TMDB

Create a TMDB account and request API access from the account's API settings. To use model-backed routing, create a Gemini API key (or use the retained DeepSeek option). Create a local `.env` file (ignored by Git) containing:

```bash
TMDB_ACCESS_TOKEN=your_api_read_access_token_here
LASTFM_API_KEY=your_lastfm_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
LLM_PROVIDER=gemini
# Optional: retain/use DeepSeek by setting LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

You can also set these values in the process environment. Set `LLM_PROVIDER` to `gemini` or `deepseek` to select explicitly. If it is omitted, Popcorn uses Gemini when `GEMINI_API_KEY` is configured, then DeepSeek when `DEEPSEEK_API_KEY` is configured; without either key it uses the deterministic router. Do not commit credentials or put them in a trace.

Create a Gemini key in [Google AI Studio](https://aistudio.google.com/apikey) and keep it server-side as `GEMINI_API_KEY`.

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

Open `http://127.0.0.1:8000`. The configured Gemini or DeepSeek model selects among Popcorn skills, which invoke Popcorn's TMDB, AniList, MusicBrainz, or Last.fm MCP tools. Without a model key, the CLI and chat app retain the small deterministic router. The chat app exposes structured execution traces from `/api/chat` and does not retain conversation history. When enabled, the user's message is sent to the selected model provider.

Try prompts such as “Recommend popular adventure anime from Japan,” “Which anime feature Spike Spiegel?”, “Which anime did Yoko Kanno work on?”, “What has Yoko Kanno released?”, “Recommend artists like Portishead,” or “Recommend tracks like Believe by Cher.” Last.fm seed-based recommendations require `LASTFM_API_KEY`; they are based on Last.fm listening data and link to Last.fm. MusicBrainz discovery returns artist candidates, selected artist details, and up to ten album, EP, or single release groups; ambiguous matches are surfaced for clarification. Popcorn does not assert soundtrack connections to movies or anime.

Without an LLM key, the deterministic router supports movie details/cast lookup and a person's movie/TV acting credits. Model-backed requests also support TV details, filtered discovery, and reference-code lookup. Searches show candidate choices when a title or person is ambiguous. Normal tests use mocked provider responses and need no credential or network.

## Skills and MCP tools

| Skill | MCP tools | Workflow |
|---|---|---|
| Movie discovery | `search_movies`, `get_movie_details` | Search the title, resolve an unambiguous result, return details and credited cast |
| TV discovery | `search_tv`, `get_tv_details` | Search a series, resolve an unambiguous result, return details and cast |
| Filtered title discovery | `discover_movies`, `discover_tv`, `get_reference_data` | Filter by genre, year, country/region, and language |
| Person credits | `search_people`, `get_person_movie_credits`, `get_person_combined_credits` | Search a person and list TMDB movie and TV acting credits |
| TMDB reference data | `get_reference_data` | Look up language, country, and movie/TV genre codes |
| Related titles | `get_related_titles` | Retrieve TMDB recommendations or similar titles for a movie/TV seed |
| Franchise exploration | `search_collections`, `get_collection_details` | Find a TMDB collection and list its constituent movies |
| Watch availability | `get_watch_providers` | Find streaming/rental/purchase availability by country; attribute JustWatch via TMDB |
| Guest ratings | `search_movies`, `search_tv`, `rate_movie`, `rate_tv`, `rate_tv_episode` | Submit ratings only on explicit request, after an unambiguous title match |
| Anime and manga title discovery | `search_anilist_media`, `get_anilist_media_details` | Search AniList, resolve ambiguity, return synopsis, metadata, characters and related media |
| Filtered anime/manga discovery | `discover_anilist_media` | Discover by genre, country, format, status, season and year |
| Character exploration | `search_anilist_characters`, `get_anilist_character_details` | Search a character and list the media appearances AniList associates with them |
| Staff exploration | `search_anilist_staff`, `get_anilist_staff_details` | Search creators/voice actors and list production roles and voice credits |
| Anime/manga relations | `search_anilist_media`, `get_anilist_media_details` | Show AniList relation edges such as adaptations, prequels, sequels and spin-offs |
| Music artist discovery | `search_musicbrainz_artists`, `get_musicbrainz_artist` | Disambiguate artist candidates and return identity, area, aliases, and source links |
| Music releases | `get_musicbrainz_artist_release_groups` | List up to ten album, EP, and single release groups with dates and source links |
| Music recommendations | `get_lastfm_recommendations` | Recommend similar artists from an artist seed, or similar tracks from an artist and track seed |

The standalone MCP server can be launched with `popcorn-mcp` after installation. It uses the MCP stdio transport. Popcorn's CLI currently hosts the same discovery tools in process through the official Python SDK client; stdio hosting is available for other MCP-compatible hosts but has not yet been validated end to end. AniList public reads require no credential.

The AniList tool-to-skill inventory and demo prompts are in [the AniList coverage map](docs/provider-coverage/anilist.md); MusicBrainz scope and limitations are in [the MusicBrainz coverage map](docs/provider-coverage/musicbrainz.md).

MusicBrainz requires a descriptive versioned User-Agent and currently documents an average source-IP limit of one request per second; Popcorn spaces calls accordingly and does not automatically retry HTTP 503. MusicBrainz data has mixed licensing: core data is CC0 and supplementary data is CC BY-NC-SA 3.0, with attribution required for the latter. This demo links every returned entity to MusicBrainz. Review the [MusicBrainz data licensing terms](https://musicbrainz.org/doc/About/Data_License) before broader reuse. Last.fm recommendations require an API key, an identifiable User-Agent, restrained request volume, and Last.fm attribution with links; they do not provide playback. Last.fm's terms also require a “powered by AudioScrobbler” button and written approval before public access to pages using its API, so do not enable the integration on a publicly hosted demo before arranging these with Last.fm. See [Last.fm API terms](https://www.last.fm/api/tos).

## Attribution

This product uses the TMDB API but is not endorsed or certified by TMDB. Movie and person results include TMDB source links. The CLI prints the attribution notice with `--credits`. See [TMDB's API FAQ and attribution requirements](https://developer.themoviedb.org/docs/faq). MusicBrainz-derived artist and release-group results link to their MusicBrainz records; consult MusicBrainz's mixed [data licensing terms](https://musicbrainz.org/doc/About/Data_License) before reuse.

## Deploy to Render

The repository includes a Render Blueprint at `render.yaml`. In Render, create a Blueprint from this GitHub repository and provide `TMDB_ACCESS_TOKEN` and `GEMINI_API_KEY` when prompted. The Blueprint selects Gemini with `LLM_PROVIDER=gemini`; add `DEEPSEEK_API_KEY` too if you want to keep it configured as an alternate, then set `LLM_PROVIDER=deepseek` to use it. For an existing service, add or update these values in its Environment settings and redeploy. The Blueprint creates a free Python web service and disables automatic deploys so deployment happens only after GitHub Actions passes Popcorn tests.

Copy the service's Deploy Hook URL from Render's Settings and add it to the GitHub repository as an Actions secret named `RENDER_DEPLOY_HOOK_URL`. The workflow skips deployment until this secret exists. Render's deploy hook is a secret; do not put its URL in source or chat. See [Render's deploy hook guide](https://render.com/docs/deploy-hooks).

## Repository layout

```text
projects/
  popcorn/          # agent, skills, provider adapters, MCP tools, and tests
  popcorn_tasting/  # separate evaluation project, to be resumed later
tests/integration/  # shared repository checks
.github/            # shared repository automation
docs/               # decisions and project guidance
```

## Current limits

- Gemini or DeepSeek is selected through `LLM_PROVIDER`; without an explicit choice, a configured Gemini key takes precedence over a DeepSeek key. The deterministic router remains as a fallback when neither key is configured. Conversation history is not retained, so each turn is independent.
- User questions are sent to the selected model when enabled. The app does not persist chat history.
- TMDB-backed movie/TV workflows, read-only AniList anime/manga skills, focused MusicBrainz artist/release discovery, and Last.fm seed-based music recommendations are implemented; games, cross-domain links, and images are not. AniList, MusicBrainz, and Last.fm live connectivity have not yet been validated. AniList's adult-content filter may not exclude every mature entry.
- TMDB guest ratings are write operations. Popcorn only submits one when the user explicitly asks, and it creates a temporary guest session for that submission.
- Movie/person matching uses simple exact-name preference and otherwise asks the user to disambiguate. It does not infer identity from similar names.
- TMDB data can be incomplete. Actor credits are described as the credits TMDB lists, not a complete filmography.
- The API has no SLA and asks clients to respect HTTP 429 responses. The adapter applies a request timeout and reports rate limiting without retrying.
- The separate Popcorn Tasting project still targets the earlier demo agent and has not been updated for this real-data slice.
