import math

import pandas as pd


def compute_date_coverage_days(transactions_df) -> int:
    """
    Compute the number of days covered by transaction data.
    """
    if transactions_df is None or transactions_df.empty or "date" not in transactions_df.columns:
        return 30

    dates = pd.to_datetime(transactions_df["date"], errors="coerce").dropna()
    if dates.empty:
        return 30

    coverage_days = (dates.max() - dates.min()).days + 1
    return max(int(coverage_days), 1)


def compute_cashflow_basics(transactions_df) -> dict:
    """
    Compute core cashflow metrics from uploaded transactions.
    """
    if transactions_df is None or transactions_df.empty or "amount" not in transactions_df.columns:
        return {
            "current_balance_estimate": 0.0,
            "coverage_days": 30,
            "total_income": 0.0,
            "total_expense": 0.0,
            "avg_daily_income": 0.0,
            "avg_daily_expense": 0.0,
            "avg_daily_net_cashflow": 0.0,
        }

    amounts = pd.to_numeric(transactions_df["amount"], errors="coerce").fillna(0.0)
    coverage_days = compute_date_coverage_days(transactions_df)
    total_income = float(amounts[amounts > 0].sum())
    total_expense = float(amounts[amounts < 0].abs().sum())
    current_balance_estimate = float(amounts.sum())
    avg_daily_income = total_income / coverage_days
    avg_daily_expense = total_expense / coverage_days

    return {
        "current_balance_estimate": current_balance_estimate,
        "coverage_days": coverage_days,
        "total_income": total_income,
        "total_expense": total_expense,
        "avg_daily_income": avg_daily_income,
        "avg_daily_expense": avg_daily_expense,
        "avg_daily_net_cashflow": avg_daily_income - avg_daily_expense,
    }


def assess_cashflow_risk(
    current_balance_estimate,
    avg_daily_expense,
    projected_operating_cashflow_30d,
    upcoming_invoice_outflow_30d,
    projected_balance_30d,
) -> dict:
    """
    Assess cashflow risk using simple explainable rules.
    """
    if avg_daily_expense == 0:
        cash_buffer_days = math.inf
    else:
        cash_buffer_days = current_balance_estimate / avg_daily_expense

    risk_level = "low"
    risk_reasons = []

    if projected_balance_30d < 0:
        risk_level = "high"
        risk_reasons.append("Projected balance over the next 30 days is negative.")
    if cash_buffer_days < 7:
        risk_level = "high"
        risk_reasons.append("Current cash buffer is below 7 days.")

    if risk_level != "high":
        if cash_buffer_days < 30:
            risk_level = "medium"
            risk_reasons.append("Current cash buffer is below 30 days.")
        if (
            current_balance_estimate > 0
            and upcoming_invoice_outflow_30d > current_balance_estimate * 0.5
        ):
            risk_level = "medium"
            risk_reasons.append("Invoices due in the next 30 days exceed 50% of the current balance.")
        if projected_operating_cashflow_30d < 0:
            risk_level = "medium"
            risk_reasons.append("Recent average daily net cash flow is negative.")

    if not risk_reasons:
        risk_reasons.append("Based on the uploaded data, cash-flow pressure over the next 30 days appears low.")

    recommended_actions = [
        "Review invoices due in the next 30 days, especially overdue or large invoices.",
        "Check whether non-essential expenses can be delayed or optimized.",
        "Confirm expected collection dates from major customers.",
        "Reserve a cash buffer for fixed expenses and supplier payments.",
    ]

    return {
        "risk_level": risk_level,
        "risk_reasons": risk_reasons,
        "recommended_actions": recommended_actions,
        "cash_buffer_days": float(cash_buffer_days),
    }


def analyze_cashflow(transactions_df, invoice_result=None, horizon_days=30) -> dict:
    """
    Run cashflow analysis and return a single result dictionary.
    """
    basics = compute_cashflow_basics(transactions_df)
    invoice_result = invoice_result or {}
    invoice_summary = invoice_result.get("summary", {})
    upcoming_invoice_outflow = float(invoice_summary.get("due_30d_amount", 0.0))
    projected_operating_cashflow = basics["avg_daily_net_cashflow"] * horizon_days
    projected_balance = (
        basics["current_balance_estimate"]
        + projected_operating_cashflow
        - upcoming_invoice_outflow
    )
    risk_result = assess_cashflow_risk(
        current_balance_estimate=basics["current_balance_estimate"],
        avg_daily_expense=basics["avg_daily_expense"],
        projected_operating_cashflow_30d=projected_operating_cashflow,
        upcoming_invoice_outflow_30d=upcoming_invoice_outflow,
        projected_balance_30d=projected_balance,
    )

    return {
        **basics,
        "projected_operating_cashflow_30d": float(projected_operating_cashflow),
        "upcoming_invoice_outflow_30d": upcoming_invoice_outflow,
        "projected_balance_30d": float(projected_balance),
        "cash_buffer_days": risk_result["cash_buffer_days"],
        "risk_level": risk_result["risk_level"],
        "risk_reasons": risk_result["risk_reasons"],
        "recommended_actions": risk_result["recommended_actions"],
        "assumptions": [
            "Current balance estimate is based on uploaded transaction income minus expenses.",
            "Projected operating cash flow over 30 days is estimated from average daily net cash flow in the uploaded data.",
            "Cash-flow analysis is a demo-level estimate and does not represent a real bank balance or professional financial forecast.",
        ],
    }
