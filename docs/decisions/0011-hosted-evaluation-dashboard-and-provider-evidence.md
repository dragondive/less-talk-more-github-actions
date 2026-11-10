# ADR 0011: Host the evaluation dashboard with Popcorn and retain provider evidence

**Status:** Accepted
**Date:** 2026-11-10

## Context

The offline evaluator already executes Popcorn's real orchestration, MCP tools and provider adapters, but live traces showed only MCP arguments and normalized results. They did not consistently identify the provider HTTP endpoint, request/response, elapsed time, or failure kind. The standalone report also presented a long case list rather than an overview with scenario and execution-path drill-down. The user requested the dashboard at `/tests` on the existing Render app, selectable comparisons (latest versus previous by default), and history for the latest ten runs. Python line coverage is outside this demo.

The Render Blueprint uses the free plan, whose filesystem is ephemeral. A persistent Render disk or hosted database would add infrastructure and cost.

## Decision

- Capture provider HTTP events inside the provider adapters and nest them under their parent MCP tool call. Record provider, method, sanitized URL and request values, bounded response data, HTTP status when known, elapsed time, and a non-sensitive error type. Do not capture headers.
- Serve a static dashboard at `/tests`, backed by same-origin read-only endpoints. Show run health, scenario outcomes and sequences, skill/MCP/provider endpoint activity, and detailed API evidence. Allow selecting any two retained runs; default to latest versus previous.
- Keep evaluation execution/scoring in the separate Popcorn Tasting project. The Popcorn web process only serves its presentation and report data.
- Publish compressed reports and a small index to a dedicated `eval-history` branch from GitHub Actions. Keep ten report files in the branch snapshot and replace that snapshot on each main-branch run. Render reads the branch through its server-side endpoint, avoiding reliance on its ephemeral filesystem.
- Exclude Python line coverage. Fixture runs remain clearly identified as scripted-model/fake-provider runs.

## Consequences

- Live traces can connect skill → MCP tool → provider request and response, while credentials in query/body fields are redacted and response payloads are bounded.
- Run history is visible without paid storage, but report availability depends on the public GitHub raw-content endpoint. The report JSON is synthetic evaluation data and must not contain private prompts.
- Provider traces are demonstration evidence, not a permanent stable telemetry schema. Changes to trace fields require keeping dashboard readers and report artifacts compatible.
- The dashboard provides execution-path coverage; it does not claim Python code coverage or model quality beyond the evaluator's configured assertions and rubrics.
