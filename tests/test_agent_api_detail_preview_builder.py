from agent_api.detail_preview_builder import (
    build_action_preview,
    build_agent_preview,
    build_anomaly_preview,
    build_cashflow_preview,
    build_data_overview,
    build_detail_navigation,
    build_detail_preview,
    build_goal_preview,
    build_invoice_preview,
    build_report_preview,
    build_tool_preview,
    build_trace_preview,
    ensure_list,
    find_tool_result,
    get_specialist_result,
    safe_get,
)


def make_context_summary():
    return {
        "business_snapshot": {
            "transaction_count": 12,
            "invoice_count": 3,
            "goal_count": 2,
            "date_min": "2026-06-01",
            "date_max": "2026-06-30",
        },
        "data_availability": {"missing_items": ["goals_df"]},
        "cashflow_summary": {
            "risk_level": "medium",
            "projected_balance_30d": 1200.0,
            "cash_buffer_days": 14,
            "risk_reasons": ["大额付款集中"],
            "recommended_actions": ["确认账户余额"],
        },
        "invoice_summary": {
            "total_invoice_amount": 10000.0,
            "unpaid_invoice_amount": 5000.0,
            "overdue_invoice_amount": 700.0,
            "due_7d_amount": 900.0,
            "due_30d_amount": 3000.0,
            "overdue_invoice_count": 1,
        },
        "anomaly_summary": {
            "rule_anomaly_count": 2,
            "model_high_risk_count": 1,
            "model_medium_risk_count": 1,
            "top_rule_anomalies": [{"merchant": "Cloud", "amount": -900}],
            "top_model_anomalies": [{"merchant": "Ads", "risk_level": "high"}],
        },
        "goal_summary": {
            "goal_count": 2,
            "high_risk_goal_count": 1,
            "medium_risk_goal_count": 1,
            "overall_progress_percent": 45.0,
            "top_risk_goals": [{"goal_name": "现金缓冲", "goal_risk_level": "high"}],
        },
        "action_summary": {
            "top_actions": [{"action_id": "A001", "title": "核查大额付款", "priority": "high"}]
        },
    }


def make_turn_result():
    return {
        "mode": "fallback",
        "manager_plan": {
            "intent": "expense_anomaly_review",
            "selected_agents": ["anomaly_agent"],
        },
        "tool_results": [
            {
                "tool_name": "get_anomaly_summary",
                "status": "success",
                "result": {"rule_anomaly_count": 3},
            },
            {
                "tool_name": "get_cashflow_summary",
                "status": "failed",
                "error": "missing context",
            },
        ],
        "tool_trace": {
            "total": 2,
            "success": 1,
            "failed": 1,
            "tools_called": ["get_anomaly_summary", "get_cashflow_summary"],
        },
        "specialist_outputs": {
            "anomaly_agent": {
                "mode": "fallback",
                "result": {
                    "summary": "异常支出摘要已生成",
                    "risks": ["大额支出需要业务背景"],
                },
            }
        },
        "chat_action_items": [
            {
                "action_id": "C001",
                "title": "核查高风险交易",
                "priority": "high",
                "status": "pending",
                "suggested_deadline": "今天",
                "source": "agent_chat",
            }
        ],
        "report_markdown": "# FinCopilot Report\n\n报告正文",
        "trace_markdown": "# Trace",
        "safety_result": {"safe": True, "risks": []},
        "trace": {"mode": "fallback"},
    }


def test_safe_get_handles_none():
    assert safe_get(None, "x", "fallback") == "fallback"


def test_ensure_list_handles_common_values():
    assert ensure_list(None) == []
    assert ensure_list("x") == ["x"]
    assert ensure_list(["x"]) == ["x"]


def test_find_tool_result_finds_named_tool():
    result = find_tool_result(make_turn_result()["tool_results"], "get_anomaly_summary")
    assert result["status"] == "success"


def test_find_tool_result_missing_returns_none():
    assert find_tool_result(make_turn_result()["tool_results"], "missing") is None


def test_get_specialist_result_supports_wrapped_and_direct_payloads():
    wrapped = get_specialist_result(make_turn_result()["specialist_outputs"], "anomaly_agent")
    direct = get_specialist_result({"x_agent": {"summary": "direct"}}, "x_agent")
    assert wrapped["summary"]
    assert direct["summary"] == "direct"


def test_build_data_overview_handles_empty_context():
    overview = build_data_overview(None)
    assert overview["transaction_count"] == 0


def test_build_cashflow_preview_handles_empty_turn_result():
    preview = build_cashflow_preview(None)
    assert preview["risk_level"] == "unknown"


def test_build_invoice_preview_handles_empty_turn_result():
    preview = build_invoice_preview(None)
    assert preview["unpaid_invoice_amount"] == 0.0


def test_build_anomaly_preview_extracts_anomaly_summary():
    preview = build_anomaly_preview(make_turn_result(), make_context_summary())
    assert preview["rule_anomaly_count"] == 3
    assert preview["agent_summary"] == "异常支出摘要已生成"


def test_build_goal_preview_handles_empty_context():
    preview = build_goal_preview(None)
    assert preview["goal_count"] == 0


def test_build_action_preview_extracts_chat_action_items():
    preview = build_action_preview(make_turn_result(), make_context_summary())
    assert preview["total"] == 1
    assert preview["items"][0]["action_id"] == "C001"


def test_build_report_preview_detects_report_markdown():
    preview = build_report_preview(make_turn_result())
    assert preview["has_report"] is True
    assert preview["report_length"] > 0


def test_build_trace_preview_extracts_mode_and_intent():
    preview = build_trace_preview(make_turn_result())
    assert preview["mode"] == "fallback"
    assert preview["intent"] == "expense_anomaly_review"


def test_build_tool_preview_summarizes_tool_results():
    preview = build_tool_preview(make_turn_result())
    assert preview["total"] == 2
    assert preview["success"] == 1
    assert preview["failed"] == 1


def test_build_agent_preview_extracts_selected_agents():
    preview = build_agent_preview(make_turn_result())
    assert preview["selected_agents"] == ["anomaly_agent"]
    assert preview["specialist_summaries"][0]["agent_name"] == "anomaly_agent"


def test_build_detail_navigation_uses_intent():
    navigation = build_detail_navigation(make_turn_result())
    assert any(item["section"] == "异常支出" for item in navigation)


def test_build_detail_navigation_does_not_return_legacy_pages():
    legacy_pages = {"财务分析", "Agent 工作台", "行动中心", "报告中心", "数据管理"}
    navigation = build_detail_navigation(make_turn_result())
    assert not legacy_pages.intersection({item["page"] for item in navigation})


def test_build_detail_preview_returns_complete_structure():
    preview = build_detail_preview(make_turn_result(), make_context_summary())
    expected_keys = {
        "data_overview",
        "cashflow_preview",
        "invoice_preview",
        "anomaly_preview",
        "goal_preview",
        "action_preview",
        "report_preview",
        "trace_preview",
        "tool_preview",
        "agent_preview",
        "detail_navigation",
        "safety_note",
    }
    assert expected_keys.issubset(preview)
