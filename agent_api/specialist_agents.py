from agent_api.config import get_agent_api_status, get_agent_model, is_agent_api_enabled
from agent_api.fallback import build_fallback_specialist_result
from agent_api.manager_agent import extract_json_from_text
from agent_api.openai_client import create_chat_completion_text, get_openai_client, sanitize_openai_error
from agent_api.prompts import build_specialist_prompt_with_context, get_agent_prompt
from agent_api.safety_guardrails import validate_specialist_result_safety
from agent_api.schemas import (
    ANOMALY_AGENT,
    CASHFLOW_AGENT,
    PLANNING_AGENT,
    REPORT_AGENT,
    SUPPORTED_SPECIALIST_AGENTS,
    validate_specialist_result,
)


def get_relevant_context_for_agent(
    agent_name: str,
    context_summary: dict | None,
    manager_plan: dict | None = None,
    tool_results: list[dict] | None = None,
) -> dict:
    """
    Return only the context slices relevant to one Specialist Agent.
    """
    context_summary = context_summary or {}
    base = {
        "manager_plan": manager_plan or {},
        "tool_results": tool_results or [],
    }
    if agent_name == CASHFLOW_AGENT:
        base.update(
            {
                "cashflow_summary": context_summary.get("cashflow_summary", {}),
                "invoice_summary": context_summary.get("invoice_summary", {}),
                "action_summary": context_summary.get("action_summary", {}),
                "progress_summary": context_summary.get("progress_summary", {}),
                "business_context": context_summary.get("business_context", {}),
                "safety_context": context_summary.get("safety_context", {}),
            }
        )
    elif agent_name == ANOMALY_AGENT:
        base.update(
            {
                "anomaly_summary": context_summary.get("anomaly_summary", {}),
                "budget_summary": context_summary.get("budget_summary", {}),
                "action_summary": context_summary.get("action_summary", {}),
                "business_context": context_summary.get("business_context", {}),
                "safety_context": context_summary.get("safety_context", {}),
            }
        )
    elif agent_name == PLANNING_AGENT:
        base.update(
            {
                "goal_summary": context_summary.get("goal_summary", {}),
                "cashflow_summary": context_summary.get("cashflow_summary", {}),
                "budget_summary": context_summary.get("budget_summary", {}),
                "action_summary": context_summary.get("action_summary", {}),
                "progress_summary": context_summary.get("progress_summary", {}),
                "business_context": context_summary.get("business_context", {}),
                "safety_context": context_summary.get("safety_context", {}),
            }
        )
    elif agent_name == REPORT_AGENT:
        base.update(
            {
                "context_summary": context_summary,
                "business_context": context_summary.get("business_context", {}),
                "safety_context": context_summary.get("safety_context", {}),
            }
        )
    return base


def build_specialist_agent_messages(
    agent_name: str,
    user_query: str,
    manager_plan: dict | None = None,
    context_summary: dict | None = None,
    tool_results: list[dict] | None = None,
) -> list[dict]:
    """
    Build Specialist Agent messages.
    """
    relevant_context = get_relevant_context_for_agent(
        agent_name,
        context_summary,
        manager_plan=manager_plan,
        tool_results=tool_results,
    )
    user_prompt = build_specialist_prompt_with_context(
        agent_name,
        user_query,
        manager_plan=manager_plan,
        context_summary=relevant_context,
    )
    return [
        {
            "role": "system",
            "content": f"{get_agent_prompt(agent_name)}\n\nYou must output JSON only. Do not output Markdown.",
        },
        {"role": "user", "content": user_prompt},
    ]


def extract_specialist_json_from_text(text: str | None) -> dict | None:
    """
    Extract Specialist Agent JSON output.
    """
    return extract_json_from_text(text)


def _fallback_specialist_result(agent_name: str, user_query: str, errors: list[str], raw_output: str = "") -> dict:
    result = build_fallback_specialist_result(user_query, agent_name)
    safety_result = validate_specialist_result_safety(result)
    return {
        "mode": "fallback",
        "agent_name": agent_name,
        "result": safety_result["sanitized_result"],
        "raw_output": raw_output,
        "errors": errors + safety_result.get("risks", []),
        "api_status": get_agent_api_status(),
    }


def call_specialist_agent_api(
    agent_name: str,
    user_query: str,
    manager_plan: dict | None = None,
    context_summary: dict | None = None,
    tool_results: list[dict] | None = None,
) -> dict:
    """
    Call one Specialist Agent API or fallback.
    """
    if agent_name not in SUPPORTED_SPECIALIST_AGENTS:
        return _fallback_specialist_result(agent_name, user_query, [f"Unsupported specialist agent: {agent_name}"])

    api_status = get_agent_api_status()
    if not is_agent_api_enabled():
        return _fallback_specialist_result(
            agent_name,
            user_query,
            [api_status.get("user_message") or api_status["reason"]],
        )

    client = get_openai_client()
    if client is None:
        return _fallback_specialist_result(agent_name, user_query, ["OpenAI client is unavailable."])

    try:
        raw_output = create_chat_completion_text(
            client=client,
            model=get_agent_model(),
            messages=build_specialist_agent_messages(
                agent_name,
                user_query,
                manager_plan=manager_plan,
                context_summary=context_summary,
                tool_results=tool_results,
            ),
        )
    except Exception as error:
        return _fallback_specialist_result(
            agent_name,
            user_query,
            [f"Specialist Agent API call failed: {sanitize_openai_error(error)}"],
        )

    parsed = extract_specialist_json_from_text(raw_output)
    if parsed is None:
        return _fallback_specialist_result(agent_name, user_query, ["Specialist Agent output is not valid JSON."], raw_output)

    result = validate_specialist_result(parsed, agent_name=agent_name)
    safety_result = validate_specialist_result_safety(result)
    return {
        "mode": "api_agent",
        "agent_name": agent_name,
        "result": safety_result["sanitized_result"],
        "raw_output": raw_output,
        "errors": safety_result.get("risks", []),
        "api_status": api_status,
    }


def call_selected_specialist_agents(
    user_query: str,
    manager_plan: dict,
    context_summary: dict | None = None,
    tool_results: list[dict] | None = None,
) -> dict:
    """
    Call all Specialist Agents selected by Manager Plan.
    """
    outputs = {}
    for agent_name in manager_plan.get("selected_agents", []) or []:
        if agent_name not in SUPPORTED_SPECIALIST_AGENTS:
            continue
        outputs[agent_name] = call_specialist_agent_api(
            agent_name,
            user_query,
            manager_plan=manager_plan,
            context_summary=context_summary,
            tool_results=tool_results,
        )
    if REPORT_AGENT not in outputs:
        outputs[REPORT_AGENT] = call_specialist_agent_api(
            REPORT_AGENT,
            user_query,
            manager_plan=manager_plan,
            context_summary=context_summary,
            tool_results=tool_results,
        )
    return outputs


def build_specialist_agents_debug_info(specialist_outputs: dict) -> dict:
    """
    Build compact debug info for Specialist Agents.
    """
    specialist_outputs = specialist_outputs or {}
    return {
        "agents_called": list(specialist_outputs.keys()),
        "modes": {
            agent_name: payload.get("mode", "fallback")
            for agent_name, payload in specialist_outputs.items()
        },
        "errors": {
            agent_name: payload.get("errors", [])
            for agent_name, payload in specialist_outputs.items()
        },
    }
