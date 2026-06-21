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
    "analyze_budget": "了解近期收入、支出和净现金流。",
    "analyze_invoices": "识别逾期、未支付和未来到期发票。",
    "analyze_cashflow": "估算未来 30 天余额和现金流风险等级。",
    "detect_rule_anomalies": "识别可能影响经营现金流的规则异常。",
    "detect_lof_anomalies": "识别偏离局部交易模式的潜在异常。",
    "explain_transaction_risk": "对选定异常生成风险解释；当前阶段不自动批量调用。",
    "analyze_goals": "计算目标完成率、缺口和风险等级。",
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
        "当前使用规则化 planner，不调用 LLM 进行自动规划。",
        "关键财务指标由确定性 Python 工具计算。",
    ]
    if plan_status == "needs_clarification":
        planner_notes.append("可以先做初步分析，但建议补充澄清信息后再生成行动清单。")
    if plan_status == "blocked":
        planner_notes.append("当前缺少关键数据或工具，无法可靠执行完整任务。")

    return {
        "task_id": task_id,
        "plan_status": plan_status,
        "tool_steps": tool_steps,
        "missing_tools": validation["missing_tools"],
        "clarifying_questions": data_check.get("clarifying_questions", []),
        "planner_notes": planner_notes,
    }
