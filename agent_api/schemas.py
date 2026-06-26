MANAGER_AGENT = "manager_agent"
CASHFLOW_AGENT = "cashflow_agent"
ANOMALY_AGENT = "anomaly_agent"
PLANNING_AGENT = "planning_agent"
REPORT_AGENT = "report_agent"
SAFETY_AGENT = "safety_agent"
UNKNOWN_AGENT = "unknown_agent"

SUPPORTED_AGENTS = [
    MANAGER_AGENT,
    CASHFLOW_AGENT,
    ANOMALY_AGENT,
    PLANNING_AGENT,
    REPORT_AGENT,
    SAFETY_AGENT,
]

SUPPORTED_SPECIALIST_AGENTS = [
    CASHFLOW_AGENT,
    ANOMALY_AGENT,
    PLANNING_AGENT,
    REPORT_AGENT,
]

SUPPORTED_AGENT_NAMES = SUPPORTED_AGENTS

SUPPORTED_INTENTS = [
    "cashflow_check",
    "expense_anomaly_review",
    "goal_or_budget_planning",
    "promotion_or_purchase_planning",
    "invoice_or_payment_review",
    "general_finance_summary",
    "unknown",
]

INTENT_TO_DEFAULT_AGENTS = {
    "cashflow_check": [CASHFLOW_AGENT, ANOMALY_AGENT],
    "expense_anomaly_review": [ANOMALY_AGENT],
    "goal_or_budget_planning": [PLANNING_AGENT, CASHFLOW_AGENT],
    "promotion_or_purchase_planning": [PLANNING_AGENT, CASHFLOW_AGENT],
    "invoice_or_payment_review": [CASHFLOW_AGENT],
    "general_finance_summary": [REPORT_AGENT],
    "unknown": [REPORT_AGENT],
}

INTENT_TO_DEFAULT_TOOLS = {
    "cashflow_check": [
        "get_cashflow_summary",
        "get_invoice_summary",
        "get_action_summary",
    ],
    "expense_anomaly_review": ["get_anomaly_summary", "get_action_summary"],
    "goal_or_budget_planning": [
        "get_goal_summary",
        "get_cashflow_summary",
        "get_action_summary",
    ],
    "promotion_or_purchase_planning": [
        "get_cashflow_summary",
        "get_goal_summary",
        "get_action_summary",
    ],
    "invoice_or_payment_review": ["get_invoice_summary", "get_cashflow_summary"],
    "general_finance_summary": [
        "get_budget_summary",
        "get_cashflow_summary",
        "get_action_summary",
    ],
    "unknown": ["get_full_context_summary"],
}


def ensure_list(value) -> list:
    """
    Convert common values into a list safely.
    """
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple) or isinstance(value, set):
        return list(value)
    if isinstance(value, str):
        return [value] if value else []
    return [value]


def normalize_intent(intent: str | None) -> str:
    """
    Normalize intent to supported values.
    """
    if intent in SUPPORTED_INTENTS:
        return intent
    return "unknown"


def normalize_agent_name(agent_name: str | None) -> str:
    """
    Normalize agent names to known agents.
    """
    if agent_name in SUPPORTED_AGENTS:
        return agent_name
    return UNKNOWN_AGENT


def normalize_confidence(confidence: str | None) -> str:
    """
    Normalize confidence to low / medium / high.
    """
    value = str(confidence or "").strip().lower()
    if value in {"low", "medium", "high"}:
        return value
    return "medium"


def get_default_manager_plan(user_query: str = "") -> dict:
    """
    Return a default Manager Plan.
    """
    return {
        "intent": "unknown",
        "user_goal": user_query or "",
        "selected_agents": [],
        "tool_plan": [],
        "need_clarification": False,
        "clarifying_questions": [],
        "response_strategy": "answer_with_fallback",
        "safety_notes": [
            "No investment, tax, legal, or debt-resolution advice.",
        ],
    }


def get_default_specialist_result(agent_name: str, summary: str = "") -> dict:
    """
    Return a default Specialist Agent result.
    """
    return {
        "agent_name": normalize_agent_name(agent_name),
        "summary": summary or "",
        "findings": [],
        "risks": [],
        "recommended_actions": [],
        "needs_user_input": False,
        "questions": [],
        "confidence": "medium",
        "safety_note": "For financial organization and risk reminders only. Not professional advice.",
    }


