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
    query = (user_query or "").lower()
    zh_cashflow = ["\u73b0\u91d1\u6d41", "\u94b1\u591f", "\u4f59\u989d", "\u591f\u4e0d\u591f"]
    zh_anomaly = ["\u5f02\u5e38", "\u53ef\u7591", "\u652f\u51fa", "\u91cd\u590d"]
    zh_purchase = ["\u4fc3\u9500", "\u8fdb\u8d27", "\u91c7\u8d2d"]
    zh_goal = ["\u76ee\u6807", "\u9884\u7b97", "\u8ba1\u5212"]
    zh_invoice = ["\u53d1\u7968", "\u6536\u6b3e", "\u4ed8\u6b3e", "\u6b20\u6b3e"]
    zh_report = ["\u603b\u7ed3"]
    if any(keyword in query for keyword in ["cash flow", "cashflow", "balance", "runway", "enough cash", "cash", *zh_cashflow]):
        return "cashflow_check"
    if any(keyword in query for keyword in ["suspicious", "expense", "anomaly", "duplicate", "unusual", *zh_anomaly]):
        return "expense_anomaly_review"
    if any(keyword in query for keyword in ["promotion", "purchase", "procurement", "inventory", *zh_purchase]):
        return "promotion_or_purchase_planning"
    if any(keyword in query for keyword in ["goal", "budget", "plan", *zh_goal]):
        return "goal_or_budget_planning"
    if any(keyword in query for keyword in ["invoice", "payment", "receivable", "payable", "collect", *zh_invoice]):
        return "invoice_or_payment_review"
    if any(keyword in query for keyword in ["reports", "report", "overview", "summary", *zh_report]):
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
            "What is the current available cash balance?",
            "Are there confirmed customer collections in the next 30 days?",
        ]
    elif intent == "promotion_or_purchase_planning":
        plan["clarifying_questions"] = [
            "How much do you plan to spend?",
            "Can this expense be delayed or split into phases?",
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
                "summary": "The live Cashflow Agent API is unavailable. Use the fallback cash-flow analysis for a first-pass review.",
                "findings": ["Cash-flow risk should be interpreted using transactions, invoices, and confirmed balance information."],
                "risks": ["If real cash balance and expected collections are unknown, the cash-flow view may be incomplete."],
                "recommended_actions": ["Confirm real cash balance.", "Confirm upcoming collections.", "Review invoices due soon."],
                "needs_user_input": True,
                "questions": ["What is the real account balance?", "Are there confirmed collections in the next 30 days?"],
            }
        )
    elif agent_name == ANOMALY_AGENT:
        result.update(
            {
                "summary": "The live Anomaly Agent API is unavailable. Review rule-based anomalies and LOF model flags.",
                "findings": ["The system can identify potentially suspicious expenses using rules and model signals."],
                "risks": ["A high model-risk score does not prove a transaction is abnormal; review receipts and business context."],
                "recommended_actions": ["Review high-risk transactions.", "Check for duplicate payments.", "Add known suppliers."],
                "needs_user_input": True,
                "questions": ["Are there known normal large payments?", "Is the merchant a regular supplier?"],
            }
        )
    elif agent_name == PLANNING_AGENT:
        result.update(
            {
                "summary": "The live Planning Agent API is unavailable. Interpret the plan using cash flow, goals, and action items.",
                "findings": ["Business planning should consider cash-flow pressure and goal gaps."],
                "risks": ["Promotions or purchases may increase cash-flow pressure."],
                "recommended_actions": ["Confirm the budget.", "Confirm expected revenue.", "Confirm purchase needs and cash buffer."],
                "needs_user_input": True,
                "questions": ["What additional revenue is expected?", "Is early purchasing required?"],
            }
        )
    elif agent_name == REPORT_AGENT:
        result.update(
            {
                "summary": "The live Report Agent API is unavailable. Use the workflow report as a fallback report.",
                "findings": ["The local workflow records task planning, tool results, action items, and progress."],
                "risks": ["Reports are based on uploaded data and user-provided context, so they may be incomplete."],
                "recommended_actions": ["Review the Agent workflow report in Reports."],
                "needs_user_input": True,
                "questions": ["Are there important invoices, receivables, or fixed expenses not yet uploaded?"],
            }
        )
    else:
        result["summary"] = "The live Specialist Agent API is unavailable. The system is using local fallback logic."
    result["safety_note"] = get_agent_safety_note()
    return validate_specialist_result(result, agent_name=agent_name)


def _fallback_answer_for_intent(intent: str) -> str:
    if intent == "cashflow_check":
        return (
            "I will first review budget, invoices, cash flow, and suspicious expenses. "
            "The live Agent API is unavailable, so FinCopilot is using the local fallback workflow."
        )
    if intent == "expense_anomaly_review":
        return (
            "I will use rule-based anomalies and LOF model signals to identify expenses that deserve review. "
            "The live Agent API is unavailable, so FinCopilot is using the local fallback workflow."
        )
    if intent in ["goal_or_budget_planning", "promotion_or_purchase_planning"]:
        return (
            "I will review cash flow, goals, and action items to help assess the plan. "
            "The live Agent API is unavailable, so FinCopilot is using the local fallback workflow."
        )
    if intent == "invoice_or_payment_review":
        return (
            "I will prioritize invoices, collections, payments, and cash-flow pressure. "
            "The live Agent API is unavailable, so FinCopilot is using the local fallback workflow."
        )
    return (
        "I can help review cash flow, suspicious expenses, invoice pressure, and goals. "
        "The live Agent API is unavailable, so FinCopilot is using local fallback logic."
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
