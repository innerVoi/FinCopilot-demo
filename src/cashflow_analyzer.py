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
        risk_reasons.append("未来 30 天预计余额为负。")
    if cash_buffer_days < 7:
        risk_level = "high"
        risk_reasons.append("当前现金缓冲低于 7 天。")

    if risk_level != "high":
        if cash_buffer_days < 30:
            risk_level = "medium"
            risk_reasons.append("当前现金缓冲低于 30 天。")
        if (
            current_balance_estimate > 0
            and upcoming_invoice_outflow_30d > current_balance_estimate * 0.5
        ):
            risk_level = "medium"
            risk_reasons.append("未来 30 天待付发票金额超过当前余额的 50%。")
        if projected_operating_cashflow_30d < 0:
            risk_level = "medium"
            risk_reasons.append("近期平均日净现金流为负。")

    if not risk_reasons:
        risk_reasons.append("当前上传数据下，未来 30 天现金流压力较低。")

    recommended_actions = [
        "核查未来 30 天到期发票，优先确认逾期和大额发票。",
        "检查可推迟或可优化的非必要支出。",
        "确认主要客户回款时间，避免付款集中造成现金流压力。",
        "为固定支出和供应商付款预留现金缓冲。",
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
            "当前余额估算基于上传交易流水中的收入总额减支出总额。",
            "未来 30 天运营现金流基于当前数据覆盖期的平均日净现金流估算。",
            "现金流分析是 demo 级估算，不代表真实账户余额或专业财务预测。",
        ],
    }
