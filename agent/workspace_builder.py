from agent.data_completeness import check_task_completeness
from agent.agent_state import (
    apply_saved_status_to_actions,
    get_business_context,
    merge_business_context,
)
from agent.clarification import assess_clarification_status
from agent.context_enricher import enrich_agent_context
from agent.action_generator import generate_action_items
from agent.priority_ranker import rank_action_items, summarize_action_items
from agent.progress_tracker import summarize_progress
from agent.progress_summary import (
    build_agent_progress_conclusion,
    build_progress_summary_text,
)
from agent.workflow_report import build_agent_workflow_report
from agent.task_templates import get_task_template
from agent.task_planner import create_task_plan
from agent.tool_executor import execute_tool_plan


def _safe_summary(context, key):
    value = (context or {}).get(key)
    if isinstance(value, dict):
        return value.get("summary", {})
    return {}


def _count_risk(df, level):
    if df is None or getattr(df, "empty", True) or "risk_level" not in df.columns:
        return 0
    return int((df["risk_level"] == level).sum())


def _top_records(df, n=3, columns=None):
    if df is None or getattr(df, "empty", True):
        return []
    columns = columns or list(df.columns)
    columns = [column for column in columns if column in df.columns]
    return df.head(n)[columns].to_dict(orient="records")


def summarize_tool_results(task_id: str, context: dict) -> dict:
    """
    Extract task-specific result summaries from existing analysis outputs.
    """
    context = context or {}
    if task_id == "cashflow_safety_check":
        cashflow = context.get("cashflow_result") or {}
        invoice_summary = _safe_summary(context, "invoice_result")
        rule_df = context.get("rule_anomalies_df")
        lof_df = context.get("lof_result_df")
        return {
            "cashflow_risk_level": cashflow.get("risk_level", "unknown"),
            "projected_balance_30d": cashflow.get("projected_balance_30d", 0.0),
            "upcoming_invoice_outflow_30d": cashflow.get("upcoming_invoice_outflow_30d", 0.0),
            "cash_buffer_days": cashflow.get("cash_buffer_days", 0.0),
            "high_risk_anomaly_count": _count_risk(rule_df, "high") + _count_risk(lof_df, "high"),
            "medium_risk_anomaly_count": _count_risk(rule_df, "medium") + _count_risk(lof_df, "medium"),
            "overdue_invoice_amount": invoice_summary.get("overdue_invoice_amount", 0.0),
        }

    if task_id == "suspicious_expense_review":
        rule_df = context.get("rule_anomalies_df")
        lof_df = context.get("lof_result_df")
        risky_model_df = lof_df
        if risky_model_df is not None and not getattr(risky_model_df, "empty", True):
            risky_model_df = risky_model_df[
                risky_model_df["risk_level"].isin(["high", "medium"])
            ]
        return {
            "rule_anomaly_count": 0 if rule_df is None or getattr(rule_df, "empty", True) else int(len(rule_df)),
            "lof_high_risk_count": _count_risk(lof_df, "high"),
            "lof_medium_risk_count": _count_risk(lof_df, "medium"),
            "top_rule_anomalies": _top_records(
                rule_df,
                columns=["date", "merchant", "amount", "anomaly_type", "risk_level"],
            ),
            "top_model_anomalies": _top_records(
                risky_model_df,
                columns=["date", "merchant", "amount", "anomaly_score", "risk_level"],
            ),
        }

    if task_id == "goal_action_plan":
        goal_summary = _safe_summary(context, "goal_result")
        return {
            "goal_count": goal_summary.get("goal_count", 0),
            "completed_goal_count": goal_summary.get("completed_goal_count", 0),
            "high_risk_goal_count": goal_summary.get("high_risk_goal_count", 0),
            "medium_risk_goal_count": goal_summary.get("medium_risk_goal_count", 0),
            "overall_progress_percent": goal_summary.get("overall_progress_percent", 0.0),
            "total_remaining_amount": goal_summary.get("total_remaining_amount", 0.0),
        }

    return {}


