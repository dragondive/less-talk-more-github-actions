---
name: title-discovery
description: Discover movies and TV series by genre, year, language, or country.
---

# Filtered title discovery

Use `discover_movies` or `discover_tv` with only criteria supplied by the user. TMDB genre IDs can be looked up with `get_reference_data` (`movie_genres` or `tv_genres`). Use ISO language and country codes returned by the same reference tool where appropriate. Return a short list with TMDB links; do not imply that the results are exhaustive.
