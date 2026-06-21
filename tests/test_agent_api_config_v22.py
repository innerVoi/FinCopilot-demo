from agent_api.config import get_agent_api_status, get_agent_model, get_openai_base_url, is_agent_api_enabled


def test_default_model_is_gpt_5_4_mini(monkeypatch):
    monkeypatch.delenv("OPENAI_AGENT_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    assert get_agent_model() == "gpt-5.4-mini"


def test_agent_api_defaults_to_try_enabled_without_flag_but_fallback_without_key(monkeypatch):
    monkeypatch.delenv("ENABLE_AGENT_API", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert is_agent_api_enabled() is False
    status = get_agent_api_status()
    assert status["mode"] == "fallback"
    assert "user_message" in status


def test_agent_api_enabled_with_key_and_no_flag(monkeypatch):
    monkeypatch.delenv("ENABLE_AGENT_API", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-valid-looking-key")
    assert is_agent_api_enabled() is True
    status = get_agent_api_status()
    assert status["mode"] == "api_agent"
    assert status["user_message"] == "当前使用真实 Agent 分析。"


def test_agent_api_false_flag_forces_fallback(monkeypatch):
    monkeypatch.setenv("ENABLE_AGENT_API", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-valid-looking-key")
    assert is_agent_api_enabled() is False
    status = get_agent_api_status()
    assert status["mode"] == "fallback"
    assert "开发调试" in status["user_message"]


def test_get_agent_api_status_returns_user_message(monkeypatch):
    monkeypatch.delenv("ENABLE_AGENT_API", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    status = get_agent_api_status()
    assert "user_message" in status
    assert status["user_message"]


def test_openai_base_url_can_be_overridden(monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.test/v1/")
    assert get_openai_base_url() == "https://example.test/v1"
    status = get_agent_api_status()
    assert status["base_url"] == "https://example.test/v1"
