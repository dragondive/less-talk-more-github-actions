# Last.fm recommendation coverage

Popcorn uses Last.fm as its seed-based recommendation source. Calls are read-only, bounded to eight suggestions, and made through the official REST API at `https://ws.audioscrobbler.com/2.0/` using JSON responses.

| API method | MCP tool | Skill | Returned fields |
|---|---|---|---|
| `artist.getSimilar` | `get_lastfm_recommendations` | `music_recommendations` | Candidate artist name, MusicBrainz ID when present, Last.fm match score, Last.fm URL |
| `track.getSimilar` | `get_lastfm_recommendations` | `music_recommendations` | Candidate track and artist, match score, Last.fm URL |

An API key is required (`LASTFM_API_KEY`); these methods do not require a user session. The caller sends an identifiable versioned User-Agent. Popcorn makes one API call per recommendation request, limits results, and does not expose or trace the key. Last.fm advises reasonable request volume. Recommendation match values are returned as provider signals, not objective quality scores.

Last.fm's API terms require credit and links to each Last.fm artist/track page, restrict ordinary API/data use to non-commercial purposes, prohibit sublicensing, and do not grant music streaming rights. The terms also specify a “powered by AudioScrobbler” button and say publicly accessible pages using Last.fm services need prior written approval, including approval of button/link placement. The project uses the API for personal/hobby demonstration, but a publicly hosted demo must not be enabled until Last.fm's approval and attribution requirements are handled. Consult the [current API terms](https://www.last.fm/api/tos); this note is not legal advice.

MusicBrainz remains a separate supporting source for artist and release metadata. Last.fm may include MusicBrainz IDs in artist results, but Popcorn does not currently make a follow-up MusicBrainz match request or claim an ID is a verified cross-provider link. No listening history, profile personalization, account access, playlist mutation, or playback is implemented.

Example prompts: “Recommend artists like Portishead”, “What artists are similar to Yoko Kanno?”, “Recommend tracks like Believe by Cher”.

All tests use mocked Last.fm responses. No live API call has been made.
