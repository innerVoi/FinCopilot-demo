from agent_api.safety_guardrails import get_agent_safety_note
from agent_api.schemas import merge_specialist_outputs


def _bullet_lines(items):
    if not items:
        return "- 暂无。"
    return "\n".join(f"- {item}" for item in items[:8])


def compose_final_answer(
    user_query: str,
    manager_plan: dict | None = None,
    specialist_outputs: dict | None = None,
    tool_results: list[dict] | None = None,
) -> str:
    """
    Compose a deterministic final answer from Manager and Specialist outputs.
    """
    manager_plan = manager_plan or {}
    merged = merge_specialist_outputs(specialist_outputs)
    return (
        "我已经让 Manager Agent 识别了你的问题，并调用了相关专业 Agent。\n\n"
        "## 任务理解\n"
        f"- 用户问题：{user_query or ''}\n"
        f"- Intent：{manager_plan.get('intent', 'unknown')}\n"
        f"- 目标：{manager_plan.get('user_goal', '')}\n"
        f"- 已调用 Agent：{', '.join(merged.get('agents_called', [])) or '暂无'}\n\n"
        "## 专业 Agent 发现\n"
        f"{_bullet_lines(merged.get('findings', []))}\n\n"
        "## 主要风险\n"
        f"{_bullet_lines(merged.get('risks', []))}\n\n"
        "## 建议行动\n"
        f"{_bullet_lines(merged.get('recommended_actions', []))}\n\n"
        "## 仍需你补充的信息\n"
        f"{_bullet_lines(merged.get('questions', []))}\n\n"
        "## 安全边界\n"
        f"{get_agent_safety_note()}"
    )


def compose_agent_trace_summary(
    manager_result: dict | None = None,
    specialist_outputs: dict | None = None,
    tool_results: list[dict] | None = None,
) -> dict:
    """
    Build a UI trace summary for the multi-agent run.
    """
    manager_result = manager_result or {}
    specialist_outputs = specialist_outputs or {}
    tool_results = tool_results or []
    return {
        "manager_mode": manager_result.get("mode", "fallback"),
        "manager_intent": (manager_result.get("manager_plan") or {}).get("intent", "unknown"),
        "tools_called": [item.get("tool_name") for item in tool_results],
        "tool_success_count": sum(1 for item in tool_results if item.get("status") == "success"),
        "specialist_agents": list(specialist_outputs.keys()),
        "specialist_modes": {
            agent_name: payload.get("mode", "fallback")
            for agent_name, payload in specialist_outputs.items()
        },
        "errors": {
            "manager": manager_result.get("errors", []),
            "specialists": {
                agent_name: payload.get("errors", [])
                for agent_name, payload in specialist_outputs.items()
            },
        },
    }
