from agent_api.openai_client import (
    check_client_available,
    create_chat_completion_text,
    extract_chat_completion_text,
    get_openai_client,
    sanitize_openai_error,
)


def test_get_openai_client_returns_none_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert get_openai_client() is None


def test_check_client_available_returns_shape(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = check_client_available()
    assert set(result) == {"available", "reason"}
    assert result["available"] is False


def test_check_client_available_does_not_require_real_request(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = check_client_available()
    assert "未检测到" in result["reason"]


def test_get_openai_client_returns_none_for_placeholder_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "your_api_key_here")
    assert get_openai_client() is None


def test_sanitize_openai_error_rewrites_401():
    error = Exception("Error code: 401 - {'error': {'message': 'Incorrect API key provided'}}")
    message = sanitize_openai_error(error)
    assert "OpenAI API Key 无效" in message
    assert "Incorrect API key provided" not in message


def test_extract_chat_completion_text_from_dict_response():
    response = {"choices": [{"message": {"content": '{"ok": true}'}}]}
    assert extract_chat_completion_text(response) == '{"ok": true}'


def test_extract_chat_completion_text_from_content_list():
    response = {"choices": [{"message": {"content": [{"text": "hello"}, {"text": " world"}]}}]}
    assert extract_chat_completion_text(response) == "hello world"


def test_create_chat_completion_text_raises_on_empty_content():
    class FakeCompletions:
        def create(self, **kwargs):
            return {"choices": [{"message": {"content": ""}}]}

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    try:
        create_chat_completion_text(FakeClient(), "model", [])
    except ValueError as error:
        assert "empty content" in str(error)
    else:
        raise AssertionError("Expected empty content to raise ValueError")
