# Popcorn Tasting

Run the offline evaluation from the repository root:

```sh
python -m popcorn_tasting --mode fixture
```

This mode uses deterministic fixture responses and records representative skill and MCP events. It requires no API keys, network access, or LLM. It exercises Popcorn Tasting's case runner, checks, coverage, regression comparison, and HTML report; it does **not** execute Popcorn's real agent or provider adapters.

The report files default to `artifacts/evaluation.json` and `artifacts/index.html`. Each report records the evaluated Git commit. In GitHub Actions, the runner also writes a Markdown summary directly to the workflow run page, including each test input/outcome, deterministic and rubric-based evaluation counts, skill/MCP coverage, and baseline regressions. CI uploads the detailed JSON and standalone HTML reports as an artifact named for the commit.

To run the same cases against Popcorn's configured agent and live providers, use `--mode live`. That mode may call paid model APIs and external providers and requires the relevant configuration. Results can vary with model/provider behavior. The case format is shared between fixture and live modes so the cases can be refined offline before live credentials are configured.

Use `--baseline path/to/evaluation.json` to identify cases that passed in a saved report but fail now. The baseline comparison is case-level and intentionally simple at this stage.

## Case format

Cases support single-turn `input` or a list of conversation `turns`. A turn can assert expected skills, MCP tools, exact response text, required phrases, or a weighted keyword rubric with sample response variants. A case can assert an expected skill sequence across turns. Reports retain trace events and sanitized invocation attributes supplied by Popcorn.

Fixture mode demonstrates the evaluation/reporting contract, not real agent quality or live model tool selection. For that evidence, run live mode when credentials and network access are available. The Actions summary is the quick dashboard; the HTML artifact is the detailed, expandable per-test trace view. There is no hosted dashboard endpoint at this stage.
