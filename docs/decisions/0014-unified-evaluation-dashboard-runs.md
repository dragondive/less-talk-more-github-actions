# ADR 0014: Publish one grouped full-evaluation run to `/tests`

## Context

The dashboard previously showed one report at a time. The automatic CI workflow produced the Python test result and 98 offline AI scenarios, while the paid manual workflow produced separate live-judge baseline, regression, and recovery reports. The newest history item could therefore appear to contain only one test.

## Decision

Extend the manually triggered full-evaluation workflow to run the Python suite, all offline AI scenarios, and the bounded live LLM-judge regression sequence. Combine their outputs into one compressed history entry per workflow run. Keep pytest tests, deterministic AI scenarios, and live judge variants as separate sections in the report and dashboard; do not present them as one interchangeable test count.

The dashboard will show unit-test names and outcomes, offline scenario coverage and traces, and live baseline/regression/recovery responses and judge scores in one selected run. Its comparison picker will prefer the previous full-evaluation run when one exists. Ordinary push and pull-request CI remains offline and does not incur model costs.

## Consequences

- A single manual run gives the `/tests` dashboard a coherent view tied to one commit and Actions run.
- The unified report retains the separate result schemas and coverage views for each evaluation type.
- The live section remains bounded to the existing single scenario and configured repetitions; applying an LLM judge to every offline case is out of scope.
- The full workflow takes longer and uses the previously approved Sarvam API quota.
