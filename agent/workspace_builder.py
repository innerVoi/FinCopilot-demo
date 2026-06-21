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
        f"本次计划状态为 {plan_status}，"
        f"复用 {execution_summary.get('reused', 0)} 个结果，"
        f"新执行 {execution_summary.get('executed', 0)} 个工具，"
        f"跳过 {execution_summary.get('skipped', 0)} 个工具。"
    )
    action_summary = action_summary or {}
    action_note = (
        f"Agent 已根据当前分析结果生成 {action_summary.get('total', 0)} 个行动项，"
        f"其中高优先级 {action_summary.get('high', 0)} 个，"
        f"中优先级 {action_summary.get('medium', 0)} 个。"
    )

    if task_id == "cashflow_safety_check":
        return (
            "根据当前上传数据，系统已完成预算、发票、现金流和异常支出的初步检查。"
            f"当前现金流风险等级为 {tool_result_summary.get('cashflow_risk_level', 'unknown')}，"
            f"未来 30 天预计余额为 {tool_result_summary.get('projected_balance_30d', 0.0):.2f}。"
            f"{execution_note}"
            f"{action_note}"
            "Agent 已将现金流风险、发票压力和异常支出转化为行动清单。"
            "请优先处理高优先级的现金流和发票任务。"
            "但由于真实账户余额和未来客户回款可能缺失，该结论仍需要用户补充信息后进一步确认。"
        )

    if task_id == "suspicious_expense_review":
        return (
            "系统已结合规则/统计识别和 LOF 模型检测，对当前交易进行异常筛查。"
            f"当前发现 {tool_result_summary.get('rule_anomaly_count', 0)} 条规则异常，"
            f"以及 {tool_result_summary.get('lof_high_risk_count', 0)} 条高风险模型异常。"
            f"{execution_note}"
            f"{action_note}"
            "Agent 已将规则异常和模型高风险交易转化为核查任务。"
            "请优先处理高风险、大额或缺少业务解释的交易。"
            "后续应将这些异常转化为核查任务。"
        )

    if task_id == "goal_action_plan":
        return (
            "系统已分析当前财务目标进度。"
            f"当前共有 {tool_result_summary.get('goal_count', 0)} 个目标，"
            f"其中 {tool_result_summary.get('high_risk_goal_count', 0)} 个为高风险目标，"
            f"整体完成率为 {tool_result_summary.get('overall_progress_percent', 0.0):.1f}%。"
            f"{execution_note}"
            f"{action_note}"
            "Agent 已将高风险财务目标转化为行动项。"
            "请优先关注高优先级且剩余缺口较大的目标。"
            "后续应围绕高优先级目标生成行动计划。"
        )

    return f"系统已完成当前任务的初步检查。{execution_note}{action_note}"


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
                "Agent 已使用用户补充的真实余额和未来回款信息修正现金流视图。"
                f"调整后未来 30 天预计余额为 {cashflow.get('adjusted_projected_balance_30d', 0.0):.2f}，"
                f"风险等级从 {cashflow.get('base_risk_level', 'unknown')} "
                f"变为 {cashflow.get('adjusted_risk_level', 'unknown')}。"
            )
        return "当前仍基于上传流水估算现金流，未使用真实账户余额或未来回款信息。"

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
                "Agent 已记录用户提供的已知正常大额付款、常用供应商或交易背景。"
                "后续生成行动清单时，应优先核查仍无法解释的高风险交易。"
            )
        return "当前异常判断主要基于规则和模型结果，尚未结合业务背景。"

    if task_id == "goal_action_plan":
        if any(
            key in business_context_used
            for key in ["goal_priority_confirmation", "expected_monthly_savings_capacity"]
        ):
            return (
                "Agent 已记录用户确认的目标优先级和月度储备能力。"
                "后续目标行动计划将优先围绕该目标生成。"
            )
        return "当前目标分析主要基于上传 goals.csv 和预算结果，尚未结合用户确认的目标优先级。"

    return "当前尚未形成补充信息影响说明。"


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
        "next_step_hint": "当前 Agent 工作流已经形成完整报告。你可以复制或下载 Markdown 报告，用于演示、复盘或后续迭代。",
    }
    workspace["workflow_report_markdown"] = build_agent_workflow_report(workspace)
    return workspace
