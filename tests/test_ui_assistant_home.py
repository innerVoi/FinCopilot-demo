from ui.assistant_home import safe_get_nested


def test_safe_get_nested_reads_nested_dict():
    data = {"a": {"b": {"c": 42}}}
    assert safe_get_nested(data, ["a", "b", "c"]) == 42


def test_safe_get_nested_returns_default_for_missing_key():
    data = {"a": {"b": 1}}
    assert safe_get_nested(data, ["a", "missing"], default="fallback") == "fallback"


def test_safe_get_nested_handles_none():
    assert safe_get_nested(None, ["a"], default=0) == 0


def test_render_assistant_home_accepts_latest_agent_turn_argument():
    import inspect

    from ui.assistant_home import render_assistant_home

    assert "latest_agent_turn" in inspect.signature(render_assistant_home).parameters


def test_render_assistant_home_accepts_chat_action_items_argument():
    import inspect

    from ui.assistant_home import render_assistant_home

    assert "chat_action_items" in inspect.signature(render_assistant_home).parameters
