import pandas as pd

from agent.data_completeness import (
    check_base_data_availability,
    check_task_completeness,
    is_non_empty_dataframe,
)


def test_is_non_empty_dataframe():
    assert is_non_empty_dataframe(pd.DataFrame([{"amount": 1}]))
    assert not is_non_empty_dataframe(pd.DataFrame())
    assert not is_non_empty_dataframe(None)


def test_check_base_data_availability_returns_available_and_missing_items():
    context = {
        "transactions_df": pd.DataFrame([{"amount": 100}]),
        "budget_result": {"summary": {"net_cashflow": 100}},
    }

    result = check_base_data_availability(context)

    assert "available_items" in result
    assert "missing_items" in result
    assert "交易流水数据" in result["available_items"]
    assert "发票数据" in result["missing_items"]


def test_cashflow_task_completeness_has_status_and_questions():
    context = {
        "transactions_df": pd.DataFrame([{"amount": 100}]),
        "budget_result": {"summary": {}},
        "invoice_result": {"summary": {}},
        "cashflow_result": {"risk_level": "medium"},
    }

    result = check_task_completeness("cashflow_safety_check", context)

    assert result["status"] in {"complete", "partial", "missing"}
    assert result["clarifying_questions"]
    assert any("真实可用余额" in question for question in result["clarifying_questions"])


def test_missing_transactions_is_missing_or_partial():
    result = check_task_completeness("cashflow_safety_check", {})

    assert result["status"] in {"missing", "partial"}


def test_task_completeness_output_shape():
    result = check_task_completeness("goal_action_plan", {}, user_inputs={})

    assert {
        "status",
        "available_items",
        "missing_items",
        "provided_business_context",
        "clarifying_questions",
        "clarification_completion_ratio",
        "notes",
    }.issubset(result.keys())


def test_provided_business_context_removes_missing_question():
    result = check_task_completeness(
        "cashflow_safety_check",
        {"transactions_df": pd.DataFrame([{"amount": 100}])},
        user_inputs={"current_cash_balance": 5000},
    )

    assert "current_cash_balance" in result["provided_business_context"]
    assert "待补充：current_cash_balance" not in result["missing_items"]
    assert all("真实可用余额" not in question for question in result["clarifying_questions"])
    assert 0 <= result["clarification_completion_ratio"] <= 1
