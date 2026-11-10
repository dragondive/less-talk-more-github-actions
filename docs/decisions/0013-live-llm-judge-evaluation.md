# ADR 0013: Add an opt-in live LLM judge demonstration

## Context

Offline evaluation runs Popcorn's actual orchestration with scripted model choices and deterministic provider responses. It demonstrates routing and test reporting, but cannot measure variable natural-language responses. The demo needs to show how a semantic evaluator can compare response quality across a regression and recovery.

## Decision

Add a manually triggered, bounded live-evaluation workflow with one movie scenario repeated three times per version. Sarvam generates each answer; a separate Sarvam completion acts as judge. The judge receives the case rubric, answer, and observed MCP results, and returns structured per-criterion scores with short rationales and evidence quotes. A weighted score and pass-rate threshold determine the semantic result. Expected skill/tool checks remain visible alongside the judge score.

The workflow uses deterministic TMDB response fixtures by default so repeated versions receive identical source evidence; the Popcorn agent, movie skill, in-process MCP server/client, live Sarvam model, and judge calls still execute. An input can select live TMDB data to include the external API. It produces a normal baseline, a controlled regression that removes the available tool catalog and asks the model to answer from memory, and a normal recovery run, then publishes all reports to the existing history so `/tests` can compare versions. Ordinary CI remains offline. `SARVAM_JUDGE_MODEL` can select another Sarvam-supported judge model; by default the judge uses `sarvam-105b` in a separate call.

## Consequences and limits

- Live evaluations use paid Sarvam generations and real TMDB requests; the workflow is opt-in and limited to one case with a small number of repetitions.
- Judge scores are probabilistic and should be interpreted as comparative evidence, not an absolute correctness oracle. Human-reviewed rubric calibration remains useful.
- A separate call to the same model is not independent adjudication. Configure a distinct supported judge model when available.
- Reports retain answer text, traces, judge rationales, scores and evidence excerpts, so scenario content should remain synthetic and safe for the public dashboard.
