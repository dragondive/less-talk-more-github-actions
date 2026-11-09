---
name: actor-filmography
description: Find a person's movie acting credits from TMDB.
---

# Actor filmography

Search for the person with `search_people`. When the result is unambiguous, call `get_person_movie_credits` with the TMDB person ID. If the search is ambiguous, show candidates and ask the user to choose. Present these as movie acting credits listed by TMDB, not as a complete or definitive filmography. Include the TMDB source link.
