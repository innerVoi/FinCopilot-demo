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
        adjustment_reasons.append("已使用用户补充的真实账户余额修正现金流视图。")
    else:
        adjusted_projected_balance = base_projected_balance
        notes.append("当前仍基于上传流水估算余额，未使用真实账户余额。")

    if expected_receivables:
        adjustment_reasons.append("已计入未来 30 天预计客户回款。")
    if unuploaded_invoices:
        adjustment_reasons.append("已扣除未上传发票或固定支出估计。")
    if large_upcoming_payments:
        adjustment_reasons.append("已扣除未来 30 天必须支付的大额款项。")

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
        adjustment_reasons.append("尚未提供可用于修正现金流视图的业务上下文。")

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
        notes.append("用户提供了已知正常大额付款说明，部分高风险交易需结合业务背景核查。")
    if is_value_provided(context.get("recurring_vendor_list")):
        notes.append("用户提供了常用供应商或固定商户信息，后续应优先核查陌生商户。")
    if is_value_provided(context.get("business_context_for_top_anomalies")):
        notes.append("用户补充了高风险交易业务背景，后续行动清单应优先处理仍无法解释的记录。")
    if not notes:
        notes.append("当前异常判断主要基于规则和模型结果，尚未结合业务背景。")

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
        notes.append(f"用户确认最高优先级目标为：{context.get('goal_priority_confirmation')}。")
    if is_value_provided(context.get("current_cash_balance")):
        notes.append("用户补充了当前真实可用于目标储备的现金余额。")
    if expected_capacity:
        notes.append(f"用户预计每月可用于储备或目标投入的金额为 {expected_capacity:.2f}。")

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
                notes.append("基于用户补充的月度储备能力，部分目标可能需要调整期限或优先级。")

    if not notes:
        notes.append("当前目标分析主要基于上传 goals.csv 和预算结果，尚未结合用户确认的目标优先级。")

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
