import json
import re

from agent_api.config import get_agent_api_status, get_agent_model, is_agent_api_enabled
from agent_api.fallback import build_fallback_manager_plan
from agent_api.openai_client import create_chat_completion_text, get_openai_client, sanitize_openai_error
from agent_api.prompts import build_manager_prompt_with_context, get_agent_prompt
from agent_api.safety_guardrails import validate_manager_plan_safety
from agent_api.schemas import MANAGER_AGENT, validate_manager_plan


def build_manager_agent_messages(user_query: str, context_summary: dict | None = None) -> list[dict]:
    """
    Build messages for the Manager Agent API call.
    """
    system_prompt = (
        f"{get_agent_prompt(MANAGER_AGENT)}\n\n"
        "你必须只输出 JSON，不要输出 Markdown，不要输出解释。"
    )
    user_prompt = build_manager_prompt_with_context(user_query, context_summary)
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def extract_json_from_text(text: str | None) -> dict | None:
    """
    Extract a JSON object from model output.
    """
    if not text:
        return None
    raw_text = text.strip()
    candidates = [raw_text]

    fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
    if fenced_match:
        candidates.insert(0, fenced_match.group(1).strip())

    object_match = re.search(r"(\{.*\})", raw_text, re.DOTALL)
    if object_match:
        candidates.append(object_match.group(1).strip())

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def _fallback_result(user_query: str, errors: list[str], raw_output: str = "") -> dict:
    manager_plan = build_fallback_manager_plan(user_query)
    safety_result = validate_manager_plan_safety(manager_plan)
    return {
        "mode": "fallback",
        "manager_plan": safety_result["sanitized_plan"],
        "raw_output": raw_output,
        "errors": errors + safety_result.get("risks", []),
        "api_status": get_agent_api_status(),
    }


def call_manager_agent_api(user_query: str, context_summary: dict | None = None) -> dict:
    """
    Call the real Manager Agent API when enabled, otherwise return fallback.
    """
    query = user_query or ""
    api_status = get_agent_api_status()
    if not is_agent_api_enabled():
        return _fallback_result(query, [api_status.get("user_message") or api_status["reason"]])

    client = get_openai_client()
    if client is None:
        return _fallback_result(query, ["OpenAI client 不可用。"])

    try:
        raw_output = create_chat_completion_text(
            client=client,
            model=get_agent_model(),
            messages=build_manager_agent_messages(query, context_summary),
        )
    except Exception as error:
        return _fallback_result(query, [f"Manager Agent API 调用失败：{sanitize_openai_error(error)}"])

    print(f'raw_output={raw_output}')
    parsed = extract_json_from_text(raw_output)
    if parsed is None:
        return _fallback_result(query, ["Manager Agent 输出不是合法 JSON。"], raw_output=raw_output)
    
    manager_plan = validate_manager_plan(parsed)
    safety_result = validate_manager_plan_safety(manager_plan)
    return {
        "mode": "api_agent",
        "manager_plan": safety_result["sanitized_plan"],
        "raw_output": raw_output,
        "errors": safety_result.get("risks", []),
        "api_status": api_status,
    }


def get_manager_plan(user_query: str, context_summary: dict | None = None) -> dict:
    """
    Return a safe Manager Plan from API or fallback.
    """
    return call_manager_agent_api(user_query, context_summary)["manager_plan"]


def build_manager_agent_debug_info(result: dict) -> dict:
    """
    Build compact debug information for UI display.
    """
    result = result or {}
    manager_plan = result.get("manager_plan", {}) or {}
    return {
        "mode": result.get("mode", "fallback"),
        "intent": manager_plan.get("intent", "unknown"),
        "selected_agents": manager_plan.get("selected_agents", []),
        "tool_plan": manager_plan.get("tool_plan", []),
        "errors": result.get("errors", []),
        "api_status": result.get("api_status", {}),
    }
