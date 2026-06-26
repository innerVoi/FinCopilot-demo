import pandas as pd

from agent.clarification import is_value_provided


def _to_float(value, default=0.0):
    if not is_value_provided(value):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _count_risk(df, level):
    if df is None or getattr(df, "empty", True) or "risk_level" not in df.columns:
        return 0
    return int((df["risk_level"] == level).sum())


def _provided_context(business_context):
    return {
        key: value
        for key, value in (business_context or {}).items()
        if is_value_provided(value)
    }


def enrich_cashflow_summary(
    cashflow_result: dict | None,
    business_context: dict | None,
) -> dict:
    """
    Use user-provided context to build an adjusted cashflow summary.
    """
    cashflow = cashflow_result or {}
    context = business_context or {}
    base_projected_balance = _to_float(cashflow.get("projected_balance_30d"))
    upcoming_invoice_outflow = _to_float(cashflow.get("upcoming_invoice_outflow_30d"))
    projected_operating_cashflow = _to_float(
        cashflow.get("projected_operating_cashflow_30d")
    )
    current_cash_balance = context.get("current_cash_balance")
    expected_receivables = _to_float(context.get("expected_receivables_30d"))
    unuploaded_invoices = _to_float(context.get("unuploaded_invoices_estimate"))
    large_upcoming_payments = _to_float(context.get("large_upcoming_payments"))
    adjustment_reasons = []
    notes = []

    if is_value_provided(current_cash_balance):
        adjusted_projected_balance = (
            _to_float(current_cash_balance)
            + expected_receivables
            + projected_operating_cashflow
            - upcoming_invoice_outflow
            - unuploaded_invoices
            - large_upcoming_payments
        )
        adjustment_reasons.append("Adjusted the cash-flow view using the user-provided real account balance.")
    else:
        adjusted_projected_balance = base_projected_balance
        notes.append("Balance is still estimated from uploaded transactions; real account balance was not used.")

    if expected_receivables:
        adjustment_reasons.append("Included expected customer collections over the next 30 days.")
    if unuploaded_invoices:
        adjustment_reasons.append("Deducted estimated unuploaded invoices or fixed expenses.")
    if large_upcoming_payments:
        adjustment_reasons.append("Deducted required large payments over the next 30 days.")

    if adjusted_projected_balance < 0:
        adjusted_risk_level = "high"
    elif (
        upcoming_invoice_outflow > 0
        and adjusted_projected_balance < upcoming_invoice_outflow * 0.5
    ) or unuploaded_invoices > max(upcoming_invoice_outflow * 0.5, 1000.0):
        adjusted_risk_level = "medium"
    else:
        adjusted_risk_level = "low"

    if not adjustment_reasons:
        adjustment_reasons.append("No business context has been provided yet to adjust the cash-flow view.")

    return {
        "base_risk_level": cashflow.get("risk_level", "unknown"),
        "adjusted_risk_level": adjusted_risk_level,
        "base_projected_balance_30d": base_projected_balance,
        "adjusted_projected_balance_30d": adjusted_projected_balance,
        "projected_operating_cashflow_30d": projected_operating_cashflow,
        "upcoming_invoice_outflow_30d": upcoming_invoice_outflow,
        "adjustment_reasons": adjustment_reasons,
        "notes": notes,
    }


