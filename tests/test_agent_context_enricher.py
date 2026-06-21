import pandas as pd

from agent.context_enricher import (
    enrich_agent_context,
    enrich_anomaly_summary,
    enrich_cashflow_summary,
    enrich_goal_summary,
)


def make_cashflow_result():
    return {
        "risk_level": "medium",
        "projected_balance_30d": 1000.0,
        "projected_operating_cashflow_30d": 500.0,
        "upcoming_invoice_outflow_30d": 700.0,
    }


def test_enrich_cashflow_summary_without_context_does_not_crash():
    summary = enrich_cashflow_summary(make_cashflow_result(), None)

    assert "adjusted_projected_balance_30d" in summary
    assert summary["adjusted_risk_level"] in {"low", "medium", "high"}


def test_enrich_cashflow_summary_uses_current_cash_balance():
    summary = enrich_cashflow_summary(
        make_cashflow_result(),
        {
            "current_cash_balance": 5000,
            "expected_receivables_30d": 1000,
            "unuploaded_invoices_estimate": 300,
            "large_upcoming_payments": 200,
        },
    )

    assert summary["adjusted_projected_balance_30d"] == 5300.0
    assert summary["adjusted_risk_level"] in {"low", "medium", "high"}


def test_enrich_anomaly_summary_handles_empty_dataframes():
    summary = enrich_anomaly_summary(
        pd.DataFrame(),
        pd.DataFrame(),
        {"recurring_vendor_list": "AWS, Stripe"},
    )

    assert summary["rule_anomaly_count"] == 0
    assert summary["business_context_notes"]


def test_enrich_goal_summary_handles_empty_goal_result():
    summary = enrich_goal_summary(None, None)

    assert summary["goal_count"] == 0
    assert summary["business_context_notes"]


def test_enrich_agent_context_returns_all_summaries():
    context = {
        "cashflow_result": make_cashflow_result(),
        "rule_anomalies_df": pd.DataFrame(),
        "lof_result_df": pd.DataFrame(),
        "goal_result": {},
    }

    enriched = enrich_agent_context(
        "cashflow_safety_check",
        context,
        {"current_cash_balance": 5000},
    )

    assert "enriched_cashflow_summary" in enriched
    assert "enriched_anomaly_summary" in enriched
    assert "enriched_goal_summary" in enriched
    assert enriched["business_context_used"]["current_cash_balance"] == 5000
