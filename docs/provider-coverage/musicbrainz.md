# MusicBrainz provider coverage

Read-only coverage implemented through the official MusicBrainz Web Service (`https://musicbrainz.org/ws/2/`):

| API operation | MCP tool | Skill | Coverage |
|---|---|---|---|
| Artist search (`artist/`, bounded to 8 candidates) | `search_musicbrainz_artists` | `music_discovery` | Candidate names, MBIDs, type, area, begin date, disambiguation, and MusicBrainz links |
| Artist lookup by MBID (`inc=aliases+url-rels`) | `get_musicbrainz_artist` | `music_discovery` | Artist type, area, disambiguation, aliases, and source link |
| Release-group browse by artist MBID (limit 10; album/EP/single) | `get_musicbrainz_artist_release_groups` | `music_discovery` | Title, release-group type, first release date, MBID, and source link |

The adapter uses JSON, a 15-second timeout, bounded query fields, and one-request-per-second spacing per process. HTTP 503 responses are surfaced without retry. The versioned User-Agent identifies Popcorn and links to the repository; if the project gains a maintainer contact URL or email, replace this with a direct contact channel.

## Limitations

- Search results are candidates. The skill requests clarification when there is no unique exact-name candidate or only one candidate is not established.
- At most ten selected release groups are shown. This is not a complete discography or bulk export.
- No MusicBrainz work/recording relationship browsing or soundtrack-to-screen claims are implemented. MusicBrainz may contain composer/work relationships, but these require additional relationship traversal and do not by themselves map to TMDB/AniList entities.
- No account access, collection/list writes, or other mutations are present.
- MusicBrainz says core database data is CC0 and supplementary data is CC BY-NC-SA 3.0. The demo retains provider attribution links; licensing details are documented at [MusicBrainz Data License](https://musicbrainz.org/doc/About/Data_License). This inventory is not legal advice.
- MusicBrainz documents non-commercial Web Service use as free; API access does not require a key, but a meaningful User-Agent is required. See its [API FAQ](https://musicbrainz.org/doc/MusicBrainz_API/FAQ).
- Tests mock all provider responses. No live MusicBrainz request was made during implementation.

Example prompts: “What has Yoko Kanno released?”, “Find the artist Portishead”, “Show albums by Brian Eno”.