def build_initial_conclusion(
    task_id: str,
    tool_result_summary: dict,
    data_check: dict,
    task_plan: dict | None = None,
    tool_execution: dict | None = None,
    action_summary: dict | None = None,
) -> str:
    """
    Build a deterministic initial conclusion for the selected task.
    """
    plan_status = (task_plan or {}).get("plan_status", "unknown")
    execution_summary = (tool_execution or {}).get("execution_summary", {})
    execution_note = (
        f"Plan status is {plan_status}. "
        f"{execution_summary.get('reused', 0)} results were reused, "
        f"{execution_summary.get('executed', 0)} tools were executed, and "
        f"{execution_summary.get('skipped', 0)} tools were skipped. "
    )
    action_summary = action_summary or {}
    action_note = (
        f"The Agent generated {action_summary.get('total', 0)} action items from the current analysis, "
        f"including {action_summary.get('high', 0)} high-priority and "
        f"{action_summary.get('medium', 0)} medium-priority items. "
    )

    if task_id == "cashflow_safety_check":
        return (
            "Based on the current uploaded data, the system completed an initial review of budget, invoices, cash flow, and suspicious expenses. "
            f"Current cash-flow risk is {tool_result_summary.get('cashflow_risk_level', 'unknown')}, "
            f"and projected balance over the next 30 days is {tool_result_summary.get('projected_balance_30d', 0.0):.2f}. "
            f"{execution_note}"
            f"{action_note}"
            "The Agent converted cash-flow risk, invoice pressure, and suspicious expenses into action items. "
            "Prioritize high-priority cash-flow and invoice tasks. "
            "Because actual account balance and future customer collections may be missing, this conclusion should be confirmed after the user adds more information."
        )

    if task_id == "suspicious_expense_review":
        return (
            "The system screened current transactions using rule/statistical checks and the LOF model. "
            f"It found {tool_result_summary.get('rule_anomaly_count', 0)} rule anomalies "
            f"and {tool_result_summary.get('lof_high_risk_count', 0)} high-risk model anomalies. "
            f"{execution_note}"
            f"{action_note}"
            "The Agent converted rule anomalies and high-risk model transactions into review tasks. "
            "Prioritize high-risk, large, or unexplained transactions."
        )

    if task_id == "goal_action_plan":
        return (
            "The system analyzed current financial goal progress. "
            f"There are {tool_result_summary.get('goal_count', 0)} goals, "
            f"including {tool_result_summary.get('high_risk_goal_count', 0)} high-risk goals, "
            f"with overall progress at {tool_result_summary.get('overall_progress_percent', 0.0):.1f}%. "
            f"{execution_note}"
            f"{action_note}"
            "The Agent converted high-risk financial goals into action items. "
            "Focus first on high-priority goals with larger remaining gaps."
        )

    return f"The system completed an initial review for the current task. {execution_note}{action_note}"


