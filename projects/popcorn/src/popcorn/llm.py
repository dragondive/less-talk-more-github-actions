"""Provider selection for Popcorn's bounded model-assisted agent loop."""

from __future__ import annotations

from popcorn import deepseek, gemini, sarvam
from popcorn.config import configured_value


PROVIDERS = {"deepseek": deepseek, "gemini": gemini, "sarvam": sarvam}


def active_provider_name() -> str | None:
    """Use explicit LLM_PROVIDER, otherwise prefer configured Sarvam, Gemini, then DeepSeek."""
    configured = configured_value("LLM_PROVIDER").lower()
    if configured:
        if configured not in PROVIDERS:
            raise ValueError("LLM_PROVIDER must be 'sarvam', 'gemini' or 'deepseek'.")
        return configured
    if sarvam.api_key():
        return "sarvam"
    if gemini.api_key():
        return "gemini"
    if deepseek.api_key():
        return "deepseek"
    return None


def provider_module(name: str):
    try:
        return PROVIDERS[name]
    except KeyError:
        raise ValueError("LLM_PROVIDER must be 'sarvam', 'gemini' or 'deepseek'.") from None
