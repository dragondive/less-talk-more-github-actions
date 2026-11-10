import pytest

from popcorn import deepseek, gemini, llm, sarvam


@pytest.fixture(autouse=True)
def do_not_use_local_sarvam_credentials(monkeypatch):
    monkeypatch.setattr(sarvam, "api_key", lambda: "")


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


def test_provider_autoselection_prefers_configured_sarvam_key(monkeypatch):
    monkeypatch.setattr(llm, "configured_value", lambda _name: "")
    monkeypatch.setattr(sarvam, "api_key", lambda: "sarvam-key")
    monkeypatch.setattr(gemini, "api_key", lambda: "gemini-key")
    monkeypatch.setattr(deepseek, "api_key", lambda: "deepseek-key")

    assert llm.active_provider_name() == "sarvam"


def test_provider_setting_selects_sarvam(monkeypatch):
    monkeypatch.setattr(llm, "configured_value", lambda name: "sarvam" if name == "LLM_PROVIDER" else "")
    assert llm.active_provider_name() == "sarvam"
    assert llm.provider_module("sarvam") is sarvam


def test_provider_autoselection_retains_deepseek(monkeypatch):
    monkeypatch.setattr(llm, "configured_value", lambda _name: "")
    monkeypatch.setattr(gemini, "api_key", lambda: "")
    monkeypatch.setattr(deepseek, "api_key", lambda: "deepseek-key")

    assert llm.active_provider_name() == "deepseek"


def test_unknown_provider_is_rejected(monkeypatch):
    monkeypatch.setattr(llm, "configured_value", lambda name: "other" if name == "LLM_PROVIDER" else "")

    with pytest.raises(ValueError, match="LLM_PROVIDER"):
        llm.active_provider_name()
