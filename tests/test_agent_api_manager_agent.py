from agent_api.manager_agent import (
    build_manager_agent_debug_info,
    build_manager_agent_messages,
    call_manager_agent_api,
    extract_json_from_text,
    get_manager_plan,
)


def test_extract_json_from_text_parses_plain_json():
    assert extract_json_from_text('{"intent": "cashflow_check"}') == {
        "intent": "cashflow_check"
    }


def test_extract_json_from_text_parses_fenced_json():
    text = '```json\n{"intent": "expense_anomaly_review"}\n```'
    assert extract_json_from_text(text) == {"intent": "expense_anomaly_review"}


def test_extract_json_from_text_invalid_returns_none():
    assert extract_json_from_text("not json") is None


def test_build_manager_agent_messages_returns_list():
    messages = build_manager_agent_messages(
        "未来 30 天现金流安全吗？",
        {"business_snapshot": {"transaction_count": 3}},
    )
    assert isinstance(messages, list)
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"


def test_build_manager_agent_messages_omits_full_dataframe_context():
    messages = build_manager_agent_messages(
        "现金流安全吗？",
        {
            "transactions_df": "FULL_DATAFRAME_SHOULD_NOT_APPEAR",
            "business_snapshot": {"transaction_count": 3},
        },
    )
    joined = "\n".join(message["content"] for message in messages)
    assert "FULL_DATAFRAME_SHOULD_NOT_APPEAR" not in joined


def test_call_manager_agent_api_disabled_returns_fallback(monkeypatch):
    monkeypatch.setenv("ENABLE_AGENT_API", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    result = call_manager_agent_api("未来 30 天现金流安全吗？")
    assert result["mode"] == "fallback"
    assert result["manager_plan"]["intent"] == "cashflow_check"
    assert result["raw_output"] == ""


def test_get_manager_plan_fallback_returns_manager_plan(monkeypatch):
    monkeypatch.setenv("ENABLE_AGENT_API", "false")
    plan = get_manager_plan("这个月哪些支出最可疑？")
    assert plan["intent"] == "expense_anomaly_review"
    assert plan["selected_agents"]


def test_build_manager_agent_debug_info_returns_core_fields():
    debug = build_manager_agent_debug_info(
        {
            "mode": "fallback",
            "manager_plan": {
                "intent": "cashflow_check",
                "selected_agents": ["cashflow_agent"],
                "tool_plan": ["get_cashflow_summary"],
            },
            "errors": ["fallback"],
        }
    )
    assert debug == {
        "mode": "fallback",
        "intent": "cashflow_check",
        "selected_agents": ["cashflow_agent"],
        "tool_plan": ["get_cashflow_summary"],
        "errors": ["fallback"],
        "api_status": {},
    }
