import pandas as pd

from src.budget_analyzer import (
    analyze_budget,
    compute_budget_summary,
    compute_category_spending,
)


def make_transactions_df():
    return pd.DataFrame(
        [
            {"date": "2026-06-01", "month": "2026-06", "amount": 1000, "category": "salary"},
            {
                "date": "2026-06-02",
                "month": "2026-06",
                "amount": 500,
                "category": "client_payment",
            },
            {"date": "2026-06-03", "month": "2026-06", "amount": -400, "category": "rent"},
            {"date": "2026-06-04", "month": "2026-06", "amount": -100, "category": "food"},
            {
                "date": "2026-06-05",
                "month": "2026-06",
                "amount": -50,
                "category": "subscription",
            },
        ]
    )


def test_budget_summary_core_metrics():
    summary = compute_budget_summary(make_transactions_df())

    assert summary["total_income"] == 1500
    assert summary["total_expense"] == 550
    assert summary["net_cashflow"] == 950
    assert 0 <= summary["fixed_expense_ratio"] <= 1


def test_category_spending_has_expected_columns():
    category_spending = compute_category_spending(make_transactions_df())

    assert {"category", "expense_amount"}.issubset(category_spending.columns)
    assert category_spending["expense_amount"].sum() == 550


def test_analyze_budget_returns_monthly_summary():
    result = analyze_budget(make_transactions_df())

    assert "monthly_summary" in result
    assert result["monthly_summary"].loc[0, "net_cashflow"] == 950
