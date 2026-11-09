# ADR 0009: Bounded browser-held chat history

**Status:** Accepted
**Date:** 2026-11-09

## Context

The chat endpoint previously treated every request as an independent question, so model-backed follow-ups could not refer to earlier turns. Popcorn does not currently need durable conversation storage, user accounts, or cross-device sessions.

## Decision

The browser keeps up to four successful user/assistant exchanges in page memory and sends that context with each chat request. Reloading the page clears it. The server validates that history consists only of alternating user and assistant messages, caps it at eight messages, 2,000 characters per message, and 8,000 characters total, then passes it to `answer`. The agent applies its own bounds and inserts only user/assistant roles after the system prompt. Traces record only the number of prior messages, not their text. No conversation content is stored by Popcorn's server.

## Consequences

- Model-backed turns can resolve follow-up references using up to four prior exchanges.
- Recent history is sent to the configured model provider along with the current turn.
- Context is local to the open browser page; reload, another tab, or another device starts a new conversation.
- The client supplies the transcript, so the server treats it as untrusted input and validates its shape and size. It is not a durable or cryptographically verified transcript.
- The deterministic fallback remains turn-local and does not resolve follow-up references.
- Provider-side handling of requests follows the selected model provider's own policies; Popcorn's no-storage behavior does not govern provider retention.

## Alternatives considered

- Server-side session storage would support trusted history across requests, but adds session lifecycle, storage, privacy, and multi-instance coordination concerns.
- Browser local storage would survive reloads, but would retain conversation data on the device beyond the active page session.

The bounded in-memory browser history is sufficient for the current demo and keeps the state lifecycle visible to the user.
