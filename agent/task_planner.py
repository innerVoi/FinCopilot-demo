from agent.data_completeness import check_task_completeness
from agent.tool_registry import get_tool_spec, validate_tool_plan


DEFAULT_TOOL_SEQUENCES = {
    "cashflow_safety_check": [
        "analyze_budget",
        "analyze_invoices",
        "analyze_cashflow",
        "detect_rule_anomalies",
        "detect_lof_anomalies",
    ],
    "suspicious_expense_review": [
        "detect_rule_anomalies",
        "detect_lof_anomalies",
        "explain_transaction_risk",
    ],
    "goal_action_plan": [
        "analyze_budget",
        "analyze_cashflow",
        "analyze_goals",
    ],
}

TOOL_PURPOSES = {
    "analyze_budget": "Understand recent income, expenses, and net cash flow.",
    "analyze_invoices": "Identify overdue, unpaid, and upcoming invoices.",
    "analyze_cashflow": "Estimate 30-day balance and cash-flow risk level.",
    "detect_rule_anomalies": "Detect rule anomalies that may affect business cash flow.",
    "detect_lof_anomalies": "Detect potential anomalies that deviate from local transaction patterns.",
    "explain_transaction_risk": "Generate a risk explanation for a selected anomaly; not called automatically in batch at this stage.",
    "analyze_goals": "Calculate goal progress, gaps, and risk levels.",
}


def get_default_tool_sequence(task_id: str) -> list[str]:
    """
    Return default tool sequence for task_id.
    """
    if task_id not in DEFAULT_TOOL_SEQUENCES:
        raise ValueError(f"Unsupported task_id: {task_id}")
    return list(DEFAULT_TOOL_SEQUENCES[task_id])


def build_tool_step(tool_name: str, step_index: int, purpose: str | None = None) -> dict:
    """
    Build one structured tool step from registry metadata.
    """
    spec = get_tool_spec(tool_name)
    return {
        "step_id": f"step_{step_index}",
        "tool_name": tool_name,
        "display_name": spec["display_name"],
        "purpose": purpose or TOOL_PURPOSES.get(tool_name, spec["description"]),
        "input_keys": spec["input_keys"],
        "output_key": spec["output_key"],
        "status": "planned",
    }


def infer_plan_status(data_check: dict, validation_result: dict) -> str:
    """
    Infer task plan status from data completeness and tool validation.
    """
    if validation_result.get("missing_tools"):
        return "blocked"
    data_status = (data_check or {}).get("status", "missing")
    if data_status == "missing":
        return "blocked"
    if data_status == "partial":
        return "needs_clarification"
    return "ready"


def create_task_plan(task_id: str, data_check: dict | None = None) -> dict:
    """
    Create a structured tool plan for a task.
    """
    if data_check is None:
        data_check = check_task_completeness(task_id, {})
    tool_names = get_default_tool_sequence(task_id)
    validation = validate_tool_plan(tool_names)
    tool_steps = [
        build_tool_step(
            tool_name,
            index,
            purpose=TOOL_PURPOSES.get(tool_name),
        )
        for index, tool_name in enumerate(tool_names, start=1)
        if tool_name in validation["available_tools"]
    ]
    plan_status = infer_plan_status(data_check, validation)
    planner_notes = [
        "The current planner is rule-based and does not call an LLM for automatic planning.",
        "Key financial metrics are calculated by deterministic Python tools.",
    ]
    if plan_status == "needs_clarification":
        planner_notes.append("An initial analysis can run now, but clarification should be added before generating action items.")
    if plan_status == "blocked":
        planner_notes.append("Key data or tools are missing, so the full task cannot run reliably.")

    return {
        "task_id": task_id,
        "plan_status": plan_status,
        "tool_steps": tool_steps,
        "missing_tools": validation["missing_tools"],
        "clarifying_questions": data_check.get("clarifying_questions", []),
        "planner_notes": planner_notes,
    }
