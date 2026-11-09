# ADR 0001: Build a narrow evaluated MCP slice first

**Status:** Accepted
**Date:** 2026-11-09

## Context

The demo's purpose is to show skill and MCP usage measurement, deterministic answer checks, and evaluation of variable natural-language output. The earlier roadmap deferred Popcorn Tasting until Popcorn was broadly functional, which would postpone the central demonstration. No entertainment provider, model provider, or paid service is required for the Hello World slice.

## Decision

Build Popcorn as a small Python application with an official MCP Python SDK server and a local MCP client. Start with `greeting` and `movie_fit` skills backed by a small local fixture. Build a separate, narrow Popcorn Tasting runner at the same time. It consumes structured invocation events, checks golden expected answers and skill/tool usage, scores the agent response with an inspectable rubric, and scores additional varied response fixtures to exercise rubric behavior.

Use GitHub Actions to run tests and the local evaluation command and publish JSON and text artifacts. Do not add a hosted model, live provider adapter, public deployment, evaluation dashboard, or general-purpose evaluator in this slice.

## Alternatives considered

- **Finish Popcorn before any evaluator work:** does not demonstrate the project's central measurement goal early.
- **Build the general evaluator first:** risks designing a platform without a concrete execution trace or task.
- **Call a third-party provider MCP server now:** adds external maintenance, credentials, network dependence, and unclear coverage before a provider scenario is selected.

## Consequences

- The first slice is inexpensive and repeatable, with no external API credentials.
- It validates SDK-backed MCP tool calls and evaluator plumbing, but not external MCP server availability or real provider coverage.
- Keyword rubric scoring is transparent but shallow. It is not a substitute for a calibrated LLM judge or human review.
- The trace and dataset formats are versioned demonstrations, not stable external contracts.
- Provider selection, model selection, endpoint coverage, deployment, and more complete trace redaction remain follow-up decisions.
