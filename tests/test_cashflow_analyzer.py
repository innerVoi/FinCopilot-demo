import pandas as pd

from src.cashflow_analyzer import (
    analyze_cashflow,
    assess_cashflow_risk,
    compute_cashflow_basics,
    compute_date_coverage_days,
)


def test_compute_date_coverage_days():
    transactions_df = pd.DataFrame(
        [
            {"date": "2026-06-01", "amount": 1000},
            {"date": "2026-06-05", "amount": -400},
        ]
    )

    assert compute_date_coverage_days(transactions_df) == 5


def test_compute_cashflow_basics():
    transactions_df = pd.DataFrame(
        [
            {"date": "2026-06-01", "amount": 1000},
            {"date": "2026-06-02", "amount": -400},
        ]
    )

    result = compute_cashflow_basics(transactions_df)

    assert result["current_balance_estimate"] == 600
    assert result["total_income"] == 1000
    assert result["total_expense"] == 400


def test_assess_cashflow_high_risk():
    result = assess_cashflow_risk(
        current_balance_estimate=100,
        avg_daily_expense=20,
        projected_operating_cashflow_30d=-200,
        upcoming_invoice_outflow_30d=200,
        projected_balance_30d=-300,
    )

    assert result["risk_level"] == "high"


def test_assess_cashflow_medium_risk():
    result = assess_cashflow_risk(
        current_balance_estimate=1000,
        avg_daily_expense=50,
        projected_operating_cashflow_30d=100,
        upcoming_invoice_outflow_30d=600,
        projected_balance_30d=500,
    )

    assert result["risk_level"] == "medium"


def test_analyze_cashflow_output_fields():
    transactions_df = pd.DataFrame(
        [
            {"date": "2026-06-01", "amount": 1000},
            {"date": "2026-06-02", "amount": -400},
        ]
    )
    invoice_result = {"summary": {"due_30d_amount": 200.0}}

    result = analyze_cashflow(transactions_df, invoice_result=invoice_result)

    expected_keys = {
        "current_balance_estimate",
        "coverage_days",
        "avg_daily_income",
        "avg_daily_expense",
        "avg_daily_net_cashflow",
        "projected_operating_cashflow_30d",
        "upcoming_invoice_outflow_30d",
        "projected_balance_30d",
        "cash_buffer_days",
        "risk_level",
        "risk_reasons",
        "recommended_actions",
        "assumptions",
    }
    assert expected_keys.issubset(result.keys())
