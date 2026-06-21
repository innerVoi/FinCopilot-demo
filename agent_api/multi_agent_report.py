import json

DISCLAIMER = (
    "本报告仅用于财务整理、风险提醒和教育性支持，不构成投资、税务、法律、"
    "债务处置或专业财务建议。重要交易和财务决策请核查原始凭证，并在必要时咨询合格专业人士。"
)


def safe_markdown_value(value) -> str:
    """
    Safely convert values into Markdown text.
    """
    if value is None:
        return "无"
    if isinstance(value, (dict, list)):
        return f"```json\n{json.dumps(value, ensure_ascii=False, indent=2)}\n```"
    return str(value)


def markdown_bullets(items, empty_text="无") -> str:
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
            "## 2. Manager Agent 任务理解",
            "",
            f"- Intent: {manager_plan.get('intent', 'unknown')}",
            f"- Selected Agents: {', '.join(manager_plan.get('selected_agents', []) or []) or '无'}",
            f"- Tool Plan: {', '.join(manager_plan.get('tool_plan', []) or []) or '无'}",
            "",
            "**澄清问题：**",
            markdown_bullets(manager_plan.get("clarifying_questions", [])),
        ]
    )


def build_tool_results_section(tool_results: list[dict] | None) -> str:
    """
    Build the tool summary call section.
    """
    lines = ["## 3. 工具摘要调用", ""]
    if not tool_results:
        lines.append("- 无工具摘要调用。")
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
    lines = ["## 4. Specialist Agents 输出", ""]
    if not specialist_outputs:
        lines.append("- 无 Specialist Agent 输出。")
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
    lines = [
        "# FinCopilot Multi-Agent 对话报告",
        "",
        "## 1. 用户问题",
        "",
        safe_markdown_value(turn_result.get("user_query", "")),
        "",
        build_manager_section(manager_plan),
        "",
        build_tool_results_section(turn_result.get("tool_results", [])),
        "",
        build_specialist_outputs_section(turn_result.get("specialist_outputs", {})),
        "",
        "## 5. 综合回复",
        "",
        safe_markdown_value(turn_result.get("assistant_reply", "")),
        "",
        "## 6. 建议行动",
        "",
        markdown_bullets(turn_result.get("suggested_actions", [])),
        "",
        "## 7. 仍需补充的信息",
        "",
        markdown_bullets(turn_result.get("clarifying_questions", [])),
        "",
        "## 8. Multi-Agent Trace",
        "",
        safe_markdown_value(trace),
        "",
        "## 9. 假设与限制",
        "",
        "- 所有关键财务数值来自本地确定性工具和已加载样例/上传数据。",
        "- Agent 输出用于解释、规划和整理，不直接修改原始数据。",
        "- 当前版本不做跨 session 持久化，不发送邮件、短信或日历提醒。",
        "",
        "## 10. 安全边界与免责声明",
        "",
        DISCLAIMER,
    ]
    return "\n".join(lines).strip() + "\n"
