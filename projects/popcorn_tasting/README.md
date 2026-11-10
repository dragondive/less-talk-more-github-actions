# Popcorn Tasting

Run the offline evaluation from the repository root:

```sh
python -m popcorn_tasting --mode fixture
```

This mode uses a scripted fake chat-completion provider and deterministic HTTP response fakes. It requires no API keys or network access. It invokes Popcorn's real `answer()` orchestration, model tool dispatch, skills, in-process MCP client/server, and provider HTTP adapters. The LLM boundary and HTTP response bytes are faked; live model/provider behavior is not covered. Model decisions, user turns, MCP arguments, HTTP request parameters/bodies and responses, normalized provider results, parent IDs, final responses, checks, and coverage are retained in the report.

The report files default to `artifacts/evaluation.json` and `artifacts/index.html`. Each report records the evaluated Git commit. In GitHub Actions, the runner also writes a Markdown summary directly to the workflow run page, including each test input/outcome, deterministic and rubric-based evaluation counts, skill/MCP coverage, and baseline regressions. CI uploads the detailed JSON and standalone HTML reports as an artifact named for the commit.

To run the same cases against Popcorn's configured agent and live providers, use `--mode live`. That mode may call paid model APIs and external providers and requires the relevant configuration. Results can vary with model/provider behavior. The case format is shared between offline and live modes.

Use `--baseline path/to/evaluation.json` to compare against an explicitly selected saved report. Pass-to-fail case and individual check changes are reported.

## Case format

Cases use natural-language conversation `turns`. A turn can assert expected skills and MCP tools, required factual phrases, context history, or a weighted keyword rubric with sample prose variants. Cases can assert skill sequences. Reports separate attempted/succeeded/failed invocation counts; expected-but-omitted and unexpected invocations are visible in coverage. Rubrics use transparent weighted phrase matching, not semantic interpretation or an LLM judge.

Offline mode demonstrates actual orchestration, MCP-path execution and provider adapter request parsing with deterministic fakes; it does not measure model quality or live provider behavior. For that evidence, run live mode when credentials and network access are available. The Actions summary is the quick dashboard; the HTML artifact contains the expandable per-test event trace. There is no hosted dashboard endpoint at this stage.
