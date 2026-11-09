# ADR 0008: Last.fm for seed-based music recommendations

**Status:** Accepted
**Date:** 2026-11-09

## Context

MusicBrainz supplies useful artist and release metadata but is not a recommendation engine. Popcorn needs a focused music recommendation workflow for a personal hobby demo. Last.fm documents similar artist and similar track methods based on listening data. Both require an API key, but these read methods do not require user authentication. Last.fm requires an identifiable User-Agent, reasonable usage, attribution and links; its standard API/data terms are non-commercial and do not grant streaming rights. Its terms also specify a “powered by AudioScrobbler” button and prior written approval before public access to pages using Last.fm services.

Other candidates have trade-offs: Spotify removed recommendations and related artists for new API use cases; ListenBrainz recommendations use a user's listening history and its recommendation endpoint is experimental; Apple Music recommendations are personalized and require user authorization/subscription. YouTube's official Data API searches videos, not a dedicated music recommendation catalog.

## Decision

Use Last.fm's `artist.getSimilar` and `track.getSimilar` for one bounded, read-only seed workflow. Artist-only seeds return similar artists; artist plus track seeds return similar tracks. Require `LASTFM_API_KEY`, make one request per user recommendation action, cap output at eight, retain Last.fm result links and provider scores, and identify results as Last.fm recommendations. Keep MusicBrainz for independent artist/release metadata; do not automatically assert that Last.fm MBIDs match MusicBrainz entities.

## Consequences

- The hobby demo gains recommendation behavior without user accounts or music playback.
- Recommendations reflect Last.fm listening data and may be incomplete or skewed; provider match scores are not objective measures.
- The API key is a local/server-side configuration value and must never appear in traces or user output.
- Non-commercial API terms fit the stated hobby use, but a publicly accessible demo needs Last.fm's written approval and approved button/link placement before enabling the integration. Any future commercial use needs separate review and Last.fm contact.
- No live Last.fm connectivity has been tested.

## Official references checked 2026-11-09

- [Last.fm artist.getSimilar](https://www.last.fm/api/show/artist.getSimilar)
- [Last.fm track.getSimilar](https://www.last.fm/api/show/track.getSimilar)
- [Last.fm API introduction and request guidance](https://www.last.fm/api/intro)
- [Last.fm API terms](https://www.last.fm/api/tos)
- [Spotify API changes](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api)
- [ListenBrainz recommendations](https://listenbrainz.readthedocs.io/en/latest/users/api/recommendation.html)
- [Apple Music recommendations](https://developer.apple.com/documentation/applemusicapi/recommendations)
- [YouTube Data API search](https://developers.google.com/youtube/data/reference/rest/v3/search?hl=en)
