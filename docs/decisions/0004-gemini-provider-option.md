# ADR 0004: Add Gemini as the preferred configurable LLM provider

**Status:** Accepted

## Context

The first deployed model-backed Popcorn attempt reached DeepSeek but received HTTP 402 because its account could not serve the request. The project should keep DeepSeek available while enabling a second provider without changing skill, MCP, or agent contracts.

## Decision

Add a small Gemini `generateContent` REST adapter with function calling, normalizing its response into the existing bounded tool loop. Keep DeepSeek unchanged as an alternate. `LLM_PROVIDER=gemini` or `LLM_PROVIDER=deepseek` selects explicitly. If omitted, Popcorn selects Gemini when `GEMINI_API_KEY` is configured, then DeepSeek when `DEEPSEEK_API_KEY` is configured. With neither key, the deterministic router remains active. Use `gemini-3.8-flash` as the initial default, overridable with `GEMINI_MODEL`.

The model can select only movie discovery and actor filmography. Popcorn continues to validate and execute skill and MCP calls itself; it does not enable Gemini-managed tools.

## Consequences

- Render needs `GEMINI_API_KEY` and `LLM_PROVIDER=gemini` for the selected deployment. The existing DeepSeek key may remain configured and can be selected by setting `LLM_PROVIDER=deepseek`.
- User prompts and bounded TMDB tool results are sent to whichever model is selected. Popcorn does not persist conversation history.
- The provider's account, quota, model availability, and pricing rules apply. Check Google AI Studio account access before relying on a particular free or paid quota.
- Provider traces identify the selected provider and model, with token usage when supplied by the API.
- Gemini HTTP 503 responses receive two short retries with exponential backoff before a safe error is returned.
- The agent and skill contracts remain independent of either model provider.
