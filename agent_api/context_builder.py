import math

import numpy as np
import pandas as pd


SUMMARY_KEYS = [
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
]


def _json_safe_value(value):
    if value is None:
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        value = float(value)
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if isinstance(value, np.bool_):
        return bool(value)
    if pd.isna(value):
        return None
    return value


def safe_float(value, default=None):
    """
    Safely convert a value to float.
    """
    try:
        if value is None or pd.isna(value):
            return default
        converted = float(value)
        if math.isnan(converted) or math.isinf(converted):
            return default
        return converted
    except (TypeError, ValueError):
        return default


def safe_int(value, default=0):
    """
    Safely convert a value to int.
    """
    try:
        if value is None or pd.isna(value):
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_str(value, default=""):
    """
    Safely convert a value to str.
    """
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass
    return str(value)


def is_non_empty_df(obj) -> bool:
    """
    Return True when obj is a non-empty DataFrame.
    """
    return isinstance(obj, pd.DataFrame) and not obj.empty


def dataframe_top_records(df, columns=None, n=5) -> list[dict]:
    """
    Convert top DataFrame records to JSON-serializable dicts.
    """
    if not is_non_empty_df(df):
        return []
    selected_columns = columns or list(df.columns)
    selected_columns = [column for column in selected_columns if column in df.columns]
    if not selected_columns:
        return []
    records = []
    for record in df.head(n)[selected_columns].to_dict(orient="records"):
        records.append({key: _json_safe_value(value) for key, value in record.items()})
    return records


def build_business_snapshot(transactions_df=None, invoices_df=None, goals_df=None) -> dict:
    """
    Build a compact business data snapshot.
    """
    date_min = None
    date_max = None
    if is_non_empty_df(transactions_df) and "date" in transactions_df.columns:
        date_min = _json_safe_value(transactions_df["date"].min())
        date_max = _json_safe_value(transactions_df["date"].max())
    return {
        "transaction_count": len(transactions_df) if isinstance(transactions_df, pd.DataFrame) else 0,
        "invoice_count": len(invoices_df) if isinstance(invoices_df, pd.DataFrame) else 0,
        "goal_count": len(goals_df) if isinstance(goals_df, pd.DataFrame) else 0,
        "date_min": date_min,
        "date_max": date_max,
        "has_transactions": is_non_empty_df(transactions_df),
        "has_invoices": is_non_empty_df(invoices_df),
        "has_goals": is_non_empty_df(goals_df),
    }


def build_data_availability(context: dict) -> dict:
    """
    Build a data availability summary.
    """
    context = context or {}
    checks = {
        "transactions_available": is_non_empty_df(context.get("transactions_df")),
        "invoices_available": is_non_empty_df(context.get("invoices_df")),
        "goals_available": is_non_empty_df(context.get("goals_df")),
        "budget_result_available": isinstance(context.get("budget_result"), dict),
        "invoice_result_available": isinstance(context.get("invoice_result"), dict),
        "cashflow_result_available": isinstance(context.get("cashflow_result"), dict),
        "goal_result_available": isinstance(context.get("goal_result"), dict),
        "rule_anomalies_available": isinstance(context.get("rule_anomalies_df"), pd.DataFrame),
        "lof_result_available": isinstance(context.get("lof_result_df"), pd.DataFrame),
        "workspace_available": isinstance(context.get("workspace"), dict) and bool(context.get("workspace")),
    }
    missing_items = [
        key.replace("_available", "")
        for key, available in checks.items()
        if not available
    ]
    checks["missing_items"] = missing_items
    return checks


def build_budget_summary(budget_result: dict | None) -> dict:
    """
    Build a budget summary.
    """
    budget_result = budget_result or {}
    summary = budget_result.get("summary", {}) if isinstance(budget_result, dict) else {}
    return {
        "total_income": safe_float(summary.get("total_income"), 0.0),
        "total_expense": safe_float(summary.get("total_expense"), 0.0),
        "net_cashflow": safe_float(summary.get("net_cashflow"), 0.0),
        "expense_income_ratio": safe_float(summary.get("expense_income_ratio")),
        "top_expense_category": summary.get("top_expense_category"),
        "largest_expense": safe_float(summary.get("largest_expense")),
        "fixed_expense_ratio": safe_float(summary.get("fixed_expense_ratio")),
        "category_spending_top": dataframe_top_records(
            budget_result.get("category_spending"),
            columns=["category", "expense_amount", "transaction_count", "expense_share"],
            n=5,
        ),
    }


