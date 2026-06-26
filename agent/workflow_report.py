import math

from src.safety import get_disclaimer


def safe_format_value(value) -> str:
    """
    Safely format common Python values as Markdown text.
    """
    if value is None:
        return "None"
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return "None"
        return f"{value:.2f}"
    if isinstance(value, (list, tuple, set)):
        return ", ".join(safe_format_value(item) for item in value) or "None"
    if isinstance(value, dict):
        if not value:
            return "None"
        return "; ".join(
            f"{key}: {safe_format_value(item)}" for key, item in value.items()
        )
    return str(value)


def filter_non_empty_context(business_context: dict | None) -> dict:
    """
    Keep only business context values that were actually provided.
    """
    return {
        key: value
        for key, value in (business_context or {}).items()
        if value not in [None, "", 0, 0.0]
    }


def markdown_list(items, empty_text="None") -> str:
    """
    Convert a list to Markdown bullets.
    """
    if not items:
        return f"- {empty_text}"
    return "\n".join(f"- {safe_format_value(item)}" for item in items)


def markdown_dict(data: dict | None, empty_text="None") -> str:
    """
    Convert a dict to Markdown bullets.
    """
    if not data:
        return f"- {empty_text}"
    return "\n".join(
        f"- **{key}**: {safe_format_value(value)}"
        for key, value in data.items()
    )


def build_action_items_section(action_items: list[dict]) -> str:
    """
    Build the action item Markdown section.
    """
    if not action_items:
        return "- No action items"

    lines = []
    for item in action_items:
        lines.append(
            f"### {item.get('action_id', '')} "
            f"[{item.get('priority', '')}][{item.get('status', '')}] "
            f"{item.get('title', '')}"
        )
        lines.append(f"- Source: {item.get('source', '')}")
        lines.append(f"- Reason: {item.get('reason', '')}")
        lines.append(f"- Suggested deadline: {item.get('suggested_deadline', '')}")
        if item.get("note"):
            lines.append(f"- Handling note: {item.get('note')}")
        lines.append("- Recommended steps:")
        for step in item.get("recommended_steps", []):
            lines.append(f"  - {safe_format_value(step)}")
        lines.append("")
    return "\n".join(lines).strip()


def build_tool_execution_section(tool_execution: dict | None) -> str:
    """
    Build the tool execution Markdown section.
    """
    records = (tool_execution or {}).get("execution_records", [])
    if not records:
        return "- No tool execution records"

    lines = []
    for record in records:
        lines.append(f"### {record.get('tool_name', '')}")
        lines.append(f"- Display name: {record.get('display_name', '')}")
        lines.append(f"- Status: {record.get('status', '')}")
        lines.append(f"- Output: {record.get('output_key', '')}")
        lines.append(f"- Summary: {safe_format_value(record.get('summary', {}))}")
        if record.get("error"):
            lines.append(f"- Error: {record.get('error')}")
        lines.append("")
    return "\n".join(lines).strip()


def _build_tool_plan_section(task_plan: dict | None) -> str:
    steps = (task_plan or {}).get("tool_steps", [])
    if not steps:
        return "- No tool call plan"
    lines = []
    for step in steps:
        lines.append(
            f"- **{step.get('step_id', '')} {step.get('tool_name', '')}**: "
            f"{step.get('purpose', '')}; "
            f"inputs: {safe_format_value(step.get('input_keys', []))}; "
            f"output: {step.get('output_key', '')}; "
            f"Status: {step.get('status', '')}"
        )
    return "\n".join(lines)


def build_agent_workflow_report(workspace: dict, include_details: bool = True) -> str:
    """
    Build a complete task-level Agent workflow report.
    """
    workspace = workspace or {}
    task = workspace.get("task", {})
    data_check = workspace.get("data_check", {})
    clarification_status = workspace.get("clarification_status", {})
    business_context = filter_non_empty_context(workspace.get("business_context"))
    task_plan = workspace.get("task_plan", {})
    progress_summary = workspace.get("progress_summary", {})

    report = [
        "# FinCopilot Agent Workflow Report",
        "",
        "## 1. Task Overview",
        f"- Task name: {task.get('task_name', 'No task selected')}",
        f"- Task goal: {task.get('task_goal', 'None')}",
        f"- Task status: {task_plan.get('plan_status', 'unknown')}",
        f"- Agent initial conclusion: {workspace.get('initial_conclusion', 'None')}",
        f"- Agent progress conclusion: {workspace.get('agent_progress_conclusion', 'None')}",
        "",
        "## 2. Agent Execution Plan",
        markdown_list(task.get("workflow_steps", [])),
        "",
        "## 3. Data Completeness Check",
        f"- Check status: {data_check.get('status', 'unknown')}",
        "- Available information:",
        markdown_list(data_check.get("available_items", [])),
        "- Missing or uncertain information:",
        markdown_list(data_check.get("missing_items", [])),
        "- Suggested follow-up questions:",
        markdown_list(data_check.get("clarifying_questions", [])),
        f"- Clarification completion: {data_check.get('clarification_completion_ratio', 0.0) * 100:.0f}%",
        "",
        "## 4. Clarification and Business Context",
        f"- Provided fields: {safe_format_value(clarification_status.get('provided_fields', []))}",
        f"- Missing fields: {safe_format_value(clarification_status.get('missing_fields', []))}",
        "- User-provided business context:",
        markdown_dict(business_context),
        "",
        "## 5. Tool Call Plan",
        _build_tool_plan_section(task_plan),
        "",
        "## 6. Tool Execution Records",
        build_tool_execution_section(workspace.get("tool_execution")),
        "",
        "## 7. Tool Result Summary",
        markdown_dict(workspace.get("tool_result_summary", {})),
        "",
        "## 8. Impact of Additional Information",
        f"- {workspace.get('context_impact_summary', 'None')}",
    ]

    if include_details:
        report.extend(
            [
                "- Enriched analysis summary:",
                markdown_dict(workspace.get("enriched_context", {})),
            ]
        )

    report.extend(
        [
            "",
            "## 9. Action Items",
            build_action_items_section(workspace.get("ranked_action_items", [])),
            "",
            "## 10. Action Item Progress",
            f"- Total action items: {progress_summary.get('total', 0)}",
            f"- Closed: {progress_summary.get('closed_count', 0)}",
            f"- Still active: {progress_summary.get('active_count', 0)}",
            f"- Completion rate: {progress_summary.get('completion_rate', 0.0) * 100:.0f}%",
            f"- High-priority active items: {progress_summary.get('high_priority_active_count', 0)}",
            f"- Progress summary: {workspace.get('progress_summary_text', 'None')}",
            "",
            "## 11. Agent Conclusions",
            f"- Initial conclusion: {workspace.get('initial_conclusion', 'None')}",
            f"- Progress conclusion: {workspace.get('agent_progress_conclusion', 'None')}",
            f"- Next-step hint: {workspace.get('next_step_hint', 'None')}",
            "",
            "## 12. Assumptions and Limits",
            "- This analysis is based on user-uploaded data and user-provided context.",
            "- If uploaded data is incomplete, the analysis may be incomplete.",
            "- Current status is stored only in the current Streamlit session.",
            "- The system does not execute real payments, transfers, or external notifications.",
            "- Cash-flow analysis is an estimate and does not represent actual account balance.",
            "- Anomaly detection results are risk alerts, not fraud determinations.",
            "",
            "## 13. Safety Boundaries and Disclaimer",
            get_disclaimer(),
            "Review source documents before important transactions and financial decisions, and consult qualified professionals when needed.",
        ]
    )
    return "\n".join(report)
