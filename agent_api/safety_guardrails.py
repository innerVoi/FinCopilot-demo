from copy import deepcopy

from agent_api.schemas import (
    SUPPORTED_SPECIALIST_AGENTS,
    get_default_agent_response,
    validate_specialist_result,
    validate_manager_plan,
)


PROHIBITED_PATTERNS = [
    "you should buy",
    "investment recommendation",
    "guaranteed profit",
    "guaranteed return",
    "certain profit",
    "certain loss",
    "this is fraud",
    "this is a scam",
    "fraud",
    "scam",
    "illegal",
    "tax evasion",
    "legally speaking",
    "sue",
    "bankruptcy",
    "debt restructuring",
    "automatic payment",
    "automatic transfer",
]

AGENT_SAFETY_NOTE = (
    "This analysis is for financial organization, risk reminders, and educational support only. "
    "It is not investment, tax, legal, debt-resolution, or professional financial advice. "
    "Review source documents before important financial decisions and consult qualified professionals when needed."
)


def get_agent_safety_note() -> str:
    """
    Return the shared Agent safety note.
    """
    return AGENT_SAFETY_NOTE


def detect_policy_risks(text: str | None) -> list[str]:
    """
    Detect simple policy risks with deterministic keyword checks.
    """
    if not text:
        return []
    return [pattern for pattern in PROHIBITED_PATTERNS if pattern in text]


def sanitize_agent_text(text: str | None) -> str:
    """
    Make high-risk text safer and append the shared safety note.
    """
    safe_text = str(text or "")
    replacements = {
        "this is fraud": "this may carry risk and should be reviewed",
        "this is a scam": "this may carry risk and should be reviewed",
        "fraud": "possible risk that needs review",
        "scam": "possible risk that needs review",
        "guaranteed profit": "outcome is uncertain",
        "guaranteed return": "outcome cannot be guaranteed",
        "certain profit": "outcome is uncertain",
        "certain loss": "outcome is uncertain",
        "automatic payment": "handle payment only after human review",
        "automatic transfer": "handle transfer only after human review",
    }
    for source, target in replacements.items():
        safe_text = safe_text.replace(source, target)
    if AGENT_SAFETY_NOTE not in safe_text:
        safe_text = f"{safe_text}\n\n{AGENT_SAFETY_NOTE}".strip()
    return safe_text


def _sanitize_dict_values(data: dict) -> dict:
    sanitized = deepcopy(data)
    for key, value in sanitized.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_agent_text(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_agent_text(item) if isinstance(item, str) else item
                for item in value
            ]
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_dict_values(value)
    return sanitized


def validate_agent_output(output: dict | None) -> dict:
    """
    Validate and sanitize an Agent output payload.
    """
    if not isinstance(output, dict):
        output = get_default_agent_response()

    text_fragments = []
    for value in output.values():
        if isinstance(value, str):
            text_fragments.append(value)
        elif isinstance(value, list):
            text_fragments.extend(str(item) for item in value)
        elif isinstance(value, dict):
            text_fragments.append(str(value))

    risks = detect_policy_risks("\n".join(text_fragments))
    sanitized_output = _sanitize_dict_values(output) if risks else deepcopy(output)
    if "safety_note" in sanitized_output:
        sanitized_output["safety_note"] = AGENT_SAFETY_NOTE
    return {
        "safe": len(risks) == 0,
        "risks": risks,
        "sanitized_output": sanitized_output,
    }


def build_safe_error_response(user_query: str, error_message: str = "") -> dict:
    """
    Build a safe fallback response for API failures.
    """
    response = get_default_agent_response(user_query=user_query, mode="fallback")
    response["final_answer"] = sanitize_agent_text(
        "The Agent API is currently unavailable, so the system has fallen back to local rule-based capability."
    )
    response["safety_note"] = AGENT_SAFETY_NOTE
    if error_message:
        response["errors"] = [str(error_message)]
    return response


def validate_manager_plan_safety(plan: dict | None) -> dict:
    """
    Validate and sanitize a Manager Plan.
    """
    sanitized_plan = validate_manager_plan(plan)
    text_to_check = "\n".join(
        [
            sanitized_plan.get("response_strategy", ""),
            *sanitized_plan.get("clarifying_questions", []),
            *sanitized_plan.get("safety_notes", []),
        ]
    )
    risks = detect_policy_risks(text_to_check)

    sanitized_plan["response_strategy"] = sanitize_agent_text(
        sanitized_plan.get("response_strategy", "answer_with_fallback")
    ).split("\n\n")[0]
    sanitized_plan["clarifying_questions"] = [
        sanitize_agent_text(question).split("\n\n")[0]
        for question in sanitized_plan.get("clarifying_questions", [])
    ]

    if not sanitized_plan.get("safety_notes"):
        sanitized_plan["safety_notes"] = [
            "Use this for financial organization and risk reminders only; do not provide investment, tax, legal, or debt-resolution advice."
        ]
    unknown_agents = [
        agent
        for agent in sanitized_plan.get("selected_agents", [])
        if agent not in SUPPORTED_SPECIALIST_AGENTS
    ]
    if unknown_agents:
        risks.extend([f"unknown_agent:{agent}" for agent in unknown_agents])

    from agent_api.tool_schemas import validate_tool_name

    unknown_tools = [
        tool
        for tool in sanitized_plan.get("tool_plan", [])
        if not validate_tool_name(tool)
    ]
    if unknown_tools:
        risks.extend([f"unknown_tool:{tool}" for tool in unknown_tools])

    sanitized_plan = validate_manager_plan(sanitized_plan)
    return {
        "safe": len(risks) == 0,
        "risks": risks,
        "sanitized_plan": sanitized_plan,
    }


def validate_specialist_result_safety(result: dict | None) -> dict:
    """
    Validate and sanitize a Specialist Agent result.
    """
    sanitized_result = validate_specialist_result(result)
    text_to_check = "\n".join(
        [
            sanitized_result.get("summary", ""),
            *sanitized_result.get("findings", []),
            *sanitized_result.get("risks", []),
            *sanitized_result.get("recommended_actions", []),
            *sanitized_result.get("questions", []),
            sanitized_result.get("safety_note", ""),
        ]
    )
    risks = detect_policy_risks(text_to_check)
    sanitized_result["summary"] = sanitize_agent_text(
        sanitized_result.get("summary", "")
    ).split("\n\n")[0]
    for key in ["findings", "risks", "recommended_actions", "questions"]:
        sanitized_result[key] = [
            sanitize_agent_text(item).split("\n\n")[0]
            for item in sanitized_result.get(key, [])
        ]
    sanitized_result["safety_note"] = AGENT_SAFETY_NOTE
    sanitized_result = validate_specialist_result(
        sanitized_result,
        agent_name=sanitized_result.get("agent_name"),
    )
    return {
        "safe": len(risks) == 0,
        "risks": risks,
        "sanitized_result": sanitized_result,
    }