def enrich_anomaly_summary(
    rule_anomalies_df=None,
    lof_result_df=None,
    business_context: dict | None = None,
) -> dict:
    """
    Use business context to supplement anomaly analysis.
    """
    context = business_context or {}
    notes = []
    if is_value_provided(context.get("known_authorized_large_payments")):
        notes.append("The user provided known normal large-payment context; some high-risk transactions should be reviewed with that context.")
    if is_value_provided(context.get("recurring_vendor_list")):
        notes.append("The user provided regular supplier or recurring merchant information; unfamiliar merchants should be prioritized for review.")
    if is_value_provided(context.get("business_context_for_top_anomalies")):
        notes.append("The user added business context for high-risk transactions; future action items should prioritize records that remain unexplained.")
    if not notes:
        notes.append("Current anomaly judgment is mainly based on rule and model results, without additional business context yet.")

    return {
        "rule_anomaly_count": 0
        if rule_anomalies_df is None or getattr(rule_anomalies_df, "empty", True)
        else int(len(rule_anomalies_df)),
        "lof_result_count": 0
        if lof_result_df is None or getattr(lof_result_df, "empty", True)
        else int(len(lof_result_df)),
        "high_risk_count": _count_risk(rule_anomalies_df, "high")
        + _count_risk(lof_result_df, "high"),
        "medium_risk_count": _count_risk(rule_anomalies_df, "medium")
        + _count_risk(lof_result_df, "medium"),
        "business_context_notes": notes,
    }


def enrich_goal_summary(
    goal_result: dict | None,
    business_context: dict | None,
) -> dict:
    """
    Use business context to supplement goal analysis.
    """
    result = goal_result or {}
    context = business_context or {}
    summary = result.get("summary", {}) if isinstance(result, dict) else {}
    goals_df = result.get("goals") if isinstance(result, dict) else None
    notes = []
    expected_capacity = _to_float(context.get("expected_monthly_savings_capacity"))

    if is_value_provided(context.get("goal_priority_confirmation")):
        notes.append(f"The user confirmed the highest-priority goal: {context.get('goal_priority_confirmation')}.")
    if is_value_provided(context.get("current_cash_balance")):
        notes.append("The user added the real cash balance currently available for goal reserves.")
    if expected_capacity:
        notes.append(f"The user expects {expected_capacity:.2f} to be available each month for reserves or goal contributions.")

    required_saving = None
    if isinstance(goals_df, pd.DataFrame) and not goals_df.empty:
        high_risk_goals = goals_df
        if "goal_risk_level" in goals_df.columns:
            high_risk_goals = goals_df[goals_df["goal_risk_level"] == "high"]
        if not high_risk_goals.empty and "required_monthly_saving" in high_risk_goals.columns:
            required_saving = float(
                pd.to_numeric(
                    high_risk_goals["required_monthly_saving"],
                    errors="coerce",
                )
                .fillna(0.0)
                .max()
            )
            if expected_capacity and expected_capacity < required_saving:
                notes.append("Based on the user-provided monthly reserve capacity, some goals may need adjusted timelines or priorities.")

    if not notes:
        notes.append("Current goal analysis is mainly based on uploaded goals.csv and budget results, without user-confirmed goal priority yet.")

    return {
        "goal_count": summary.get("goal_count", 0),
        "high_risk_goal_count": summary.get("high_risk_goal_count", 0),
        "overall_progress_percent": summary.get("overall_progress_percent", 0.0),
        "goal_priority_confirmation": context.get("goal_priority_confirmation", ""),
        "expected_monthly_savings_capacity": expected_capacity,
        "max_high_risk_required_monthly_saving": required_saving,
        "business_context_notes": notes,
    }


def enrich_agent_context(
    task_id: str,
    context: dict,
    business_context: dict | None = None,
) -> dict:
    """
    Build enriched summaries for the selected Agent task.
    """
    context = context or {}
    business_context = business_context or {}
    return {
        "enriched_cashflow_summary": enrich_cashflow_summary(
            context.get("cashflow_result"),
            business_context,
        ),
        "enriched_anomaly_summary": enrich_anomaly_summary(
            rule_anomalies_df=context.get("rule_anomalies_df"),
            lof_result_df=context.get("lof_result_df"),
            business_context=business_context,
        ),
        "enriched_goal_summary": enrich_goal_summary(
            context.get("goal_result"),
            business_context,
        ),
        "business_context_used": _provided_context(business_context),
        "task_id": task_id,
    }