def build_context_impact_summary(task_id: str, enriched_context: dict) -> str:
    """
    Explain how user-provided context changes the current Agent analysis.
    """
    business_context_used = enriched_context.get("business_context_used", {})

    if task_id == "cashflow_safety_check":
        cashflow = enriched_context.get("enriched_cashflow_summary", {})
        if any(
            key in business_context_used
            for key in ["current_cash_balance", "expected_receivables_30d"]
        ):
            return (
                "The Agent used the user-provided actual balance and future receivables to adjust the cash-flow view. "
                f"Adjusted projected balance over the next 30 days is {cashflow.get('adjusted_projected_balance_30d', 0.0):.2f}, "
                f"and risk changed from {cashflow.get('base_risk_level', 'unknown')} "
                f"to {cashflow.get('adjusted_risk_level', 'unknown')}."
            )
        return "Cash flow is still estimated from uploaded transactions only; actual account balance or future receivables were not used."

    if task_id == "suspicious_expense_review":
        if any(
            key in business_context_used
            for key in [
                "known_authorized_large_payments",
                "recurring_vendor_list",
                "business_context_for_top_anomalies",
            ]
        ):
            return (
                "The Agent recorded user-provided known normal large payments, recurring suppliers, or transaction context. "
                "Future action items should prioritize high-risk transactions that still cannot be explained."
            )
        return "Current anomaly judgment is mainly based on rule and model results, without additional business context yet."

    if task_id == "goal_action_plan":
        if any(
            key in business_context_used
            for key in ["goal_priority_confirmation", "expected_monthly_savings_capacity"]
        ):
            return (
                "The Agent recorded the user-confirmed goal priority and monthly reserve capacity. "
                "Future goal action planning will focus on that priority."
            )
        return "Current goal analysis is mainly based on uploaded goals.csv and budget results, without user-confirmed goal priority yet."

    return "No additional-information impact summary is available yet."


def build_agent_workspace(
    task_id: str,
    context: dict,
    user_inputs: dict | None = None,
    agent_state: dict | None = None,
) -> dict:
    """
    Build the Agent Workspace view model.
    """
    task = get_task_template(task_id)
    state_context = get_business_context(agent_state)
    business_context = merge_business_context(state_context, user_inputs)
    data_check = check_task_completeness(
        task_id,
        context or {},
        user_inputs=business_context,
    )
    clarification_status = assess_clarification_status(task_id, business_context)
    task_plan = create_task_plan(task_id, data_check=data_check)
    tool_execution = execute_tool_plan(task_plan, context or {}, reuse_existing=True)
    updated_context = tool_execution.get("updated_context", context or {})
    summary = summarize_tool_results(task_id, updated_context)
    enriched_context = enrich_agent_context(
        task_id,
        updated_context,
        business_context=business_context,
    )
    context_impact_summary = build_context_impact_summary(task_id, enriched_context)
    action_workspace = {
        "clarification_status": clarification_status,
        "enriched_context": enriched_context,
    }
    action_items = generate_action_items(
        task_id,
        updated_context,
        workspace=action_workspace,
    )
    ranked_action_items = rank_action_items(action_items)
    ranked_action_items = apply_saved_status_to_actions(
        ranked_action_items,
        agent_state=agent_state,
        task_id=task_id,
    )
    action_summary = summarize_action_items(ranked_action_items)
    progress_summary = summarize_progress(ranked_action_items)
    progress_summary_text = build_progress_summary_text(
        ranked_action_items,
        progress_summary=progress_summary,
    )
    agent_progress_conclusion = build_agent_progress_conclusion(
        task_id,
        ranked_action_items,
        progress_summary=progress_summary,
    )
    conclusion = build_initial_conclusion(
        task_id,
        summary,
        data_check,
        task_plan=task_plan,
        tool_execution=tool_execution,
        action_summary=action_summary,
    )
    workspace = {
        "task": task,
        "data_check": data_check,
        "clarification_status": clarification_status,
        "business_context": business_context,
        "task_plan": task_plan,
        "tool_execution": tool_execution,
        "tool_plan": task_plan["tool_steps"],
        "tool_result_summary": summary,
        "enriched_context": enriched_context,
        "context_impact_summary": context_impact_summary,
        "action_items": action_items,
        "ranked_action_items": ranked_action_items,
        "action_summary": action_summary,
        "progress_summary": progress_summary,
        "progress_summary_text": progress_summary_text,
        "agent_progress_conclusion": agent_progress_conclusion,
        "initial_conclusion": conclusion,
        "next_step_hint": "The current Agent workflow has produced a complete report. You can copy or download the Markdown report for demo, review, or future iteration.",
    }
    workspace["workflow_report_markdown"] = build_agent_workflow_report(workspace)
    return workspace
