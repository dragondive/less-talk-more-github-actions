# Music recommendations

Use Last.fm for read-only recommendations from an explicit music seed.

- For an artist seed, return similar artist candidates.
- For an artist and track seed, return similar track candidates.
- Keep the seed clear in the response and retain the Last.fm links.
- Present Last.fm match values only as provider-reported ranking signals, not as objective similarity or quality measurements.
- Do not imply that Last.fm results are playable, available in a particular streaming service, or personalized to the current user.
- Do not invent matches when Last.fm returns no results.
