from agent.clarification import (
    assess_clarification_status,
    build_clarification_panel_data,
    get_clarification_schema,
    get_questions_for_task,
    is_value_provided,
)


def test_get_clarification_schema_returns_non_empty_list():
    schema = get_clarification_schema()

    assert isinstance(schema, list)
    assert schema


def test_get_questions_for_task_returns_questions_for_each_task():
    assert get_questions_for_task("cashflow_safety_check")
    assert get_questions_for_task("suspicious_expense_review")
    assert get_questions_for_task("goal_action_plan")


def test_is_value_provided_handles_empty_and_valid_values():
    assert not is_value_provided(None)
    assert not is_value_provided("")
    assert not is_value_provided("   ")
    assert not is_value_provided(0)
    assert is_value_provided("AWS")
    assert is_value_provided(5000)


def test_assess_clarification_status_reports_fields_and_ratio():
    status = assess_clarification_status(
        "cashflow_safety_check",
        {"current_cash_balance": 5000},
    )

    assert "current_cash_balance" in status["provided_fields"]
    assert "current_cash_balance" not in status["missing_fields"]
    assert 0 <= status["completion_ratio"] <= 1


def test_build_clarification_panel_data_returns_status():
    panel = build_clarification_panel_data(
        "suspicious_expense_review",
        {"recurring_vendor_list": "AWS"},
    )

    assert panel["task_id"] == "suspicious_expense_review"
    assert panel["questions"]
    assert "status" in panel
