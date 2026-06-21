import json

import pandas as pd

from agent_api.context_builder import (
    build_agent_context_summary,
    build_anomaly_summary,
    build_budget_summary,
    build_business_snapshot,
    build_cashflow_summary,
    build_goal_summary,
    build_invoice_summary,
    dataframe_top_records,
    is_non_empty_df,
    safe_float,
    safe_int,
    safe_str,
)


def test_safe_float_handles_common_values():
    assert safe_float(None) is None
    assert safe_float("2.5") == 2.5
    assert safe_float(3) == 3.0


def test_safe_int_handles_common_values():
    assert safe_int(None) == 0
    assert safe_int("2") == 2
    assert safe_int(3.0) == 3


def test_safe_str_handles_none():
    assert safe_str(None) == ""


def test_is_non_empty_df_detects_empty_and_non_empty():
    assert is_non_empty_df(pd.DataFrame()) is False
    assert is_non_empty_df(pd.DataFrame([{"a": 1}])) is True


def test_dataframe_top_records_returns_json_safe_dicts():
    df = pd.DataFrame([{"date": pd.Timestamp("2026-01-01"), "amount": 1.2, "x": None}])
    records = dataframe_top_records(df, columns=["date", "amount", "x"])
    assert records == [{"date": "2026-01-01T00:00:00", "amount": 1.2, "x": None}]


def test_build_business_snapshot_handles_empty_dataframe():
    snapshot = build_business_snapshot(pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    assert snapshot["transaction_count"] == 0
    assert snapshot["has_transactions"] is False


def test_build_summaries_handle_none_or_empty_dataframes():
    assert build_budget_summary(None)["total_income"] == 0.0
    assert build_invoice_summary(None)["overdue_invoice_count"] == 0
    assert build_cashflow_summary(None)["risk_level"] == "unknown"
    assert build_anomaly_summary(pd.DataFrame(), pd.DataFrame())["rule_anomaly_count"] == 0
    assert build_goal_summary(None)["goal_count"] == 0


def test_build_agent_context_summary_returns_complete_json_serializable_structure():
    context = {
        "transactions_df": pd.DataFrame(
            [{"date": pd.Timestamp("2026-06-01"), "amount": 100}]
        ),
        "invoices_df": pd.DataFrame([{"amount": 200}]),
        "goals_df": pd.DataFrame([{"goal_name": "buffer"}]),
        "budget_result": {"summary": {"total_income": 100, "total_expense": 20}},
        "invoice_result": {"summary": {"overdue_invoice_amount": 5}},
        "cashflow_result": {"risk_level": "medium", "projected_balance_30d": 80},
        "goal_result": {"summary": {"goal_count": 1}},
        "rule_anomalies_df": pd.DataFrame([{"merchant": "AWS", "amount": -10}]),
        "lof_result_df": pd.DataFrame([{"merchant": "Cloud", "risk_level": "high"}]),
        "workspace": {
            "action_summary": {"total": 1, "high": 1, "medium": 0, "low": 0},
            "ranked_action_items": [{"action_id": "A001", "title": "Check", "priority": "high"}],
            "progress_summary": {"total": 1, "active_count": 1},
            "workflow_report_markdown": "# Report",
        },
        "agent_state": {"business_context": {"current_cash_balance": 5000}},
    }
    summary = build_agent_context_summary(context)
    expected_keys = {
        "business_snapshot",
        "data_availability",
        "budget_summary",
        "invoice_summary",
        "cashflow_summary",
        "anomaly_summary",
        "goal_summary",
        "action_summary",
        "progress_summary",
        "report_summary",
        "business_context",
        "safety_context",
    }
    assert expected_keys.issubset(summary.keys())
    json.dumps(summary, ensure_ascii=False)
