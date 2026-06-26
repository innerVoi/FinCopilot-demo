from agent_api.safety_guardrails import get_agent_safety_note
from agent_api.schemas import merge_specialist_outputs


def _bullet_lines(items):
    if not items:
        return "- None yet."
    return "\n".join(f"- {item}" for item in items[:8])


def compose_final_answer(
    user_query: str,
    manager_plan: dict | None = None,
    specialist_outputs: dict | None = None,
    tool_results: list[dict] | None = None,
    memory_context: dict | None = None,
) -> str:
    """
    Compose a deterministic final answer from Manager and Specialist outputs.
    """
    manager_plan = manager_plan or {}
    memory_context = memory_context or {}
    merged = merge_specialist_outputs(specialist_outputs)
    memory_count = int(memory_context.get("memory_count") or 0)
    if memory_count:
        memory_examples = []
        for key in [
            "known_normal_payments",
            "known_suppliers",
            "cash_context",
            "expected_receivables",
            "recurring_expenses",
            "business_rules",
            "user_preferences",
            "known_risks",
        ]:
            memory_examples.extend(memory_context.get(key) or [])
        memory_note = (
            f"This analysis used {memory_count} user-confirmed business memory item(s). "
            f"Examples: {'; '.join(str(item) for item in memory_examples[:3]) or 'see this turn memory summary'}."
        )
    else:
        memory_note = "This analysis is mainly based on the currently uploaded data. No historical business memory is available yet."
    return (
        "The Manager Agent interpreted your question and selected the relevant Specialist Agents.\n\n"
        "## Task Understanding\n"
        f"- User question: {user_query or ''}\n"
        f"- Intent：{manager_plan.get('intent', 'unknown')}\n"
        f"- Goal: {manager_plan.get('user_goal', '')}\n"
        f"- Agents called: {', '.join(merged.get('agents_called', [])) or 'none'}\n\n"
        "## Specialist Findings\n"
        f"{_bullet_lines(merged.get('findings', []))}\n\n"
        "## Key Risks\n"
        f"{_bullet_lines(merged.get('risks', []))}\n\n"
        "## Suggested Actions\n"
        f"{_bullet_lines(merged.get('recommended_actions', []))}\n\n"
        "## Information Still Needed\n"
        f"{_bullet_lines(merged.get('questions', []))}\n\n"
        "## Business Memory\n"
        f"- {memory_note}\n\n"
        "## Safety Boundary\n"
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
