import pytest

from agent.task_planner import create_task_plan, get_default_tool_sequence


def make_data_check(status="ready"):
    return {
        "status": status,
        "clarifying_questions": ["请确认当前账户余额。"],
    }


def test_default_sequences_cover_three_tasks():
    assert "analyze_cashflow" in get_default_tool_sequence("cashflow_safety_check")
    assert "detect_rule_anomalies" in get_default_tool_sequence(
        "suspicious_expense_review"
    )
    assert "detect_lof_anomalies" in get_default_tool_sequence(
        "suspicious_expense_review"
    )
    assert "analyze_goals" in get_default_tool_sequence("goal_action_plan")


def test_get_default_tool_sequence_rejects_unknown_task():
    with pytest.raises(ValueError):
        get_default_tool_sequence("unknown_task")


def test_create_task_plan_returns_structured_plan():
    plan = create_task_plan("cashflow_safety_check", data_check=make_data_check())

    assert plan["task_id"] == "cashflow_safety_check"
    assert plan["plan_status"] == "ready"
    assert plan["missing_tools"] == []
    assert plan["tool_steps"]
    assert plan["tool_steps"][0]["step_id"] == "step_1"


def test_create_task_plan_marks_partial_data_for_clarification():
    plan = create_task_plan("goal_action_plan", data_check=make_data_check("partial"))

    assert plan["plan_status"] == "needs_clarification"
    assert plan["clarifying_questions"] == ["请确认当前账户余额。"]


def test_create_task_plan_marks_missing_data_blocked():
    plan = create_task_plan("suspicious_expense_review", data_check=make_data_check("missing"))

    assert plan["plan_status"] == "blocked"
