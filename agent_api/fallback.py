from agent_api.safety_guardrails import get_agent_safety_note, sanitize_agent_text
from agent_api.schemas import (
    ANOMALY_AGENT,
    CASHFLOW_AGENT,
    PLANNING_AGENT,
    REPORT_AGENT,
    get_default_agent_response,
    get_default_manager_plan,
    get_default_specialist_result,
    validate_manager_plan,
    validate_specialist_result,
)


def infer_intent_from_query(user_query: str | None) -> str:
    """
    Infer intent from a user query with deterministic keyword rules.
    """
    query = user_query or ""
    if any(keyword in query for keyword in ["现金流", "钱够", "余额", "够不够"]):
        return "cashflow_check"
    if any(keyword in query for keyword in ["异常", "可疑", "支出", "重复"]):
        return "expense_anomaly_review"
    if any(keyword in query for keyword in ["促销", "进货", "采购"]):
        return "promotion_or_purchase_planning"
    if any(keyword in query for keyword in ["目标", "预算", "计划"]):
        return "goal_or_budget_planning"
    if any(keyword in query for keyword in ["发票", "收款", "付款", "欠款"]):
        return "invoice_or_payment_review"
    if any(keyword in query for keyword in ["总结", "报告", "概览"]):
        return "general_finance_summary"
    return "unknown"


def _agents_for_intent(intent: str) -> list[str]:
    if intent == "cashflow_check":
        return [CASHFLOW_AGENT, REPORT_AGENT]
    if intent == "expense_anomaly_review":
        return [ANOMALY_AGENT, REPORT_AGENT]
    if intent in ["goal_or_budget_planning", "promotion_or_purchase_planning"]:
        return [PLANNING_AGENT, CASHFLOW_AGENT, REPORT_AGENT]
    if intent == "invoice_or_payment_review":
        return [CASHFLOW_AGENT, REPORT_AGENT]
    return [REPORT_AGENT]


def _tools_for_intent(intent: str) -> list[str]:
    if intent == "cashflow_check":
        return ["get_budget_summary", "get_invoice_summary", "get_cashflow_summary"]
    if intent == "expense_anomaly_review":
        return ["get_anomaly_summary"]
    if intent in ["goal_or_budget_planning", "promotion_or_purchase_planning"]:
        return ["get_cashflow_summary", "get_goal_summary", "get_action_summary"]
    if intent == "invoice_or_payment_review":
        return ["get_invoice_summary", "get_cashflow_summary"]
    if intent == "general_finance_summary":
        return ["get_budget_summary", "get_cashflow_summary", "get_goal_summary"]
    return []


def build_fallback_manager_plan(user_query: str | None) -> dict:
    """
    Build a fallback Manager Plan.
    """
    query = user_query or ""
    intent = infer_intent_from_query(query)
    plan = get_default_manager_plan(query)
    plan.update(
        {
            "intent": intent,
            "user_goal": query,
            "selected_agents": _agents_for_intent(intent),
            "tool_plan": _tools_for_intent(intent),
            "need_clarification": intent in ["cashflow_check", "promotion_or_purchase_planning"],
            "clarifying_questions": [],
            "response_strategy": "fallback_to_local_workflow",
            "safety_notes": [get_agent_safety_note()],
        }
    )
    if intent == "cashflow_check":
        plan["clarifying_questions"] = [
            "当前企业账户真实可用余额是多少？",
            "未来 30 天是否有确定客户回款？",
        ]
    elif intent == "promotion_or_purchase_planning":
        plan["clarifying_questions"] = [
            "计划投入金额是多少？",
            "这笔支出是否可以延期或分阶段执行？",
        ]
    return validate_manager_plan(plan)