def build_invoice_summary(invoice_result: dict | None) -> dict:
    """
    Build an invoice summary.
    """
    invoice_result = invoice_result or {}
    summary = invoice_result.get("summary", {}) if isinstance(invoice_result, dict) else {}
    return {
        "total_invoice_amount": safe_float(summary.get("total_invoice_amount"), 0.0),
        "paid_invoice_amount": safe_float(summary.get("paid_invoice_amount"), 0.0),
        "unpaid_invoice_amount": safe_float(summary.get("unpaid_invoice_amount"), 0.0),
        "overdue_invoice_amount": safe_float(summary.get("overdue_invoice_amount"), 0.0),
        "due_7d_amount": safe_float(summary.get("due_7d_amount"), 0.0),
        "due_30d_amount": safe_float(summary.get("due_30d_amount"), 0.0),
        "overdue_invoice_count": len(invoice_result.get("overdue", [])) if invoice_result.get("overdue") is not None else 0,
        "upcoming_invoice_count": len(invoice_result.get("upcoming_30d", [])) if invoice_result.get("upcoming_30d") is not None else 0,
    }


def build_cashflow_summary(cashflow_result: dict | None, workspace: dict | None = None) -> dict:
    """
    Build a cashflow summary, including enriched cashflow when available.
    """
    cashflow_result = cashflow_result or {}
    workspace = workspace or {}
    enriched_cashflow = (
        workspace.get("enriched_context", {}).get("enriched_cashflow_summary", {})
        if isinstance(workspace, dict)
        else {}
    )
    summary = {
        "risk_level": cashflow_result.get("risk_level", "unknown"),
        "current_balance_estimate": safe_float(cashflow_result.get("current_balance_estimate")),
        "projected_operating_cashflow_30d": safe_float(cashflow_result.get("projected_operating_cashflow_30d")),
        "upcoming_invoice_outflow_30d": safe_float(cashflow_result.get("upcoming_invoice_outflow_30d")),
        "projected_balance_30d": safe_float(cashflow_result.get("projected_balance_30d")),
        "cash_buffer_days": safe_float(cashflow_result.get("cash_buffer_days")),
        "risk_reasons": [safe_str(item) for item in cashflow_result.get("risk_reasons", [])],
        "recommended_actions": [safe_str(item) for item in cashflow_result.get("recommended_actions", [])],
    }
    if enriched_cashflow:
        summary.update(
            {
                "adjusted_risk_level": enriched_cashflow.get("adjusted_risk_level", "unknown"),
                "adjusted_projected_balance_30d": safe_float(
                    enriched_cashflow.get("adjusted_projected_balance_30d")
                ),
                "adjustment_reasons": [
                    safe_str(item)
                    for item in enriched_cashflow.get("adjustment_reasons", [])
                ],
            }
        )
    return summary


def build_anomaly_summary(rule_anomalies_df=None, lof_result_df=None, max_records=5) -> dict:
    """
    Build an anomaly summary.
    """
    model_high = 0
    model_medium = 0
    if is_non_empty_df(lof_result_df) and "risk_level" in lof_result_df.columns:
        model_high = int((lof_result_df["risk_level"] == "high").sum())
        model_medium = int((lof_result_df["risk_level"] == "medium").sum())

    anomaly_columns = [
        "date",
        "merchant",
        "amount",
        "category",
        "risk_level",
        "anomaly_type",
        "reason",
    ]
    model_columns = anomaly_columns + ["anomaly_score", "model_evidence"]
    top_model_df = lof_result_df
    if is_non_empty_df(lof_result_df) and "risk_level" in lof_result_df.columns:
        risky_df = lof_result_df[lof_result_df["risk_level"].isin(["high", "medium"])]
        top_model_df = risky_df if not risky_df.empty else lof_result_df

    return {
        "rule_anomaly_count": len(rule_anomalies_df) if isinstance(rule_anomalies_df, pd.DataFrame) else 0,
        "model_high_risk_count": model_high,
        "model_medium_risk_count": model_medium,
        "top_rule_anomalies": dataframe_top_records(rule_anomalies_df, anomaly_columns, max_records),
        "top_model_anomalies": dataframe_top_records(top_model_df, model_columns, max_records),
    }


def build_goal_summary(goal_result: dict | None, max_records=5) -> dict:
    """
    Build a goal summary.
    """
    goal_result = goal_result or {}
    summary = goal_result.get("summary", {}) if isinstance(goal_result, dict) else {}
    goals_df = goal_result.get("goals") if isinstance(goal_result, dict) else None
    top_risk_goals = goals_df
    if is_non_empty_df(goals_df) and "goal_risk_level" in goals_df.columns:
        risky_goals = goals_df[goals_df["goal_risk_level"].isin(["high", "medium"])]
        top_risk_goals = risky_goals if not risky_goals.empty else goals_df
    return {
        "goal_count": safe_int(summary.get("goal_count"), 0),
        "completed_goal_count": safe_int(summary.get("completed_goal_count"), 0),
        "high_risk_goal_count": safe_int(summary.get("high_risk_goal_count"), 0),
        "medium_risk_goal_count": safe_int(summary.get("medium_risk_goal_count"), 0),
        "overall_progress_percent": safe_float(summary.get("overall_progress_percent")),
        "total_remaining_amount": safe_float(summary.get("total_remaining_amount")),
        "top_risk_goals": dataframe_top_records(
            top_risk_goals,
            columns=[
                "goal_id",
                "goal_name",
                "priority",
                "remaining_amount",
                "progress_percent",
                "goal_risk_level",
                "goal_status",
                "goal_recommendation",
            ],
            n=max_records,
        ),
    }


