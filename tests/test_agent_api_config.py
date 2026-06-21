from agent_api.config import (
    get_agent_api_status,
    get_agent_model,
    get_openai_api_key,
    get_openai_base_url,
    is_agent_api_enabled,
    should_use_fallback,
)


def test_get_agent_model_returns_string(monkeypatch):
    monkeypatch.delenv("OPENAI_AGENT_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    assert get_agent_model() == "gpt-5.4-mini"


def test_get_openai_base_url_defaults_to_openai_endpoint(monkeypatch):
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_BASE", raising=False)
    monkeypatch.delenv("OPENAI_API_URL", raising=False)
    assert get_openai_base_url() == "https://api.openai.com"


def test_get_agent_api_status_shape(monkeypatch):
    monkeypatch.setenv("ENABLE_AGENT_API", "false")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    status = get_agent_api_status()
    assert set(status) == {
        "enabled",
        "has_api_key",
        "has_invalid_api_key",
        "model",
        "base_url",
        "mode",
        "reason",
        "user_message",
    }


def test_disabled_flag_keeps_agent_api_disabled(monkeypatch):
    monkeypatch.setenv("ENABLE_AGENT_API", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-valid-looking-key")
    assert is_agent_api_enabled() is False


def test_missing_api_key_uses_fallback(monkeypatch):
    monkeypatch.setenv("ENABLE_AGENT_API", "true")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert should_use_fallback() is True


def test_placeholder_api_key_is_not_accepted(monkeypatch):
    monkeypatch.setenv("ENABLE_AGENT_API", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "your_api_key_here")
    status = get_agent_api_status()
    assert get_openai_api_key() is None
    assert is_agent_api_enabled() is False
    assert status["has_invalid_api_key"] is True
    assert status["mode"] == "fallback"
    assert "fallback" in status["user_message"]


def test_malformed_api_key_is_not_accepted(monkeypatch):
    monkeypatch.setenv("ENABLE_AGENT_API", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    assert get_openai_api_key() is None
    assert is_agent_api_enabled() is False


def test_plausible_api_key_can_enable_agent_api(monkeypatch):
    monkeypatch.setenv("ENABLE_AGENT_API", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-valid-looking-key")
    assert get_openai_api_key() == "sk-test-valid-looking-key"
    assert is_agent_api_enabled() is True
