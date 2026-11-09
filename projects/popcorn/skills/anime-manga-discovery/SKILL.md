# Anime and Manga Discovery

Use the AniList-backed `anime_manga_discovery` workflow for public anime or manga questions.

1. Search only the requested media type (`ANIME` or `MANGA`).
2. If the results do not identify one unambiguous title, show candidates and ask the user to choose.
3. Retrieve details only after selecting a candidate. Preserve AniList's source links.
4. Treat synopsis, genres, publication metadata, listed characters, and relations as provider-sourced. Do not infer cross-provider connections.
5. Public read access needs no account or key. Do not use AniList for personal lists or mutations in this skill.

The API can be temporarily degraded or rate limited. Report that clearly and let the user retry later. Search results exclude entries marked adult, but that filter may not be complete; use care with mature content.
