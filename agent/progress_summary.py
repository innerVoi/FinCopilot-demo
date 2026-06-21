from agent.progress_tracker import get_top_active_actions, summarize_progress


def build_progress_summary_text(
    action_items: list[dict],
    progress_summary: dict | None = None,
) -> str:
    """
    Build a concise progress summary.
    """
    summary = progress_summary or summarize_progress(action_items)
    top_active = get_top_active_actions(action_items, n=3)
    top_titles = "、".join(item.get("title", "") for item in top_active if item.get("title"))
    focus_sentence = (
        f"建议优先处理：{top_titles}。"
        if top_titles
        else "当前没有需要优先处理的未关闭行动项。"
    )
    return (
        f"当前任务共有 {summary.get('total', 0)} 个行动项，"
        f"其中 {summary.get('closed_count', 0)} 个已关闭，"
        f"{summary.get('active_count', 0)} 个仍需处理。"
        f"仍有 {summary.get('high_priority_active_count', 0)} 个高优先级行动项未完成，"
        f"完成率为 {summary.get('completion_rate', 0.0) * 100:.0f}%。"
        f"{focus_sentence}"
    )


def build_agent_progress_conclusion(
    task_id: str,
    action_items: list[dict],
    progress_summary: dict | None = None,
) -> str:
    """
    Build a task-specific progress conclusion.
    """
    summary = progress_summary or summarize_progress(action_items)
    high_active_count = summary.get("high_priority_active_count", 0)
    active_count = summary.get("active_count", 0)

    if active_count == 0 and summary.get("total", 0) > 0:
        return "当前行动项均已关闭。建议复查关键数据后生成任务级总结报告。"

    if task_id == "cashflow_safety_check":
        if high_active_count:
            return "现金流安全检查仍有高优先级行动项未完成，因此当前不能认为现金流风险已经完全处理。建议优先完成现金流和发票相关任务后再复查。"
        return "现金流安全检查仍有部分行动项待处理。建议继续跟进未关闭任务，并在关键付款或回款更新后复查现金流。"

    if task_id == "suspicious_expense_review":
        if high_active_count:
            return "异常支出处理仍有未核查的高风险交易。建议先核查高风险、大额或缺少业务背景的记录。"
        return "异常支出处理仍有部分核查任务未关闭。建议继续记录核查结果，避免将未确认交易直接视为事实异常。"

    if task_id == "goal_action_plan":
        if high_active_count:
            return "财务目标行动计划中仍存在未处理的高风险目标。建议先确认目标优先级和月度储备能力。"
        return "财务目标行动计划仍有部分任务待处理。建议继续跟踪目标缺口和可用储备能力。"

    return "当前仍有行动项需要处理。建议优先完成高优先级任务后再生成总结。"


def action_items_to_status_markdown(action_items: list[dict]) -> str:
    """
    Convert action items with status to Markdown.
    """
    lines = ["# FinCopilot 行动项进展"]
    for item in action_items or []:
        lines.append(
            f"## [{item.get('priority', '')}][{item.get('status', '')}] "
            f"{item.get('title', '')}"
        )
        lines.append(f"- ID：{item.get('action_id', '')}")
        lines.append(f"- 来源：{item.get('source', '')}")
        lines.append(f"- 原因：{item.get('reason', '')}")
        lines.append(f"- 建议截止时间：{item.get('suggested_deadline', '')}")
        lines.append(f"- 当前状态：{item.get('status', '')}")
        if item.get("note"):
            lines.append(f"- 处理备注：{item.get('note')}")
        lines.append("- 建议步骤：")
        for step in item.get("recommended_steps", []):
            lines.append(f"  - {step}")
        lines.append("")
    return "\n".join(lines)
