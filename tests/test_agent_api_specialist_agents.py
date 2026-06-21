from agent_api.schemas import CASHFLOW_AGENT, ANOMALY_AGENT, PLANNING_AGENT
from agent_api.specialist_agents import (
    build_specialist_agent_messages,
    build_specialist_agents_debug_info,
    call_selected_specialist_agents,
    call_specialist_agent_api,
    get_relevant_context_for_agent,
)


def make_context():
    return {
        "transactions_df": "FULL_DATAFRAME_SHOULD_NOT_APPEAR",
        "cashflow_summary": {"risk_level": "medium"},
        "invoice_summary": {"overdue_invoice_amount": 100},
        "anomaly_summary": {"rule_anomaly_count": 2},
        "budget_summary": {"total_expense": 500},
        "goal_summary": {"goal_count": 1},
        "action_summary": {"total": 3},
        "progress_summary": {"active_count": 2},
        "business_context": {"current_cash_balance": 1000},
        "safety_context": {"no_fraud_determination": True},
    }


def test_relevant_context_cashflow_agent_is_limited():
    context = get_relevant_context_for_agent(CASHFLOW_AGENT, make_context())
    assert "cashflow_summary" in context
    assert "invoice_summary" in context
    assert "transactions_df" not in context


def test_relevant_context_anomaly_agent_is_limited():
    context = get_relevant_context_for_agent(ANOMALY_AGENT, make_context())
    assert "anomaly_summary" in context
    assert "cashflow_summary" not in context


def test_relevant_context_planning_agent_is_limited():
    context = get_relevant_context_for_agent(PLANNING_AGENT, make_context())
    assert "goal_summary" in context
    assert "action_summary" in context


def test_build_specialist_agent_messages_returns_list_without_full_dataframe():
    messages = build_specialist_agent_messages(
        CASHFLOW_AGENT,
        "现金流安全吗？",
        manager_plan={"intent": "cashflow_check"},
        context_summary=make_context(),
    )
    joined = "\n".join(message["content"] for message in messages)
    assert isinstance(messages, list)
    assert "FULL_DATAFRAME_SHOULD_NOT_APPEAR" not in joined


def test_call_specialist_agent_api_disabled_returns_fallback(monkeypatch):
    monkeypatch.setenv("ENABLE_AGENT_API", "false")
    result = call_specialist_agent_api(CASHFLOW_AGENT, "现金流安全吗？")
    assert result["mode"] == "fallback"
    assert result["result"]["agent_name"] == CASHFLOW_AGENT


def test_call_specialist_agent_api_placeholder_key_returns_fallback(monkeypatch):
    monkeypatch.setenv("ENABLE_AGENT_API", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "your_api_key_here")
    result = call_specialist_agent_api(CASHFLOW_AGENT, "有哪些发票或付款要优先处理？")
    assert result["mode"] == "fallback"
    assert result["api_status"]["has_invalid_api_key"] is True
    assert "fallback" in result["errors"][0]


def test_call_selected_specialist_agents_returns_multiple_fallbacks(monkeypatch):
    monkeypatch.setenv("ENABLE_AGENT_API", "false")
    outputs = call_selected_specialist_agents(
        "现金流安全吗？",
        {"selected_agents": [CASHFLOW_AGENT, ANOMALY_AGENT]},
        context_summary=make_context(),
    )
    assert CASHFLOW_AGENT in outputs
    assert ANOMALY_AGENT in outputs
    assert "report_agent" in outputs


def test_build_specialist_agents_debug_info_returns_core_fields():
    debug = build_specialist_agents_debug_info(
        {
            CASHFLOW_AGENT: {"mode": "fallback", "errors": ["x"]},
            ANOMALY_AGENT: {"mode": "fallback", "errors": []},
        }
    )
    assert debug["agents_called"] == [CASHFLOW_AGENT, ANOMALY_AGENT]
    assert debug["modes"][CASHFLOW_AGENT] == "fallback"
    assert debug["errors"][CASHFLOW_AGENT] == ["x"]
