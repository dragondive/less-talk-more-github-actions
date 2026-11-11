# Popcorn Tasting

Run the offline evaluation from the repository root:

```sh
python -m popcorn_tasting --mode fixture
```

This mode runs 98 natural-language scenarios across movie, TV, anime, music discovery, artist recommendations, AniList character/staff/relation exploration, and cross-domain conversations. It includes follow-ups, history checks, ambiguity/no-result handling, deterministic assertions, and rubric-scored answer variants. A scripted fake chat-completion provider and deterministic HTTP response fakes keep it offline. It invokes Popcorn's real `answer()` orchestration, model tool dispatch, skills, in-process MCP client/server, and provider HTTP adapters. Model decisions, user turns, MCP arguments, HTTP parameters/bodies and responses, normalized provider results, parent IDs, final responses, checks, and coverage appear in the report.

The JSON report defaults to `artifacts/evaluation.json`. Pass `--html path/to/report.html` only when a standalone HTML export is explicitly useful. Each report records the evaluated Git commit. In GitHub Actions, the runner also writes a Markdown summary directly to the workflow run page, including each test input/outcome, deterministic and rubric-based evaluation counts, skill/MCP/provider API coverage, and baseline regressions. CI uploads the detailed JSON as an artifact named for the commit; the interactive dashboard is served by the Render app at `/tests`.

To run with real provider APIs while keeping model decisions scripted, use `--mode mcp`; this invokes Popcorn's real MCP/provider path and may require network access and configured credentials. Use `--case-ids id1 id2` to run a bounded subset. These calls may be subject to provider rate limits. To use Popcorn's configured model too, use `--mode live`; that may call paid model APIs as well as external providers. Results can vary. The case format is shared between these modes, although offline assertions may need adjustment when live provider records differ.

## Full evaluation demo

Manually run the **Popcorn Full Evaluation Demo** workflow to see the complete suite as one `/tests` history entry. A run includes the Python test suite, all 98 offline AI scenarios, and the live Sarvam judge scenario across baseline, injected regression, and recovery. The dashboard keeps these categories distinct while showing them together: unit-test names and status, skill/MCP/provider coverage and scenario traces, plus live responses, judge criteria, and score changes. It displays the exact Python test count for each commit.

Add the repository Actions secret `SARVAM_API_KEY` under **Settings → Secrets and variables → Actions** before dispatching the workflow. `TMDB_ACCESS_TOKEN` is also required when choosing live TMDB data; fixture mode needs only the Sarvam key. The workflow validates these secrets before making paid calls. Each demo produces multiple answer-generation and judge calls, so it uses paid model API quota. Choosing live TMDB data also makes real provider requests; the fixed evidence option avoids provider outages and makes versions comparable. The default judge model is the same Sarvam model in a separate evaluation call; `SARVAM_JUDGE_MODEL` can select a different Sarvam-supported judge model when the account has access. Each combined report is published as one of the last ten dashboard runs.

Run locally from the repository root with the same configured environment. The fixed-provider option keeps the live LLM, Popcorn skill and in-process MCP calls real while holding TMDB evidence constant; omit it to use live TMDB APIs:

```sh
python -m popcorn_tasting --mode live-judge \
  --dataset projects/popcorn_tasting/data/golden/live_judge_demo.json \
  --repetitions 3 --fixture-provider-data --output artifacts/live-baseline.json
python -m popcorn_tasting --mode live-judge \
  --dataset projects/popcorn_tasting/data/golden/live_judge_demo.json \
  --repetitions 3 --fixture-provider-data --inject-regression --baseline artifacts/live-baseline.json \
  --output artifacts/live-regression.json
python -m popcorn_tasting --mode live-judge \
  --dataset projects/popcorn_tasting/data/golden/live_judge_demo.json \
  --repetitions 3 --fixture-provider-data --baseline artifacts/live-regression.json \
  --output artifacts/live-recovery.json
```

The regression option temporarily removes the agent's available tool catalog and tells it to answer from memory. This models a source-grounding regression. The real LLM still generates the response and the LLM judge still evaluates it. The evaluator also checks expected skill/tool execution, so missing provider evidence is visible separately from the semantic score. The demo is deliberately opt-in; ordinary CI remains offline.

Use `--baseline path/to/evaluation.json` to compare against an explicitly selected saved report. Pass-to-fail case and individual check changes are reported.

## Case format

Cases use natural-language conversation `turns`. A turn can assert expected skills and MCP tools, required factual phrases, context history, or a weighted keyword rubric with sample prose variants. Cases can assert skill sequences. Live judge cases use an `llm_judge` rubric with criterion descriptions, weights, minimum score, and minimum pass rate. Reports separate attempted/succeeded/failed invocation counts; expected-but-omitted and unexpected invocations are visible in coverage. Offline keyword rubrics remain transparent phrase checks; the opt-in live judge mode evaluates semantics against the observed MCP evidence.

Offline mode demonstrates actual orchestration, MCP-path execution and provider adapter request parsing with deterministic fakes; it does not measure model quality or live provider behavior. The `mcp` mode provides real-provider evidence using scripted model choices. The Render-hosted `/tests` dashboard is the interactive overview and drill-down; GitHub Actions retains the concise run summary and detailed JSON artifact. Each CI evaluation run is also added to a rolling history of ten reports for selectable comparisons.
