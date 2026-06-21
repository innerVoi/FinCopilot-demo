import math

from src.safety import get_disclaimer


def safe_format_value(value) -> str:
    """
    Safely format common Python values as Markdown text.
    """
    if value is None:
        return "无"
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return "无"
        return f"{value:.2f}"
    if isinstance(value, (list, tuple, set)):
        return "、".join(safe_format_value(item) for item in value) or "无"
    if isinstance(value, dict):
        if not value:
            return "无"
        return "；".join(
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


def markdown_list(items, empty_text="无") -> str:
    """
    Convert a list to Markdown bullets.
    """
    if not items:
        return f"- {empty_text}"
    return "\n".join(f"- {safe_format_value(item)}" for item in items)


def markdown_dict(data: dict | None, empty_text="无") -> str:
    """
    Convert a dict to Markdown bullets.
    """
    if not data:
        return f"- {empty_text}"
    return "\n".join(
        f"- **{key}**：{safe_format_value(value)}"
        for key, value in data.items()
    )


def build_action_items_section(action_items: list[dict]) -> str:
    """
    Build the action item Markdown section.
    """
    if not action_items:
        return "- 无行动项"

    lines = []
    for item in action_items:
        lines.append(
            f"### {item.get('action_id', '')} "
            f"[{item.get('priority', '')}][{item.get('status', '')}] "
            f"{item.get('title', '')}"
        )
        lines.append(f"- 来源：{item.get('source', '')}")
        lines.append(f"- 原因：{item.get('reason', '')}")
        lines.append(f"- 建议截止时间：{item.get('suggested_deadline', '')}")
        if item.get("note"):
            lines.append(f"- 处理备注：{item.get('note')}")
        lines.append("- 建议步骤：")
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
        return "- 无工具执行记录"

    lines = []
    for record in records:
        lines.append(f"### {record.get('tool_name', '')}")
        lines.append(f"- 显示名称：{record.get('display_name', '')}")
        lines.append(f"- 状态：{record.get('status', '')}")
        lines.append(f"- 输出：{record.get('output_key', '')}")
        lines.append(f"- 摘要：{safe_format_value(record.get('summary', {}))}")
        if record.get("error"):
            lines.append(f"- 错误：{record.get('error')}")
        lines.append("")
    return "\n".join(lines).strip()


def _build_tool_plan_section(task_plan: dict | None) -> str:
    steps = (task_plan or {}).get("tool_steps", [])
    if not steps:
        return "- 无工具调用计划"
    lines = []
    for step in steps:
        lines.append(
            f"- **{step.get('step_id', '')} {step.get('tool_name', '')}**："
            f"{step.get('purpose', '')}；"
            f"输入：{safe_format_value(step.get('input_keys', []))}；"
            f"输出：{step.get('output_key', '')}；"
            f"状态：{step.get('status', '')}"
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
        "# FinCopilot Agent 工作流报告",
        "",
        "## 1. 任务概览",
        f"- 任务名称：{task.get('task_name', '未选择任务')}",
        f"- 任务目标：{task.get('task_goal', '无')}",
        f"- 任务状态：{task_plan.get('plan_status', 'unknown')}",
        f"- Agent 初步结论：{workspace.get('initial_conclusion', '无')}",
        f"- Agent 进展结论：{workspace.get('agent_progress_conclusion', '无')}",
        "",
        "## 2. Agent 执行计划",
        markdown_list(task.get("workflow_steps", [])),
        "",
        "## 3. 数据完整性检查",
        f"- 检查状态：{data_check.get('status', 'unknown')}",
        "- 已具备信息：",
        markdown_list(data_check.get("available_items", [])),
        "- 缺失或不确定信息：",
        markdown_list(data_check.get("missing_items", [])),
        "- 建议追问：",
        markdown_list(data_check.get("clarifying_questions", [])),
        f"- 澄清完成度：{data_check.get('clarification_completion_ratio', 0.0) * 100:.0f}%",
        "",
        "## 4. 澄清问题与业务上下文",
        f"- 已回答字段：{safe_format_value(clarification_status.get('provided_fields', []))}",
        f"- 未回答字段：{safe_format_value(clarification_status.get('missing_fields', []))}",
        "- 用户已补充业务上下文：",
        markdown_dict(business_context),
        "",
        "## 5. 工具调用计划",
        _build_tool_plan_section(task_plan),
        "",
        "## 6. 工具执行记录",
        build_tool_execution_section(workspace.get("tool_execution")),
        "",
        "## 7. 工具结果摘要",
        markdown_dict(workspace.get("tool_result_summary", {})),
        "",
        "## 8. 补充信息对分析的影响",
        f"- {workspace.get('context_impact_summary', '无')}",
    ]

    if include_details:
        report.extend(
            [
                "- 补全后的分析摘要：",
                markdown_dict(workspace.get("enriched_context", {})),
            ]
        )

    report.extend(
        [
            "",
            "## 9. 行动清单",
            build_action_items_section(workspace.get("ranked_action_items", [])),
            "",
            "## 10. 行动项进展",
            f"- 行动项总数：{progress_summary.get('total', 0)}",
            f"- 已关闭：{progress_summary.get('closed_count', 0)}",
            f"- 仍需处理：{progress_summary.get('active_count', 0)}",
            f"- 完成率：{progress_summary.get('completion_rate', 0.0) * 100:.0f}%",
            f"- 高优先级未完成：{progress_summary.get('high_priority_active_count', 0)}",
            f"- 进展摘要：{workspace.get('progress_summary_text', '无')}",
            "",
            "## 11. Agent 结论",
            f"- 初步结论：{workspace.get('initial_conclusion', '无')}",
            f"- 进展结论：{workspace.get('agent_progress_conclusion', '无')}",
            f"- 下一步提示：{workspace.get('next_step_hint', '无')}",
            "",
            "## 12. 假设与限制",
            "- 当前分析基于用户上传数据和用户补充信息。",
            "- 如果上传数据不完整，分析结果可能不完整。",
            "- 当前状态仅保存在当前 Streamlit session 中。",
            "- 系统不会执行真实付款、转账或外部通知。",
            "- 现金流分析是估算，不代表真实账户余额。",
            "- 异常检测结果是风险提醒，不代表欺诈认定。",
            "",
            "## 13. 安全边界与免责声明",
            get_disclaimer(),
            "重要交易和财务决策请核查原始凭证，并在必要时咨询合格专业人士。",
        ]
    )
    return "\n".join(report)
