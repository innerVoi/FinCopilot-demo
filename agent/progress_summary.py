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
    top_titles = ", ".join(item.get("title", "") for item in top_active if item.get("title"))
    focus_sentence = (
        f"Recommended priorities: {top_titles}."
        if top_titles
        else "There are no open action items that need priority handling right now."
    )
    return (
        f"This task has {summary.get('total', 0)} action items, "
        f"including {summary.get('closed_count', 0)} closed and "
        f"{summary.get('active_count', 0)} still active. "
        f"{summary.get('high_priority_active_count', 0)} high-priority action items remain open, "
        f"and completion rate is {summary.get('completion_rate', 0.0) * 100:.0f}%. "
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
        return "All action items are closed. Review key data and then generate a task-level summary report."

    if task_id == "cashflow_safety_check":
        if high_active_count:
            return "The cash-flow safety check still has high-priority action items open, so cash-flow risk should not be treated as fully handled yet. Complete cash-flow and invoice tasks first, then review again."
        return "The cash-flow safety check still has some action items open. Continue tracking open tasks and review cash flow again after key payments or collections change."

    if task_id == "suspicious_expense_review":
        if high_active_count:
            return "Suspicious expense handling still has high-risk transactions that have not been reviewed. Check high-risk, large, or unexplained records first."
        return "Suspicious expense handling still has some review tasks open. Continue recording review results and avoid treating unconfirmed transactions as factual issues."

    if task_id == "goal_action_plan":
        if high_active_count:
            return "The goals action plan still has unresolved high-risk goals. Confirm goal priority and monthly reserve capacity first."
        return "The goals action plan still has some open tasks. Continue tracking goal gaps and available reserve capacity."

    return "There are still action items to handle. Complete high-priority tasks before generating a summary."


def action_items_to_status_markdown(action_items: list[dict]) -> str:
    """
    Convert action items with status to Markdown.
    """
    lines = ["# FinCopilot Action Item Progress"]
    for item in action_items or []:
        lines.append(
            f"## [{item.get('priority', '')}][{item.get('status', '')}] "
            f"{item.get('title', '')}"
        )
        lines.append(f"- ID: {item.get('action_id', '')}")
        lines.append(f"- Source: {item.get('source', '')}")
        lines.append(f"- Reason: {item.get('reason', '')}")
        lines.append(f"- Suggested deadline: {item.get('suggested_deadline', '')}")
        lines.append(f"- Current status: {item.get('status', '')}")
        if item.get("note"):
            lines.append(f"- Handling note: {item.get('note')}")
        lines.append("- Recommended steps:")
        for step in item.get("recommended_steps", []):
            lines.append(f"  - {step}")
        lines.append("")
    return "\n".join(lines)
