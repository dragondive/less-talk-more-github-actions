# ADR 0007: MusicBrainz read-only artist discovery

**Status:** Accepted
**Date:** 2026-11-09

## Context

Popcorn's first useful music workflow needs a documented, attributable provider path with mocked tests. MusicBrainz exposes artist search, MBID lookup, and release-group browse endpoints. Search results can be ambiguous; API requests require a meaningful versioned User-Agent and the current source-IP policy averages one request per second. Artist lookups can include at most 25 linked entities, while browse supports paging.

MusicBrainz documents work-to-artist composer relationships, but traversing recording/work links is a separate workflow. It does not identify matching film or anime records, so similar names cannot establish a soundtrack connection.

## Decision

Use a small custom, read-only MusicBrainz REST adapter behind Popcorn's existing shared MCP server. Provide bounded artist search, artist lookup by MBID, and a bounded browse of album, EP, and single release groups. Keep ambiguity handling in a `music_discovery` skill, and retain provider IDs and source URLs. Space requests by at least one second per process, use a versioned User-Agent, and surface HTTP 503 without automatic retries. Exclude account features, bulk harvesting, and soundtrack-to-screen assertions.

## Consequences

- Normal tests remain offline and deterministic.
- One user workflow can require three sequential requests; the spacing can add about two seconds before network latency.
- The initial User-Agent links to the repository because no direct maintainer contact address has been configured.
- MusicBrainz licensing is mixed: core data is CC0; supplementary data is CC BY-NC-SA 3.0. Popcorn includes attribution links and documents that data reuse should be reviewed against MusicBrainz terms.
- Live connectivity and deployed behavior remain unverified.

## Official references checked 2026-11-09

- [API overview and lookup/browse relationship behavior](https://musicbrainz.org/doc/MusicBrainz_API)
- [Rate limiting and User-Agent requirements](https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting)
- [Search syntax and supported entities](https://musicbrainz.org/doc/MusicBrainz_API/Search)
- [Data licensing](https://musicbrainz.org/doc/About/Data_License)
- [API FAQ (non-commercial use and authentication)](https://musicbrainz.org/doc/MusicBrainz_API/FAQ)
- [Work relationships](https://musicbrainz.org/doc/Work)