def get_default_agent_response(user_query: str = "", mode: str = "fallback") -> dict:
    """
    Return a default final Agent response.
    """
    return {
        "mode": mode if mode in ["api_agent", "fallback"] else "fallback",
        "user_query": user_query or "",
        "manager_plan": get_default_manager_plan(user_query),
        "agent_outputs": {},
        "final_answer": "",
        "suggested_actions": [],
        "clarifying_questions": [],
        "safety_note": "For financial organization and risk reminders only. Not professional advice.",
        "errors": [],
    }


def validate_manager_plan(plan: dict | None) -> dict:
    """
    Validate and complete a Manager Plan.
    """
    default_plan = get_default_manager_plan()
    if not isinstance(plan, dict):
        return default_plan

    merged = {**default_plan, **plan}
    merged["intent"] = normalize_intent(merged.get("intent"))
    merged["user_goal"] = str(merged.get("user_goal") or "")
    merged["selected_agents"] = [
        normalize_agent_name(agent)
        for agent in ensure_list(merged.get("selected_agents"))
    ]
    merged["selected_agents"] = [
        agent
        for agent in merged["selected_agents"]
        if agent in SUPPORTED_SPECIALIST_AGENTS
    ]
    if not merged["selected_agents"]:
        merged["selected_agents"] = INTENT_TO_DEFAULT_AGENTS.get(
            merged["intent"],
            INTENT_TO_DEFAULT_AGENTS["unknown"],
        )
    from agent_api.tool_schemas import validate_tool_name

    merged["tool_plan"] = [
        str(item)
        for item in ensure_list(merged.get("tool_plan"))
        if validate_tool_name(str(item))
    ]
    if not merged["tool_plan"]:
        merged["tool_plan"] = INTENT_TO_DEFAULT_TOOLS.get(
            merged["intent"],
            INTENT_TO_DEFAULT_TOOLS["unknown"],
        )
    merged["need_clarification"] = bool(merged.get("need_clarification"))
    merged["clarifying_questions"] = [
        str(item) for item in ensure_list(merged.get("clarifying_questions"))
    ]
    merged["response_strategy"] = str(
        merged.get("response_strategy") or "answer_with_fallback"
    )
    merged["safety_notes"] = [str(item) for item in ensure_list(merged.get("safety_notes"))]
    return merged


def validate_specialist_result(result: dict | None, agent_name: str = UNKNOWN_AGENT) -> dict:
    """
    Validate and complete a Specialist Agent result.
    """
    default_result = get_default_specialist_result(agent_name)
    if not isinstance(result, dict):
        return default_result

    merged = {**default_result, **result}
    merged["agent_name"] = normalize_agent_name(merged.get("agent_name") or agent_name)
    merged["summary"] = str(merged.get("summary") or "")
    merged["findings"] = [str(item) for item in ensure_list(merged.get("findings"))]
    merged["risks"] = [str(item) for item in ensure_list(merged.get("risks"))]
    merged["recommended_actions"] = [
        str(item) for item in ensure_list(merged.get("recommended_actions"))
    ]
    merged["needs_user_input"] = bool(merged.get("needs_user_input"))
    merged["questions"] = [str(item) for item in ensure_list(merged.get("questions"))]
    merged["confidence"] = normalize_confidence(merged.get("confidence"))
    merged["safety_note"] = str(merged.get("safety_note") or default_result["safety_note"])
    return merged


def merge_specialist_outputs(specialist_outputs: dict | None) -> dict:
    """
    Merge multiple Specialist Agent outputs into one compact summary.
    """
    summaries = []
    findings = []
    risks = []
    recommended_actions = []
    questions = []
    agents_called = []
    needs_user_input = False
    for agent_name, payload in (specialist_outputs or {}).items():
        result = payload.get("result", payload) if isinstance(payload, dict) else {}
        result = validate_specialist_result(result, agent_name=agent_name)
        agents_called.append(result["agent_name"])
        if result["summary"]:
            summaries.append(result["summary"])
        findings.extend(result.get("findings", []))
        risks.extend(result.get("risks", []))
        recommended_actions.extend(result.get("recommended_actions", []))
        questions.extend(result.get("questions", []))
        needs_user_input = needs_user_input or bool(result.get("needs_user_input"))
    return {
        "summaries": summaries,
        "findings": findings,
        "risks": risks,
        "recommended_actions": recommended_actions,
        "questions": questions,
        "needs_user_input": needs_user_input,
        "agents_called": agents_called,
    }
