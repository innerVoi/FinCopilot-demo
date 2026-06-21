from ui.chat_page import build_placeholder_assistant_reply


def test_cashflow_query_returns_cashflow_reply():
    reply = build_placeholder_assistant_reply("未来 30 天现金流安全吗？")
    assert "现金流" in reply
    assert "Agent 工作台" in reply


def test_anomaly_query_returns_anomaly_reply():
    reply = build_placeholder_assistant_reply("这个月哪些支出最可疑？")
    assert "LOF" in reply
    assert "可疑" in reply or "支出" in reply


def test_goal_query_returns_planning_reply():
    reply = build_placeholder_assistant_reply("我能不能花 5000 做促销？")
    assert "目标" in reply
    assert "计划" in reply or "稳妥" in reply


def test_reply_contains_disclaimer():
    reply = build_placeholder_assistant_reply("帮我看看")
    assert "不构成投资、税务、法律、债务处置或专业财务建议" in reply


def test_empty_query_does_not_crash():
    reply = build_placeholder_assistant_reply("")
    assert "现金流" in reply
    assert "不构成投资" in reply


def test_render_chat_page_accepts_none_context():
    import inspect

    from ui.chat_page import render_chat_page

    assert "agent_context_summary" in inspect.signature(render_chat_page).parameters


def test_chat_page_has_turn_sync_helper():
    import inspect

    from ui.chat_page import sync_turn_outputs_to_chat_state

    assert "turn_result" in inspect.signature(sync_turn_outputs_to_chat_state).parameters
