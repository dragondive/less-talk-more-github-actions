# ADR 0010: Start Popcorn Tasting with an offline fake-backed agent runner

**Status:** Accepted
**Date:** 2026-11-10

## Context

Popcorn now has real provider-backed skills and structured traces. A useful stakeholder evaluation should demonstrate deterministic checks, variable answer scoring, conversation cases, tool/skill coverage, cross-provider sequences, regression comparison, and a readable report. A live model/API dependency would make early iteration costly and nondeterministic.

## Decision

Extend the separate Popcorn Tasting project with a small JSON case format and runner adapter. Provide an offline mode that scripts the LLM boundary and deterministic fake HTTP responses while invoking Popcorn's agent, tool dispatch, skills, in-process MCP path and provider HTTP adapters. Keep a live mode that invokes Popcorn with configured model and provider APIs. Preserve trace events, check outcomes, MCP arguments, provider HTTP request/response evidence, normalized provider payloads and parent IDs. Generate JSON and standalone HTML reports with the evaluated commit identifier. Compare with an explicitly selected baseline, including individual checks.

## Alternatives considered

- Wait for an LLM API and build only against live runs: delays test design and makes routine CI depend on credentials, network availability, cost, and model variance.
- Hand-author agent traces and answers: simple, but it does not prove orchestration. Offline mode instead executes actual orchestration and MCP dispatch with replaceable fakes at model/provider client boundaries.
- Add a hosted dashboard or database: unnecessary for the initial runner slice; workflow artifacts and the Actions summary are sufficient until a demo walkthrough requires selection and historical comparison. ADR 0011 records the later approved dashboard and storage decision.

## Consequences

- Evaluator semantics, case schemas, regression reporting, and HTML rendering can be developed now.
- Offline runs exercise real orchestration, skills, MCP client/server and provider adapter parsing with scripted model decisions and fake HTTP response bytes; they do not prove live routing or model/provider quality.
- Live mode shares the case schema but may require provider credentials and can be nondeterministic.
- Report payloads can include provider response data and user query arguments. Avoid putting private prompts into committed cases and review artifact access before publishing live reports.
- Rubric scoring is transparent keyword matching, not semantic evaluation. A calibrated judge remains future optional work.
