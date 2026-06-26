import math

import pandas as pd


def get_reference_date(transactions_df=None, reference_date=None):
    """
    Resolve analysis reference date.
    """
    if reference_date is not None:
        return pd.to_datetime(reference_date).normalize()

    if transactions_df is not None and not transactions_df.empty and "date" in transactions_df.columns:
        dates = pd.to_datetime(transactions_df["date"], errors="coerce").dropna()
        if not dates.empty:
            return dates.max().normalize()

    return pd.Timestamp.today().normalize()


def _recommend_goal_action(goal_status, goal_risk_level):
    if goal_status == "completed":
        return "This goal is close to completion or already completed. Keep the current tracking and review cadence."
    if goal_status == "overdue":
        return "This goal is overdue. Update the target date or reset the target amount."
    if goal_risk_level == "high":
        return "Current net cash flow may not support this goal reliably. Reassess the timeline or monthly savings plan."
    if goal_risk_level == "medium":
        return "Track monthly progress for this goal and prioritize reducing non-essential spending."
    return "Goal progress is relatively stable. Keep the current savings pace."


def analyze_single_goal(
    goal_row,
    net_cashflow=0.0,
    cashflow_risk_level="low",
    reference_date=None,
) -> dict:
    """
    Analyze one financial goal.
    """
    if isinstance(goal_row, pd.Series):
        goal = goal_row.to_dict()
    else:
        goal = dict(goal_row)

    reference_date = get_reference_date(reference_date=reference_date)
    target_amount = float(goal.get("target_amount", 0.0) or 0.0)
    current_amount = float(goal.get("current_amount", 0.0) or 0.0)
    due_date = pd.to_datetime(goal.get("due_date", reference_date), errors="coerce")
    if pd.isna(due_date):
        due_date = reference_date
    due_date = due_date.normalize()
    priority = str(goal.get("priority", "medium")).lower()

    progress_ratio = current_amount / target_amount if target_amount > 0 else 0.0
    progress_ratio = min(max(progress_ratio, 0.0), 1.0)
    remaining_amount = max(target_amount - current_amount, 0.0)
    days_remaining = max((due_date - reference_date).days, 0)
    months_remaining = max(days_remaining / 30, 1)
    required_monthly_saving = remaining_amount / months_remaining
    if required_monthly_saving == 0:
        support_ratio = math.inf
    else:
        support_ratio = net_cashflow / required_monthly_saving

    goal_risk_level = "low"
    if remaining_amount == 0:
        goal_status = "completed"
    else:
        if days_remaining == 0:
            goal_risk_level = "high"
            goal_status = "overdue"
        elif required_monthly_saving > net_cashflow:
            goal_risk_level = "high"
            goal_status = "high risk"
        elif cashflow_risk_level == "high" and priority == "high":
            goal_risk_level = "high"
            goal_status = "high risk"
        elif required_monthly_saving > net_cashflow * 0.5:
            goal_risk_level = "medium"
            goal_status = "needs attention"
        elif cashflow_risk_level == "medium" and priority in ["high", "medium"]:
            goal_risk_level = "medium"
            goal_status = "needs attention"
        else:
            goal_status = "on track"

    return {
        "goal_id": goal.get("goal_id", ""),
        "goal_name": goal.get("goal_name", ""),
        "target_amount": target_amount,
        "current_amount": current_amount,
        "remaining_amount": remaining_amount,
        "due_date": due_date,
        "priority": priority,
        "progress_ratio": progress_ratio,
        "progress_percent": progress_ratio * 100,
        "days_remaining": int(days_remaining),
        "months_remaining": float(months_remaining),
        "required_monthly_saving": float(required_monthly_saving),
        "net_cashflow_support_ratio": float(support_ratio),
        "goal_risk_level": goal_risk_level,
        "goal_status": goal_status,
        "goal_recommendation": _recommend_goal_action(goal_status, goal_risk_level),
    }


def analyze_goals(
    goals_df,
    budget_result=None,
    cashflow_result=None,
    reference_date=None,
) -> dict:
    """
    Analyze all financial goals and return summary plus detail table.
    """
    columns = [
        "goal_id",
        "goal_name",
        "target_amount",
        "current_amount",
        "remaining_amount",
        "due_date",
        "priority",
        "progress_ratio",
        "progress_percent",
        "days_remaining",
        "months_remaining",
        "required_monthly_saving",
        "net_cashflow_support_ratio",
        "goal_risk_level",
        "goal_status",
        "goal_recommendation",
    ]
    if goals_df is None or goals_df.empty:
        return {
            "summary": {
                "goal_count": 0,
                "completed_goal_count": 0,
                "high_risk_goal_count": 0,
                "medium_risk_goal_count": 0,
                "total_target_amount": 0.0,
                "total_current_amount": 0.0,
                "total_remaining_amount": 0.0,
                "overall_progress_percent": 0.0,
            },
            "goals": pd.DataFrame(columns=columns),
        }

    budget_summary = (budget_result or {}).get("summary", {})
    net_cashflow = float(budget_summary.get("net_cashflow", 0.0))
    cashflow_risk_level = (cashflow_result or {}).get("risk_level", "low")
    reference_date = get_reference_date(reference_date=reference_date)

    rows = [
        analyze_single_goal(
            goal_row,
            net_cashflow=net_cashflow,
            cashflow_risk_level=cashflow_risk_level,
            reference_date=reference_date,
        )
        for _, goal_row in goals_df.iterrows()
    ]
    goals_analysis_df = pd.DataFrame(rows, columns=columns)
    total_target = float(goals_analysis_df["target_amount"].sum())
    total_current = float(goals_analysis_df["current_amount"].sum())
    total_remaining = float(goals_analysis_df["remaining_amount"].sum())
    overall_progress = total_current / total_target * 100 if total_target > 0 else 0.0
    overall_progress = min(max(overall_progress, 0.0), 100.0)

    return {
        "summary": {
            "goal_count": int(len(goals_analysis_df)),
            "completed_goal_count": int((goals_analysis_df["goal_status"] == "completed").sum()),
            "high_risk_goal_count": int((goals_analysis_df["goal_risk_level"] == "high").sum()),
            "medium_risk_goal_count": int((goals_analysis_df["goal_risk_level"] == "medium").sum()),
            "total_target_amount": total_target,
            "total_current_amount": total_current,
            "total_remaining_amount": total_remaining,
            "overall_progress_percent": overall_progress,
        },
        "goals": goals_analysis_df,
    }
