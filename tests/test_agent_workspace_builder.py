import pandas as pd

from agent.agent_state import update_action_status
from agent.workspace_builder import build_agent_workspace, summarize_tool_results


def make_context():
    return {
        "transactions_df": pd.DataFrame([{"amount": 100}, {"amount": -50}]),
        "invoices_df": pd.DataFrame([{"amount": 200}]),
        "goals_df": pd.DataFrame([{"target_amount": 1000, "current_amount": 300}]),
        "budget_result": {"summary": {"net_cashflow": 50}},
        "invoice_result": {"summary": {"overdue_invoice_amount": 100}},
        "cashflow_result": {
            "risk_level": "medium",
            "projected_balance_30d": 500.0,
            "upcoming_invoice_outflow_30d": 300.0,
            "cash_buffer_days": 12.0,
        },
        "goal_result": {
            "summary": {
                "goal_count": 2,
                "completed_goal_count": 0,
                "high_risk_goal_count": 1,
                "medium_risk_goal_count": 1,
                "overall_progress_percent": 30.0,
                "total_remaining_amount": 700.0,
            }
        },
        "rule_anomalies_df": pd.DataFrame(
            [{"merchant": "AWS", "amount": -620, "risk_level": "medium"}]
        ),
        "lof_result_df": pd.DataFrame(
            [{"merchant": "Vendor X", "amount": -2600, "risk_level": "high", "anomaly_score": 0.9}]
        ),
    }


def test_build_agent_workspace_output_shape():
    workspace = build_agent_workspace("cashflow_safety_check", make_context())

    assert {
        "task",
        "data_check",
        "clarification_status",
        "business_context",
        "tool_plan",
        "task_plan",
        "tool_execution",
        "tool_result_summary",
        "enriched_context",
        "context_impact_summary",
        "action_items",
        "ranked_action_items",
        "action_summary",
        "progress_summary",
        "progress_summary_text",
        "agent_progress_conclusion",
        "workflow_report_markdown",
        "initial_conclusion",
        "next_step_hint",
    }.issubset(workspace.keys())
    assert isinstance(workspace["action_items"], list)
    assert isinstance(workspace["ranked_action_items"], list)
    assert "total" in workspace["action_summary"]
    assert isinstance(workspace["workflow_report_markdown"], str)
    assert workspace["task"]["task_name"] in workspace["workflow_report_markdown"]
    assert "安全边界" in workspace["workflow_report_markdown"]


def test_cashflow_summary_contains_cashflow_fields():
    summary = summarize_tool_results("cashflow_safety_check", make_context())

    assert "cashflow_risk_level" in summary
    assert "projected_balance_30d" in summary


def test_suspicious_expense_summary_contains_anomaly_fields():
    summary = summarize_tool_results("suspicious_expense_review", make_context())

    assert summary["rule_anomaly_count"] == 1
    assert summary["lof_high_risk_count"] == 1


def test_goal_action_summary_contains_goal_fields():
    summary = summarize_tool_results("goal_action_plan", make_context())

    assert summary["goal_count"] == 2
    assert summary["high_risk_goal_count"] == 1


def test_empty_context_does_not_crash():
    workspace = build_agent_workspace("goal_action_plan", {})

    assert workspace["tool_result_summary"]["goal_count"] == 0
    assert isinstance(workspace["action_items"], list)
    assert workspace["action_summary"]["total"] >= 0
    assert isinstance(workspace["workflow_report_markdown"], str)
    assert workspace["initial_conclusion"]


def test_workspace_uses_user_inputs_for_context_impact():
    workspace = build_agent_workspace(
        "cashflow_safety_check",
        make_context(),
        user_inputs={
            "current_cash_balance": 5000,
            "expected_receivables_30d": 1000,
        },
    )

    assert workspace["business_context"]["current_cash_balance"] == 5000
    assert workspace["clarification_status"]["completion_ratio"] > 0
    assert workspace["enriched_context"]["enriched_cashflow_summary"][
        "adjusted_projected_balance_30d"
    ] != workspace["enriched_context"]["enriched_cashflow_summary"][
        "base_projected_balance_30d"
    ]
    assert "已使用用户补充" in workspace["context_impact_summary"]


def test_goal_action_plan_generates_goal_actions():
    context = make_context()
    context["goal_result"]["goals"] = pd.DataFrame(
        [
            {
                "goal_name": "30 天现金缓冲",
                "goal_risk_level": "high",
                "remaining_amount": 3000,
                "goal_recommendation": "目标存在达成风险。",
            }
        ]
    )

    workspace = build_agent_workspace("goal_action_plan", context)

    assert any(item["source"] == "goal" for item in workspace["action_items"])


def test_workspace_applies_saved_action_status():
    state = update_action_status(
        None,
        "cashflow_safety_check",
        "A001",
        "done",
        note="已处理。",
    )

    workspace = build_agent_workspace(
        "cashflow_safety_check",
        make_context(),
        agent_state=state,
    )

    assert "progress_summary" in workspace
    assert "progress_summary_text" in workspace
    assert "agent_progress_conclusion" in workspace
    first_action = next(
        item for item in workspace["ranked_action_items"] if item["action_id"] == "A001"
    )
    assert first_action["status"] == "done"
    assert first_action["note"] == "已处理。"
