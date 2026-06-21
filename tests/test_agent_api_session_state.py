from agent_api.session_state import (
    add_turn_result,
    append_assistant_message,
    append_user_message,
    ensure_agent_chat_state,
    get_chat_action_items,
    get_default_agent_chat_state,
    get_latest_turn_result,
    reset_agent_chat_state,
    update_chat_action_items,
    update_latest_reports,
)


def test_default_agent_chat_state_shape():
    state = get_default_agent_chat_state()
    assert {"messages", "turns", "latest_turn_result", "latest_trace"}.issubset(state)
    assert "chat_action_items" in state
    assert "latest_report_markdown" in state
    assert "latest_trace_markdown" in state


def test_ensure_agent_chat_state_completes_missing_fields():
    state = ensure_agent_chat_state({"messages": []})
    assert "latest_suggested_actions" in state
    assert "chat_action_items" in state
    assert state["latest_report_markdown"] == ""


def test_append_user_message():
    state = append_user_message(None, "hello")
    assert state["messages"][0]["role"] == "user"


def test_append_assistant_message():
    state = append_assistant_message(None, "hi", metadata={"x": 1})
    assert state["messages"][0]["role"] == "assistant"
    assert state["messages"][0]["metadata"] == {"x": 1}


def test_add_turn_result_updates_latest_fields():
    turn = {
        "user_query": "q",
        "assistant_reply": "a",
        "suggested_actions": ["act"],
        "clarifying_questions": ["question"],
        "report_markdown": "# report",
        "trace_markdown": "# trace",
    }
    state = add_turn_result(None, turn, trace={"trace_id": "t"})
    assert state["latest_turn_result"] == turn
    assert state["latest_trace"] == {"trace_id": "t"}
    assert state["latest_suggested_actions"] == ["act"]
    assert state["latest_report_markdown"] == "# report"
    assert state["latest_trace_markdown"] == "# trace"


def test_reset_agent_chat_state_clears_state():
    assert reset_agent_chat_state()["messages"] == []


def test_get_latest_turn_result():
    state = add_turn_result(None, {"assistant_reply": "a"})
    assert get_latest_turn_result(state)["assistant_reply"] == "a"


def test_update_and_get_chat_action_items():
    action_items = [{"action_id": "C001", "title": "确认余额"}]
    state = update_chat_action_items(None, action_items)
    assert get_chat_action_items(state) == action_items


def test_update_latest_reports():
    state = update_latest_reports(None, report_markdown="# report", trace_markdown="# trace")
    assert state["latest_report_markdown"] == "# report"
    assert state["latest_trace_markdown"] == "# trace"
