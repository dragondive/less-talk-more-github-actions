# ADR 0010: Start Popcorn Tasting with an offline fixture runner

**Status:** Accepted
**Date:** 2026-11-10

## Context

Popcorn now has real provider-backed skills and structured traces. A useful stakeholder evaluation should demonstrate deterministic checks, variable answer scoring, conversation cases, tool/skill coverage, cross-provider sequences, regression comparison, and a readable report. A live model/API dependency would make early iteration costly and nondeterministic.

## Decision

Extend the separate Popcorn Tasting project with a small JSON case format and runner adapter. Provide a deterministic fixture mode for no-credential CI runs and a live mode that invokes Popcorn's configured agent. Preserve trace events, check outcomes, and provider tool response payloads for inspection. Generate JSON and standalone HTML reports with the evaluated commit identifier. Allow comparison with a saved baseline report.

## Alternatives considered

- Wait for an LLM API and build only against live runs: delays test design and makes routine CI depend on credentials, network availability, cost, and model variance.
- Make fixture mode stand in for real agent quality: simple, but it would overstate what has been exercised. The report and documentation must identify fixture runs as contract/evaluator demonstrations.
- Add a hosted dashboard or database: unnecessary for a hobby demo; workflow artifacts and static HTML are sufficient initially.

## Consequences

- Evaluator semantics, case schemas, regression reporting, and HTML rendering can be developed now.
- Fixture runs do not prove real Popcorn routing, live MCP execution, or model quality.
- Live mode shares the case schema but may require provider credentials and can be nondeterministic.
- Report payloads can include provider response data and user query arguments. Avoid putting private prompts into committed cases and review artifact access before publishing live reports.
- Rubric scoring is transparent keyword matching, not semantic evaluation. A calibrated judge remains future optional work.
