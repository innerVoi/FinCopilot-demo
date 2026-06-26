import json

DISCLAIMER = (
    "This report is for financial organization, risk reminders, and educational support only. "
    "It is not investment, tax, legal, debt-resolution, or professional financial advice. "
    "Review source documents before important financial decisions and consult qualified professionals when needed."
)


def safe_markdown_value(value) -> str:
    """
    Safely convert values into Markdown text.
    """
    if value is None:
        return "None"
    if isinstance(value, (dict, list)):
        return f"```json\n{json.dumps(value, ensure_ascii=False, indent=2)}\n```"
    return str(value)


def markdown_bullets(items, empty_text="None") -> str:
    """
    Convert a list into Markdown bullets.
    """
    if not items:
        return f"- {empty_text}"
    if not isinstance(items, list):
        items = [items]
    lines = []
    for item in items:
        if isinstance(item, (dict, list)):
            lines.append(f"- {json.dumps(item, ensure_ascii=False)}")
        else:
            lines.append(f"- {item}")
    return "\n".join(lines)


def build_manager_section(manager_plan: dict | None) -> str:
    """
    Build the Manager Agent understanding section.
    """
    manager_plan = manager_plan or {}
    return "\n".join(
        [
            "## 2. Manager Agent Task Understanding",
            "",
            f"- Intent: {manager_plan.get('intent', 'unknown')}",
            f"- Selected Agents: {', '.join(manager_plan.get('selected_agents', []) or []) or 'None'}",
            f"- Tool Plan: {', '.join(manager_plan.get('tool_plan', []) or []) or 'None'}",
            "",
            "**Clarifying Questions:**",
            markdown_bullets(manager_plan.get("clarifying_questions", [])),
        ]
    )


def build_tool_results_section(tool_results: list[dict] | None) -> str:
    """
    Build the tool summary call section.
    """
    lines = ["## 3. Tool Summary Calls", ""]
    if not tool_results:
        lines.append("- No tool summary calls.")
        return "\n".join(lines)

    for result in tool_results:
        result = result or {}
        lines.append(f"### {result.get('tool_name', result.get('name', 'unknown_tool'))}")
        lines.append(f"- Status: {result.get('status', 'unknown')}")
        if result.get("error"):
            lines.append(f"- Error: {result.get('error')}")
        summary = result.get("summary", result.get("result", {}))
        lines.append(safe_markdown_value(summary))
        lines.append("")
    return "\n".join(lines).strip()


def build_specialist_outputs_section(specialist_outputs: dict | None) -> str:
    """
    Build the Specialist Agents output section.
    """
    lines = ["## 4. Specialist Agent Outputs", ""]
    if not specialist_outputs:
        lines.append("- No Specialist Agent outputs.")
        return "\n".join(lines)

    for agent_name, payload in specialist_outputs.items():
        payload = payload or {}
        result = payload.get("result", {}) or {}
        lines.append(f"### {agent_name}")
        lines.append(f"- Mode: {payload.get('mode', 'fallback')}")
        lines.append("")
        lines.append("**Findings:**")
        lines.append(markdown_bullets(result.get("findings", [])))
        lines.append("")
        lines.append("**Risks:**")
        lines.append(markdown_bullets(result.get("risks", [])))
        lines.append("")
        lines.append("**Recommended Actions:**")
        lines.append(markdown_bullets(result.get("recommended_actions", [])))
        lines.append("")
    return "\n".join(lines).strip()


def build_multi_agent_report(turn_result: dict | None) -> str:
    """
    Build a Markdown report from one run_multi_agent_turn result.
    """
    turn_result = turn_result or {}
    manager_plan = turn_result.get("manager_plan", {}) or {}
    trace = turn_result.get("trace", {}) or {}
    persisted_actions = ((turn_result.get("persistence_result") or {}).get("actions") or [])
    pending_actions = sum(1 for item in persisted_actions if isinstance(item, dict) and item.get("status") == "pending")
    handled_actions = sum(1 for item in persisted_actions if isinstance(item, dict) and item.get("status") != "pending")
    lines = [
        "# FinCopilot Multi-Agent Conversation Report",
        "",
        "## 1. User Question",
        "",
        safe_markdown_value(turn_result.get("user_query", "")),
        "",
        build_manager_section(manager_plan),
        "",
        build_tool_results_section(turn_result.get("tool_results", [])),
        "",
        build_specialist_outputs_section(turn_result.get("specialist_outputs", {})),
        "",
        "## 5. Synthesized Response",
        "",
        safe_markdown_value(turn_result.get("assistant_reply", "")),
        "",
        "## 6. Suggested Actions",
        "",
        markdown_bullets(turn_result.get("suggested_actions", [])),
        "",
        f"- Pending action items: {pending_actions}",
        f"- Handled action items: {handled_actions}",
        "",
        "## 7. Information Still Needed",
        "",
        markdown_bullets(turn_result.get("clarifying_questions", [])),
        "",
        "## 8. Multi-Agent Trace",
        "",
        safe_markdown_value(trace),
        "",
        "## 9. Assumptions and Limits",
        "",
        "- All key financial numbers come from local deterministic tools and loaded sample or uploaded data.",
        "- Agent outputs are used for explanation, planning, and organization; they do not directly modify source data.",
        "- This version does not persist across sessions or send email, SMS, or calendar reminders.",
        "",
        "## 10. Safety Boundaries and Disclaimer",
        "",
        DISCLAIMER,
    ]
    return "\n".join(lines).strip() + "\n"
