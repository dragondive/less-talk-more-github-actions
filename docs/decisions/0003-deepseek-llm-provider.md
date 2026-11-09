# ADR 0003: Use DeepSeek for the first model-backed Popcorn flow

**Status:** Accepted

## Context

Popcorn's first real-data slice uses a deterministic router for movie and actor requests. The chat app needs more flexible intent handling and should produce natural-language responses, including clearly labeled subjective movie-fit observations, while keeping TMDB as the factual source.

## Decision

Use DeepSeek's OpenAI-compatible Chat Completions API, with `deepseek-flash` as the default model. Enable the model when `DEEPSEEK_API_KEY` is configured. Provide only two bounded function tools to it: movie discovery and actor filmography. Popcorn validates tool names and arguments, executes skills and MCP calls locally, and returns results to the model for phrasing. Retain the deterministic router when no API key is set.

## Alternatives considered

- OpenAI API: mature function-calling integration, but requires separate API access and billing from most ChatGPT subscriptions.
- Gemini API: supports function calling and has a free-of-charge tier for some usage, but would require a separate provider adapter.
- Local model hosting: avoids sending prompts to a third-party API but adds inference hosting and maintenance requirements.

## Consequences

- `DEEPSEEK_API_KEY` must be set in Render's environment for deployed chat requests to use DeepSeek. It is not stored in GitHub or sent to the browser.
- User questions are sent to DeepSeek when model mode is enabled. Popcorn does not persist conversation history.
- Provider facts still come from TMDB tool results; the model is instructed not to invent TMDB facts and to label movie-fit judgments as interpretation.
- DeepSeek API errors are surfaced as safe messages. API usage incurs provider charges according to DeepSeek's current model pricing.
- The adapter uses the documented non-thinking mode for Chat Completions tool selection. A future provider change should not require changing skill or MCP contracts.