def build_fallback_specialist_result(user_query: str | None, agent_name: str) -> dict:
    """
    Build a fallback Specialist Agent result.
    """
    result = get_default_specialist_result(agent_name)
    if agent_name == CASHFLOW_AGENT:
        result.update(
            {
                "summary": "当前真实 Cashflow Agent API 未启用，建议在 Agent 工作台查看现金流分析结果。",
                "findings": ["现金流风险需要结合交易、发票和补充余额信息判断。"],
                "risks": ["如果真实余额和未来回款未知，现金流判断可能不完整。"],
                "recommended_actions": ["确认真实余额。", "确认未来回款。", "核查近期到期发票。"],
                "needs_user_input": True,
                "questions": ["当前账户真实余额是多少？", "未来 30 天是否有确定回款？"],
            }
        )
    elif agent_name == ANOMALY_AGENT:
        result.update(
            {
                "summary": "当前真实 Anomaly Agent API 未启用，建议查看规则异常和 LOF 模型异常。",
                "findings": ["系统可基于规则和模型识别潜在异常支出。"],
                "risks": ["模型高风险不等于事实异常，需要结合凭证和业务背景核查。"],
                "recommended_actions": ["核查高风险交易。", "确认是否重复付款。", "补充常用供应商名单。"],
                "needs_user_input": True,
                "questions": ["是否存在已知正常的大额付款？", "相关商户是否为固定供应商？"],
            }
        )
    elif agent_name == PLANNING_AGENT:
        result.update(
            {
                "summary": "当前真实 Planning Agent API 未启用，建议结合现金流、目标和行动项谨慎判断。",
                "findings": ["经营计划需要结合现金流和目标缺口。"],
                "risks": ["促销或采购可能增加现金流压力。"],
                "recommended_actions": ["确认预算。", "确认预期收入。", "确认采购需求和现金缓冲。"],
                "needs_user_input": True,
                "questions": ["预计新增收入是多少？", "是否需要提前采购？"],
            }
        )
    elif agent_name == REPORT_AGENT:
        result.update(
            {
                "summary": "当前真实 Report Agent API 未启用，可以先使用 Agent 工作流报告。",
                "findings": ["本地 workflow 已记录任务规划、工具结果、行动项和进展。"],
                "risks": ["报告基于上传数据和用户补充信息，可能不完整。"],
                "recommended_actions": ["查看报告中心中的 Agent 工作流报告。"],
                "needs_user_input": True,
                "questions": ["是否还有未上传的重要发票、应收款或固定支出？"],
            }
        )
    else:
        result["summary"] = "当前真实 Specialist Agent API 未启用，系统使用本地规则化能力。"
    result["safety_note"] = get_agent_safety_note()
    return validate_specialist_result(result, agent_name=agent_name)


def _fallback_answer_for_intent(intent: str) -> str:
    if intent == "cashflow_check":
        return (
            "我会优先检查预算、发票、现金流和异常支出。目前真实 Agent API 未启用，"
            "因此先使用本地规则化工作流。你可以在 Agent 工作台选择“检查未来 30 天现金流是否安全”查看完整过程。"
        )
    if intent == "expense_anomaly_review":
        return (
            "我会结合规则异常和 LOF 模型结果，找出最值得核查的支出。目前真实 Agent API 未启用，"
            "因此先使用本地规则化工作流。你可以在 Agent 工作台选择“处理本月最可疑的异常支出”。"
        )
    if intent in ["goal_or_budget_planning", "promotion_or_purchase_planning"]:
        return (
            "我会检查现金流、财务目标和行动项，帮助你评估当前计划是否稳妥。目前真实 Agent API 未启用，"
            "因此先使用本地规则化工作流。后续版本将由 Planning Agent 生成更完整的方案比较。"
        )
    if intent == "invoice_or_payment_review":
        return (
            "我会优先整理发票、收款、付款和现金流压力。目前真实 Agent API 未启用，"
            "因此先使用本地规则化工作流。你可以查看财务分析中的“发票与现金流”。"
        )
    return (
        "我可以帮助你检查现金流、异常支出、发票压力和财务目标。目前真实 Agent API 未启用，"
        "因此先使用本地规则化能力。"
    )


def build_fallback_agent_response(user_query: str | None, reason: str = "") -> dict:
    """
    Build a complete fallback Agent response.
    """
    query = user_query or ""
    manager_plan = build_fallback_manager_plan(query)
    intent = manager_plan["intent"]
    agent_outputs = {
        agent_name: build_fallback_specialist_result(query, agent_name)
        for agent_name in manager_plan.get("selected_agents", [])
    }
    response = get_default_agent_response(user_query=query, mode="fallback")
    response.update(
        {
            "manager_plan": manager_plan,
            "agent_outputs": agent_outputs,
            "final_answer": sanitize_agent_text(_fallback_answer_for_intent(intent)),
            "suggested_actions": [
                action
                for output in agent_outputs.values()
                for action in output.get("recommended_actions", [])
            ],
            "clarifying_questions": manager_plan.get("clarifying_questions", []),
            "safety_note": get_agent_safety_note(),
            "errors": [reason] if reason else [],
        }
    )
    return response
