---
name: title-rating
description: Submit an explicitly requested TMDB guest rating for a movie, TV series, or episode.
---

# Title rating

Only run this skill when the user directly asks Popcorn to submit a rating. Confirm the title against TMDB and ask which result they mean if ambiguous. Accept only TMDB's 0.5–10 half-point scale. Episode ratings also require the season and episode numbers. A temporary guest session is created for each submission and is not returned to the chat or stored. Never infer a rating from a recommendation request or review.
