# Popcorn Tasting

Run the offline evaluation from the repository root:

```sh
python -m popcorn_tasting --mode fixture
```

This mode runs 98 natural-language scenarios across movie, TV, anime, music discovery, artist recommendations, AniList character/staff/relation exploration, and cross-domain conversations. It includes follow-ups, history checks, ambiguity/no-result handling, deterministic assertions, and rubric-scored answer variants. A scripted fake chat-completion provider and deterministic HTTP response fakes keep it offline. It invokes Popcorn's real `answer()` orchestration, model tool dispatch, skills, in-process MCP client/server, and provider HTTP adapters. Model decisions, user turns, MCP arguments, HTTP parameters/bodies and responses, normalized provider results, parent IDs, final responses, checks, and coverage appear in the report.

The JSON report defaults to `artifacts/evaluation.json`. Pass `--html path/to/report.html` only when a standalone HTML export is explicitly useful. Each report records the evaluated Git commit. In GitHub Actions, the runner also writes a Markdown summary directly to the workflow run page, including each test input/outcome, deterministic and rubric-based evaluation counts, skill/MCP/provider API coverage, and baseline regressions. CI uploads the detailed JSON as an artifact named for the commit; the interactive dashboard is served by the Render app at `/tests`.

To run with real provider APIs while keeping model decisions scripted, use `--mode mcp`; this invokes Popcorn's real MCP/provider path and may require network access and configured credentials. Use `--case-ids id1 id2` to run a bounded subset. These calls may be subject to provider rate limits. To use Popcorn's configured model too, use `--mode live`; that may call paid model APIs as well as external providers. Results can vary. The case format is shared between these modes, although offline assertions may need adjustment when live provider records differ.

Use `--baseline path/to/evaluation.json` to compare against an explicitly selected saved report. Pass-to-fail case and individual check changes are reported.

## Case format

Cases use natural-language conversation `turns`. A turn can assert expected skills and MCP tools, required factual phrases, context history, or a weighted keyword rubric with sample prose variants. Cases can assert skill sequences. Reports separate attempted/succeeded/failed invocation counts; expected-but-omitted and unexpected invocations are visible in coverage. Rubrics use transparent weighted phrase matching, not semantic interpretation or an LLM judge.

Offline mode demonstrates actual orchestration, MCP-path execution and provider adapter request parsing with deterministic fakes; it does not measure model quality or live provider behavior. The `mcp` mode provides real-provider evidence using scripted model choices. The Render-hosted `/tests` dashboard is the interactive overview and drill-down; GitHub Actions retains the concise run summary and detailed JSON artifact. Each CI evaluation run is also added to a rolling history of ten reports for selectable comparisons.
