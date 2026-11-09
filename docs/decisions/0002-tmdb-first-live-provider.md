# ADR 0002: Use TMDB for Popcorn's first live provider slice

**Status:** Accepted
**Date:** 2026-11-09

## Context

Popcorn needs to become useful before work resumes on the separate evaluation project. Movie detail/cast lookup and actor filmography are concrete requests, and TMDB is the agreed initial movie/TV provider. The official API supports movie/person search, movie credits, and person movie credits. Its application API accepts an API Read Access Token as a Bearer token. The provider says the developer API is free for non-commercial purposes with attribution, does not provide an SLA, and asks clients to respect HTTP 429 responses.

## Decision

Implement a small Python TMDB v3 adapter and expose its read operations as Popcorn MCP tools. Build two focused skills: movie discovery/details/cast and actor filmography. Keep request intent routing deterministic and model-independent for this stage. Read `TMDB_ACCESS_TOKEN` from the process environment and never include it in traces or errors. Preserve TMDB IDs and source links, and ask for clarification when results are ambiguous.

## Alternatives considered

- Adopt a third-party TMDB MCP server: adds an external maintenance and license dependency; a small adapter is adequate for the first read-only workflows.
- Add an LLM provider immediately: adds an account and usage-cost choice before live provider workflows and skill boundaries are established. The user selected a provider-independent agent first.
- Implement several entertainment providers together: broadens the milestone before the first live workflow is validated.

## Consequences

- The first real-data agent capabilities require a TMDB API Read Access Token for live use; tests inject mocked HTTP responses and do not need credentials. See [TMDB application authentication](https://developer.themoviedb.org/docs/authentication-application).
- The MCP tool and provider layers remain replaceable, while the current intent router supports only a small set of explicit question forms.
- TMDB data may be incomplete; credits are reported as TMDB-listed records and include source links. See TMDB's [official API FAQ](https://developer.themoviedb.org/docs/faq) for non-commercial use and attribution terms.
- The CLI presents TMDB's required attribution notice. Any future visual UI must use an approved TMDB logo as required by TMDB.
- No model-generated prose or provider connectivity has been exercised in this change; those require a later model/provider decision and a configured local token respectively.
