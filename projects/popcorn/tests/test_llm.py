import pytest

from popcorn import deepseek, gemini, llm


def test_provider_setting_selects_explicit_provider(monkeypatch):
    monkeypatch.setattr(llm, "configured_value", lambda name: "deepseek" if name == "LLM_PROVIDER" else "")
    monkeypatch.setattr(gemini, "api_key", lambda: "gemini-key")
    monkeypatch.setattr(deepseek, "api_key", lambda: "deepseek-key")

    assert llm.active_provider_name() == "deepseek"


def test_provider_autoselection_prefers_configured_gemini_key(monkeypatch):
    monkeypatch.setattr(llm, "configured_value", lambda _name: "")
    monkeypatch.setattr(gemini, "api_key", lambda: "gemini-key")
    monkeypatch.setattr(deepseek, "api_key", lambda: "deepseek-key")

    assert llm.active_provider_name() == "gemini"


def test_provider_autoselection_retains_deepseek(monkeypatch):
    monkeypatch.setattr(llm, "configured_value", lambda _name: "")
    monkeypatch.setattr(gemini, "api_key", lambda: "")
    monkeypatch.setattr(deepseek, "api_key", lambda: "deepseek-key")

    assert llm.active_provider_name() == "deepseek"


def test_unknown_provider_is_rejected(monkeypatch):
    monkeypatch.setattr(llm, "configured_value", lambda name: "other" if name == "LLM_PROVIDER" else "")

    with pytest.raises(ValueError, match="LLM_PROVIDER"):
        llm.active_provider_name()