def build_action_summary(workspace: dict | None, max_records=5) -> dict:
    """
    Build an action item summary.
    """
    workspace = workspace or {}
    action_summary = workspace.get("action_summary", {})
    top_actions = []
    for item in (workspace.get("ranked_action_items", []) or [])[:max_records]:
        top_actions.append(
            {
                "action_id": item.get("action_id"),
                "title": item.get("title"),
                "priority": item.get("priority"),
                "source": item.get("source"),
                "status": item.get("status"),
                "reason": item.get("reason"),
                "suggested_deadline": item.get("suggested_deadline"),
            }
        )
    return {
        "total": safe_int(action_summary.get("total"), 0),
        "high": safe_int(action_summary.get("high"), 0),
        "medium": safe_int(action_summary.get("medium"), 0),
        "low": safe_int(action_summary.get("low"), 0),
        "by_source": action_summary.get("by_source", {}) if isinstance(action_summary.get("by_source", {}), dict) else {},
        "top_actions": top_actions,
    }


def build_progress_summary_from_workspace(workspace: dict | None) -> dict:
    """
    Build a progress summary from workspace.
    """
    progress_summary = (workspace or {}).get("progress_summary", {})
    return {
        "total": safe_int(progress_summary.get("total"), 0),
        "active_count": safe_int(progress_summary.get("active_count"), 0),
        "closed_count": safe_int(progress_summary.get("closed_count"), 0),
        "completion_rate": safe_float(progress_summary.get("completion_rate"), 0.0),
        "high_priority_active_count": safe_int(progress_summary.get("high_priority_active_count"), 0),
        "pending": safe_int(progress_summary.get("pending"), 0),
        "in_progress": safe_int(progress_summary.get("in_progress"), 0),
        "needs_follow_up": safe_int(progress_summary.get("needs_follow_up"), 0),
        "done": safe_int(progress_summary.get("done"), 0),
        "ignored": safe_int(progress_summary.get("ignored"), 0),
        "verified_normal": safe_int(progress_summary.get("verified_normal"), 0),
    }


def build_report_summary(workspace: dict | None) -> dict:
    """
    Build a workflow report summary.
    """
    report = (workspace or {}).get("workflow_report_markdown", "") or ""
    return {
        "has_workflow_report": bool(report),
        "report_length": len(report),
        "report_preview": report[:500],
    }


def build_business_context_summary(agent_state: dict | None) -> dict:
    """
    Extract non-empty business context from agent_state.
    """
    business_context = (agent_state or {}).get("business_context", {})
    allowed_fields = [
        "current_cash_balance",
        "expected_receivables_30d",
        "unuploaded_invoices_estimate",
        "large_upcoming_payments",
        "known_authorized_large_payments",
        "recurring_vendor_list",
        "business_context_for_top_anomalies",
        "goal_priority_confirmation",
        "expected_monthly_savings_capacity",
        "business_notes",
    ]
    result = {}
    for field in allowed_fields:
        value = business_context.get(field)
        if value not in [None, "", 0, 0.0, [], {}]:
            result[field] = _json_safe_value(value)
    return result


def build_safety_context() -> dict:
    """
    Build the fixed safety boundary context.
    """
    return {
        "no_investment_advice": True,
        "no_tax_advice": True,
        "no_legal_advice": True,
        "no_debt_advice": True,
        "no_fraud_determination": True,
        "no_payment_execution": True,
        "financial_disclaimer_required": True,
    }


def build_agent_context_summary(context: dict) -> dict:
    """
    Build the unified LLM-safe Agent context summary.
    """
    context = context or {}
    summary = {
        "business_snapshot": build_business_snapshot(
            context.get("transactions_df"),
            context.get("invoices_df"),
            context.get("goals_df"),
        ),
        "data_availability": build_data_availability(context),
        "budget_summary": build_budget_summary(context.get("budget_result")),
        "invoice_summary": build_invoice_summary(context.get("invoice_result")),
        "cashflow_summary": build_cashflow_summary(
            context.get("cashflow_result"),
            context.get("workspace"),
        ),
        "anomaly_summary": build_anomaly_summary(
            context.get("rule_anomalies_df"),
            context.get("lof_result_df"),
        ),
        "goal_summary": build_goal_summary(context.get("goal_result")),
        "action_summary": build_action_summary(context.get("workspace")),
        "progress_summary": build_progress_summary_from_workspace(context.get("workspace")),
        "report_summary": build_report_summary(context.get("workspace")),
        "business_context": build_business_context_summary(context.get("agent_state")),
        "safety_context": build_safety_context(),
    }
    return {key: summary.get(key) for key in SUMMARY_KEYS}
