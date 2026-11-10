# ADR 0012: Add Sarvam as the selected LLM provider

## Context

Popcorn's tool loop needs a model API that supports function tools while leaving skill execution and MCP calls inside Popcorn. A Sarvam API key is now available for the first live model trial. Gemini and DeepSeek adapters already exist and should remain usable.

## Decision

Add a small REST adapter for Sarvam's OpenAI-compatible `POST /v2/chat/completions` endpoint. Use `sarvam-105b` by default, permit `SARVAM_MODEL` override, send bounded tool schemas with `tool_choice=auto`, and normalize nothing because the response uses the existing Chat Completions shape. Select Sarvam explicitly with `LLM_PROVIDER=sarvam`; when no provider is selected, prefer a configured Sarvam key, then Gemini, then DeepSeek. Render's Blueprint selects Sarvam and asks for `SARVAM_API_KEY`.

## Consequences

- Popcorn continues to validate tool calls and execute skills/MCP operations locally.
- Provider requests are live and may incur usage charges; ordinary tests use injected HTTP fakes.
- API credentials remain server-side and are not written to traces.
- Gemini and DeepSeek remain available through their explicit provider settings.
- A bounded live request is required to validate the account's entitlement and the end-to-end tool path.
